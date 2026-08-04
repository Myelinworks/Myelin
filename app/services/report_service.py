"""Read-through assembly for `GET /quarters/{id}/report` -- the Phase 9 student-facing report.

Same discipline as `quarter_run_service.py`'s read paths: never recompute, only reconstruct
already-persisted data and hand it to the pure `build_quarter_report`. The lock (`run_quarter`) is
the only place anything is computed; this module's only job is loading what it already wrote.

Three pieces need reconstruction rather than a straight column read, and each is documented at its
own function below: `QuarterResult` (the existing generic `_from_jsonable` round-trip),
`QuarterScore` (partially persisted -- two scalar sums are re-derived by summation, never by
re-scoring), and category-aggregated evidence (queried rows converted to `EvidenceFact`, then fed
through the exact same pure `aggregate_by_category` `engines/evidence.py` already exports and
tests -- "aggregation exists and is queryable" per Phase 9's Item 0 is what this function proves).
"""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engines.evidence import EvidenceFact, aggregate_by_category
from app.engines.quarter import QuarterResult
from app.engines.report import QuarterReport, RunSummary, ScoreTrajectoryPoint, build_quarter_report
from app.engines.scoring import ModifierOutcome, QuarterScore, TraitScore
from app.engines.survival import SurvivalOutcome, is_terminal
from app.models.company import Company
from app.models.evidence import EvidenceRecord
from app.models.quarter import Quarter, QuarterStatus
from app.models.quarter_performance import QuarterPerformance
from app.services.quarter_run_service import _from_jsonable

ZERO = Decimal(0)


class QuarterNotLockedError(Exception):
    """Raised when a report is requested for a quarter that hasn't been locked yet -- there is no
    report before `run_quarter()` has run. The route maps this to 409, matching `routes/deps.py`'s
    existing convention for "wrong quarter-lock state" (`get_open_quarter`'s 409 on a locked
    quarter is the mirror image of this one)."""

    def __init__(self, quarter_id: uuid.UUID):
        self.quarter_id = quarter_id
        super().__init__(f"quarter {quarter_id} has not been locked yet -- no report exists")


def _reconstruct_score(performance: QuarterPerformance) -> QuarterScore:
    """`QuarterPerformance` never persists the full `QuarterScore` object -- only `ceo_score`,
    `score_band`, `trait_points` and `modifiers_applied` (`quarter_run_service.py::run_quarter`).
    `mechanical_points_available`/`unscored_points`/`trait_points_earned`/`modifier_points`/
    `raw_score` are re-derived here by summing numbers already present in `trait_points`/
    `modifiers_applied` -- the same sums `score_quarter` itself computes, never a re-score.
    """
    traits = tuple(_from_jsonable(TraitScore, t) for t in performance.trait_points)
    modifiers = tuple(_from_jsonable(ModifierOutcome, m) for m in performance.modifiers_applied)

    mechanical_points_available = sum((t.weight_scored for t in traits), start=ZERO)
    unscored_points = sum((t.weight for t in traits), start=ZERO) - mechanical_points_available
    trait_points_earned = sum((t.points_earned for t in traits), start=ZERO)
    modifier_points = sum((m.applied_points for m in modifiers), start=ZERO)

    return QuarterScore(
        traits=traits,
        modifiers=modifiers,
        mechanical_points_available=mechanical_points_available,
        unscored_points=unscored_points,
        trait_points_earned=trait_points_earned,
        modifier_points=modifier_points,
        raw_score=trait_points_earned + modifier_points,
        normalised_score=performance.ceo_score,
        band=performance.score_band,
    )


def _evidence_fact_from_record(row: EvidenceRecord) -> EvidenceFact:
    return EvidenceFact(
        department=row.department,
        evidence_key=row.evidence_key,
        value=row.evidence_value,
        categories=tuple(row.categories),
        detail=row.detail or "",
        weight=row.weight,
        weight_status=row.weight_status or "",
    )


async def _aggregated_evidence(session: AsyncSession, quarter_id: uuid.UUID) -> dict[str, tuple[EvidenceFact, ...]]:
    """Queries this quarter's Phase 8 producer rows (`decision_id IS NULL` -- the legacy
    per-decision pipeline's rows are a different system) and aggregates them by cognitive-dimension
    category via the pure `aggregate_by_category`, never a re-implementation of that grouping."""
    rows = (
        await session.execute(
            select(EvidenceRecord).where(EvidenceRecord.quarter_id == quarter_id, EvidenceRecord.decision_id.is_(None))
        )
    ).scalars().all()
    facts = tuple(_evidence_fact_from_record(row) for row in rows)
    return aggregate_by_category(facts)


async def _prior_result(session: AsyncSession, quarter: Quarter) -> QuarterResult | None:
    if quarter.number == 1:
        return None
    prior = (
        await session.execute(
            select(Quarter).where(Quarter.company_id == quarter.company_id, Quarter.number == quarter.number - 1)
        )
    ).scalar_one_or_none()
    if prior is None:
        return None
    prior_performance = (
        await session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == prior.id))
    ).scalar_one_or_none()
    if prior_performance is None or prior_performance.engine_result is None:
        return None
    return _from_jsonable(QuarterResult, prior_performance.engine_result)


async def _run_summary(session: AsyncSession, company: Company, result: QuarterResult) -> RunSummary | None:
    """Only attached once the run has reached a terminal status. Just the aggregation of quarters
    that already exist -- no Q4 endgame content (Phase 11, blocked)."""
    if not is_terminal(company.run_status):
        return None

    rows = (
        await session.execute(
            select(QuarterPerformance.ceo_score, QuarterPerformance.score_band, Quarter.number)
            .join(Quarter, Quarter.id == QuarterPerformance.quarter_id)
            .where(QuarterPerformance.company_id == company.id, QuarterPerformance.ceo_score.is_not(None))
            .order_by(Quarter.number)
        )
    ).all()
    trajectory = tuple(
        ScoreTrajectoryPoint(quarter_number=number, ceo_score=ceo_score, band=band)
        for ceo_score, band, number in rows
    )
    return RunSummary(
        score_trajectory=trajectory,
        final_valuation_inr=result.valuation.blended_inr,
        terminal_status=company.run_status,
    )


async def build_report_for_quarter(session: AsyncSession, quarter_id: uuid.UUID) -> QuarterReport:
    """Loads every already-persisted piece a locked quarter needs and assembles the report --
    idempotent, never mutates, raises `QuarterNotLockedError` for a quarter that isn't locked yet.
    """
    quarter = await session.get(Quarter, quarter_id)
    if quarter is None:
        raise QuarterNotLockedError(quarter_id)

    performance = (
        await session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == quarter_id))
    ).scalar_one_or_none()
    if quarter.status != QuarterStatus.CLOSED or performance is None or performance.engine_result is None:
        raise QuarterNotLockedError(quarter_id)

    company = await session.get(Company, quarter.company_id)

    result = _from_jsonable(QuarterResult, performance.engine_result)
    score = _reconstruct_score(performance)
    evidence = await _aggregated_evidence(session, quarter_id)
    prior_result = await _prior_result(session, quarter)
    survival = SurvivalOutcome(
        status=company.run_status, triggered_by=company.survival_condition, detail=company.survival_detail
    )
    run_summary = await _run_summary(session, company, result)

    return build_quarter_report(
        company_id=company.id,
        quarter_id=quarter.id,
        quarter_number=quarter.number,
        run_status=company.run_status,
        result=result,
        score=score,
        evidence=evidence,
        survival=survival,
        prior_result=prior_result,
        run_summary=run_summary,
    )

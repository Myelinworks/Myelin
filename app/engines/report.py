"""`build_quarter_report` -- the Phase 9 student-facing report assembler.

Pure: no I/O, no DB session, no clock, no RNG, same discipline as every other `engines/` module.
It computes nothing new -- no scoring, no business-impact math, no evidence extraction. Every
number it renders already exists on one of its inputs; the only arithmetic here is presentation-
layer reshaping of numbers already given (a delta between two already-computed quarters, a ratio
of two already-computed fields), never a new coefficient, never a config lookup, never a formula
that isn't already validated elsewhere.

**Deliberately does not accept ORM models.** The phase spec's signature names `company: Company`
and `quarter: Quarter`, but every other pure engine in this codebase (`compute_quarter`,
`score_quarter`, `evaluate_survival`, `extract_evidence`) takes plain dataclasses/scalars, never a
SQLAlchemy model -- importing one here would be the one `engines/` module coupled to the ORM.
Callers (the report service) unpack the scalars they need (`company.id`, `company.run_status`,
`quarter.id`, `quarter.number`) before calling in. Same kind of narrow, documented deviation
`engines/scoring.py`'s module docstring makes for `prior_allocations`.

**Two sections are kept structurally separate on purpose** (`docs/02`'s dual-pipeline thesis):
`CompanyOutcome`/`BindingConstraint` answer "what happened to the company," `DecisionQuality`
answers "how good were these decisions." `DecisionQuality` is built from `score: QuarterScore`
alone and never reads `result: QuarterResult` -- a student must never be able to read the report as
"you made money, therefore you scored well."

**The score is honest about its own incompleteness.** Phase 7 established that only 6 of 21
sub-criteria are `MECHANICAL`; the rest are `JUDGMENT` and come back `UNSCORED`. `DecisionQuality`
renders those as `unscored_criteria` with their stated reason, never as a zero (a zero would read
as a failure the student didn't earn) and never silently dropped.
"""

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.engines.quarter import QuarterResult
from app.engines.scoring import CriterionResult, QuarterScore
from app.engines.survival import RunStatus, SurvivalOutcome

# Re-exported so callers don't need a second import for the type `evidence` is expected in --
# `aggregate_by_category`'s own return type, reused verbatim rather than wrapped in a new type.
AggregatedEvidence = dict[str, tuple[Any, ...]]


@dataclass(frozen=True)
class Metric:
    """One outcome number plus its quarter-over-quarter change. `delta` is `None` when there is no
    prior quarter to compare against -- never `0`, which would misreport "no change" for a number
    that simply has no history yet."""

    value: Decimal
    delta: Decimal | None


@dataclass(frozen=True)
class CompanyOutcome:
    """Section A -- "what happened to the company." Every field traces to `QuarterResult` alone."""

    units_sold: Metric
    revenue_inr: Metric
    cogs_inr: Metric
    gross_profit_inr: Metric
    net_cash_flow_inr: Metric
    closing_cash_inr: Metric
    # `None` (with a reason, never a nonsensical value) when NCF >= 0 this quarter -- "quarters
    # until cash runs out" is undefined with no burn.
    cash_runway_quarters: Metric | None
    cash_runway_gap_reason: str | None
    # `None` exactly when `result.valuation.blended_inr` is `None` -- the existing gap on
    # `Valuation` itself (asset-based inputs not sourced for this company), passed through
    # unchanged, never a new gap invented here.
    valuation_inr: Metric | None
    valuation_gap_reason: str | None


@dataclass(frozen=True)
class BindingConstraint:
    """Section B -- one entry per hard gate that actually bound this quarter (0 to 3 entries).
    `demand_lost` is the same gap `engines/scoring.py`'s zero-waste/ceiling-undershot modifiers
    already compute, reframed as "how much was left on the table" rather than "was it clean"."""

    gate: str  # "sales_capacity" | "conversion_ceiling" | "available_to_sell"
    demand_lost: Decimal
    demand_lost_unit: str  # "leads" | "conversion_points" | "units"
    detail: str


@dataclass(frozen=True)
class ModifierLine:
    id: str
    points: Decimal
    fired: bool
    applied_points: Decimal
    detail: str


@dataclass(frozen=True)
class ScoredCriterion:
    id: str
    trait: str
    result: str
    points: Decimal | None
    detail: str


@dataclass(frozen=True)
class UnscoredCriterion:
    """`reason` is `CriterionScore.detail` for a JUDGMENT criterion -- the `reason` string from
    config (`ScoringCriterion.reason`), never a zero and never hidden."""

    id: str
    trait: str
    reason: str


@dataclass(frozen=True)
class DecisionQuality:
    """Section C -- "how good were these decisions." Built from `score: QuarterScore` only; no
    field here is derived from `QuarterResult`. `ceo_score`/`band` are `QuarterScore`'s
    scoreable-portion-normalised numbers, labelled as such, not presented as the complete rubric.
    """

    ceo_score: Decimal
    band: str
    mechanical_points_available: Decimal
    unscored_points: Decimal
    modifiers: tuple[ModifierLine, ...]
    scored_criteria: tuple[ScoredCriterion, ...]
    unscored_criteria: tuple[UnscoredCriterion, ...]


@dataclass(frozen=True)
class ScoreTrajectoryPoint:
    quarter_number: int
    ceo_score: Decimal
    band: str


@dataclass(frozen=True)
class RunSummary:
    """Attached only when the run has reached a terminal status. Just the aggregation of quarters
    that already exist -- no Q4 endgame content (Momentum Score, tiers, term sheets; Phase 11)."""

    score_trajectory: tuple[ScoreTrajectoryPoint, ...]
    final_valuation_inr: Decimal | None
    terminal_status: RunStatus


@dataclass(frozen=True)
class QuarterReport:
    company_id: uuid.UUID
    quarter_id: uuid.UUID
    quarter_number: int

    outcome: CompanyOutcome
    binding_constraints: tuple[BindingConstraint, ...]
    decision_quality: DecisionQuality
    evidence: AggregatedEvidence

    run_status: RunStatus
    survival_triggered_by: str | None
    survival_detail: str | None

    run_summary: RunSummary | None = None


def _metric(value: Decimal, prior_value: Decimal | None) -> Metric:
    return Metric(value=value, delta=(value - prior_value) if prior_value is not None else None)


def _cash_runway_quarters(result: QuarterResult) -> Decimal | None:
    """`Closing Cash / |Net Cash Flow|`, both already on `QuarterResult` -- the ratio
    `docs/12-quarter-1-reference.md` §10 quotes (Rs 1,18,72,163 / Rs 31,27,837 = 3.8 quarters).
    Undefined (not zero, not infinite) when the quarter didn't burn cash."""
    if result.net_cash_flow_inr >= 0:
        return None
    return result.closing_cash_inr / abs(result.net_cash_flow_inr)


def _cash_runway_metric(result: QuarterResult, prior_result: QuarterResult | None) -> Metric | None:
    current = _cash_runway_quarters(result)
    if current is None:
        return None
    prior = _cash_runway_quarters(prior_result) if prior_result is not None else None
    return Metric(value=current, delta=(current - prior) if prior is not None else None)


def _valuation_metric(result: QuarterResult, prior_result: QuarterResult | None) -> Metric | None:
    current = result.valuation.blended_inr
    if current is None:
        return None
    prior = prior_result.valuation.blended_inr if prior_result is not None else None
    return Metric(value=current, delta=(current - prior) if prior is not None else None)


def _company_outcome(result: QuarterResult, prior_result: QuarterResult | None) -> CompanyOutcome:
    prior = prior_result
    return CompanyOutcome(
        units_sold=_metric(result.units_sold, prior.units_sold if prior else None),
        revenue_inr=_metric(result.revenue_inr, prior.revenue_inr if prior else None),
        cogs_inr=_metric(result.cogs_inr, prior.cogs_inr if prior else None),
        gross_profit_inr=_metric(result.gross_profit_inr, prior.gross_profit_inr if prior else None),
        net_cash_flow_inr=_metric(result.net_cash_flow_inr, prior.net_cash_flow_inr if prior else None),
        closing_cash_inr=_metric(result.closing_cash_inr, prior.closing_cash_inr if prior else None),
        cash_runway_quarters=_cash_runway_metric(result, prior_result),
        cash_runway_gap_reason=(
            None
            if result.net_cash_flow_inr < 0
            else "quarter was cash-flow positive or breakeven -- runway (quarters until cash runs "
            "out at the current burn rate) is not a meaningful figure when there is no burn"
        ),
        valuation_inr=_valuation_metric(result, prior_result),
        valuation_gap_reason=result.valuation.gap_reason,
    )


def binding_constraints(result: QuarterResult) -> tuple[BindingConstraint, ...]:
    """All three gates are checked independently -- more than one can bind in the same quarter
    (Q1 does: Sales Capacity and the Conversion Ceiling both bind), which is exactly what Systems
    Thinking sub-criterion 3 (`engines/scoring.py`) is built to catch. An empty tuple is a
    genuinely good outcome: nothing left demand on the table.

    Public (not `_`-prefixed) because Phase 12's `services/run_service.py` reuses it directly for
    the "binding-gate hint from the prior quarter" on the run-state read -- the same computation,
    not a second implementation of it.
    """
    constraints: list[BindingConstraint] = []

    if result.capacity_bound:
        lost = result.effective_leads - result.effective_sales_capacity
        constraints.append(
            BindingConstraint(
                gate="sales_capacity",
                demand_lost=lost,
                demand_lost_unit="leads",
                detail=(
                    f"Sales Capacity ({result.effective_sales_capacity} effective) bound {lost} "
                    f"leads' worth of demand out of {result.effective_leads} effective leads generated"
                ),
            )
        )
    if result.ceiling_bound:
        lost = result.raw_conversion_pct - result.conversion_ceiling_pct
        constraints.append(
            BindingConstraint(
                gate="conversion_ceiling",
                demand_lost=lost,
                demand_lost_unit="conversion_points",
                detail=(
                    f"the Conversion Ceiling ({result.conversion_ceiling_pct}%) capped {lost} points "
                    f"of raw conversion ({result.raw_conversion_pct}%) -- a build-quality limit, not "
                    f"a demand or capacity limit"
                ),
            )
        )
    if result.supply_bound:
        lost = result.total_units_demanded - result.available_to_sell
        constraints.append(
            BindingConstraint(
                gate="available_to_sell",
                demand_lost=lost,
                demand_lost_unit="units",
                detail=(
                    f"Available to Sell ({result.available_to_sell} units) bound {lost} units of "
                    f"demand out of {result.total_units_demanded} units demanded"
                ),
            )
        )
    return tuple(constraints)


def _decision_quality(score: QuarterScore) -> DecisionQuality:
    modifiers = tuple(
        ModifierLine(id=m.id, points=m.points, fired=m.fired, applied_points=m.applied_points, detail=m.detail)
        for m in score.modifiers
    )
    # CriterionResult is a StrEnum, so this comparison is correct whether `c.result` is a genuine
    # enum member (the normal in-process path, right after `score_quarter` runs) or the plain str
    # it round-trips to through JSON (the report service's reconstruction path) -- StrEnum equality
    # is value-based either way.
    scored_criteria = tuple(
        ScoredCriterion(id=c.id, trait=c.trait, result=str(c.result), points=c.points, detail=c.detail)
        for trait in score.traits
        for c in trait.criteria
        if c.result != CriterionResult.UNSCORED
    )
    unscored_criteria = tuple(
        UnscoredCriterion(id=c.id, trait=c.trait, reason=c.detail)
        for trait in score.traits
        for c in trait.criteria
        if c.result == CriterionResult.UNSCORED
    )
    return DecisionQuality(
        ceo_score=score.normalised_score,
        band=score.band,
        mechanical_points_available=score.mechanical_points_available,
        unscored_points=score.unscored_points,
        modifiers=modifiers,
        scored_criteria=scored_criteria,
        unscored_criteria=unscored_criteria,
    )


def build_quarter_report(
    *,
    company_id: uuid.UUID,
    quarter_id: uuid.UUID,
    quarter_number: int,
    run_status: RunStatus,
    result: QuarterResult,
    score: QuarterScore,
    evidence: AggregatedEvidence,
    survival: SurvivalOutcome,
    prior_result: QuarterResult | None,
    run_summary: RunSummary | None = None,
) -> QuarterReport:
    """Assemble one quarter's report from already-computed pieces. No I/O, no scoring, no
    business-impact math -- if a number isn't already reachable from one of these arguments, it
    does not appear in the output.

    `run_status` is `Company.run_status` (already persisted, and the only source that correctly
    carries `COMPLETED` -- `survival: SurvivalOutcome` never produces it, since Phase 11's endgame
    tiering, not `evaluate_survival`, decides that). `survival` supplies the human-readable
    `triggered_by`/`detail` explanation for DISTRESSED/FAILED.
    """
    return QuarterReport(
        company_id=company_id,
        quarter_id=quarter_id,
        quarter_number=quarter_number,
        outcome=_company_outcome(result, prior_result),
        binding_constraints=binding_constraints(result),
        decision_quality=_decision_quality(score),
        evidence=evidence,
        run_status=run_status,
        survival_triggered_by=survival.triggered_by,
        survival_detail=survival.detail,
        run_summary=run_summary,
    )

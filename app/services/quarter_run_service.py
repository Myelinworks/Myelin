"""Thin persistence wrapper around the pure `compute_quarter()`.

Loads opening state, calls the pure function, writes closing state, returns the result. No
business logic lives here -- every number in the result comes from
`app.engines.quarter.compute_quarter`; this module's only job is loading its inputs from the DB
and persisting its output.

Distinct from `app.services.quarter_engine.run_quarter`, which orchestrates the legacy per-decision
Business Impact / Evidence / Cognitive Scoring pipeline -- a genuinely different system (CLAUDE.md:
"Two pipelines stay independent"), kept and tested, just no longer what `POST /lock` calls.
"""

import hashlib
import json
import types
import uuid
from dataclasses import fields, is_dataclass
from decimal import Decimal
from typing import Any, Union, get_args, get_origin, get_type_hints

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.loader import load_profile, load_scenario, load_seed
from app.config.schema import Scenario
from app.engines.quarter import QuarterResult, compute_quarter
from app.engines.state import CompanyState, QuarterAllocations
from app.engines.survival import RunStatus, SurvivalOutcome, evaluate_survival, tier_assignment_quarter
from app.models.company import Company
from app.models.company_state_snapshot import CompanyStateSnapshot
from app.models.quarter import Quarter, QuarterStatus
from app.models.quarter_allocation import QuarterAllocation
from app.models.quarter_performance import QuarterPerformance

# Mirrors QuarterAllocations' fields exactly (see app/engines/state.py) so a QuarterAllocation
# row converts to the dataclass with no per-field mapping to keep in sync by hand.
_ALLOCATION_FIELDS = (
    "google_ads",
    "meta_ads",
    "social_influencer",
    "content_seo",
    "events_pr",
    "email_marketing",
    "referral",
    "prelaunch_buzz",
    "reps",
    "crm_tools",
    "onboarding",
    "quality_qa",
    "innovation",
    "manufacturing",
    "supplier_qc",
    "logistics",
    "culture_benefits",
    "training_development",
    "cx_team",
    "compliance_legal",
    "financial_planning",
    "audit_prep",
    "warranty_years",
)


# --- Generic dataclass <-> JSON round-trip ---------------------------------------------------
# QuarterResult/Valuation/CompanyState together have 60+ fields, almost all Decimal, several
# nested. Hand-writing a converter per field would silently go stale the next time a field is
# added to the pure engine; walking `dataclasses.fields()` keeps this automatically in sync.


def _to_jsonable(value: Any) -> Any:
    """Decimal -> str (exact, not float-lossy), dataclasses -> dict, recursively."""
    if isinstance(value, Decimal):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: _to_jsonable(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    return value


def _from_jsonable(annotation: Any, value: Any) -> Any:
    if value is None:
        return None
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        non_none = next(a for a in get_args(annotation) if a is not type(None))
        return _from_jsonable(non_none, value)
    if is_dataclass(annotation):
        hints = get_type_hints(annotation)
        return annotation(**{f.name: _from_jsonable(hints[f.name], value[f.name]) for f in fields(annotation)})
    if annotation is Decimal:
        return Decimal(value)
    if origin is dict:
        _, value_type = get_args(annotation)
        return {k: _from_jsonable(value_type, v) for k, v in value.items()}
    return value  # int, str, bool round-trip through JSON as-is


def _result_hash(result_json: dict[str, Any], run_status: RunStatus) -> str:
    """sha256 over the canonical (sorted-key) serialised result -- not Python's `hash()`, which
    is salted per process and would never compare equal across two runs, let alone two processes.

    Run status is hashed alongside the result because it is part of what locking this quarter
    decided: the same numbers can leave a company ACTIVE or DISTRESSED depending on the history
    behind them, and a hash that ignored that would call two different outcomes identical.
    """
    canonical = json.dumps({"result": result_json, "run_status": run_status.value}, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _to_allocations(row: QuarterAllocation | None) -> QuarterAllocations:
    if row is None:
        return QuarterAllocations()
    return QuarterAllocations(**{field: getattr(row, field) for field in _ALLOCATION_FIELDS})


async def _load_opening_state(session: AsyncSession, quarter: Quarter, seed: Any) -> CompanyState:
    if quarter.number == 1:
        return CompanyState.opening(seed)

    prior = (
        await session.execute(
            select(Quarter).where(Quarter.company_id == quarter.company_id, Quarter.number == quarter.number - 1)
        )
    ).scalar_one_or_none()
    if prior is None:
        raise ValueError(
            f"quarter {quarter.id} is quarter {quarter.number} for its company, but no quarter "
            f"{quarter.number - 1} exists to carry state forward from"
        )

    snapshot = (
        await session.execute(select(CompanyStateSnapshot).where(CompanyStateSnapshot.quarter_id == prior.id))
    ).scalar_one_or_none()
    if snapshot is None:
        raise ValueError(f"prior quarter {prior.id} has no closing-state snapshot -- lock it before this one")

    return _from_jsonable(CompanyState, snapshot.state)


async def _prior_results(session: AsyncSession, quarter: Quarter) -> list[QuarterResult]:
    """Every already-locked quarter's result for this company, oldest first.

    Survival needs the whole run, not just the quarter being locked: `buffer_breached` is "at any
    point", and `sustained_decline` counts a streak across quarters.
    """
    rows = (
        (
            await session.execute(
                select(QuarterPerformance.engine_result)
                .join(Quarter, Quarter.id == QuarterPerformance.quarter_id)
                .where(
                    Quarter.company_id == quarter.company_id,
                    Quarter.number < quarter.number,
                    QuarterPerformance.engine_result.isnot(None),
                )
                .order_by(Quarter.number)
            )
        )
        .scalars()
        .all()
    )
    return [_from_jsonable(QuarterResult, row) for row in rows]


def _run_status(outcome: SurvivalOutcome, quarter: Quarter, scenario: Scenario) -> RunStatus:
    """Fold the survival outcome and the scenario's length into one persisted status.

    FAILED wins outright -- a run that ran out of cash on its last quarter did not complete.
    Otherwise reaching `total_quarters` means COMPLETED, which shadows DISTRESSED: both are true,
    but "the run is over" is what gates quarter creation. The distress signal is not lost, because
    `survival_condition` records what fired regardless of the status it ends up under, which is
    what Q4 tiering reads.
    """
    if outcome.status is RunStatus.FAILED:
        return RunStatus.FAILED
    if quarter.number >= scenario.total_quarters:
        return RunStatus.COMPLETED
    return outcome.status


async def run_quarter(session: AsyncSession, quarter_id: uuid.UUID) -> QuarterResult:
    """Run one quarter end to end and persist the result, or return the already-persisted result
    unchanged if this quarter is already locked.

    Idempotent: calling this twice never recomputes, never rewrites, and never duplicates a row --
    every write upserts on `quarter_id` (each of QuarterPerformance and CompanyStateSnapshot is
    already unique on it), and the lock transition plus both writes commit in one transaction.
    """
    quarter = await session.get(Quarter, quarter_id)
    if quarter is None:
        raise ValueError(f"quarter {quarter_id} not found")

    performance = (
        await session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == quarter_id))
    ).scalar_one_or_none()

    if quarter.status == QuarterStatus.CLOSED:
        if performance is None or performance.engine_result is None:
            raise ValueError(
                f"quarter {quarter_id} is locked but has no persisted engine result -- it was "
                "closed by a different pipeline, or before this wrapper computed anything"
            )
        return _from_jsonable(QuarterResult, performance.engine_result)

    company = await session.get(Company, quarter.company_id)
    if company is None:
        raise ValueError(f"quarter {quarter_id} references company {quarter.company_id}, which does not exist")

    seed = load_seed(company.seed_name)
    profile = load_profile(company.profile_name)

    allocation_row = (
        await session.execute(select(QuarterAllocation).where(QuarterAllocation.quarter_id == quarter_id))
    ).scalar_one_or_none()
    allocations = _to_allocations(allocation_row)

    opening_state = await _load_opening_state(session, quarter, seed)

    result = compute_quarter(opening_state, allocations, profile, seed)

    # Survival is evaluated inside this same transaction, over the whole run including the
    # quarter being locked -- so the lock, the result and the status it produced all commit
    # together or not at all.
    scenario = load_scenario(company.scenario_id)
    history = [*await _prior_results(session, quarter), result]
    outcome = evaluate_survival(
        history, profile.survival, tier_assignment_quarter(scenario.total_quarters)
    )
    run_status = _run_status(outcome, quarter, scenario)

    company.run_status = run_status
    company.survival_condition = outcome.triggered_by
    company.survival_detail = outcome.detail

    result_json = _to_jsonable(result)
    state_json = result_json["closing_state"]

    if performance is None:
        performance = QuarterPerformance(company_id=quarter.company_id, quarter_id=quarter_id)
        session.add(performance)
    performance.result_hash = _result_hash(result_json, run_status)
    performance.engine_result = result_json

    snapshot = (
        await session.execute(select(CompanyStateSnapshot).where(CompanyStateSnapshot.quarter_id == quarter_id))
    ).scalar_one_or_none()
    if snapshot is None:
        snapshot = CompanyStateSnapshot(company_id=quarter.company_id, quarter_id=quarter_id, state=state_json)
        session.add(snapshot)
    else:
        snapshot.state = state_json

    quarter.status = QuarterStatus.CLOSED

    await session.commit()
    return result

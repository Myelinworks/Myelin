"""Read-through assembly for `GET .../endgame`, and the upsert behind `POST .../endgame`.

Same discipline as `report_service.py`: the preview never recomputes anything `run_quarter()`
hasn't already persisted for Q1-Q3 -- it loads those results and this company's already-decided
survival status, then hands them to the pure `engines.endgame.build_endgame_preview`. Submitting a
decision is a plain upsert on `company_id`; scoring the decision's outcome only happens later, at
Q4's own lock (`quarter_run_service.py::run_quarter`), never here.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.loader import load_profile, load_scenario
from app.engines import endgame
from app.engines.quarter import QuarterResult
from app.engines.survival import SurvivalOutcome, tier_assignment_quarter
from app.models.company import Company
from app.models.endgame_decision import EndgameDecision
from app.models.quarter import Quarter, QuarterStatus
from app.models.quarter_performance import QuarterPerformance
from app.services.quarter_run_service import _from_jsonable


class EndgameNotReadyError(Exception):
    """Raised when the endgame preview is requested before Q3 has locked -- Tier Assignment and
    every Path A/B figure are derived from Q1-Q3's already-locked results, so there is nothing to
    show yet."""

    def __init__(self, quarter_id: uuid.UUID, detail: str):
        self.quarter_id = quarter_id
        super().__init__(detail)


class NotEndgameQuarterError(Exception):
    """Raised when `.../endgame` is requested against a quarter that isn't the scenario's last
    one -- Q4 is structurally different (docs/16), so there is no endgame to preview or decide for
    Q1-Q3."""

    def __init__(self, quarter_id: uuid.UUID, quarter_number: int, total_quarters: int):
        self.quarter_id = quarter_id
        super().__init__(
            f"quarter {quarter_id} is quarter {quarter_number} of {total_quarters} -- the endgame "
            f"only exists on the scenario's last quarter"
        )


async def _locked_result(session: AsyncSession, company_id: uuid.UUID, number: int) -> QuarterResult | None:
    row = (
        await session.execute(
            select(QuarterPerformance.engine_result)
            .join(Quarter, Quarter.id == QuarterPerformance.quarter_id)
            .where(
                Quarter.company_id == company_id,
                Quarter.number == number,
                QuarterPerformance.engine_result.isnot(None),
            )
        )
    ).scalar_one_or_none()
    return _from_jsonable(QuarterResult, row) if row is not None else None


async def get_endgame_preview(session: AsyncSession, quarter_id: uuid.UUID) -> endgame.EndgamePreview:
    quarter = await session.get(Quarter, quarter_id)
    if quarter is None:
        raise EndgameNotReadyError(quarter_id, f"quarter {quarter_id} not found")

    company = await session.get(Company, quarter.company_id)
    scenario = load_scenario(company.scenario_id)
    if quarter.number != scenario.total_quarters:
        raise NotEndgameQuarterError(quarter_id, quarter.number, scenario.total_quarters)

    profile = load_profile(company.profile_name)
    q3_number = tier_assignment_quarter(scenario.total_quarters)
    q1_result = await _locked_result(session, company.id, 1)
    q2_result = await _locked_result(session, company.id, 2)
    q3_result = await _locked_result(session, company.id, q3_number)
    if q1_result is None or q2_result is None or q3_result is None:
        raise EndgameNotReadyError(
            quarter_id,
            f"quarter {q3_number} (and everything before it) must be locked before the endgame "
            f"can be previewed",
        )

    survival = SurvivalOutcome(
        status=company.run_status, triggered_by=company.survival_condition, detail=company.survival_detail
    )
    return endgame.build_endgame_preview(q1_result, q2_result, q3_result, survival, profile.endgame)


async def submit_endgame_decision(
    session: AsyncSession, quarter: Quarter, path: str, term_sheet_name: str, reasoning: str | None
) -> EndgameDecision:
    if quarter.status == QuarterStatus.CLOSED:
        raise ValueError(f"quarter {quarter.id} is locked; the endgame decision is immutable")

    row = (
        await session.execute(select(EndgameDecision).where(EndgameDecision.company_id == quarter.company_id))
    ).scalar_one_or_none()
    if row is None:
        row = EndgameDecision(company_id=quarter.company_id, quarter_id=quarter.id)
        session.add(row)
    row.path = path
    row.term_sheet_name = term_sheet_name
    row.reasoning = reasoning
    await session.commit()
    await session.refresh(row)
    return row

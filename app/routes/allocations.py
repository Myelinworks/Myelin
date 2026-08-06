"""One POST route per department, each upserting that department's columns onto the quarter's
single QuarterAllocation row. Six calls build up the 22-line spend model, plus a 7th for crisis
response (Phase 10, only meaningful in the quarter a crisis fires) -- not the legacy per-decision
submission flow `routes/_factory.py` serves.

Allocations are pure inputs to `compute_quarter()`; nothing here computes or writes a `*State`
row. Only `run_quarter()` does that, and only once the quarter is locked (see the design-rule
comment in `routes/_factory.py`).
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.engines.run_state import Move
from app.models.quarter import Quarter
from app.models.quarter_allocation import QuarterAllocation
from app.routes.deps import require_quarter_move
from app.schemas.allocation import (
    CrisisAllocationSubmit,
    FinanceAdminAllocationSubmit,
    HrAllocationSubmit,
    MarketingAllocationSubmit,
    OperationsAllocationSubmit,
    QuarterAllocationResponse,
    RndAllocationSubmit,
    SalesAllocationSubmit,
)
from app.schemas.errors import WRITE_RESPONSES

router = APIRouter(prefix="/companies/{company_id}/quarters/{quarter_id}/allocations", tags=["allocations"])


async def _upsert(
    company_id: uuid.UUID, quarter: Quarter, fields: dict[str, Any], session: AsyncSession
) -> QuarterAllocation:
    row = (
        await session.execute(select(QuarterAllocation).where(QuarterAllocation.quarter_id == quarter.id))
    ).scalar_one_or_none()
    if row is None:
        row = QuarterAllocation(company_id=company_id, quarter_id=quarter.id)
        session.add(row)
    for field, value in fields.items():
        setattr(row, field, value)
    await session.commit()
    await session.refresh(row)
    return row


def _add_department_route(department: str, schema: type[BaseModel], move: Move) -> None:
    """A closure per call, not per loop iteration -- `department`/`schema`/`move` are bound as
    this function's own arguments, so each of the 7 calls below gets its own value, not the
    loop's last one (the classic late-binding bug this sidesteps by not looping over a shared
    scope). `move` (Phase 12) is `SUBMIT_ALLOCATION` for the 6 real departments and
    `SUBMIT_CRISIS_ALLOCATION` for crisis -- the single gatekeeper refuses crisis submissions
    outside the scenario's crisis quarter, not just outside an open quarter."""

    is_crisis = department == "crisis"

    @router.post(
        f"/{department}",
        response_model=QuarterAllocationResponse,
        name=f"submit_{department}_allocation",
        responses=WRITE_RESPONSES,
        summary=f"Submit the {department} allocation",
        description=(
            "Upserts the crisis-response fields (price_match_fund, comparison_ads, "
            "retention_offers, emergency_supply_fund, crisis_choice, crisis_choice_d_spend) onto "
            "this quarter's single allocation row. Legal only in the scenario's crisis quarter "
            "(`RunStateResponse.crisis_quarter`) -- submitting it in any other quarter returns "
            "`illegal_move` (409). Evaluated against the opening snapshot only; never mutates "
            "`*State` -- only `POST .../lock` does that."
            if is_crisis
            else f"Upserts the {department} department's spend lines onto this quarter's single "
            "allocation row -- pure input, evaluated only when the quarter locks. Legal only "
            "while this quarter is open (`RunStateResponse.legal_moves` includes "
            "`submit_allocation`); calling it on a locked quarter or before one is open returns "
            "`illegal_move` (409)."
        ),
    )
    async def submit_allocation(
        company_id: uuid.UUID,
        submission: schema,  # type: ignore[valid-type]
        quarter: Quarter = Depends(require_quarter_move(move)),
        session: AsyncSession = Depends(get_db),
    ) -> QuarterAllocation:
        return await _upsert(company_id, quarter, submission.model_dump(), session)


_add_department_route("marketing", MarketingAllocationSubmit, Move.SUBMIT_ALLOCATION)
_add_department_route("sales", SalesAllocationSubmit, Move.SUBMIT_ALLOCATION)
_add_department_route("rnd", RndAllocationSubmit, Move.SUBMIT_ALLOCATION)
_add_department_route("operations", OperationsAllocationSubmit, Move.SUBMIT_ALLOCATION)
_add_department_route("hr", HrAllocationSubmit, Move.SUBMIT_ALLOCATION)
_add_department_route("finance_admin", FinanceAdminAllocationSubmit, Move.SUBMIT_ALLOCATION)
# Not one of the 6 CLAUDE.md departments -- crisis response (Phase 10) is its own category, only
# meaningful in the quarter a crisis fires. Reuses the same upsert-onto-one-row factory unchanged.
_add_department_route("crisis", CrisisAllocationSubmit, Move.SUBMIT_CRISIS_ALLOCATION)

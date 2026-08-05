import uuid
from typing import Callable, Coroutine

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.engines.run_state import Move
from app.models.company import Company
from app.models.modifier import Modifier
from app.models.quarter import Quarter, QuarterStatus
from app.services.run_service import require_move


async def get_quarter(
    company_id: uuid.UUID,
    quarter_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> Quarter:
    """Loads the Quarter regardless of lock state -- for read-only routes (state, report)."""
    quarter = await session.get(Quarter, quarter_id)
    if quarter is None or quarter.company_id != company_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Quarter {quarter_id} not found for company {company_id}")
    return quarter


async def get_open_quarter(quarter: Quarter = Depends(get_quarter)) -> Quarter:
    """Same lookup, plus the immutability guard: decisions are rejected once a quarter is
    locked. Still used by the legacy per-decision pipeline (`routes/_factory.py`) -- the 22-line
    pipeline's own write routes use `require_quarter_move` below instead (Phase 12), which folds
    this same check into the single legal-move gatekeeper alongside crisis-quarter/Q4-only gating.
    """
    if quarter.status == QuarterStatus.CLOSED:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Quarter {quarter.id} is locked; decisions are immutable")
    return quarter


def require_quarter_move(
    move: Move,
) -> Callable[[Quarter, AsyncSession], Coroutine[None, None, Quarter]]:
    """Dependency factory: loads the quarter (regardless of lock state, same as `get_quarter`),
    then consults `engines/run_state.py`'s single gatekeeper for `move` before letting a write
    route proceed. Raises `IllegalMoveError` (mapped to a consistent JSON body by `main.py`'s
    handler) rather than a route-specific 409/404 -- this is what Phase 12 routes writes through
    instead of `get_open_quarter`'s bare lock-state check, so a crisis-only or Q4-only move is
    refused for the right reason, not just "the quarter is locked".
    """

    async def _dependency(
        quarter: Quarter = Depends(get_quarter),
        session: AsyncSession = Depends(get_db),
    ) -> Quarter:
        company = await session.get(Company, quarter.company_id)
        await require_move(session, company, move)
        return quarter

    return _dependency


async def get_quarter_modifiers(quarter_id: uuid.UUID, session: AsyncSession) -> dict[str, float]:
    result = await session.execute(select(Modifier).where(Modifier.quarter_id == quarter_id))
    return {m.modifier_key: m.value for m in result.scalars()}

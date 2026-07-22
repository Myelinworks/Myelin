import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.modifier import Modifier
from app.models.quarter import Quarter, QuarterStatus


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
    locked. The single place this rule lives -- every workspace decision-submission route
    depends on this instead of duplicating the check.
    """
    if quarter.status == QuarterStatus.CLOSED:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Quarter {quarter.id} is locked; decisions are immutable")
    return quarter


async def get_quarter_modifiers(quarter_id: uuid.UUID, session: AsyncSession) -> dict[str, float]:
    result = await session.execute(select(Modifier).where(Modifier.quarter_id == quarter_id))
    return {m.modifier_key: m.value for m in result.scalars()}

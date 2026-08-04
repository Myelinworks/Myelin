import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.quarter import Quarter
from app.models.quarter_performance import QuarterPerformance
from app.routes.deps import get_quarter
from app.schemas.quarter import LeaderboardEntry, LeaderboardResponse, QuarterReportResponse
from app.services.quarter_run_service import run_quarter
from app.services.report_service import QuarterNotLockedError, build_report_for_quarter

router = APIRouter(prefix="/companies/{company_id}", tags=["quarter"])


@router.post("/quarters/{quarter_id}/lock", response_model=QuarterReportResponse)
async def lock_quarter(
    company_id: uuid.UUID,
    quarter: Quarter = Depends(get_quarter),
    session: AsyncSession = Depends(get_db),
) -> QuarterReportResponse:
    """Runs the pure 22-line engine (`compute_quarter`, via `run_quarter`) over this quarter's
    submitted allocations, persists the result, and returns the full Phase 9 report for it.

    Idempotent: `run_quarter` itself is the lock guard -- an already-locked quarter returns its
    persisted result unchanged rather than recomputing or 409ing, so calling this twice is safe.
    """
    await run_quarter(session, quarter.id)
    report = await build_report_for_quarter(session, quarter.id)
    return QuarterReportResponse.model_validate(report)


@router.get("/quarters/{quarter_id}/report", response_model=QuarterReportResponse)
async def get_quarter_report(
    company_id: uuid.UUID,
    quarter: Quarter = Depends(get_quarter),
    session: AsyncSession = Depends(get_db),
) -> QuarterReportResponse:
    """Reads back everything the lock transaction already persisted -- never recomputes, never
    mutates. 409s (matching `routes/deps.py`'s convention for "wrong quarter-lock state") for a
    quarter that hasn't been locked yet: there is no report before the quarter is run.
    """
    try:
        report = await build_report_for_quarter(session, quarter.id)
    except QuarterNotLockedError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return QuarterReportResponse.model_validate(report)


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    company_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> LeaderboardResponse:
    """Reads QuarterPerformance rollups -- never live-aggregates cognitive_scores."""
    rows = (
        await session.execute(
            select(QuarterPerformance, Quarter.number)
            .join(Quarter, Quarter.id == QuarterPerformance.quarter_id)
            .where(QuarterPerformance.company_id == company_id)
            .order_by(Quarter.number)
        )
    ).all()
    entries = [
        LeaderboardEntry(
            company_id=company_id,
            quarter_id=performance.quarter_id,
            quarter_number=number,
            overall_score=performance.overall_score,
        )
        for performance, number in rows
    ]
    return LeaderboardResponse(entries=entries)

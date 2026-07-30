import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.decision import Decision
from app.models.evidence import EvidenceRecord
from app.models.quarter import Quarter
from app.models.quarter_performance import QuarterPerformance
from app.routes.deps import get_quarter
from app.schemas.quarter import LeaderboardEntry, LeaderboardResponse, QuarterReportResponse
from app.services.quarter_run_service import run_quarter

router = APIRouter(prefix="/companies/{company_id}", tags=["quarter"])


async def _report_response(
    company_id: uuid.UUID, quarter: Quarter, performance: QuarterPerformance, session: AsyncSession
) -> QuarterReportResponse:
    decisions_submitted = (
        await session.execute(select(func.count()).select_from(Decision).where(Decision.quarter_id == quarter.id))
    ).scalar_one()
    evidence_records_generated = (
        await session.execute(
            select(func.count()).select_from(EvidenceRecord).where(EvidenceRecord.quarter_id == quarter.id)
        )
    ).scalar_one()

    engine_result = performance.engine_result or {}
    return QuarterReportResponse(
        company_id=company_id,
        quarter_id=quarter.id,
        overall_score=performance.overall_score,
        dimension_scores=performance.dimension_scores,
        decisions_submitted=decisions_submitted,
        evidence_records_generated=evidence_records_generated,
        generated_at=performance.created_at,
        units_sold=engine_result.get("units_sold"),
        revenue_inr=engine_result.get("revenue_inr"),
        net_cash_flow_inr=engine_result.get("net_cash_flow_inr"),
        closing_cash_inr=engine_result.get("closing_cash_inr"),
        result_hash=performance.result_hash,
    )


@router.post("/quarters/{quarter_id}/lock", response_model=QuarterReportResponse)
async def lock_quarter(
    company_id: uuid.UUID,
    quarter: Quarter = Depends(get_quarter),
    session: AsyncSession = Depends(get_db),
) -> QuarterReportResponse:
    """Runs the pure 22-line engine (`compute_quarter`, via `run_quarter`) over this quarter's
    submitted allocations and persists the result.

    Idempotent: `run_quarter` itself is the lock guard -- an already-locked quarter returns its
    persisted result unchanged rather than recomputing or 409ing, so calling this twice is safe.
    """
    await run_quarter(session, quarter.id)

    performance = (
        await session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == quarter.id))
    ).scalar_one()
    return await _report_response(company_id, quarter, performance, session)


@router.get("/quarters/{quarter_id}/report", response_model=QuarterReportResponse)
async def get_quarter_report(
    company_id: uuid.UUID,
    quarter: Quarter = Depends(get_quarter),
    session: AsyncSession = Depends(get_db),
) -> QuarterReportResponse:
    """Reads back the persisted QuarterPerformance row -- does not recompute anything."""
    performance = (
        await session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == quarter.id))
    ).scalar_one_or_none()
    if performance is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Quarter {quarter.id} has not been locked yet -- no report")

    return await _report_response(company_id, quarter, performance, session)


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

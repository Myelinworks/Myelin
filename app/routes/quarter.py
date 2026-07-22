import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.decision import Decision
from app.models.evidence import EvidenceRecord
from app.models.quarter import Quarter, QuarterStatus
from app.models.quarter_performance import QuarterPerformance
from app.routes.deps import get_open_quarter, get_quarter, get_quarter_modifiers
from app.schemas.quarter import LeaderboardEntry, LeaderboardResponse, QuarterReportResponse
from app.services.quarter_engine import run_quarter

router = APIRouter(prefix="/companies/{company_id}", tags=["quarter"])


@router.post("/quarters/{quarter_id}/lock", response_model=QuarterReportResponse)
async def lock_quarter(
    company_id: uuid.UUID,
    quarter: Quarter = Depends(get_open_quarter),
    session: AsyncSession = Depends(get_db),
) -> QuarterReportResponse:
    decisions = list((await session.execute(select(Decision).where(Decision.quarter_id == quarter.id))).scalars())

    prior_quarter = (
        await session.execute(
            select(Quarter).where(Quarter.company_id == company_id, Quarter.number == quarter.number - 1)
        )
    ).scalar_one_or_none()
    prior_evidence: list[EvidenceRecord] = []
    if prior_quarter is not None:
        prior_evidence = list(
            (
                await session.execute(select(EvidenceRecord).where(EvidenceRecord.quarter_id == prior_quarter.id))
            ).scalars()
        )

    modifiers = await get_quarter_modifiers(quarter.id, session)

    result = run_quarter(company_id, quarter.id, decisions, modifiers, prior_quarter_evidence=prior_evidence)

    session.add_all(result.evidence_records)
    session.add_all(result.cognitive_scores)
    session.add(result.quarter_performance)
    quarter.status = QuarterStatus.CLOSED
    await session.commit()
    await session.refresh(result.quarter_performance)

    return QuarterReportResponse(
        company_id=company_id,
        quarter_id=quarter.id,
        overall_score=result.quarter_performance.overall_score,
        dimension_scores=result.quarter_performance.dimension_scores,
        decisions_submitted=len(decisions),
        evidence_records_generated=len(result.evidence_records),
        generated_at=result.quarter_performance.created_at,
    )


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

    decisions_submitted = (
        await session.execute(select(func.count()).select_from(Decision).where(Decision.quarter_id == quarter.id))
    ).scalar_one()
    evidence_records_generated = (
        await session.execute(
            select(func.count()).select_from(EvidenceRecord).where(EvidenceRecord.quarter_id == quarter.id)
        )
    ).scalar_one()

    return QuarterReportResponse(
        company_id=company_id,
        quarter_id=quarter.id,
        overall_score=performance.overall_score,
        dimension_scores=performance.dimension_scores,
        decisions_submitted=decisions_submitted,
        evidence_records_generated=evidence_records_generated,
        generated_at=performance.created_at,
    )


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

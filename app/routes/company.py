"""Company and quarter creation, plus read-through of current state.

The creation routes are the only place a Company, Quarter or Modifier row comes into existence
through the API -- before these, every test had to seed through the ORM and nothing on a
deployed instance could be exercised end to end.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.loader import load_scenario
from app.core.db import get_db
from app.models.company import Company
from app.models.quarter import Quarter
from app.models.quarter_allocation import QuarterAllocation
from app.routes.deps import get_quarter, get_quarter_modifiers
from app.schemas.company import (
    CompanyCreate,
    CompanyDetailResponse,
    CompanyResponse,
    QuarterDetailResponse,
    QuarterSummary,
    ScenarioResponse,
)
from app.services.company_service import ScenarioAssignmentError, create_company, create_quarter

router = APIRouter(tags=["company"])

# Columns on QuarterAllocation that are not Rs-lakh spend lines: bookkeeping, plus the warranty
# choice, which is surfaced as its own integer field rather than as a 23rd "spend line".
_NON_ALLOCATION_COLUMNS = {"id", "company_id", "quarter_id", "created_at", "warranty_years"}


async def _load_company(company_id: uuid.UUID, session: AsyncSession) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Company {company_id} not found")
    return company


def _scenario_response(company: Company) -> ScenarioResponse:
    scenario = load_scenario(company.scenario_id)
    return ScenarioResponse(
        scenario_id=scenario.scenario_id,
        display_name=scenario.display_name,
        total_quarters=scenario.total_quarters,
        crisis_quarter=scenario.crisis_quarter,
    )


@router.post("/companies", response_model=CompanyDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_company_route(
    payload: CompanyCreate,
    session: AsyncSession = Depends(get_db),
) -> CompanyDetailResponse:
    """Create a company on a scenario, assigning one deterministically if none is given."""
    try:
        company = await create_company(
            session, name=payload.name, scenario_id=payload.scenario_id, company_id=payload.company_id
        )
    except (ScenarioAssignmentError, FileNotFoundError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    await session.commit()
    return CompanyDetailResponse(
        id=company.id,
        created_at=company.created_at,
        name=company.name,
        scenario_id=company.scenario_id,
        seed_name=company.seed_name,
        profile_name=company.profile_name,
        scenario=_scenario_response(company),
        quarters=[],
    )


@router.get("/companies/{company_id}", response_model=CompanyDetailResponse)
async def get_company(
    company_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> CompanyDetailResponse:
    """Read-through of current state. Computes nothing."""
    company = await _load_company(company_id, session)
    quarters = (
        (await session.execute(select(Quarter).where(Quarter.company_id == company_id).order_by(Quarter.number)))
        .scalars()
        .all()
    )

    return CompanyDetailResponse(
        id=company.id,
        created_at=company.created_at,
        name=company.name,
        scenario_id=company.scenario_id,
        seed_name=company.seed_name,
        profile_name=company.profile_name,
        scenario=_scenario_response(company),
        quarters=[QuarterSummary.model_validate(q, from_attributes=True) for q in quarters],
    )


@router.post(
    "/companies/{company_id}/quarters", response_model=QuarterDetailResponse, status_code=status.HTTP_201_CREATED
)
async def create_quarter_route(
    company_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
) -> QuarterDetailResponse:
    """Open the company's next quarter, carrying forward the prior quarter's closing state."""
    company = await _load_company(company_id, session)
    try:
        quarter = await create_quarter(session, company)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    await session.commit()
    return await _quarter_detail(quarter, session)


@router.get("/companies/{company_id}/quarters/{quarter_id}", response_model=QuarterDetailResponse)
async def get_quarter_detail(
    quarter: Quarter = Depends(get_quarter),
    session: AsyncSession = Depends(get_db),
) -> QuarterDetailResponse:
    """Read-through of current state. Computes nothing."""
    return await _quarter_detail(quarter, session)


async def _quarter_detail(quarter: Quarter, session: AsyncSession) -> QuarterDetailResponse:
    allocation = (
        await session.execute(select(QuarterAllocation).where(QuarterAllocation.quarter_id == quarter.id))
    ).scalar_one_or_none()

    return QuarterDetailResponse(
        id=quarter.id,
        company_id=quarter.company_id,
        number=quarter.number,
        status=quarter.status,
        cash_balance=quarter.cash_balance,
        revenue=quarter.revenue,
        created_at=quarter.created_at,
        closed_at=quarter.closed_at,
        modifiers=await get_quarter_modifiers(quarter.id, session),
        allocations=None
        if allocation is None
        else {
            column.key: getattr(allocation, column.key)
            for column in allocation.__table__.columns
            if column.key not in _NON_ALLOCATION_COLUMNS
        },
        warranty_years=None if allocation is None else allocation.warranty_years,
    )

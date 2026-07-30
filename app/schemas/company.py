import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.quarter import QuarterStatus
from app.schemas.base import ORMBase


class CompanyCreate(BaseModel):
    name: str
    # Omit to have one assigned deterministically from the company id.
    scenario_id: str | None = None
    # Accepted so a run can be replayed onto the same identifier and land the same scenario
    # assignment. Omit and one is generated.
    company_id: uuid.UUID | None = None


class ScenarioResponse(BaseModel):
    scenario_id: str
    display_name: str
    total_quarters: int
    crisis_quarter: int | None


class QuarterSummary(BaseModel):
    id: uuid.UUID
    number: int
    status: QuarterStatus
    cash_balance: Decimal
    revenue: Decimal


class CompanyResponse(ORMBase):
    name: str
    scenario_id: str
    seed_name: str
    profile_name: str


class CompanyDetailResponse(CompanyResponse):
    """Read-through of current state. Nothing here is computed -- the numbers are whatever the
    last `run_quarter()` persisted."""

    scenario: ScenarioResponse
    quarters: list[QuarterSummary]


class QuarterDetailResponse(BaseModel):
    id: uuid.UUID
    company_id: uuid.UUID
    number: int
    status: QuarterStatus
    cash_balance: Decimal
    revenue: Decimal
    created_at: datetime
    closed_at: datetime | None

    modifiers: dict[str, float]
    # The 22 spend lines submitted so far, or `None` if no department has submitted yet.
    # `warranty_years` is kept out of this dict and surfaced separately: it is a strategic
    # choice, not a spend line, and typing it as Decimal alongside them would serialise the
    # count as a money string.
    allocations: dict[str, Decimal] | None
    warranty_years: int | None

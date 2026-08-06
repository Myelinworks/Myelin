import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.engines.survival import RunStatus
from app.models.quarter import QuarterStatus
from app.schemas._examples import example
from app.schemas.base import ORMBase


class CompanyCreate(BaseModel):
    """`POST /companies` -- starts a new run. The authenticated caller becomes the run's owner."""

    model_config = ConfigDict(json_schema_extra={"example": example("company_create_request")})

    name: str = Field(description="Display name for the company, e.g. \"Nadi Wear\".")
    scenario_id: str | None = Field(
        default=None, description="Omit to have one assigned deterministically from the company id."
    )
    company_id: uuid.UUID | None = Field(
        default=None,
        description="Accepted so a run can be replayed onto the same identifier and land the same "
        "scenario assignment. Omit and one is generated.",
    )


class ScenarioResponse(BaseModel):
    scenario_id: str
    display_name: str
    total_quarters: int = Field(description="How many quarters this scenario runs.")
    crisis_quarter: int | None = Field(description="Which quarter number carries a crisis event, or null.")


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
    owner_id: uuid.UUID | None = Field(
        default=None, description="The authenticated user who started this run -- the authorization key."
    )

    run_status: RunStatus
    survival_condition: str | None = Field(
        default=None,
        description="Which survival condition last fired (e.g. \"cash_exhausted\", \"buffer_breached\"), "
        "or null if none has. Stays populated after a DISTRESSED run is upgraded to COMPLETED -- "
        "that is the signal Q4 tiering reads.",
    )
    survival_detail: str | None = Field(default=None, description="The specific numbers that fired it.")


class CompanyDetailResponse(CompanyResponse):
    """`POST /companies` and `GET /companies/{company_id}`. Read-through of current state --
    nothing here is computed; the numbers are whatever the last `run_quarter()` persisted."""

    model_config = ConfigDict(
        from_attributes=True, json_schema_extra={"example": example("company_detail_response")}
    )

    scenario: ScenarioResponse
    quarters: list[QuarterSummary]


class QuarterDetailResponse(BaseModel):
    """`GET .../quarters/{quarter_id}` and the response of `POST .../quarters`. The quarter's
    current submitted-so-far state -- not a report; there is no scored outcome until it locks."""

    model_config = ConfigDict(json_schema_extra={"example": example("quarter_detail_after_allocations")})

    id: uuid.UUID
    company_id: uuid.UUID
    number: int
    status: QuarterStatus
    cash_balance: Decimal = Field(description="Opening cash balance this quarter carried forward with.")
    revenue: Decimal = Field(description="Zero until this quarter locks.")
    created_at: datetime
    closed_at: datetime | None = Field(default=None, description="Null until this quarter locks.")

    modifiers: dict[str, float] = Field(
        description="The 4 legacy percentage-influence modifiers (brand_strength, "
        "market_saturation, inventory_availability, competitor_activity), materialised at "
        "quarter creation from scenario config. Not part of the 22-line power-law chain."
    )
    allocations: dict[str, Decimal] | None = Field(
        default=None,
        description="The 22 spend lines submitted so far (department key -> Rs lakhs), or null "
        "if no department has submitted yet. `warranty_years` is kept out of this dict and "
        "surfaced separately below: it's a strategic choice, not a spend line.",
    )
    warranty_years: int | None = Field(default=None, description="1, 2, or 3 -- null until R&D's line is submitted.")
    crisis: dict[str, Decimal | str | None] | None = Field(
        default=None,
        description="Crisis response fields (crisis_choice, price_match_fund, comparison_ads, "
        "retention_offers, emergency_supply_fund, crisis_choice_d_spend) -- only meaningful in "
        "the crisis quarter. Null alongside `allocations` when nothing has been submitted yet.",
    )

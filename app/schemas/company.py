import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.engines.survival import RunStatus
from app.models.quarter import QuarterStatus
from app.schemas._examples import example
from app.schemas.base import ORMBase


# Documented identically on `CompanyResponse` and `CompanyListItem`: the same field, and a
# client that reads it off one response must not be told something different by the other.
_SEQ_DESCRIPTION = (
    "This owner's run number -- their 1st, 2nd, 3rd run -- assigned once at creation and never "
    "reassigned. Unique per owner, so it is the readable handle a client can put in a URL "
    "(`/run/2`) instead of the uuid; `id` remains the only key every API path and foreign key uses."
)


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


class CompanyUpdate(BaseModel):
    """`PATCH /companies/{company_id}` -- rename an existing run."""

    name: str = Field(description="New display name for the company.")


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
    seq: int = Field(description=_SEQ_DESCRIPTION)
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


class CompanyListItem(BaseModel):
    """One row of `GET /companies` -- enough to render a "resume a run" list without a follow-up
    request per company, and nothing more. Everything here is already-persisted state; no engine
    function runs to build it.

    `latest_ceo_score`/`latest_band` come from the most recently *locked* quarter, so a run whose
    current quarter is still open reports the previous quarter's score rather than null -- the
    number a student recognises as "where I left off".
    """

    id: uuid.UUID
    seq: int = Field(description=_SEQ_DESCRIPTION)
    name: str
    created_at: datetime
    run_status: RunStatus
    scenario_id: str
    total_quarters: int = Field(description="How many quarters this run's scenario plays.")
    crisis_quarter: int | None = Field(description="Which quarter number carries a crisis event, or null.")

    current_quarter_number: int | None = Field(
        default=None, description="Null before the first quarter is opened."
    )
    current_quarter_status: QuarterStatus | None = None
    quarters_locked: int = Field(description="How many of this run's quarters have been locked so far.")

    latest_ceo_score: Decimal | None = Field(
        default=None, description="Most recently locked quarter's CEO score. Null before any quarter locks."
    )
    latest_band: str | None = Field(default=None, description="Band for `latest_ceo_score`.")


class CompanyListResponse(BaseModel):
    """`GET /companies` -- every run owned by the authenticated caller, newest first.

    Strictly owner-scoped: this is "my runs", not a directory of everyone's. An instructor
    listing a cohort's runs is a different, unbuilt endpoint with its own access rule -- folding
    it in here would silently widen what a plain `GET /companies` returns depending on who asks.
    """

    total: int
    entries: list[CompanyListItem]


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

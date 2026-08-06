"""Submission payloads for the 6 department allocation routes, plus the response shape.

Field names and department groupings mirror `app.engines.state.QuarterAllocations` and
CLAUDE.md's department split (Marketing 8 / Sales 3 / R&D 2 (+warranty) / Operations 3 / HR 3 /
Finance-Admin 3) exactly -- this is the 22-line model, not the legacy ~72-key Decision taxonomy
`app/schemas/decision.py` serves.
"""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas._examples import example
from app.schemas.base import QuarterScopedBase

ZERO = Decimal("0")
# All 6 department submit payloads share the same unit: spend in Rs lakhs (Rs 1,00,000). A field
# left at the default 0 spends nothing on that line -- fields are independently optional, not
# all-or-nothing per department.
_SPEND_DESCRIPTION = "Spend in Rs lakhs (Rs 1,00,000). 0 (the default) spends nothing on this line."


class MarketingAllocationSubmit(BaseModel):
    """`POST .../allocations/marketing` -- one of the 6 department submissions making up the
    22-line spend model (CLAUDE.md). All 8 fields independently default to 0."""

    google_ads: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    meta_ads: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    social_influencer: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    content_seo: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    events_pr: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    email_marketing: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    referral: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    prelaunch_buzz: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)


class SalesAllocationSubmit(BaseModel):
    """`POST .../allocations/sales`."""

    reps: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    crm_tools: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    onboarding: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)


class RndAllocationSubmit(BaseModel):
    """`POST .../allocations/rnd`."""

    quality_qa: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    innovation: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    warranty_years: int = Field(default=0, description="1, 2, or 3 -- a strategic choice, not a spend line.")


class OperationsAllocationSubmit(BaseModel):
    """`POST .../allocations/operations`."""

    manufacturing: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    supplier_qc: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    logistics: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)


class HrAllocationSubmit(BaseModel):
    """`POST .../allocations/hr`."""

    culture_benefits: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    training_development: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    cx_team: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)


class FinanceAdminAllocationSubmit(BaseModel):
    """`POST .../allocations/finance_admin`."""

    compliance_legal: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    financial_planning: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)
    audit_prep: Decimal = Field(default=ZERO, description=_SPEND_DESCRIPTION)


class CrisisAllocationSubmit(BaseModel):
    """`POST .../allocations/crisis` -- the 7th allocation line, meaningful only in the crisis
    quarter (`RunStateResponse.crisis_quarter`; `submit_crisis_allocation` is illegal in any
    other quarter and returns `illegal_move`). See `docs/frontend-integration-guide.md`'s Q3
    section: the specific crisis scenario (A-D) is currently not exposed by any read endpoint --
    only which quarter carries it.
    """

    model_config = ConfigDict(json_schema_extra={"example": example("crisis_allocation_submit_request")})

    crisis_choice: Literal["A", "B", "C", "D"] | None = Field(
        default=None,
        description="The Strategic Choice picked in response to the crisis. This is a different "
        "letter axis than the crisis SCENARIO (also A-D) -- e.g. Scenario B (Marketing Blitz) "
        "Choice A means \"cut price\", a different posture than Scenario A's own Choice A. "
        "Null (or omitted) is a legal, real response: ignoring the crisis entirely, which is "
        "legal but penalised (docs/11-crisis-system.md's \"crisis ignored\" -4 modifier).",
    )
    price_match_fund: Decimal = Field(default=ZERO, description=f"Scenario A/B recovery line. {_SPEND_DESCRIPTION}")
    comparison_ads: Decimal = Field(default=ZERO, description=f"Scenario A/B recovery line. {_SPEND_DESCRIPTION}")
    retention_offers: Decimal = Field(default=ZERO, description=f"Scenario A/B recovery line. {_SPEND_DESCRIPTION}")
    emergency_supply_fund: Decimal = Field(
        default=ZERO, description=f"Scenario D recovery line. {_SPEND_DESCRIPTION}"
    )
    crisis_choice_d_spend: Decimal = Field(
        default=ZERO,
        description="Generic on purpose: only one crisis fires per quarter, so this always means "
        f"whichever scenario's own Choice-D line is active. {_SPEND_DESCRIPTION}",
    )


class QuarterAllocationResponse(QuarterScopedBase):
    """The full current allocation row -- every department's submitted lines, not just the one
    just posted, so a caller can see the whole quarter's spend picture after each submission."""

    model_config = ConfigDict(
        from_attributes=True, json_schema_extra={"example": example("allocation_submit_response")}
    )

    google_ads: Decimal
    meta_ads: Decimal
    social_influencer: Decimal
    content_seo: Decimal
    events_pr: Decimal
    email_marketing: Decimal
    referral: Decimal
    prelaunch_buzz: Decimal
    reps: Decimal
    crm_tools: Decimal
    onboarding: Decimal
    quality_qa: Decimal
    innovation: Decimal
    warranty_years: int
    manufacturing: Decimal
    supplier_qc: Decimal
    logistics: Decimal
    culture_benefits: Decimal
    training_development: Decimal
    cx_team: Decimal
    compliance_legal: Decimal
    financial_planning: Decimal
    audit_prep: Decimal
    crisis_choice: Literal["A", "B", "C", "D"] | None
    price_match_fund: Decimal
    comparison_ads: Decimal
    retention_offers: Decimal
    emergency_supply_fund: Decimal
    crisis_choice_d_spend: Decimal

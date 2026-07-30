"""Submission payloads for the 6 department allocation routes, plus the response shape.

Field names and department groupings mirror `app.engines.state.QuarterAllocations` and
CLAUDE.md's department split (Marketing 8 / Sales 3 / R&D 2 (+warranty) / Operations 3 / HR 3 /
Finance-Admin 3) exactly -- this is the 22-line model, not the legacy ~72-key Decision taxonomy
`app/schemas/decision.py` serves.
"""

from decimal import Decimal

from pydantic import BaseModel

from app.schemas.base import QuarterScopedBase

ZERO = Decimal("0")


class MarketingAllocationSubmit(BaseModel):
    google_ads: Decimal = ZERO
    meta_ads: Decimal = ZERO
    social_influencer: Decimal = ZERO
    content_seo: Decimal = ZERO
    events_pr: Decimal = ZERO
    email_marketing: Decimal = ZERO
    referral: Decimal = ZERO
    prelaunch_buzz: Decimal = ZERO


class SalesAllocationSubmit(BaseModel):
    reps: Decimal = ZERO
    crm_tools: Decimal = ZERO
    onboarding: Decimal = ZERO


class RndAllocationSubmit(BaseModel):
    quality_qa: Decimal = ZERO
    innovation: Decimal = ZERO
    warranty_years: int = 0


class OperationsAllocationSubmit(BaseModel):
    manufacturing: Decimal = ZERO
    supplier_qc: Decimal = ZERO
    logistics: Decimal = ZERO


class HrAllocationSubmit(BaseModel):
    culture_benefits: Decimal = ZERO
    training_development: Decimal = ZERO
    cx_team: Decimal = ZERO


class FinanceAdminAllocationSubmit(BaseModel):
    compliance_legal: Decimal = ZERO
    financial_planning: Decimal = ZERO
    audit_prep: Decimal = ZERO


class QuarterAllocationResponse(QuarterScopedBase):
    """The full current allocation row -- every department's submitted lines, not just the one
    just posted, so a caller can see the whole quarter's spend picture after each submission."""

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

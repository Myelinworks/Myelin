import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin

# Numeric(10, 4): allocations are Rs lakhs (`app/engines/state.py`'s QuarterAllocations doc,
# e.g. Rs 2,73,600 referral spend -> x = 2.736), so 4 decimal places keeps the exact rupee value.
_LAKHS = Numeric(10, 4)


class QuarterAllocation(UUIDPkMixin, TimestampMixin, Base):
    """The 22 department spend lines for one quarter, plus the warranty choice -- the persisted
    form of `app.engines.state.QuarterAllocations`.

    One row per quarter, built up by the 6 department submission routes (one POST per
    department), each upserting only its own columns. Column names and defaults mirror
    `QuarterAllocations` exactly so the ORM row converts to the dataclass field-for-field.
    """

    __tablename__ = "quarter_allocations"
    __table_args__ = (UniqueConstraint("quarter_id", name="uq_quarter_allocation_quarter"),)

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    quarter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quarters.id"), nullable=False)

    # Marketing -- 8 lines
    google_ads: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    meta_ads: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    social_influencer: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    content_seo: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    events_pr: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    email_marketing: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    referral: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    prelaunch_buzz: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)

    # Sales -- 3 lines
    reps: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    crm_tools: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    onboarding: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)

    # R&D -- 2 lines + warranty choice
    quality_qa: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    innovation: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    warranty_years: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Operations -- 3 lines
    manufacturing: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    supplier_qc: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    logistics: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)

    # HR -- 3 lines
    culture_benefits: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    training_development: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    cx_team: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)

    # Finance/Admin -- 3 lines
    compliance_legal: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    financial_planning: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    audit_prep: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)

    # Crisis response (Phase 10, docs/11-crisis-system.md) -- only meaningful in the quarter a
    # crisis fires; all-zero/null otherwise. crisis_choice_d_spend is generic on purpose (see
    # app/engines/state.py's QuarterAllocations docstring): only one crisis fires per quarter, so
    # one column always means "this quarter's active scenario's own Choice-D line".
    crisis_choice: Mapped[str | None] = mapped_column(String(1), nullable=True)
    price_match_fund: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    comparison_ads: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    retention_offers: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    emergency_supply_fund: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)
    crisis_choice_d_spend: Mapped[Decimal] = mapped_column(_LAKHS, nullable=False, default=0)

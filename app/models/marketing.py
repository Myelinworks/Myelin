import uuid
from decimal import Decimal

from sqlalchemy import Float, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class MarketingState(UUIDPkMixin, TimestampMixin, Base):
    """Marketing workspace KPI snapshot for one quarter."""

    __tablename__ = "marketing_states"

    quarter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quarters.id"), unique=True, nullable=False
    )
    marketing_spend: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    leads_generated: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_acquisition_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    brand_awareness_score: Mapped[float] = mapped_column(Float, nullable=False)

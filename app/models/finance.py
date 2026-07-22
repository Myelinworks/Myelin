import uuid
from decimal import Decimal

from sqlalchemy import Float, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class FinanceState(UUIDPkMixin, TimestampMixin, Base):
    """Finance workspace KPI snapshot for one quarter."""

    __tablename__ = "finance_states"

    quarter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quarters.id"), unique=True, nullable=False
    )
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    expenses: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    burn_rate: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    runway_months: Mapped[float | None] = mapped_column(Float, nullable=True)

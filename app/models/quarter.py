import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
    from app.models.company import Company


class QuarterStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    CLOSED = "closed"


class Quarter(UUIDPkMixin, TimestampMixin, Base):
    """A quarterly state snapshot: aggregate cash/revenue position for one company at one point in the simulation."""

    __tablename__ = "quarters"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[QuarterStatus] = mapped_column(
        SAEnum(QuarterStatus, name="quarter_status"), default=QuarterStatus.IN_PROGRESS, nullable=False
    )

    cash_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship(back_populates="quarters")

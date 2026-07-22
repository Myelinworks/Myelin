import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class CXState(UUIDPkMixin, TimestampMixin, Base):
    """Customer Experience workspace KPI snapshot for one quarter."""

    __tablename__ = "cx_states"

    quarter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quarters.id"), unique=True, nullable=False
    )
    csat_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    churn_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    support_tickets_resolved: Mapped[int] = mapped_column(Integer, nullable=False)

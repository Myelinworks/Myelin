import uuid
from decimal import Decimal

from sqlalchemy import Float, ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class OperationsState(UUIDPkMixin, TimestampMixin, Base):
    """Operations workspace KPI snapshot for one quarter."""

    __tablename__ = "operations_states"

    quarter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quarters.id"), unique=True, nullable=False
    )
    fulfillment_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    operational_efficiency_score: Mapped[float] = mapped_column(Float, nullable=False)
    incident_count: Mapped[int] = mapped_column(Integer, nullable=False)

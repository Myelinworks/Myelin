import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class SalesState(UUIDPkMixin, TimestampMixin, Base):
    """Sales workspace KPI snapshot for one quarter."""

    __tablename__ = "sales_states"

    quarter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quarters.id"), unique=True, nullable=False
    )
    pipeline_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    deals_closed: Mapped[int] = mapped_column(Integer, nullable=False)
    quota_attainment_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

import uuid

from sqlalchemy import Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class ProductState(UUIDPkMixin, TimestampMixin, Base):
    """Product workspace KPI snapshot for one quarter."""

    __tablename__ = "product_states"

    quarter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quarters.id"), unique=True, nullable=False
    )
    features_shipped: Mapped[int] = mapped_column(Integer, nullable=False)
    nps_score: Mapped[float] = mapped_column(Float, nullable=False)
    tech_debt_index: Mapped[float] = mapped_column(Float, nullable=False)

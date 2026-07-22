import uuid

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class Modifier(UUIDPkMixin, TimestampMixin, Base):
    """A named quarter-level modifier (Brand Strength, Market Saturation, Inventory Availability,
    Competitor Activity, ...) multiplied into a decision's base impact % in decision_engine.

    Kept as rows rather than fixed Quarter columns so new modifier types can be introduced
    without a schema migration.
    """

    __tablename__ = "modifiers"
    __table_args__ = (UniqueConstraint("quarter_id", "modifier_key", name="uq_modifier_quarter_key"),)

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    quarter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quarters.id"), nullable=False)
    modifier_key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)

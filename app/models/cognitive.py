import uuid

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class CognitiveScore(UUIDPkMixin, TimestampMixin, Base):
    """A single cognitive dimension score (e.g. Strategic Thinking, Adaptability, Leadership) for one quarter.

    Computed by the Cognitive Scoring Engine from EvidenceRecords, never from raw KPI/business-impact data.
    """

    __tablename__ = "cognitive_scores"

    quarter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quarters.id"), nullable=False)
    dimension: Mapped[str] = mapped_column(String(100), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)

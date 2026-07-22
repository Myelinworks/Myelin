import uuid
from typing import Any

from sqlalchemy import Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class QuarterPerformance(UUIDPkMixin, TimestampMixin, Base):
    """Leaderboard-ready rollup of one company's cognitive performance for one quarter.

    Written once by quarter_engine at the end of the Run Quarter flow (after cognitive_scoring_engine
    has produced that quarter's CognitiveScore rows), so leaderboard reads don't need to aggregate
    cognitive_scores on every request.
    """

    __tablename__ = "quarter_performances"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    quarter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quarters.id"), unique=True, nullable=False
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    dimension_scores: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

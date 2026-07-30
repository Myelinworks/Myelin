import uuid
from typing import Any

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class QuarterPerformance(UUIDPkMixin, TimestampMixin, Base):
    """One row per quarter, written by two independent pipelines that don't run at the same time:

    - `overall_score`/`dimension_scores`: the legacy cognitive-performance rollup, written by
      `services/quarter_engine.py` after cognitive_scoring_engine produces that quarter's
      CognitiveScore rows.
    - `result_hash`/`engine_result`: the pure 22-line engine's persisted `QuarterResult`,
      written by `services/quarter_run_service.py::run_quarter`.

    Both are nullable because neither pipeline requires the other to have run first -- a row
    can carry only one, both, or (before either has run) neither.
    """

    __tablename__ = "quarter_performances"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    quarter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quarters.id"), unique=True, nullable=False
    )
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dimension_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # sha256 over the canonical (sorted-key) serialised QuarterResult -- not Python's hash(),
    # which is salted per process and would never compare equal across two runs.
    result_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    engine_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

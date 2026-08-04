import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import Float, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class QuarterPerformance(UUIDPkMixin, TimestampMixin, Base):
    """One row per quarter, written by three independent pipelines that don't run at the same time:

    - `overall_score`/`dimension_scores`: the legacy cognitive-performance rollup, written by
      `services/quarter_engine.py` after cognitive_scoring_engine produces that quarter's
      CognitiveScore rows.
    - `result_hash`/`engine_result`: the pure 22-line engine's persisted `QuarterResult`,
      written by `services/quarter_run_service.py::run_quarter`.
    - `ceo_score`/`score_band`/`trait_points`/`modifiers_applied`/`unscored_criteria`: the pure
      scoring engine's persisted `QuarterScore` (`app.engines.scoring.score_quarter`), computed
      and written alongside `engine_result` in the same `run_quarter` transaction. Not reused
      from `overall_score`/`dimension_scores` -- those belong to the legacy cognitive pipeline and
      mean something different; two scoring systems sharing one column is exactly the ambiguity
      this codebase avoids.

    All nullable because no pipeline requires another to have run first -- a row can carry any
    subset of them, including none, before anything has run.
    """

    __tablename__ = "quarter_performances"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    quarter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("quarters.id"), unique=True, nullable=False
    )
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    dimension_scores: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # sha256 over the canonical (sorted-key) serialised QuarterResult plus the CEO score --
    # not Python's hash(), which is salted per process and would never compare equal across
    # two runs.
    result_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    engine_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # QuarterScore.normalised_score -- the trait portion rescaled to 100 (held-out JUDGMENT
    # weight excluded) plus modifiers on top. Bands are read off this number, not raw_score.
    ceo_score: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    score_band: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trait_points: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    modifiers_applied: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    unscored_criteria: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

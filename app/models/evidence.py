import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Index, Numeric, String, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.decision import Workspace
from app.models.mixins import TimestampMixin, UUIDPkMixin


class EvidenceRecord(UUIDPkMixin, TimestampMixin, Base):
    """A structured behavioral signal, never a score. Two independent producers write this table,
    the same way three independent pipelines write `quarter_performances` -- each pipeline owns a
    disjoint set of nullable columns and never reads the other's.

    - `decision_id`/`workspace`: the legacy per-decision pipeline (`app/services/evidence_engine.py`,
      the ~72-key `Decision` taxonomy). Kept and tested as-is; this row shape is untouched by Phase 8.
    - `department`/`weight`/`weight_status`/`detail`: the Phase 8 producer on the 22-line model
      (`app/engines/evidence.py`), written by `run_quarter()`. `decision_id` is `NULL` here -- there
      is no per-decision row in the 22-line model, evidence is generated from the whole locked
      `QuarterAllocation` at once.

    Both share `evidence_key`, `evidence_value` and `categories` -- categories are cognitive
    dimensions (the same 7 trait keys `ScoringConfig.traits` uses), never a workspace/department,
    per CLAUDE.md's aggregate-by-category rule.
    """

    __tablename__ = "evidence_records"
    __table_args__ = (
        # Idempotent re-lock for the Phase 8 producer only: legacy rows (decision_id NOT NULL) are
        # unconstrained, since a quarter can legitimately hold several legacy Decisions that emit
        # the same evidence_key.
        Index(
            "uq_evidence_records_quarter_key_new_pipeline",
            "quarter_id",
            "evidence_key",
            unique=True,
            postgresql_where=text("decision_id IS NULL"),
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    quarter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quarters.id"), nullable=False)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("decisions.id"), nullable=True
    )
    workspace: Mapped[Workspace | None] = mapped_column(SAEnum(Workspace, name="workspace"), nullable=True)

    # Phase 8 producer only. One of the 6 CLAUDE.md-canonical department buckets ("marketing",
    # "sales", "rnd", "operations", "hr", "finance_admin") -- exactly `QuarterAllocations`' `*_total`
    # groupings. Plain string, not a DB enum, matching the precedent of `ScoringBand.name` /
    # `quarter_performances.score_band`.
    department: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # `None` when no sourced weight exists for this evidence_key anywhere in docs/ (the common
    # case); `weight_status` says why rather than leaving it silently weightless.
    weight: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    weight_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # The concrete checkable condition this record traces to (e.g. "6 of 7 diminishing-curve
    # channels funded"). Never a judgment word.
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    evidence_key: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    categories: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)

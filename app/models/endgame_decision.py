import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class EndgameDecision(UUIDPkMixin, TimestampMixin, Base):
    """The Q4 strategic decision (`docs/16-quarter-4-endgame.md` section 3) -- one row per company,
    submitted before Q4 locks. `path` is "A" (debt-funded growth), "B" (acquisition offer), or "C"
    (deliberate independence); `term_sheet_name` is which named offer from the assigned tier's menu
    was picked (`app.config.schema.EndgameConfig`'s term-sheet menus). `reasoning` is free text,
    read by a future judgment scorer exactly like Phase 8's evidence -- never scored here.

    The *outcome* (covenant hit/missed, correct/incorrect acceptance) is only knowable once Q4's
    own `QuarterResult` exists, so scoring happens at Q4's lock (`services/quarter_run_service.py`),
    not at submission time.
    """

    __tablename__ = "endgame_decisions"
    __table_args__ = (UniqueConstraint("company_id", name="uq_endgame_decision_company"),)

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    quarter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quarters.id"), nullable=False)

    path: Mapped[str] = mapped_column(String(1), nullable=False)
    term_sheet_name: Mapped[str] = mapped_column(String(100), nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)

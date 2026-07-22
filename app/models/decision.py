import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class Workspace(StrEnum):
    FINANCE = "finance"
    MARKETING = "marketing"
    PRODUCT = "product"
    SALES = "sales"
    OPERATIONS = "operations"
    CX = "cx"


class DecisionStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    PROCESSED = "processed"


class Decision(UUIDPkMixin, TimestampMixin, Base):
    """A single student decision submitted in one workspace during one quarter."""

    __tablename__ = "decisions"

    quarter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quarters.id"), nullable=False)
    workspace: Mapped[Workspace] = mapped_column(SAEnum(Workspace, name="workspace"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    # Identifies WHAT was decided (e.g. "increase_google_ads_budget", "FIN-001") -- the key
    # decision_engine and evidence_engine look up in the workspace's rules config. `payload`
    # carries the decision-specific inputs (e.g. the channel spend split).
    decision_key: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[DecisionStatus] = mapped_column(
        SAEnum(DecisionStatus, name="decision_status"), default=DecisionStatus.DRAFT, nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    logs: Mapped[list["DecisionLog"]] = relationship(back_populates="decision")


class DecisionLog(UUIDPkMixin, TimestampMixin, Base):
    """An immutable audit record of one pipeline run (business impact or evidence) against a decision, for replay."""

    __tablename__ = "decision_logs"

    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("decisions.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    decision: Mapped["Decision"] = relationship(back_populates="logs")

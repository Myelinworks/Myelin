import uuid
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.decision import Workspace
from app.models.mixins import TimestampMixin, UUIDPkMixin


class EvidenceRecord(UUIDPkMixin, TimestampMixin, Base):
    """A structured behavioral signal produced by the Evidence pipeline for one decision.

    Evidence is boolean/enum/amount flags (e.g. "Diversified Investment = YES"), never a score --
    scoring happens downstream in the Cognitive Scoring Engine, which reads these rows and never
    reads raw KPI/business-impact data.
    """

    __tablename__ = "evidence_records"

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    quarter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quarters.id"), nullable=False)
    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("decisions.id"), nullable=False)
    workspace: Mapped[Workspace] = mapped_column(SAEnum(Workspace, name="workspace"), nullable=False)

    evidence_key: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    categories: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)

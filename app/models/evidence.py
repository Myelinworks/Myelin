import uuid
from typing import Any

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class EvidenceRecord(UUIDPkMixin, TimestampMixin, Base):
    """A behavioral signal captured alongside a decision (e.g. time-to-decide, revision count).

    Feeds the Cognitive Scoring Engine only — never read back into the Business Impact pipeline.
    """

    __tablename__ = "evidence_records"

    decision_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("decisions.id"), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

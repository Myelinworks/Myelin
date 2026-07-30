import uuid
from typing import Any

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class CompanyStateSnapshot(UUIDPkMixin, TimestampMixin, Base):
    """Serialised `app.engines.state.CompanyState` as of the end of one quarter -- the persisted
    carry-forward mechanism between quarters.

    `compute_quarter`'s opening state has ~20 cumulative fields (Brand Score, Quality Score, the
    Buzz payout clock, etc.) with no other DB representation. Storing the dataclass as JSON
    (`app/services/quarter_run_service.py` owns the (de)serialisation -- `app/engines/` stays
    DB-free per CLAUDE.md) avoids inventing 20 parallel columns that would drift from
    `CompanyState`'s actual shape every time a field is added there.
    """

    __tablename__ = "company_state_snapshots"
    __table_args__ = (UniqueConstraint("quarter_id", name="uq_company_state_snapshot_quarter"),)

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    quarter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("quarters.id"), nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

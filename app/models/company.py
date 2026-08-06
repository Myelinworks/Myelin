import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.engines.survival import RunStatus
from app.models.mixins import TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
    from app.models.app_user import AppUser
    from app.models.quarter import Quarter


class Company(UUIDPkMixin, TimestampMixin, Base):
    """A student's simulated company — the root of one CEO simulation run.

    `seed_name`/`profile_name` select the `CompanySeed`/`SimulationProfile` config
    `run_quarter()` loads to run `compute_quarter()`. They are copied from the scenario at
    creation time rather than looked up through `scenario_id` on every run: a company that has
    already played three quarters must keep running against the config it started on, even if
    the scenario file is later edited. `scenario_id` records which scenario it came from, and
    is what `total_quarters`/`crisis_quarter` are read from.
    """

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    scenario_id: Mapped[str] = mapped_column(String(100), nullable=False, default="nadi_wear_standard")
    seed_name: Mapped[str] = mapped_column(String(100), nullable=False, default="nadi_wear")
    profile_name: Mapped[str] = mapped_column(String(100), nullable=False, default="default")

    # Recomputed from the full quarter history on every lock (`services/quarter_run_service.py`),
    # never incrementally patched -- `buffer_breached` is "at any point", so the answer depends
    # on quarters already behind us. `survival_condition`/`survival_detail` name what fired,
    # and survive a later upgrade to COMPLETED so Q4 tiering can still see *why* a finished run
    # was distressed.
    run_status: Mapped[RunStatus] = mapped_column(
        SAEnum(RunStatus, name="run_status"), nullable=False, default=RunStatus.ACTIVE
    )
    survival_condition: Mapped[str | None] = mapped_column(String(100), nullable=True)
    survival_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Nullable at the schema level only because there is no real user data to backfill --
    # every ownership check (services/authorization_service.py) treats a null owner as
    # "nobody's," so an owner-less row is permanently unwritable/unreadable through the API
    # rather than a bypass. `routes/company.py::create_company_route` always stamps this from
    # the authenticated caller going forward.
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("app_users.id"), nullable=True, index=True
    )

    quarters: Mapped[list["Quarter"]] = relationship(back_populates="company")
    owner: Mapped["AppUser | None"] = relationship(back_populates="companies")

from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.engines.survival import RunStatus
from app.models.mixins import TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
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

    quarters: Mapped[list["Quarter"]] = relationship(back_populates="company")

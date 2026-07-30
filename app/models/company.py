from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
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

    quarters: Mapped[list["Quarter"]] = relationship(back_populates="company")

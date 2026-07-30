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
    `run_quarter()` loads to run `compute_quarter()`. Defaults to Nadi Wear on the default
    profile -- the only fully-specified company -- until Phase 5's scenario system assigns
    these from a scenario instead of the default.
    """

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    seed_name: Mapped[str] = mapped_column(String(100), nullable=False, default="nadi_wear")
    profile_name: Mapped[str] = mapped_column(String(100), nullable=False, default="default")

    quarters: Mapped[list["Quarter"]] = relationship(back_populates="company")

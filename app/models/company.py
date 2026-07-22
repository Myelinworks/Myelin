from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin

if TYPE_CHECKING:
    from app.models.quarter import Quarter


class Company(UUIDPkMixin, TimestampMixin, Base):
    """A student's simulated company — the root of one CEO simulation run."""

    __tablename__ = "companies"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    quarters: Mapped[list["Quarter"]] = relationship(back_populates="company")

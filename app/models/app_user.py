import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.company import Company


class AppUser(TimestampMixin, Base):
    """The local mirror of a Supabase Auth identity.

    `id` is the Supabase `sub` claim itself, not a `UUIDPkMixin`-generated id -- there is
    exactly one row per Supabase identity, so a second surrogate key would just be a
    redundant unique column to keep in sync. Provisioned get-or-create on first authenticated
    request (`services/auth_service.get_or_create_app_user`); `role` defaults to "student"
    there and is only ever elevated by a manual DB/seed operation, never a self-service route.
    """

    __tablename__ = "app_users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="student")

    companies: Mapped[list["Company"]] = relationship(back_populates="owner")

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ARRAY, Boolean, String
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

    The profile fields below (everything but `id`/`email`/`role`) are the onboarding-screen
    answers (`components/auth/OnboardingProfile.tsx` on the frontend) -- all optional, all
    nullable, filled in by `PATCH /profile` rather than at signup. `institution_*` is stored
    flat (mirroring the frontend's `InstitutionRef` shape) rather than as a JSON blob, matching
    this model's existing plain-column style.
    """

    __tablename__ = "app_users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="student")

    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    institution_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    institution_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: False for a self-typed institution not in the directory (`OTHER_INSTITUTION_PREFIX` on
    #: the frontend) -- meaningless once `institution_id` is null, so it defaults false rather
    #: than nullable.
    institution_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    degree: Mapped[str | None] = mapped_column(String(80), nullable=True)
    current_year: Mapped[str | None] = mapped_column(String(40), nullable=True)
    #: At most `MAX_GOALS` (3) entries from the frontend's fixed `goalOptions` list.
    goals: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False, default=list)

    companies: Mapped[list["Company"]] = relationship(back_populates="owner")

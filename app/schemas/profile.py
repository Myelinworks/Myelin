import uuid
from datetime import datetime

from pydantic import BaseModel, Field

MAX_GOALS = 3


class InstitutionRef(BaseModel):
    """Mirrors the frontend's `InstitutionRef` (`lib/institutions.ts`) exactly -- `id` is what
    gets stored, `name` is display-only, `verified` is false for a self-typed institution not
    in the frontend's directory."""

    id: str
    name: str
    verified: bool = False


class ProfileResponse(BaseModel):
    """`GET /profile` -- the current user's account plus every onboarding answer, `null` for
    whichever ones were never answered. `institution` is `None` exactly when `institution_id`
    is unset on the row."""

    user_id: uuid.UUID
    email: str
    role: str
    created_at: datetime

    first_name: str | None = None
    institution: InstitutionRef | None = None
    degree: str | None = None
    current_year: str | None = None
    goals: list[str] = Field(default_factory=list)


class ProfileUpdate(BaseModel):
    """`PATCH /profile` -- every field optional and independently nullable, so a client can
    update one answer without resending the rest. Send a field as `null` to clear it, omit it
    to leave it unchanged (standard PATCH semantics via `exclude_unset`).
    """

    first_name: str | None = None
    institution: InstitutionRef | None = None
    degree: str | None = None
    current_year: str | None = None
    #: Replaces the stored list outright when present -- never merged, matching how the
    #: onboarding screen's checkbox group already works. Capped at `MAX_GOALS`.
    goals: list[str] | None = Field(default=None, max_length=MAX_GOALS)

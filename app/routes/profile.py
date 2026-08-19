"""The account settings surface: read and edit the onboarding answers signup collects, and
nothing else -- role elevation stays a manual DB/seed operation (`services/authorization_service`
docstring), never exposed here. Run history is `GET /companies`, already owner-scoped; this
router does not duplicate it.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.models.app_user import AppUser
from app.routes.deps import get_current_user
from app.schemas.profile import InstitutionRef, ProfileResponse, ProfileUpdate
from app.services.auth_service import CurrentUser

router = APIRouter(prefix="/profile", tags=["profile"])


def _to_response(row: AppUser) -> ProfileResponse:
    institution = (
        InstitutionRef(id=row.institution_id, name=row.institution_name, verified=row.institution_verified)
        if row.institution_id is not None
        else None
    )
    return ProfileResponse(
        user_id=row.id,
        email=row.email,
        role=row.role,
        created_at=row.created_at,
        first_name=row.first_name,
        institution=institution,
        degree=row.degree,
        current_year=row.current_year,
        goals=list(row.goals),
    )


@router.get(
    "",
    response_model=ProfileResponse,
    summary="Read your profile",
    description="Your account plus every onboarding answer -- `null` for whichever were never "
    "answered. The get-or-create on every authenticated request means this row always exists "
    "by the time this route runs.",
)
async def get_profile(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    row = await session.get(AppUser, user.id)
    return _to_response(row)


@router.patch(
    "",
    response_model=ProfileResponse,
    summary="Update your profile",
    description="Every field optional and independently nullable -- a field left out of the "
    "payload is unchanged, a field sent as `null` is cleared. `goals` replaces the stored list "
    "outright when present, capped at 3.",
)
async def patch_profile(
    payload: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    row = await session.get(AppUser, user.id)
    changes = payload.model_dump(exclude_unset=True)

    if "first_name" in changes:
        row.first_name = changes["first_name"]
    if "institution" in changes:
        institution = changes["institution"]
        if institution is None:
            row.institution_id = None
            row.institution_name = None
            row.institution_verified = False
        else:
            row.institution_id = institution["id"]
            row.institution_name = institution["name"]
            row.institution_verified = institution["verified"]
    if "degree" in changes:
        row.degree = changes["degree"]
    if "current_year" in changes:
        row.current_year = changes["current_year"]
    if "goals" in changes:
        row.goals = changes["goals"] or []

    await session.commit()
    await session.refresh(row)
    return _to_response(row)

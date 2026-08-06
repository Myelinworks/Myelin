"""Thin proxy routes over Supabase Auth's own REST API -- password hashing and session-token
signing are entirely Supabase's; this backend never implements either (see
`app/services/auth_service.py`). Kept in the backend, rather than left to a frontend calling
Supabase directly, so the full register -> login -> play lifecycle stays testable end to end
via httpx/pytest, the same way Phase 12's acceptance tests exercise the run lifecycle.
"""

from fastapi import APIRouter, Depends

from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.services.auth_service import SupabaseAuthClient, get_supabase_auth_client

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=201,
    summary="Register a new user",
    description="Creates a Supabase Auth identity via Supabase's own signup API and returns a "
    "session. Not run-scoped -- no Bearer token required to call this. Call this once per user, "
    "then `POST /auth/login` on return visits.",
)
async def register(
    payload: RegisterRequest,
    client: SupabaseAuthClient = Depends(get_supabase_auth_client),
) -> AuthResponse:
    result = await client.sign_up(email=payload.email, password=payload.password)
    return AuthResponse(**result)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in an existing user",
    description="Proxies to Supabase Auth's password grant and returns a session. Send the "
    "returned `access_token` as `Authorization: Bearer <access_token>` on every subsequent request.",
)
async def login(
    payload: LoginRequest,
    client: SupabaseAuthClient = Depends(get_supabase_auth_client),
) -> AuthResponse:
    result = await client.sign_in(email=payload.email, password=payload.password)
    return AuthResponse(**result)

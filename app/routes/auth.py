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


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    payload: RegisterRequest,
    client: SupabaseAuthClient = Depends(get_supabase_auth_client),
) -> AuthResponse:
    result = await client.sign_up(email=payload.email, password=payload.password)
    return AuthResponse(**result)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    client: SupabaseAuthClient = Depends(get_supabase_auth_client),
) -> AuthResponse:
    result = await client.sign_in(email=payload.email, password=payload.password)
    return AuthResponse(**result)

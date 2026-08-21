"""Thin proxy routes over Supabase Auth's own REST API -- password hashing and session-token
signing are entirely Supabase's; this backend never implements either (see
`app/services/auth_service.py`). Kept in the backend, rather than left to a frontend calling
Supabase directly, so the full register -> login -> play lifecycle stays testable end to end
via httpx/pytest, the same way Phase 12's acceptance tests exercise the run lifecycle.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.routes.deps import NotAuthenticatedError
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.services.auth_service import (
    PasswordResetMisconfigured,
    SupabaseAuthClient,
    SupabaseAuthError,
    get_supabase_auth_client,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=201,
    summary="Register a new user",
    description="Creates a Supabase Auth identity via Supabase's own signup API and returns a "
    "session. Not run-scoped -- no Bearer token required to call this. Call this once per user, "
    "then `POST /auth/login` on return visits. 422 (plain `detail`) if Supabase rejects the "
    "email/password itself (invalid domain, weak password, already registered); 429 (plain "
    "`detail`) if Supabase's signup rate limit was hit.",
)
async def register(
    payload: RegisterRequest,
    client: SupabaseAuthClient = Depends(get_supabase_auth_client),
) -> AuthResponse:
    try:
        result = await client.sign_up(email=payload.email, password=payload.password)
    except SupabaseAuthError as exc:
        # Rate limiting is the one signup rejection that isn't about the input itself.
        if exc.status_code == 429:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, exc.message) from exc
        # Everything else Supabase's signup endpoint rejects (bad email, weak password,
        # already-registered, ...) is a malformed/rejected request, not a server failure.
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.message) from exc
    return AuthResponse(**result)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in an existing user",
    description="Proxies to Supabase Auth's password grant and returns a session. Send the "
    "returned `access_token` as `Authorization: Bearer <access_token>` on every subsequent "
    "request. 401 `{\"error\": \"not_authenticated\"}` for any rejected login attempt (wrong "
    "password, unknown email, unconfirmed email, ...); 429 (plain `detail`) if Supabase's "
    "login rate limit was hit.",
)
async def login(
    payload: LoginRequest,
    client: SupabaseAuthClient = Depends(get_supabase_auth_client),
) -> AuthResponse:
    try:
        result = await client.sign_in(email=payload.email, password=payload.password)
    except SupabaseAuthError as exc:
        if exc.status_code == 429:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, exc.message) from exc
        # Any other rejection (wrong password, unknown email, unconfirmed email, ...) means
        # this request didn't authenticate -- the same envelope `get_current_user` uses for a
        # missing/invalid Bearer token, so the frontend's one 401 handler catches both.
        raise NotAuthenticatedError(exc.message) from exc
    return AuthResponse(**result)


@router.post(
    "/refresh",
    response_model=AuthResponse,
    summary="Renew an expiring session",
    description="Proxies to Supabase Auth's refresh grant and returns a new session. Supabase "
    "access tokens expire after roughly an hour -- shorter than a four-quarter run takes to "
    "play -- so a client holding a `refresh_token` calls this instead of letting the session "
    "die mid-run. 401 `{\"error\": \"not_authenticated\"}` if the refresh token is itself "
    "expired, already used, or revoked: at that point the user really does have to log in "
    "again. 429 (plain `detail`) if Supabase's rate limit was hit.",
)
async def refresh(
    payload: RefreshRequest,
    client: SupabaseAuthClient = Depends(get_supabase_auth_client),
) -> AuthResponse:
    try:
        result = await client.refresh_session(refresh_token=payload.refresh_token)
    except SupabaseAuthError as exc:
        if exc.status_code == 429:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, exc.message) from exc
        # A refresh token Supabase will not trade is indistinguishable, to the client, from
        # having no session at all -- same 401 envelope as `/login` and `get_current_user`,
        # so the frontend's one 401 handler is all that is needed to send them to login.
        raise NotAuthenticatedError(exc.message) from exc
    return AuthResponse(**result)


@router.post(
    "/forgot-password",
    summary="Request a password-reset email",
    description="Proxies to Supabase Auth's `/recover`. Always returns the same generic ack "
    "whether or not the email is registered -- Supabase itself never reveals that, to prevent "
    "email enumeration. The emailed link lands on the caller's own origin when this API "
    "already accepts browser requests from it (so a reset started on production lands on "
    "production, and one started on a preview deploy lands on that preview), and on the "
    "configured `FRONTEND_URL` otherwise. 500 if Supabase would not honour that landing page "
    "-- no email is sent in that case, because the link in it would 404. 429 (plain `detail`) "
    "if Supabase's rate limit was hit.",
)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    client: SupabaseAuthClient = Depends(get_supabase_auth_client),
    settings: Settings = Depends(get_settings),
) -> dict:
    # The link has to point back at whichever deployment the caller is on. `Origin` is only
    # trusted when it is already on this API's own CORS allow-list; anything else falls back
    # to the configured FRONTEND_URL.
    redirect_to = settings.reset_redirect_for(request.headers.get("origin"))

    try:
        await client.request_password_reset(email=payload.email, redirect_to=redirect_to)
    except PasswordResetMisconfigured as exc:
        # Nothing was sent, and saying "check your inbox" here is exactly the lie that made
        # this bug invisible. The operator-facing fix goes to the log, not to the user.
        logger.error("Refused to send a password-reset email. %s", exc.detail)
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Password resets are misconfigured on this deployment, so the emailed link would "
            "not work. No email was sent -- please contact support.",
        ) from exc
    except SupabaseAuthError as exc:
        if exc.status_code == 429:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, exc.message) from exc
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.message) from exc
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post(
    "/reset-password",
    summary="Complete a password reset",
    description="Proxies to Supabase Auth's `PUT /user`, authenticated with the short-lived "
    "recovery `access_token` from the emailed reset link (the frontend reads it out of the "
    "URL fragment after Supabase's redirect). 422 (plain `detail`) if the token is expired/"
    "invalid or Supabase rejects the new password itself.",
)
async def reset_password(
    payload: ResetPasswordRequest,
    client: SupabaseAuthClient = Depends(get_supabase_auth_client),
) -> dict:
    try:
        await client.confirm_password_reset(
            access_token=payload.access_token, new_password=payload.new_password
        )
    except SupabaseAuthError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, exc.message) from exc
    return {"message": "Password updated."}

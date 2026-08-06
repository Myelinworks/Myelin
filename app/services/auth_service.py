"""Phase 13: identity, not authorization.

Verifies a Supabase Auth JWT (signature only, via Supabase's own JWKS -- no hand-rolled
crypto) and resolves it to the local `AppUser` row that carries the one thing Supabase's
token has no concept of: this app's `role`. `get_current_user` in `routes/deps.py` is the
only caller that turns an HTTP `Authorization` header into a `CurrentUser`; this module never
touches HTTP itself.

`SupabaseAuthClient`/`HttpxSupabaseAuthClient` are the register/login proxy's own concern --
thin wrappers around Supabase Auth's REST API (password hashing and session-token signing are
entirely Supabase's, this backend never implements either). Exposed as a FastAPI dependency
(`get_supabase_auth_client`) rather than a bare module import so tests can swap in a fake via
`app.dependency_overrides`, the same mechanism already used for `get_db`.
"""

import uuid
from dataclasses import dataclass
from typing import Protocol

import httpx
import jwt
from fastapi import Depends
from jwt import PyJWKClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.app_user import AppUser


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    email: str
    role: str


_jwk_client: PyJWKClient | None = None
_jwk_client_url: str | None = None


def _get_jwk_client(settings: Settings) -> PyJWKClient:
    """Module-level singleton, rebuilt only if the configured JWKS URL changes (e.g. between
    test runs that swap settings) -- `PyJWKClient` already caches fetched keys internally,
    so this just avoids re-creating the client (and its cache) on every request."""
    global _jwk_client, _jwk_client_url
    if _jwk_client is None or _jwk_client_url != settings.supabase_jwks_url:
        _jwk_client = PyJWKClient(settings.supabase_jwks_url, cache_keys=True, lifespan=600)
        _jwk_client_url = settings.supabase_jwks_url
    return _jwk_client


def verify_jwt(token: str, settings: Settings) -> dict:
    """Verifies signature via Supabase's JWKS, returns decoded claims. Raises a
    `jwt.PyJWTError` subclass (expired, bad signature, wrong audience, ...) on any failure --
    the caller (`routes/deps.py::get_current_user`) is responsible for turning that into the
    401 `not_authenticated` envelope."""
    signing_key = _get_jwk_client(settings).get_signing_key_from_jwt(token)
    return jwt.decode(token, signing_key.key, algorithms=["ES256", "RS256"], audience="authenticated")


async def get_or_create_app_user(session: AsyncSession, *, sub: uuid.UUID, email: str) -> AppUser:
    """Get-or-create against `app_users`, defaulting `role="student"`. The only place a role
    is ever assigned automatically -- elevation to instructor/admin is a manual DB/seed
    operation, never a self-service endpoint."""
    user = await session.get(AppUser, sub)
    if user is None:
        user = AppUser(id=sub, email=email, role="student")
        session.add(user)
        await session.flush()
    return user


class SupabaseAuthClient(Protocol):
    async def sign_up(self, *, email: str, password: str) -> dict: ...
    async def sign_in(self, *, email: str, password: str) -> dict: ...


class HttpxSupabaseAuthClient:
    """Calls Supabase Auth's own REST API for password hashing and session-token issuance --
    this backend never implements either itself."""

    def __init__(self, settings: Settings):
        self._base_url = settings.supabase_url
        self._api_key = settings.supabase_publishable_key

    async def _call(self, path: str, payload: dict) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}{path}",
                json=payload,
                headers={"apikey": self._api_key, "Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
        return {
            "access_token": data["access_token"],
            "refresh_token": data.get("refresh_token"),
            "user_id": data["user"]["id"],
            "email": data["user"]["email"],
        }

    async def sign_up(self, *, email: str, password: str) -> dict:
        return await self._call("/auth/v1/signup", {"email": email, "password": password})

    async def sign_in(self, *, email: str, password: str) -> dict:
        return await self._call(
            "/auth/v1/token?grant_type=password", {"email": email, "password": password}
        )


def get_supabase_auth_client(settings: Settings = Depends(get_settings)) -> SupabaseAuthClient:
    """FastAPI dependency -- a bare import would make the real Supabase client impossible to
    swap out in tests via `app.dependency_overrides`, the same mechanism already used for
    `get_db`."""
    return HttpxSupabaseAuthClient(settings)

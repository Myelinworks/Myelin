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
    # Small leeway absorbs local/clock skew vs Supabase's iat (common on Windows hosts).
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience="authenticated",
        leeway=30,
    )


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


class SupabaseAuthError(Exception):
    """A *known* rejection from Supabase Auth itself (bad credentials, rejected signup input,
    rate limiting) -- carries Supabase's own status code and message so `routes/auth.py` can
    map it to this API's envelope without losing the real reason. Only raised for 4xx
    responses; a 5xx from Supabase (or a network failure) is treated as a genuine
    infrastructure failure and left to propagate as the existing unhandled-exception 500 --
    this type exists to normalize *expected* auth failures, not to hide real outages.
    """

    def __init__(self, status_code: int, error_code: str | None, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message


def _to_auth_error(response: httpx.Response) -> SupabaseAuthError:
    """Parses whatever structured body Supabase actually returned, rather than pattern-matching
    on status code alone -- GoTrue uses two different shapes across its endpoints: signup/signin
    errors carry `error_code`/`msg` (e.g. `{"error_code": "email_address_invalid", "msg": ...}`),
    while the password-grant token endpoint uses OAuth2's `error`/`error_description`. Falls back
    to the raw response text if the body isn't JSON at all, so the real reason is never lost."""
    try:
        body = response.json()
    except ValueError:
        return SupabaseAuthError(response.status_code, None, response.text or "Supabase Auth rejected the request")

    error_code = body.get("error_code") or body.get("error")
    message = body.get("msg") or body.get("error_description") or error_code or "Supabase Auth rejected the request"
    return SupabaseAuthError(response.status_code, error_code, message)


class PasswordResetMisconfigured(Exception):
    """The reset link this deployment would email is one Supabase will not honour.

    Raised *instead of* sending, because the alternative is a cheerful "check your inbox"
    followed by a 404 -- Supabase answers `/auth/v1/recover` with the same 200 whether or not
    it kept our `redirect_to`, so this is the only point at which the difference is visible.
    Carries the operator-facing fix in `detail`; the route logs that and tells the user
    something honest and short.
    """

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class SupabaseAuthClient(Protocol):
    async def sign_up(self, *, email: str, password: str) -> dict: ...
    async def sign_in(self, *, email: str, password: str) -> dict: ...
    async def refresh_session(self, *, refresh_token: str) -> dict: ...
    async def request_password_reset(self, *, email: str, redirect_to: str | None = None) -> None: ...
    async def confirm_password_reset(self, *, access_token: str, new_password: str) -> None: ...


class HttpxSupabaseAuthClient:
    """Calls Supabase Auth's own REST API for password hashing and session-token issuance --
    this backend never implements either itself."""

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        self._settings = settings
        self._base_url = settings.supabase_url
        self._api_key = settings.supabase_publishable_key
        self._redirect_url = settings.password_reset_redirect
        # None means "real network" (httpx's own default) -- only ever overridden by tests, to
        # exercise this exact error-classification logic against a mocked Supabase response
        # instead of duplicating `_call` in the test suite.
        self._transport = transport

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict | None = None,
        bearer: str | None = None,
    ) -> httpx.Response:
        """Shared request/error-classification plumbing for every Supabase Auth call --
        `_call` (signup/signin) and the password-reset proxy methods below all funnel through
        this so the 4xx/5xx split only lives in one place."""
        headers = {"apikey": self._api_key, "Content-Type": "application/json"}
        if bearer is not None:
            headers["Authorization"] = f"Bearer {bearer}"
        async with httpx.AsyncClient(transport=self._transport) as client:
            response = await client.request(
                method, f"{self._base_url}{path}", json=json, params=params, headers=headers
            )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Only 4xx is a *known* auth rejection worth normalizing -- a 5xx here means
            # Supabase's own infrastructure is failing, which is a real outage, not a
            # rejected login/signup, so it falls through to the generic 500 unchanged.
            if 400 <= exc.response.status_code < 500:
                raise _to_auth_error(exc.response) from exc
            raise
        return response

    async def _call(self, path: str, payload: dict) -> dict:
        response = await self._request("POST", path, json=payload)
        data = response.json()
        # A 200 with no session at all means Supabase didn't issue one (e.g. the project still
        # requires email confirmation) -- an unhandled KeyError on the lines below would surface
        # as an opaque 500 instead of the normal, mapped 4xx `routes/auth.py` already handles.
        if "access_token" not in data or "user" not in data:
            raise SupabaseAuthError(
                502,
                "no_session_returned",
                "Supabase Auth did not return a session for this request "
                "(email confirmation may still be required on this project)",
            )
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

    async def refresh_session(self, *, refresh_token: str) -> dict:
        """Trades a refresh token for a fresh access token via Supabase's refresh grant.

        Supabase access tokens expire after an hour by default -- comfortably shorter than a
        four-quarter run takes to play. Without this the session simply died mid-run and the
        frontend's 401 handler signed the CEO out somewhere around Q3, which is exactly what
        the refresh token issued alongside every session is for.
        """
        return await self._call(
            "/auth/v1/token?grant_type=refresh_token", {"refresh_token": refresh_token}
        )

    async def request_password_reset(self, *, email: str, redirect_to: str | None = None) -> None:
        """Proxies to `/auth/v1/recover` -- Supabase emails a recovery link itself and, like
        signup, never reveals whether the address is actually registered.

        `redirect_to` is the landing page the emailed link carries. The route resolves it from
        the requesting origin (`Settings.reset_redirect_for`) so the link points back at the
        deployment the user is actually on; the configured fallback is used only when it is
        omitted, which is what a non-browser caller does.

        Checks that Supabase will actually honour that landing page before sending anything.
        One extra GET is worth strictly more than a 404 in someone's inbox, and this endpoint
        is rate-limited by Supabase to a handful of calls an hour regardless.
        """
        target = redirect_to or self._redirect_url
        probe = await probe_password_reset_redirect(
            self._settings, redirect_to=target, transport=self._transport
        )
        if not probe.ok:
            raise PasswordResetMisconfigured(probe.detail)
        params = {"redirect_to": target} if target else None
        await self._request("POST", "/auth/v1/recover", json={"email": email}, params=params)

    async def confirm_password_reset(self, *, access_token: str, new_password: str) -> None:
        """Proxies to `PUT /auth/v1/user` using the short-lived access token Supabase's
        recovery-link redirect carries -- the same token the frontend reads out of the URL
        fragment (`#access_token=...&type=recovery`, never sent to any server)."""
        await self._request(
            "PUT", "/auth/v1/user", json={"password": new_password}, bearer=access_token
        )


@dataclass(frozen=True)
class RedirectProbe:
    """What Supabase actually does with our configured `redirect_to`."""

    ok: bool
    configured: str
    landed_on: str
    detail: str


async def probe_password_reset_redirect(
    settings: Settings,
    *,
    redirect_to: str | None = None,
    transport: httpx.BaseTransport | None = None,
) -> RedirectProbe:
    """Ask Supabase, without sending anyone an email, where a reset link would actually land.

    GoTrue validates `redirect_to` against the project's allow-list *before* it validates the
    token itself, so a deliberately-bogus token is enough: an allow-listed URL comes back in
    the `Location` header, and a rejected one is silently swapped for the project's Site URL.
    That silent swap is unobservable from `/auth/v1/recover` (which answers 200 either way),
    so without this check a misconfigured allow-list only shows up as a 404 in a user's inbox.

    Called at startup against the configured fallback, and again per request against the URL a
    reset is actually about to be emailed with -- one cheap GET is worth strictly more than a
    404 in someone's inbox, and this endpoint is rate-limited by Supabase regardless.

    Never raises -- a probe that cannot reach Supabase reports itself as inconclusive rather
    than taking startup down with it.
    """
    configured = redirect_to or settings.password_reset_redirect
    if not settings.supabase_url:
        return RedirectProbe(True, configured, "", "no Supabase URL configured; probe skipped")

    try:
        async with httpx.AsyncClient(transport=transport, timeout=10.0) as client:
            response = await client.get(
                f"{settings.supabase_url}/auth/v1/verify",
                params={"token": "redirect-allow-list-probe", "type": "recovery", "redirect_to": configured},
                headers={"apikey": settings.supabase_publishable_key},
                follow_redirects=False,
            )
    except httpx.HTTPError as exc:
        return RedirectProbe(True, configured, "", f"could not reach Supabase Auth ({exc!r}); probe inconclusive")

    location = response.headers.get("location", "")
    if not location:
        return RedirectProbe(True, configured, "", "Supabase did not redirect; probe inconclusive")

    # Supabase appends the failure as a fragment (`#error=...`) -- the part before it is the
    # target it chose, which is the only thing being checked here.
    landed_on = location.split("#", 1)[0].split("?", 1)[0].rstrip("/")
    ok = landed_on == configured.split("#", 1)[0].split("?", 1)[0].rstrip("/")
    detail = (
        "Supabase honours this redirect"
        if ok
        else (
            f"Supabase rejected {configured!r} and fell back to the project's Site URL "
            f"({landed_on!r}). Password-reset links will land there instead of on the "
            "reset-password page. Fix: Supabase dashboard -> Authentication -> URL "
            f"Configuration -> add {configured!r} to Redirect URLs (and make sure Site URL is "
            "a real URL, not a wildcard pattern)."
        )
    )
    return RedirectProbe(ok, configured, landed_on, detail)


def get_supabase_auth_client(settings: Settings = Depends(get_settings)) -> SupabaseAuthClient:
    """FastAPI dependency -- a bare import would make the real Supabase client impossible to
    swap out in tests via `app.dependency_overrides`, the same mechanism already used for
    `get_db`."""
    return HttpxSupabaseAuthClient(settings)

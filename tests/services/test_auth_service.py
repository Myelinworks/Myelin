"""`HttpxSupabaseAuthClient._call`'s error-classification boundary: a 4xx from Supabase Auth is
a *known* rejection (bad credentials, rejected signup input, rate limit) and gets normalized to
`SupabaseAuthError`; a 5xx, or a transport-level failure that never produces a response at all,
is a genuine infrastructure problem and must propagate unchanged -- no test here should catch
those as `SupabaseAuthError`. `routes/auth.py`'s mapping of `SupabaseAuthError` to this API's own
envelope is covered separately in `tests/routes/test_authorization.py`.

Each test injects an `httpx.MockTransport` via `HttpxSupabaseAuthClient`'s own `transport`
parameter, exercising the real `_call` implementation against a scripted Supabase response
rather than duplicating it.
"""

import httpx
import pytest

from app.core.config import Settings
from app.services.auth_service import (
    HttpxSupabaseAuthClient,
    SupabaseAuthError,
    probe_password_reset_redirect,
)

SETTINGS = Settings(supabase_url="https://example.supabase.co", supabase_publishable_key="test-key")


def _client_with(handler) -> HttpxSupabaseAuthClient:
    return HttpxSupabaseAuthClient(SETTINGS, transport=httpx.MockTransport(handler))


async def test_rejected_signup_input_becomes_a_known_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400, json={"code": 400, "error_code": "email_address_invalid", "msg": "Email address is invalid"}
        )

    client = _client_with(handler)

    with pytest.raises(SupabaseAuthError) as exc_info:
        await client.sign_up(email="bad@nowhere.invalid", password="correct horse battery staple")

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "email_address_invalid"
    assert exc_info.value.message == "Email address is invalid"


async def test_bad_login_credentials_become_a_known_auth_error():
    """GoTrue's password-grant endpoint uses OAuth2's `error`/`error_description` shape, not
    the `error_code`/`msg` shape signup/rate-limit responses use -- confirms `_to_auth_error`
    reads both, not just one."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant", "error_description": "Invalid login credentials"})

    client = _client_with(handler)

    with pytest.raises(SupabaseAuthError) as exc_info:
        await client.sign_in(email="student@myelin.dev", password="wrong-password")

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code == "invalid_grant"
    assert exc_info.value.message == "Invalid login credentials"


async def test_rate_limit_becomes_a_known_auth_error_with_429():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429, json={"code": 429, "error_code": "over_email_send_rate_limit", "msg": "email rate limit exceeded"}
        )

    client = _client_with(handler)

    with pytest.raises(SupabaseAuthError) as exc_info:
        await client.sign_up(email="student@myelin.dev", password="correct horse battery staple")

    assert exc_info.value.status_code == 429
    assert exc_info.value.error_code == "over_email_send_rate_limit"


async def test_non_json_4xx_body_falls_back_to_raw_text():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="Bad Request")

    client = _client_with(handler)

    with pytest.raises(SupabaseAuthError) as exc_info:
        await client.sign_in(email="student@myelin.dev", password="wrong-password")

    assert exc_info.value.status_code == 400
    assert exc_info.value.error_code is None
    assert exc_info.value.message == "Bad Request"


async def test_supabase_5xx_is_a_real_outage_not_a_known_auth_error():
    """A 5xx means Supabase's own infrastructure is failing -- this must NOT be normalized into
    `SupabaseAuthError`; it has to keep propagating as the original `httpx.HTTPStatusError` so
    it surfaces as the existing generic 500, unchanged."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, text="Service Unavailable")

    client = _client_with(handler)

    with pytest.raises(httpx.HTTPStatusError):
        await client.sign_in(email="student@myelin.dev", password="correct horse battery staple")


async def test_network_failure_propagates_unchanged():
    """No response at all (DNS failure, connection refused, timeout, ...) never reaches the
    4xx/5xx branch -- confirms a transport-level failure isn't accidentally caught anywhere
    on this path either."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = _client_with(handler)

    with pytest.raises(httpx.ConnectError):
        await client.sign_in(email="student@myelin.dev", password="correct horse battery staple")


async def test_signup_without_a_session_becomes_a_known_auth_error_not_a_keyerror():
    """When the Supabase project still requires email confirmation, `/signup` returns 200 with
    a bare user object -- no `access_token`, no `user` wrapper. Must not surface as a raw
    `KeyError` (-> opaque 500); `routes/auth.py` already knows how to map `SupabaseAuthError`."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "abc-123", "email": "student@myelin.dev", "aud": "authenticated"})

    client = _client_with(handler)

    with pytest.raises(SupabaseAuthError) as exc_info:
        await client.sign_up(email="student@myelin.dev", password="correct horse battery staple")

    assert exc_info.value.status_code == 502
    assert exc_info.value.error_code == "no_session_returned"


async def test_forgot_password_calls_recover_with_redirect_to():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content
        return httpx.Response(200, json={})

    settings = Settings(
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="test-key",
        password_reset_redirect_url="http://localhost:3000/reset-password",
    )
    client = HttpxSupabaseAuthClient(settings, transport=httpx.MockTransport(handler))

    await client.request_password_reset(email="student@myelin.dev")

    assert "/auth/v1/recover" in captured["url"]
    assert "redirect_to=http" in captured["url"]


async def test_forgot_password_rate_limit_becomes_a_known_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429, json={"code": 429, "error_code": "over_email_send_rate_limit", "msg": "email rate limit exceeded"}
        )

    client = _client_with(handler)

    with pytest.raises(SupabaseAuthError) as exc_info:
        await client.request_password_reset(email="student@myelin.dev")

    assert exc_info.value.status_code == 429


async def test_reset_password_sends_bearer_and_new_password():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["auth_header"] = request.headers.get("authorization")
        captured["body"] = request.content
        return httpx.Response(200, json={"id": "abc-123"})

    client = _client_with(handler)

    await client.confirm_password_reset(access_token="recovery-token", new_password="new correct horse battery")

    assert captured["auth_header"] == "Bearer recovery-token"
    assert b"new correct horse battery" in captured["body"]


async def test_reset_password_expired_token_becomes_a_known_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error_code": "invalid_token", "msg": "Token has expired or is invalid"})

    client = _client_with(handler)

    with pytest.raises(SupabaseAuthError) as exc_info:
        await client.confirm_password_reset(access_token="stale-token", new_password="new correct horse battery")

    assert exc_info.value.status_code == 401


async def test_refresh_uses_the_refresh_grant_and_returns_a_new_session():
    """A run outlives Supabase's ~1h access token, so the session has to be renewable. The
    refresh grant takes `refresh_token`, not credentials, and answers with the same session
    shape `/login` does."""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = request.content
        return httpx.Response(
            200,
            json={
                "access_token": "fresh-access-token",
                "refresh_token": "next-refresh-token",
                "user": {"id": "11111111-1111-1111-1111-111111111111", "email": "student@myelin.dev"},
            },
        )

    result = await _client_with(handler).refresh_session(refresh_token="old-refresh-token")

    assert "grant_type=refresh_token" in captured["url"]
    assert b"old-refresh-token" in captured["body"]
    assert result["access_token"] == "fresh-access-token"
    assert result["refresh_token"] == "next-refresh-token"


async def test_refresh_with_a_dead_token_becomes_a_known_auth_error():
    """A revoked/already-spent refresh token is the one case where the user really does have to
    log in again -- it must arrive as a mapped rejection, not an opaque 500."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": "invalid_grant", "error_description": "Invalid Refresh Token"})

    with pytest.raises(SupabaseAuthError) as exc_info:
        await _client_with(handler).refresh_session(refresh_token="spent-token")

    assert exc_info.value.status_code == 400
    assert exc_info.value.message == "Invalid Refresh Token"


async def test_recover_derives_the_redirect_from_frontend_url_when_unset():
    """A blank `PASSWORD_RESET_REDIRECT_URL` used to mean "send no redirect_to at all", which
    hands Supabase the choice -- and Supabase chooses the project's Site URL. There is now
    always a redirect_to, derived from `FRONTEND_URL`."""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={})

    settings = Settings(
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="test-key",
        frontend_url="https://myelin.example/",
        password_reset_redirect_url="",
    )
    client = HttpxSupabaseAuthClient(settings, transport=httpx.MockTransport(handler))

    await client.request_password_reset(email="student@myelin.dev")

    assert "redirect_to=https%3A%2F%2Fmyelin.example%2Freset-password" in captured["url"]


async def test_probe_reports_a_redirect_supabase_honours():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            303, headers={"location": "http://localhost:3000/reset-password#access_token=x&type=recovery"}
        )

    probe = await probe_password_reset_redirect(SETTINGS, transport=httpx.MockTransport(handler))

    assert probe.ok


async def test_probe_catches_the_silent_fallback_to_the_site_url():
    """The exact failure that made every reset link a 404: Supabase drops a redirect_to that is
    not allow-listed and substitutes the project's Site URL, without ever saying so."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            303, headers={"location": "https://some-other-host.example/**#error=access_denied"}
        )

    probe = await probe_password_reset_redirect(SETTINGS, transport=httpx.MockTransport(handler))

    assert not probe.ok
    assert probe.landed_on == "https://some-other-host.example/**"
    assert "Redirect URLs" in probe.detail


async def test_probe_never_takes_startup_down_when_supabase_is_unreachable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    probe = await probe_password_reset_redirect(SETTINGS, transport=httpx.MockTransport(handler))

    assert probe.ok
    assert "inconclusive" in probe.detail


async def test_recover_prefers_the_redirect_the_route_resolved_over_the_configured_one():
    """The route reads the landing page off the requesting origin so a reset started on
    production lands on production. The configured `FRONTEND_URL` is only the fallback, and
    must not override what it was handed."""
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json={})

    settings = Settings(
        supabase_url="https://example.supabase.co",
        supabase_publishable_key="test-key",
        frontend_url="http://localhost:3000",
    )
    client = HttpxSupabaseAuthClient(settings, transport=httpx.MockTransport(handler))

    await client.request_password_reset(
        email="student@myelin.dev", redirect_to="https://myelin.example/reset-password"
    )

    assert "redirect_to=https%3A%2F%2Fmyelin.example%2Freset-password" in captured["url"]
    assert "localhost" not in captured["url"]

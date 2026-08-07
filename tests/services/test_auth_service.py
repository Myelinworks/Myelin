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
from app.services.auth_service import HttpxSupabaseAuthClient, SupabaseAuthError

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

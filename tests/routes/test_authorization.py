"""Phase 13 acceptance: identity and ownership, layered strictly in front of the gatekeeper.

Every case here reuses `test_company_routes.py`'s own HTTP helpers so a full run is built the
same way `TestFullSimulationOverHttp` builds one -- the only thing under test is *who* is
allowed to touch it, never the engine numbers themselves.

`app.dependency_overrides` is a single global dict on the shared FastAPI `app` instance, so
two simultaneously-live client fixtures with different `get_current_user` overrides collide --
whichever was set up last wins for *every* client's requests, not just its own. The fixtures
below all share one `AsyncClient`/`db_session` pair and swap the override immediately before
each request instead, via `_as_user`.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.main import app
from app.models.app_user import AppUser
from app.routes.deps import get_current_user
from app.services.auth_service import CurrentUser, SupabaseAuthError, get_supabase_auth_client
from tests.routes.test_company_routes import Q1_BY_DEPARTMENT, _create_company, _open_quarter


def _as_user(user: CurrentUser | None) -> None:
    """Points the shared app's `get_current_user` override at `user` for whatever request
    comes next -- `None` removes the override entirely, simulating no Bearer token at all."""
    if user is None:
        app.dependency_overrides.pop(get_current_user, None)
    else:
        app.dependency_overrides[get_current_user] = lambda: user


@pytest_asyncio.fixture
async def auth_client(db_session: AsyncSession, current_test_user: CurrentUser):
    """One client, one shared identity dict -- starts authenticated as `current_test_user`
    (the same student `company_and_quarter`/`_create_company` calls end up owned by)."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    _as_user(current_test_user)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def other_user(db_session: AsyncSession) -> CurrentUser:
    other = AppUser(id=uuid.uuid4(), email="other@myelin.dev", role="student")
    db_session.add(other)
    await db_session.flush()
    return CurrentUser(id=other.id, email=other.email, role=other.role)


@pytest_asyncio.fixture
async def instructor_user(db_session: AsyncSession) -> CurrentUser:
    instructor = AppUser(id=uuid.uuid4(), email="prof@myelin.dev", role="instructor")
    db_session.add(instructor)
    await db_session.flush()
    return CurrentUser(id=instructor.id, email=instructor.email, role=instructor.role)


class TestCrossUserAccess:
    async def test_other_user_cannot_read_the_company(self, auth_client, current_test_user, other_user):
        _as_user(current_test_user)
        company = await _create_company(auth_client)

        _as_user(other_user)
        response = await auth_client.get(f"/companies/{company['id']}")

        assert response.status_code == 403
        assert response.json()["error"] == "not_permitted"

    async def test_other_user_cannot_read_the_run_state(self, auth_client, current_test_user, other_user):
        _as_user(current_test_user)
        company = await _create_company(auth_client)

        _as_user(other_user)
        response = await auth_client.get(f"/companies/{company['id']}/run")

        assert response.status_code == 403
        assert response.json()["error"] == "not_permitted"

    async def test_other_user_cannot_read_the_leaderboard(self, auth_client, current_test_user, other_user):
        _as_user(current_test_user)
        company = await _create_company(auth_client)

        _as_user(other_user)
        response = await auth_client.get(f"/companies/{company['id']}/leaderboard")

        assert response.status_code == 403
        assert response.json()["error"] == "not_permitted"

    async def test_other_user_cannot_open_a_quarter(self, auth_client, current_test_user, other_user):
        _as_user(current_test_user)
        company = await _create_company(auth_client)

        _as_user(other_user)
        response = await auth_client.post(f"/companies/{company['id']}/quarters")

        assert response.status_code == 403
        assert response.json()["error"] == "not_permitted"

    async def test_other_user_cannot_read_a_quarter(self, auth_client, current_test_user, other_user):
        _as_user(current_test_user)
        company = await _create_company(auth_client)
        q1 = await _open_quarter(auth_client, company["id"])

        _as_user(other_user)
        response = await auth_client.get(f"/companies/{company['id']}/quarters/{q1['id']}")

        assert response.status_code == 403
        assert response.json()["error"] == "not_permitted"

    async def test_other_user_cannot_submit_an_allocation(self, auth_client, current_test_user, other_user):
        _as_user(current_test_user)
        company = await _create_company(auth_client)
        q1 = await _open_quarter(auth_client, company["id"])

        _as_user(other_user)
        response = await auth_client.post(
            f"/companies/{company['id']}/quarters/{q1['id']}/allocations/marketing",
            json=Q1_BY_DEPARTMENT["marketing"],
        )

        assert response.status_code == 403
        assert response.json()["error"] == "not_permitted"

    async def test_other_user_cannot_lock_the_quarter(self, auth_client, current_test_user, other_user):
        _as_user(current_test_user)
        company = await _create_company(auth_client)
        q1 = await _open_quarter(auth_client, company["id"])

        _as_user(other_user)
        response = await auth_client.post(f"/companies/{company['id']}/quarters/{q1['id']}/lock")

        # Ownership is checked before legality: refused as not_permitted, not illegal_move,
        # even though locking an empty-allocation quarter would otherwise be legal.
        assert response.status_code == 403
        assert response.json()["error"] == "not_permitted"


class TestInstructorReadOnlyAccess:
    async def test_instructor_can_read_a_students_company(self, auth_client, current_test_user, instructor_user):
        _as_user(current_test_user)
        company = await _create_company(auth_client)

        _as_user(instructor_user)
        response = await auth_client.get(f"/companies/{company['id']}")

        assert response.status_code == 200

    async def test_instructor_can_read_a_students_run_state(self, auth_client, current_test_user, instructor_user):
        _as_user(current_test_user)
        company = await _create_company(auth_client)

        _as_user(instructor_user)
        response = await auth_client.get(f"/companies/{company['id']}/run")

        assert response.status_code == 200

    async def test_instructor_cannot_write_to_a_students_run(self, auth_client, current_test_user, instructor_user):
        _as_user(current_test_user)
        company = await _create_company(auth_client)

        _as_user(instructor_user)
        response = await auth_client.post(f"/companies/{company['id']}/quarters")

        assert response.status_code == 403
        assert response.json()["error"] == "not_permitted"

    async def test_instructor_cannot_submit_an_allocation(self, auth_client, current_test_user, instructor_user):
        _as_user(current_test_user)
        company = await _create_company(auth_client)
        q1 = await _open_quarter(auth_client, company["id"])

        _as_user(instructor_user)
        response = await auth_client.post(
            f"/companies/{company['id']}/quarters/{q1['id']}/allocations/marketing",
            json=Q1_BY_DEPARTMENT["marketing"],
        )

        assert response.status_code == 403
        assert response.json()["error"] == "not_permitted"


class TestUnauthenticatedAccess:
    async def test_unauthenticated_request_to_get_company_is_refused(self, auth_client):
        _as_user(None)
        response = await auth_client.get(f"/companies/{uuid.uuid4()}")

        assert response.status_code == 401
        assert response.json()["error"] == "not_authenticated"

    async def test_unauthenticated_request_to_create_company_is_refused(self, auth_client):
        _as_user(None)
        response = await auth_client.post("/companies", json={"name": "X"})

        assert response.status_code == 401
        assert response.json()["error"] == "not_authenticated"

    async def test_unauthenticated_request_to_run_state_is_refused(self, auth_client):
        _as_user(None)
        response = await auth_client.get(f"/companies/{uuid.uuid4()}/run")

        assert response.status_code == 401
        assert response.json()["error"] == "not_authenticated"


class FakeSupabaseAuthClient:
    """Stands in for `HttpxSupabaseAuthClient` -- no real network call to Supabase. Verifies
    the register/login proxy routes and their response shape, not Supabase's own crypto."""

    async def sign_up(self, *, email: str, password: str) -> dict:
        return {
            "access_token": "fake-access-token",
            "refresh_token": "fake-refresh-token",
            "user_id": str(uuid.uuid4()),
            "email": email,
        }

    async def sign_in(self, *, email: str, password: str) -> dict:
        return await self.sign_up(email=email, password=password)

    async def request_password_reset(self, *, email: str) -> None:
        return None

    async def confirm_password_reset(self, *, access_token: str, new_password: str) -> None:
        return None


class TestRegisterAndLoginProxy:
    async def test_register_calls_through_to_the_supabase_client(self, auth_client):
        _as_user(None)
        app.dependency_overrides[get_supabase_auth_client] = lambda: FakeSupabaseAuthClient()
        try:
            response = await auth_client.post(
                "/auth/register", json={"email": "student@myelin.dev", "password": "correct horse battery staple"}
            )
        finally:
            del app.dependency_overrides[get_supabase_auth_client]

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "student@myelin.dev"
        assert body["access_token"] == "fake-access-token"

    async def test_login_calls_through_to_the_supabase_client(self, auth_client):
        _as_user(None)
        app.dependency_overrides[get_supabase_auth_client] = lambda: FakeSupabaseAuthClient()
        try:
            response = await auth_client.post(
                "/auth/login", json={"email": "student@myelin.dev", "password": "correct horse battery staple"}
            )
        finally:
            del app.dependency_overrides[get_supabase_auth_client]

        assert response.status_code == 200
        assert response.json()["email"] == "student@myelin.dev"


class _FakeAuthClientThatRaises:
    """Stands in for `HttpxSupabaseAuthClient` when Supabase itself rejected the request (or
    the call failed outright) -- `error` is whatever `sign_up`/`sign_in` should raise, verifying
    `routes/auth.py`'s mapping of that failure to this API's own envelope."""

    def __init__(self, error: Exception):
        self._error = error

    async def sign_up(self, *, email: str, password: str) -> dict:
        raise self._error

    async def sign_in(self, *, email: str, password: str) -> dict:
        raise self._error

    async def request_password_reset(self, *, email: str) -> None:
        raise self._error

    async def confirm_password_reset(self, *, access_token: str, new_password: str) -> None:
        raise self._error


class TestAuthProxyFailureMapping:
    """Both routes go through the *same* Supabase call; only the mapping of a rejection differs
    (login: wrong-credentials means not-authenticated; register: rejected input means the request
    itself was malformed) -- see `routes/auth.py`."""

    async def _register_with(self, auth_client, error: Exception):
        _as_user(None)
        app.dependency_overrides[get_supabase_auth_client] = lambda: _FakeAuthClientThatRaises(error)
        try:
            return await auth_client.post(
                "/auth/register", json={"email": "student@myelin.dev", "password": "correct horse battery staple"}
            )
        finally:
            del app.dependency_overrides[get_supabase_auth_client]

    async def _login_with(self, auth_client, error: Exception):
        _as_user(None)
        app.dependency_overrides[get_supabase_auth_client] = lambda: _FakeAuthClientThatRaises(error)
        try:
            return await auth_client.post(
                "/auth/login", json={"email": "student@myelin.dev", "password": "wrong-password"}
            )
        finally:
            del app.dependency_overrides[get_supabase_auth_client]

    async def test_bad_login_credentials_return_not_authenticated_not_500(self, auth_client):
        error = SupabaseAuthError(400, "invalid_grant", "Invalid login credentials")
        response = await self._login_with(auth_client, error)

        assert response.status_code == 401
        assert response.json() == {"error": "not_authenticated"}

    async def test_rejected_registration_input_returns_422_with_supabases_reason(self, auth_client):
        error = SupabaseAuthError(400, "email_address_invalid", "Email address is invalid")
        response = await self._register_with(auth_client, error)

        assert response.status_code == 422
        assert response.json()["detail"] == "Email address is invalid"

    async def test_registration_rate_limit_returns_429_not_500(self, auth_client):
        error = SupabaseAuthError(429, "over_email_send_rate_limit", "email rate limit exceeded")
        response = await self._register_with(auth_client, error)

        assert response.status_code == 429
        assert response.json()["detail"] == "email rate limit exceeded"

    async def test_login_rate_limit_returns_429_not_401(self, auth_client):
        error = SupabaseAuthError(429, "over_email_send_rate_limit", "email rate limit exceeded")
        response = await self._login_with(auth_client, error)

        assert response.status_code == 429
        assert response.json()["detail"] == "email rate limit exceeded"

    async def test_genuine_infrastructure_failure_is_not_caught_here(self, auth_client):
        """A failure that isn't a `SupabaseAuthError` (Supabase itself down, a network error)
        must stay uncaught by `routes/auth.py`'s new try/except -- Starlette's own
        `ServerErrorMiddleware` is what turns this into the existing generic 500 in a real
        deployment (confirmed manually: an unhandled exception there returns a plain-text 500).
        `httpx`'s `ASGITransport` re-raises rather than swallowing that already-sent response,
        so the way to confirm "not caught" here is that it still propagates -- same as before
        this change, since nothing in `login`/`register` catches anything but
        `SupabaseAuthError`.
        """
        with pytest.raises(RuntimeError, match="Supabase is unreachable"):
            await self._login_with(auth_client, RuntimeError("Supabase is unreachable"))


class TestForgotAndResetPasswordProxy:
    """Same proxy shape as register/login (`TestRegisterAndLoginProxy` /
    `TestAuthProxyFailureMapping` above): a known `SupabaseAuthError` maps to this API's own
    envelope, everything else propagates unchanged."""

    async def test_forgot_password_returns_generic_ack(self, auth_client):
        _as_user(None)
        app.dependency_overrides[get_supabase_auth_client] = lambda: FakeSupabaseAuthClient()
        try:
            response = await auth_client.post("/auth/forgot-password", json={"email": "student@myelin.dev"})
        finally:
            del app.dependency_overrides[get_supabase_auth_client]

        assert response.status_code == 200
        assert "message" in response.json()

    async def test_forgot_password_rate_limit_returns_429_not_500(self, auth_client):
        _as_user(None)
        error = SupabaseAuthError(429, "over_email_send_rate_limit", "email rate limit exceeded")
        app.dependency_overrides[get_supabase_auth_client] = lambda: _FakeAuthClientThatRaises(error)
        try:
            response = await auth_client.post("/auth/forgot-password", json={"email": "student@myelin.dev"})
        finally:
            del app.dependency_overrides[get_supabase_auth_client]

        assert response.status_code == 429

    async def test_forgot_password_rejected_email_returns_422_not_500(self, auth_client):
        _as_user(None)
        error = SupabaseAuthError(400, "email_address_invalid", "Email address is invalid")
        app.dependency_overrides[get_supabase_auth_client] = lambda: _FakeAuthClientThatRaises(error)
        try:
            response = await auth_client.post("/auth/forgot-password", json={"email": "not-an-email"})
        finally:
            del app.dependency_overrides[get_supabase_auth_client]

        assert response.status_code == 422
        assert response.json()["detail"] == "Email address is invalid"

    async def test_reset_password_returns_confirmation(self, auth_client):
        _as_user(None)
        app.dependency_overrides[get_supabase_auth_client] = lambda: FakeSupabaseAuthClient()
        try:
            response = await auth_client.post(
                "/auth/reset-password",
                json={"access_token": "recovery-token", "new_password": "correct horse battery staple"},
            )
        finally:
            del app.dependency_overrides[get_supabase_auth_client]

        assert response.status_code == 200
        assert "message" in response.json()

    async def test_reset_password_expired_token_returns_422_not_500(self, auth_client):
        _as_user(None)
        error = SupabaseAuthError(401, "invalid_token", "Token has expired or is invalid")
        app.dependency_overrides[get_supabase_auth_client] = lambda: _FakeAuthClientThatRaises(error)
        try:
            response = await auth_client.post(
                "/auth/reset-password",
                json={"access_token": "stale-token", "new_password": "correct horse battery staple"},
            )
        finally:
            del app.dependency_overrides[get_supabase_auth_client]

        assert response.status_code == 422
        assert response.json()["detail"] == "Token has expired or is invalid"

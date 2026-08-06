"""Route/DB integration test infrastructure.

Runs against the same Supabase project as the app, but in a dedicated `test` Postgres
schema (via SQLAlchemy's schema_translate_map) rather than `public` -- so integration
tests never touch real application data. Each test runs inside a transaction that's
rolled back afterward, so the schema stays empty between tests without needing per-test
TRUNCATE calls.
"""

import uuid
from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.core.config import get_settings
from app.core.db import Base, get_db
from app.main import app
from app.models.app_user import AppUser
from app.routes.deps import get_current_user
from app.services.auth_service import CurrentUser

# Import every model module so Base.metadata is fully populated before create_all runs.
from app.models import (  # noqa: F401
    app_user,
    cognitive,
    company,
    company_state_snapshot,
    cx,
    decision,
    endgame_decision,
    evidence,
    finance,
    marketing,
    modifier,
    operations,
    product,
    quarter,
    quarter_allocation,
    quarter_performance,
    sales,
)

TEST_SCHEMA = "test"


@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    settings = get_settings()
    engine = create_async_engine(
        settings.database_url,
        connect_args={"statement_cache_size": 0},
    ).execution_options(schema_translate_map={None: TEST_SCHEMA})

    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {TEST_SCHEMA}"))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


@pytest_asyncio.fixture
async def current_test_user(db_session: AsyncSession) -> CurrentUser:
    """The auth-bypass fixture for route tests: provisions a `student` `AppUser` row directly
    via ORM rather than going through a real Supabase JWT. Named explicitly (not silently
    auto-applied) so a reader of a test file can see identity is being stubbed here, matching
    how `client` already stubs `get_db`.
    """
    user = AppUser(id=uuid.uuid4(), email="test@myelin.dev", role="student")
    db_session.add(user)
    await db_session.flush()
    return CurrentUser(id=user.id, email=user.email, role=user.role)


@pytest_asyncio.fixture
async def client(db_session: AsyncSession, current_test_user: CurrentUser) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def override_get_current_user() -> CurrentUser:
        return current_test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

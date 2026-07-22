"""Route/DB integration test infrastructure.

Runs against the same Supabase project as the app, but in a dedicated `test` Postgres
schema (via SQLAlchemy's schema_translate_map) rather than `public` -- so integration
tests never touch real application data. Each test runs inside a transaction that's
rolled back afterward, so the schema stays empty between tests without needing per-test
TRUNCATE calls.
"""

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.core.config import get_settings
from app.core.db import Base, get_db
from app.main import app

# Import every model module so Base.metadata is fully populated before create_all runs.
from app.models import (  # noqa: F401
    cognitive,
    company,
    cx,
    decision,
    evidence,
    finance,
    marketing,
    modifier,
    operations,
    product,
    quarter,
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
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

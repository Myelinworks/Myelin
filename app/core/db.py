from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# statement_cache_size=0 disables asyncpg's prepared-statement cache, required when
# DATABASE_URL points at a PgBouncer transaction pooler (e.g. Supabase's Supavisor) --
# transaction pooling doesn't preserve prepared statements across pooled connections,
# so caching them causes "prepared statement already exists" errors.
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"statement_cache_size": 0},
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

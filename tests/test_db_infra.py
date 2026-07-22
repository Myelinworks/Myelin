"""Smoke tests for the test-schema DB fixture itself -- verifies the real Supabase
connection, table creation in the `test` schema, and per-test rollback isolation all work
before any route tests are built on top of it.
"""

from sqlalchemy import select

from app.models.company import Company


async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_can_write_and_read_a_row(db_session):
    company = Company(name="Acme Test Co")
    db_session.add(company)
    await db_session.flush()

    result = await db_session.execute(select(Company).where(Company.name == "Acme Test Co"))
    assert result.scalar_one().name == "Acme Test Co"


async def test_previous_test_rolled_back(db_session):
    result = await db_session.execute(select(Company).where(Company.name == "Acme Test Co"))
    assert result.scalar_one_or_none() is None

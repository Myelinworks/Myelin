import pytest_asyncio

from app.models.company import Company
from app.models.quarter import Quarter, QuarterStatus


@pytest_asyncio.fixture
async def company_and_quarter(db_session):
    company = Company(name="Test Co")
    db_session.add(company)
    await db_session.flush()

    quarter = Quarter(
        company_id=company.id,
        number=1,
        status=QuarterStatus.IN_PROGRESS,
        cash_balance=100000,
        revenue=0,
    )
    db_session.add(quarter)
    await db_session.flush()

    return company, quarter

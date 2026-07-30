"""run_quarter() -- Phase 4: the persistence wrapper around the pure compute_quarter().

Uses the same `db_session` fixture the route tests use (root `tests/conftest.py`), since this
module genuinely needs a session -- it is the persistence layer, not the pure one.
"""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.company import Company
from app.models.company_state_snapshot import CompanyStateSnapshot
from app.models.quarter import Quarter, QuarterStatus
from app.models.quarter_allocation import QuarterAllocation
from app.models.quarter_performance import QuarterPerformance
from app.services.quarter_run_service import run_quarter

# docs/12-quarter-1-reference.md §12: Rs 45,00,000 across six departments.
Q1_ALLOCATION_FIELDS = dict(
    google_ads=Decimal("4.00"),
    meta_ads=Decimal("1.92"),
    social_influencer=Decimal("2.08"),
    content_seo=Decimal("1.28"),
    events_pr=Decimal("0.80"),
    email_marketing=Decimal("1.60"),
    referral=Decimal("2.40"),
    prelaunch_buzz=Decimal("1.92"),
    reps=Decimal("5.45"),
    crm_tools=Decimal("1.30"),
    onboarding=Decimal("1.25"),
    quality_qa=Decimal("2.75"),
    innovation=Decimal("2.25"),
    manufacturing=Decimal("3.30"),
    supplier_qc=Decimal("1.50"),
    logistics=Decimal("1.20"),
    culture_benefits=Decimal("1.20"),
    training_development=Decimal("0.90"),
    cx_team=Decimal("0.90"),
    compliance_legal=Decimal("2.80"),
    financial_planning=Decimal("2.10"),
    audit_prep=Decimal("2.10"),
    warranty_years=1,
)


@pytest.fixture
async def nadi_wear_company(db_session):
    company = Company(name="Nadi Wear", seed_name="nadi_wear", profile_name="default")
    db_session.add(company)
    await db_session.flush()
    return company


@pytest.fixture
async def q1_quarter(db_session, nadi_wear_company):
    quarter = Quarter(
        company_id=nadi_wear_company.id,
        number=1,
        status=QuarterStatus.IN_PROGRESS,
        cash_balance=0,
        revenue=0,
    )
    db_session.add(quarter)
    await db_session.flush()
    db_session.add(QuarterAllocation(company_id=nadi_wear_company.id, quarter_id=quarter.id, **Q1_ALLOCATION_FIELDS))
    await db_session.flush()
    return quarter


class TestQ1ThroughPersistence:
    async def test_reproduces_the_q1_headline_numbers(self, db_session, q1_quarter):
        result = await run_quarter(db_session, q1_quarter.id)

        assert result.units_sold == pytest.approx(Decimal("561.62"), abs=Decimal("1"))
        assert round(result.units_sold) == 562
        assert abs(result.net_cash_flow_inr - Decimal("-3127837")) < Decimal("1")

    async def test_locks_the_quarter(self, db_session, q1_quarter):
        await run_quarter(db_session, q1_quarter.id)
        await db_session.refresh(q1_quarter)

        assert q1_quarter.status == QuarterStatus.CLOSED

    async def test_writes_a_closing_state_snapshot(self, db_session, q1_quarter):
        await run_quarter(db_session, q1_quarter.id)

        snapshot = (
            await db_session.execute(
                select(CompanyStateSnapshot).where(CompanyStateSnapshot.quarter_id == q1_quarter.id)
            )
        ).scalar_one()
        assert snapshot.state["quarter_number"] == 2
        assert Decimal(snapshot.state["brand_score"]) > 0


class TestIdempotency:
    async def test_double_run_returns_identical_result_and_hash(self, db_session, q1_quarter):
        first = await run_quarter(db_session, q1_quarter.id)
        first_performance = (
            await db_session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == q1_quarter.id))
        ).scalar_one()
        first_hash = first_performance.result_hash

        second = await run_quarter(db_session, q1_quarter.id)

        assert second == first
        assert first_hash is not None

        performance_count = (
            await db_session.execute(
                select(func.count())
                .select_from(QuarterPerformance)
                .where(QuarterPerformance.quarter_id == q1_quarter.id)
            )
        ).scalar_one()
        snapshot_count = (
            await db_session.execute(
                select(func.count())
                .select_from(CompanyStateSnapshot)
                .where(CompanyStateSnapshot.quarter_id == q1_quarter.id)
            )
        ).scalar_one()

        assert performance_count == 1
        assert snapshot_count == 1

    async def test_hash_is_stable_not_python_hash(self, db_session, q1_quarter):
        """A stable hash must be identical across separate runs, unlike Python's salted-per-process
        hash() -- proven here by checking it survives a full second run through the DB."""
        await run_quarter(db_session, q1_quarter.id)
        performance = (
            await db_session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == q1_quarter.id))
        ).scalar_one()
        first_hash = performance.result_hash

        await run_quarter(db_session, q1_quarter.id)
        await db_session.refresh(performance)

        assert performance.result_hash == first_hash
        assert len(first_hash) == 64  # sha256 hex digest


# docs/13-quarter-2-reference.md §4: Variant A, Efficiency-Final (Rs 42,73,200). Same allocation
# as tests/engines/test_q2_conversion.py's Q2_EFFICIENCY_ALLOCATIONS -- this is the persisted
# equivalent of that pure-layer chaining test.
Q2_EFFICIENCY_ALLOCATION_FIELDS = dict(
    google_ads=Decimal("0.50"),
    meta_ads=Decimal("0.50"),
    social_influencer=Decimal("2.50"),
    content_seo=Decimal("1.50"),
    events_pr=Decimal("0.80"),
    email_marketing=Decimal("1.60"),
    referral=Decimal("2.736"),
    prelaunch_buzz=Decimal("1.364"),
    reps=Decimal("6.458"),
    crm_tools=Decimal("2.00"),
    onboarding=Decimal("2.00"),
    quality_qa=Decimal("4.00"),
    innovation=Decimal("3.00"),
    manufacturing=Decimal("1.024"),
    supplier_qc=Decimal("1.25"),
    logistics=Decimal("1.00"),
    culture_benefits=Decimal("1.50"),
    training_development=Decimal("2.00"),
    cx_team=Decimal("1.50"),
    compliance_legal=Decimal("2.20"),
    financial_planning=Decimal("1.80"),
    audit_prep=Decimal("1.50"),
    warranty_years=2,
)


class TestQ1ToQ2CarryForwardSurvivesPersistence:
    """tests/engines/test_q2_conversion.py already proves the pure chain carries Q1's closing
    state into Q2 correctly. That does not prove the persistence layer round-trips CompanyState
    through JSON without loss -- this does, by locking Q1 through run_quarter(), creating Q2 from
    the *persisted* snapshot (not the in-memory pure result), locking Q2, and checking it still
    reproduces the doc's figures.
    """

    async def test_q2_efficiency_reproduces_the_doc_through_persisted_state(
        self, db_session, nadi_wear_company, q1_quarter
    ):
        await run_quarter(db_session, q1_quarter.id)

        q2 = Quarter(
            company_id=nadi_wear_company.id,
            number=2,
            status=QuarterStatus.IN_PROGRESS,
            cash_balance=0,
            revenue=0,
        )
        db_session.add(q2)
        await db_session.flush()
        db_session.add(
            QuarterAllocation(company_id=nadi_wear_company.id, quarter_id=q2.id, **Q2_EFFICIENCY_ALLOCATION_FIELDS)
        )
        await db_session.flush()

        result = await run_quarter(db_session, q2.id)

        # docs/13-quarter-2-reference.md §4: raw 28.4%, final Conversion Rate 27.0%. Neither
        # depends on Repeat Purchase Rate, so both reproduce the doc exactly through persistence.
        assert abs(result.raw_conversion_pct - Decimal("28.4")) < Decimal("0.05")
        assert abs(result.conversion_rate_pct - Decimal("27.0")) < Decimal("0.1")

        # units_sold does NOT reproduce the doc's 872 -- the real Nadi Wear seed's opening Repeat
        # Purchase Rate is null (see the P1 gap in docs/10-implementation-gaps.md this test
        # discovered), so Q1's actual closing rate is ~8.99%, not the doc's assumed 19.0%, and
        # free repeat units fall ~56 units short. This asserts the value the engine is actually,
        # correctly producing from real opening data -- not the doc's figure, which assumes an
        # opening rate nothing in the seed states.
        assert abs(result.units_sold - Decimal("816")) < Decimal("1")

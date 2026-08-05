"""run_quarter() -- Phase 4: the persistence wrapper around the pure compute_quarter().

Uses the same `db_session` fixture the route tests use (root `tests/conftest.py`), since this
module genuinely needs a session -- it is the persistence layer, not the pure one.
"""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models.company import Company
from app.models.company_state_snapshot import CompanyStateSnapshot
from app.models.evidence import EvidenceRecord
from app.models.quarter import Quarter, QuarterStatus
from app.models.quarter_allocation import QuarterAllocation
from app.models.quarter_performance import QuarterPerformance
from app.engines.survival import RunStatus
from app.services.company_service import assign_crisis_scenario
from app.services.quarter_run_service import _result_hash, run_quarter

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


class TestScorePersistence:
    """Phase 7 T3: the CEO score is computed and persisted in the same transaction as the engine
    result, and re-locking returns the identical score and hash."""

    async def test_score_is_persisted_on_lock(self, db_session, q1_quarter):
        await run_quarter(db_session, q1_quarter.id)

        performance = (
            await db_session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == q1_quarter.id))
        ).scalar_one()

        assert performance.ceo_score is not None
        assert performance.score_band is not None
        assert performance.trait_points is not None
        assert performance.modifiers_applied is not None
        assert performance.unscored_criteria is not None

    async def test_nadi_wear_q1_modifiers_match_the_pure_engine_test(self, db_session, q1_quarter):
        """docs/12-quarter-1-reference.md: profitability fires negative, perfect-channel-match
        fires positive (Referral hit its Rs 2,40,000 cap exactly). Same facts as
        tests/engines/test_scoring.py::TestNadiWearQ1, verified here through the DB round-trip."""
        await run_quarter(db_session, q1_quarter.id)

        performance = (
            await db_session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == q1_quarter.id))
        ).scalar_one()

        modifiers = {m["id"]: m for m in performance.modifiers_applied}
        assert modifiers["profitability_achieved"]["fired"] is False
        assert modifiers["perfect_channel_match"]["fired"] is True
        assert Decimal(modifiers["perfect_channel_match"]["applied_points"]) == 2

    async def test_leadership_is_unscored_in_the_persisted_breakdown(self, db_session, q1_quarter):
        await run_quarter(db_session, q1_quarter.id)

        performance = (
            await db_session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == q1_quarter.id))
        ).scalar_one()

        leadership_ids = {c["id"] for c in performance.unscored_criteria if c["trait"] == "leadership"}
        assert leadership_ids == {"leadership_1", "leadership_2", "leadership_3"}

    async def test_relocking_returns_the_identical_score_and_hash(self, db_session, q1_quarter):
        await run_quarter(db_session, q1_quarter.id)
        first = (
            await db_session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == q1_quarter.id))
        ).scalar_one()
        first_score, first_band, first_hash = first.ceo_score, first.score_band, first.result_hash
        first_traits, first_modifiers = first.trait_points, first.modifiers_applied

        await run_quarter(db_session, q1_quarter.id)
        await db_session.refresh(first)

        assert first.ceo_score == first_score
        assert first.score_band == first_band
        assert first.result_hash == first_hash
        assert first.trait_points == first_traits
        assert first.modifiers_applied == first_modifiers


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

    async def test_rerunning_a_locked_quarter_does_not_re_evaluate_survival(
        self, db_session, nadi_wear_company, q1_quarter
    ):
        """The lock guard returns before survival runs at all, so a second call cannot move the
        status -- important because `buffer_breached` is "at any point" and `sustained_decline`
        counts a streak, so a re-evaluation on a longer history could legitimately reach a
        different answer and silently rewrite a recorded outcome.
        """
        await run_quarter(db_session, q1_quarter.id)
        performance = (
            await db_session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == q1_quarter.id))
        ).scalar_one()
        first_status, first_hash = nadi_wear_company.run_status, performance.result_hash

        await run_quarter(db_session, q1_quarter.id)
        await db_session.refresh(nadi_wear_company)
        await db_session.refresh(performance)

        assert nadi_wear_company.run_status == first_status == RunStatus.ACTIVE
        assert performance.result_hash == first_hash

    async def test_run_status_is_part_of_the_hash(self, db_session, q1_quarter):
        """Two quarters with identical numbers but different run status are different outcomes,
        and a hash that ignored status would call them the same.
        """
        await run_quarter(db_session, q1_quarter.id)
        performance = (
            await db_session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == q1_quarter.id))
        ).scalar_one()

        score_hash_input = {
            "trait_points": performance.trait_points,
            "modifiers_applied": performance.modifiers_applied,
        }
        assert performance.result_hash != _result_hash(
            performance.engine_result, RunStatus.DISTRESSED, score_hash_input
        )
        assert performance.result_hash == _result_hash(
            performance.engine_result, RunStatus.ACTIVE, score_hash_input
        )

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

        # docs/13-quarter-2-reference.md §4: raw 28.4%, Conversion Rate 27.0%, 872 units.
        assert abs(result.raw_conversion_pct - Decimal("28.4")) < Decimal("0.05")
        assert abs(result.conversion_rate_pct - Decimal("27.0")) < Decimal("0.1")
        assert abs(result.units_sold - Decimal("872")) < Decimal("1")

        # docs/13 §4: "Available to Sell = 300 + 729 (carried inventory) = 1,029". Q2 is the
        # first quarter where attrition is non-zero, so this is the only carry-forward assertion
        # that can catch the attrition discount going missing from Production Capacity again --
        # reliability alone would give 1,052. Kept at +/-1, not widened to accommodate anything.
        assert abs(result.available_to_sell - Decimal("1029")) < Decimal("1")

        # The free-repeat-units term is what the derived opening Repeat Purchase Rate feeds, and
        # it is the whole difference between this and the ~816 units the null seed produced
        # before Phase 5 closed that gap (docs/13 §4 quotes 107).
        assert abs(result.free_repeat_units - Decimal("107")) < Decimal("1")


class TestEvidencePersistence:
    """Phase 8: `extract_evidence` runs inside the same lock transaction as the result and the
    score, writing `EvidenceRecord` rows tagged `decision_id=None` -- the new pipeline's rows,
    distinct from anything the legacy per-decision evidence engine writes."""

    async def test_evidence_is_persisted_on_lock(self, db_session, q1_quarter):
        await run_quarter(db_session, q1_quarter.id)

        rows = (
            await db_session.execute(select(EvidenceRecord).where(EvidenceRecord.quarter_id == q1_quarter.id))
        ).scalars().all()

        assert len(rows) == 22
        assert all(row.decision_id is None for row in rows)
        assert all(row.workspace is None for row in rows)
        assert {row.department for row in rows if row.department is not None} == {
            "marketing", "sales", "rnd", "operations", "hr", "finance_admin",
        }

    async def test_nadi_wear_q1_required_flags_survive_the_db_round_trip(self, db_session, q1_quarter):
        """Same facts as tests/engines/test_evidence.py::TestNadiWearQ1RequiredFlags, checked here
        through the persisted JSONB round-trip."""
        await run_quarter(db_session, q1_quarter.id)

        rows = (
            await db_session.execute(select(EvidenceRecord).where(EvidenceRecord.quarter_id == q1_quarter.id))
        ).scalars().all()
        by_key = {row.evidence_key: row for row in rows}

        assert by_key["marketing_diversification"].evidence_value["channels_funded"] == 7
        assert by_key["marketing_cac_discipline"].evidence_value["at_cap"] is True
        assert by_key["finance_cash_preservation"].evidence_value["buffer_preserved"] is True

    async def test_evidence_does_not_enter_the_result_hash(self, db_session, q1_quarter):
        await run_quarter(db_session, q1_quarter.id)
        performance = (
            await db_session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == q1_quarter.id))
        ).scalar_one()
        hash_before = performance.result_hash

        rows = (
            await db_session.execute(select(EvidenceRecord).where(EvidenceRecord.quarter_id == q1_quarter.id))
        ).scalars().all()
        assert len(rows) == 22

        score_hash_input = {"trait_points": performance.trait_points, "modifiers_applied": performance.modifiers_applied}
        assert hash_before == _result_hash(performance.engine_result, RunStatus.ACTIVE, score_hash_input)

    async def test_relocking_is_idempotent_no_duplicate_evidence_rows(self, db_session, q1_quarter):
        await run_quarter(db_session, q1_quarter.id)
        first_rows = (
            await db_session.execute(
                select(EvidenceRecord).where(EvidenceRecord.quarter_id == q1_quarter.id).order_by(EvidenceRecord.evidence_key)
            )
        ).scalars().all()
        first_values = {row.evidence_key: row.evidence_value for row in first_rows}

        # The quarter is already CLOSED after the first call, so this is the same idempotency
        # guard TestIdempotency proves for QuarterPerformance/CompanyStateSnapshot -- run_quarter
        # short-circuits before recomputing anything.
        await run_quarter(db_session, q1_quarter.id)

        second_rows = (
            await db_session.execute(
                select(EvidenceRecord).where(EvidenceRecord.quarter_id == q1_quarter.id).order_by(EvidenceRecord.evidence_key)
            )
        ).scalars().all()
        second_values = {row.evidence_key: row.evidence_value for row in second_rows}

        assert len(first_rows) == len(second_rows) == 22
        assert first_values == second_values

    async def test_legacy_evidence_records_are_unaffected(self, db_session, q1_quarter, nadi_wear_company):
        """A pre-existing legacy-pipeline EvidenceRecord (decision_id set) for the same quarter
        must survive `run_quarter()`'s delete-and-reinsert of the new pipeline's rows untouched --
        the delete is scoped to `decision_id IS NULL`."""
        from app.models.decision import Decision, DecisionStatus, Workspace

        decision = Decision(
            quarter_id=q1_quarter.id,
            workspace=Workspace.MARKETING,
            title="legacy decision",
            decision_key="marketing_budget_allocation",
            payload={},
            status=DecisionStatus.SUBMITTED,
        )
        db_session.add(decision)
        await db_session.flush()

        legacy_record = EvidenceRecord(
            company_id=nadi_wear_company.id,
            quarter_id=q1_quarter.id,
            decision_id=decision.id,
            workspace=Workspace.MARKETING,
            evidence_key="diversified_investment",
            evidence_value="YES",
            categories=["strategic_thinking"],
        )
        db_session.add(legacy_record)
        await db_session.flush()

        await run_quarter(db_session, q1_quarter.id)
        await db_session.refresh(legacy_record)

        assert legacy_record.evidence_value == "YES"

        new_pipeline_rows = (
            await db_session.execute(
                select(func.count())
                .select_from(EvidenceRecord)
                .where(EvidenceRecord.quarter_id == q1_quarter.id, EvidenceRecord.decision_id.is_(None))
            )
        ).scalar_one()
        legacy_rows = (
            await db_session.execute(
                select(func.count())
                .select_from(EvidenceRecord)
                .where(EvidenceRecord.quarter_id == q1_quarter.id, EvidenceRecord.decision_id.is_not(None))
            )
        ).scalar_one()
        assert new_pipeline_rows == 22
        assert legacy_rows == 1


class TestCrisisPersistence:
    """Phase 10: crisis application persists through the DB round trip, inside the same lock
    transaction and result_hash as everything else."""

    @pytest.fixture
    async def q3_locked(self, db_session, nadi_wear_company):
        """Plays Q1 -> Q2 -> Q3 for a fresh company through run_quarter(), submitting a
        universally-valid crisis choice ("C", never the blocked Choice-A/Feature-Leapfrog
        combination) on whichever scenario this company's id deterministically assigns."""
        for number in (1, 2):
            quarter = Quarter(
                company_id=nadi_wear_company.id, number=number, status=QuarterStatus.IN_PROGRESS,
                cash_balance=0, revenue=0,
            )
            db_session.add(quarter)
            await db_session.flush()
            db_session.add(
                QuarterAllocation(company_id=nadi_wear_company.id, quarter_id=quarter.id, **Q1_ALLOCATION_FIELDS)
            )
            await db_session.flush()
            await run_quarter(db_session, quarter.id)

        q3 = Quarter(
            company_id=nadi_wear_company.id, number=3, status=QuarterStatus.IN_PROGRESS, cash_balance=0, revenue=0,
        )
        db_session.add(q3)
        await db_session.flush()
        db_session.add(
            QuarterAllocation(
                company_id=nadi_wear_company.id, quarter_id=q3.id,
                crisis_choice="C", comparison_ads=Decimal("5.0"), emergency_supply_fund=Decimal("1.0"),
                **Q1_ALLOCATION_FIELDS,
            )
        )
        await db_session.flush()
        await run_quarter(db_session, q3.id)
        return q3

    async def test_crisis_scenario_and_choice_persist_in_engine_result(
        self, db_session, nadi_wear_company, q3_locked
    ):
        performance = (
            await db_session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == q3_locked.id))
        ).scalar_one()
        expected_scenario = assign_crisis_scenario(nadi_wear_company.id)

        assert performance.engine_result["crisis_scenario"] == expected_scenario
        assert performance.engine_result["crisis_choice"] == "C"

    async def test_crisis_modifiers_are_persisted(self, db_session, q3_locked):
        performance = (
            await db_session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == q3_locked.id))
        ).scalar_one()
        modifier_ids = {m["id"] for m in performance.modifiers_applied}

        assert {
            "crisis_fully_neutralized", "crisis_proofed_by_prior_investment",
            "structural_improvement_made", "crisis_ignored",
        }.issubset(modifier_ids)

    async def test_result_hash_covers_the_crisis_outcome(self, db_session, nadi_wear_company, q3_locked):
        performance = (
            await db_session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == q3_locked.id))
        ).scalar_one()
        await db_session.refresh(nadi_wear_company)
        score_hash_input = {"trait_points": performance.trait_points, "modifiers_applied": performance.modifiers_applied}

        assert performance.result_hash == _result_hash(
            performance.engine_result, nadi_wear_company.run_status, score_hash_input
        )
        # Tampering with the crisis outcome must move the hash -- proves it's actually inside the
        # hashed surface, not just persisted alongside it.
        tampered = dict(performance.engine_result)
        tampered["crisis_fully_neutralized"] = not tampered["crisis_fully_neutralized"]
        assert _result_hash(tampered, nadi_wear_company.run_status, score_hash_input) != performance.result_hash

    async def test_relocking_the_crisis_quarter_is_idempotent(self, db_session, q3_locked):
        first = (
            await db_session.execute(select(QuarterPerformance).where(QuarterPerformance.quarter_id == q3_locked.id))
        ).scalar_one()
        first_hash, first_result = first.result_hash, first.engine_result

        await run_quarter(db_session, q3_locked.id)
        await db_session.refresh(first)

        assert first.result_hash == first_hash
        assert first.engine_result == first_result

    async def test_crisis_allocation_fields_round_trip(self, db_session, q3_locked):
        row = (
            await db_session.execute(select(QuarterAllocation).where(QuarterAllocation.quarter_id == q3_locked.id))
        ).scalar_one()

        assert row.crisis_choice == "C"
        assert row.comparison_ads == Decimal("5.0000")
        assert row.emergency_supply_fund == Decimal("1.0000")

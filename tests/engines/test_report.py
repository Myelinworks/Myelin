"""Phase 9: the pure quarter-report assembler. No database -- every fixture here is either the
real Nadi Wear Q1/Q2 chain (reusing the already-validated fixtures from test_quarter_q1.py /
test_q2_conversion.py) or a `dataclasses.replace()` of it for edge cases (positive-NCF quarter,
missing valuation inputs), never a hand-built QuarterResult from scratch.
"""

import uuid
from dataclasses import replace
from decimal import Decimal

import pytest

from app.engines.evidence import aggregate_by_category, extract_evidence
from app.engines.quarter import compute_quarter
from app.engines.report import Metric, RunSummary, ScoreTrajectoryPoint, build_quarter_report
from app.engines.scoring import score_quarter
from app.engines.survival import RunStatus, SurvivalOutcome, evaluate_survival, tier_assignment_quarter
from tests.engines.test_q2_conversion import Q2_EFFICIENCY_ALLOCATIONS
from tests.engines.test_quarter_q1 import Q1_ALLOCATIONS, q1  # noqa: F401 -- fixture import


@pytest.fixture(scope="module")
def q1_evidence(nadi_wear, profile):
    from app.engines.state import CompanyState

    opening = CompanyState.opening(nadi_wear)
    return aggregate_by_category(extract_evidence(Q1_ALLOCATIONS, opening, profile, nadi_wear))


@pytest.fixture(scope="module")
def q1_score(q1, profile):
    return score_quarter(q1, None, Q1_ALLOCATIONS, profile.scoring)


@pytest.fixture(scope="module")
def q1_survival(q1, profile):
    return evaluate_survival([q1], profile.survival, tier_assignment_quarter(4))


@pytest.fixture(scope="module")
def q1_report(q1, q1_score, q1_evidence, q1_survival):
    return build_quarter_report(
        company_id=uuid.uuid4(),
        quarter_id=uuid.uuid4(),
        quarter_number=1,
        run_status=RunStatus.ACTIVE,
        result=q1,
        score=q1_score,
        evidence=q1_evidence,
        survival=q1_survival,
        prior_result=None,
    )


@pytest.fixture(scope="module")
def q2(q1, profile, nadi_wear):
    return compute_quarter(q1.closing_state, Q2_EFFICIENCY_ALLOCATIONS, profile, nadi_wear)


@pytest.fixture(scope="module")
def q2_report(q1, q2, profile, nadi_wear):
    from app.engines.state import CompanyState

    q2_score = score_quarter(q2, q1, Q2_EFFICIENCY_ALLOCATIONS, profile.scoring, prior_allocations=Q1_ALLOCATIONS)
    q2_evidence = aggregate_by_category(
        extract_evidence(Q2_EFFICIENCY_ALLOCATIONS, q1.closing_state, profile, nadi_wear, prior_allocations=Q1_ALLOCATIONS)
    )
    q2_survival = evaluate_survival([q1, q2], profile.survival, tier_assignment_quarter(4))
    return build_quarter_report(
        company_id=uuid.uuid4(),
        quarter_id=uuid.uuid4(),
        quarter_number=2,
        run_status=RunStatus.ACTIVE,
        result=q2,
        score=q2_score,
        evidence=q2_evidence,
        survival=q2_survival,
        prior_result=q1,
    )


class TestQ1RequiredAcceptanceNumbers:
    def test_net_cash_flow(self, q1_report):
        assert abs(q1_report.outcome.net_cash_flow_inr.value - Decimal("-3127837")) < Decimal("5")

    def test_sales_capacity_is_named_as_a_binding_gate_with_216_leads_lost(self, q1_report):
        by_gate = {bc.gate: bc for bc in q1_report.binding_constraints}
        assert "sales_capacity" in by_gate
        assert abs(by_gate["sales_capacity"].demand_lost - Decimal("216")) < Decimal("1")
        assert by_gate["sales_capacity"].demand_lost_unit == "leads"

    def test_profitability_modifier_shown_negative(self, q1_report):
        modifiers = {m.id: m for m in q1_report.decision_quality.modifiers}
        assert modifiers["profitability_achieved"].fired is False
        assert "-3,127,8" in modifiers["profitability_achieved"].detail

    def test_perfect_channel_match_shown_positive_with_cap_as_its_reason(self, q1_report):
        modifiers = {m.id: m for m in q1_report.decision_quality.modifiers}
        fact = modifiers["perfect_channel_match"]
        assert fact.fired is True
        assert fact.applied_points == 2
        assert "referral_lead_cap=800.00" in fact.detail
        assert "referral leads=800.00" in fact.detail

    def test_leadership_criteria_are_all_in_the_unscored_block(self, q1_report):
        leadership_ids = {c.id for c in q1_report.decision_quality.unscored_criteria if c.trait == "leadership"}
        assert leadership_ids == {"leadership_1", "leadership_2", "leadership_3"}
        assert all(len(c.reason) > 0 for c in q1_report.decision_quality.unscored_criteria if c.trait == "leadership")

    def test_unscored_block_matches_phase_7s_15_of_21(self, q1_report):
        assert len(q1_report.decision_quality.unscored_criteria) == 15
        assert len(q1_report.decision_quality.scored_criteria) == 6

    def test_cash_runway_matches_the_doc(self, q1_report):
        """docs/12-quarter-1-reference.md §10: "Cash Runway | ~3.8 quarters"."""
        assert q1_report.outcome.cash_runway_quarters is not None
        assert abs(q1_report.outcome.cash_runway_quarters.value - Decimal("3.8")) < Decimal("0.05")


class TestNoDeltasInQ1DeltasInQ2:
    def test_q1_has_no_deltas(self, q1_report):
        outcome = q1_report.outcome
        assert outcome.units_sold.delta is None
        assert outcome.revenue_inr.delta is None
        assert outcome.net_cash_flow_inr.delta is None
        assert outcome.closing_cash_inr.delta is None
        assert outcome.valuation_inr.delta is None

    def test_q2_deltas_equal_q2_minus_q1(self, q1, q2, q1_report, q2_report):
        assert q2_report.outcome.units_sold.delta == q2.units_sold - q1.units_sold
        assert q2_report.outcome.revenue_inr.delta == q2.revenue_inr - q1.revenue_inr
        assert q2_report.outcome.closing_cash_inr.delta == q2.closing_cash_inr - q1.closing_cash_inr

    def test_q2_valuation_delta_is_populated(self, q1, q2, q2_report):
        assert q2_report.outcome.valuation_inr.delta == q2.valuation.blended_inr - q1.valuation.blended_inr


class TestCashRunwayUndefinedWhenProfitable:
    def test_positive_ncf_has_no_runway_but_has_a_reason(self, q1):
        from app.engines.report import _company_outcome  # pure helper, safe to unit-test directly

        profitable = replace(q1, net_cash_flow_inr=Decimal("100"), closing_cash_inr=q1.closing_cash_inr)
        outcome = _company_outcome(profitable, None)
        assert outcome.cash_runway_quarters is None
        assert outcome.cash_runway_gap_reason is not None
        assert "no burn" in outcome.cash_runway_gap_reason


class TestValuationGapPassesThroughUnchanged:
    def test_none_blended_valuation_carries_its_existing_gap_reason(self, q1):
        from app.engines.report import _company_outcome

        gapped_valuation = replace(q1.valuation, blended_inr=None, gap_reason="synthetic test gap")
        gapped_result = replace(q1, valuation=gapped_valuation)
        outcome = _company_outcome(gapped_result, None)
        assert outcome.valuation_inr is None
        assert outcome.valuation_gap_reason == "synthetic test gap"


class TestScoreAndOutcomeAreSeparable:
    """The load-bearing separation: a student must never read the report as "you made money,
    therefore you scored well". Proven here by wildly changing every section-A number while
    keeping `score` identical, and asserting `decision_quality` doesn't move a single field."""

    def test_decision_quality_is_unaffected_by_outcome_numbers(self, q1, q1_score, q1_evidence, q1_survival):
        wildly_different_result = replace(
            q1,
            units_sold=Decimal("999999"),
            revenue_inr=Decimal("99999999"),
            net_cash_flow_inr=Decimal("99999999"),
            closing_cash_inr=Decimal("99999999"),
        )

        real_report = build_quarter_report(
            company_id=uuid.uuid4(), quarter_id=uuid.uuid4(), quarter_number=1, run_status=RunStatus.ACTIVE,
            result=q1, score=q1_score, evidence=q1_evidence, survival=q1_survival, prior_result=None,
        )
        mutated_report = build_quarter_report(
            company_id=uuid.uuid4(), quarter_id=uuid.uuid4(), quarter_number=1, run_status=RunStatus.ACTIVE,
            result=wildly_different_result, score=q1_score, evidence=q1_evidence, survival=q1_survival,
            prior_result=None,
        )

        assert real_report.decision_quality == mutated_report.decision_quality
        assert real_report.outcome != mutated_report.outcome


class TestFailedRunNamesTheCondition:
    def test_failed_status_and_survival_detail_surface_in_plain_language(self, q1, q1_score, q1_evidence):
        failed_result = replace(q1, closing_cash_inr=Decimal("-1"))
        survival = SurvivalOutcome(
            status=RunStatus.FAILED,
            triggered_by="cash_exhausted",
            detail="closing cash reached Rs -1.00 in Q1, at or below zero",
        )
        report = build_quarter_report(
            company_id=uuid.uuid4(), quarter_id=uuid.uuid4(), quarter_number=1, run_status=RunStatus.FAILED,
            result=failed_result, score=q1_score, evidence=q1_evidence, survival=survival, prior_result=None,
        )

        assert report.run_status == RunStatus.FAILED
        assert report.survival_triggered_by == "cash_exhausted"
        assert "at or below zero" in report.survival_detail


class TestRunSummaryIsJustAggregation:
    def test_run_summary_passes_through_unchanged_when_provided(self, q1, q1_score, q1_evidence, q1_survival):
        summary = RunSummary(
            score_trajectory=(
                ScoreTrajectoryPoint(quarter_number=1, ceo_score=Decimal("55.26"), band="Weak"),
                ScoreTrajectoryPoint(quarter_number=2, ceo_score=Decimal("70.00"), band="Competent"),
            ),
            final_valuation_inr=Decimal("100000000"),
            terminal_status=RunStatus.COMPLETED,
        )
        report = build_quarter_report(
            company_id=uuid.uuid4(), quarter_id=uuid.uuid4(), quarter_number=2, run_status=RunStatus.COMPLETED,
            result=q1, score=q1_score, evidence=q1_evidence, survival=q1_survival, prior_result=None,
            run_summary=summary,
        )
        assert report.run_summary == summary

    def test_run_summary_is_none_by_default(self, q1_report):
        assert q1_report.run_summary is None


class TestEvidenceIsCategoryAggregatedNotWorkspace:
    def test_capital_allocation_spans_multiple_departments(self, q1_report):
        capital_allocation_facts = q1_report.evidence["capital_allocation"]
        departments = {f.department for f in capital_allocation_facts}
        assert len(departments) >= 2

    def test_evidence_observations_read_as_facts_not_grades(self, q1_report):
        for facts in q1_report.evidence.values():
            for fact in facts:
                assert isinstance(fact.value, (dict, str, list, tuple))


class TestPurity:
    def test_two_builds_of_the_same_inputs_are_byte_identical(self, q1, q1_score, q1_evidence, q1_survival):
        first = build_quarter_report(
            company_id=uuid.UUID(int=1), quarter_id=uuid.UUID(int=2), quarter_number=1, run_status=RunStatus.ACTIVE,
            result=q1, score=q1_score, evidence=q1_evidence, survival=q1_survival, prior_result=None,
        )
        second = build_quarter_report(
            company_id=uuid.UUID(int=1), quarter_id=uuid.UUID(int=2), quarter_number=1, run_status=RunStatus.ACTIVE,
            result=q1, score=q1_score, evidence=q1_evidence, survival=q1_survival, prior_result=None,
        )
        assert first == second

    def test_metric_delta_is_none_not_zero_with_no_prior(self, q1_report):
        assert q1_report.outcome.units_sold.delta is None
        assert q1_report.outcome.units_sold.delta != Decimal(0)

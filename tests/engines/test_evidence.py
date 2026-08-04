"""Phase 8: the evidence pipeline on the 22 lines. Pure-layer tests -- no database.

`Q1_ALLOCATIONS`/`compute_quarter` are reused from `test_quarter_q1.py` so the Nadi Wear Q1
assertions here are checked against the exact same fixture the business-impact regression suite
already validates against `docs/12-quarter-1-reference.md`.
"""

import dataclasses
from decimal import Decimal

import pytest

from app.engines.evidence import (
    FINANCE_ADMIN,
    HR,
    MARKETING,
    OPERATIONS,
    RND,
    SALES,
    WEIGHT_CONFIRMED,
    WEIGHT_DESCRIPTIVE_ONLY,
    WEIGHT_NOT_APPLICABLE,
    aggregate_by_category,
    extract_evidence,
)
from app.engines.quarter import compute_quarter
from app.engines.state import CompanyState, QuarterAllocations
from tests.engines.test_quarter_q1 import Q1_ALLOCATIONS


@pytest.fixture(scope="module")
def opening(nadi_wear):
    return CompanyState.opening(nadi_wear)


@pytest.fixture(scope="module")
def q1_facts(opening, profile, nadi_wear):
    return extract_evidence(Q1_ALLOCATIONS, opening, profile, nadi_wear)


def _by_key(facts):
    return {f.evidence_key: f for f in facts}


class TestNadiWearQ1RequiredFlags:
    """The four flags the phase spec's acceptance criteria name explicitly."""

    def test_diversification_seven_channels_funded(self, q1_facts):
        fact = _by_key(q1_facts)["marketing_diversification"]
        assert fact.value["channels_funded"] == 7
        assert fact.value["diversified"] is True
        assert fact.value["channels"] == (
            "content_seo", "email_marketing", "events_pr", "google_ads", "meta_ads",
            "prelaunch_buzz", "social_influencer",
        )
        assert "referral" not in fact.value["channels"]

    def test_long_term_investment_buzz_and_seo(self, q1_facts):
        fact = _by_key(q1_facts)["marketing_long_term_investment"]
        assert set(fact.value["channels_funded"]) == {"content_seo", "prelaunch_buzz"}

    def test_cac_discipline_referral_at_cap_exactly(self, q1_facts):
        fact = _by_key(q1_facts)["marketing_cac_discipline"]
        assert fact.value["at_cap"] is True
        assert fact.value["leads"] == fact.value["lead_cap"] == Decimal("800.00")
        assert fact.value["wasted_spend_inr"] == Decimal("0.00")

    def test_cash_preservation_margin_is_healthy(self, q1_facts):
        """The proxy (pre-revenue discretionary margin), computed only from opening state +
        allocations -- never `closing_cash_inr`, which needs the full chain (rule 5)."""
        fact = _by_key(q1_facts)["finance_cash_preservation"]
        assert fact.value["buffer_preserved"] is True
        assert fact.value["margin_inr"] > 0

    def test_real_closing_cash_independently_confirms_the_proxy(self, opening, profile, nadi_wear):
        """Cross-validates the proxy against the real business-impact number
        (docs/12-quarter-1-reference.md: Rs 1,18,72,163 closing cash, Rs 10,00,000 buffer) without
        `evidence.py` itself ever reading `QuarterResult` -- this check lives in the test, not the
        producer."""
        result = compute_quarter(opening, Q1_ALLOCATIONS, profile, nadi_wear)
        assert result.closing_cash_inr > nadi_wear.working_capital_buffer_inr
        assert abs(result.closing_cash_inr - Decimal("11872163")) < Decimal("5")


class TestConsistentObjective:
    def test_not_applicable_in_q1_no_prior_quarter(self, q1_facts):
        fact = _by_key(q1_facts)["consistent_objective"]
        assert fact.weight_status == WEIGHT_NOT_APPLICABLE
        assert fact.value == "no_prior_quarter"

    def test_fires_true_when_no_compounding_line_dropped_to_zero(self, opening, profile, nadi_wear):
        facts = extract_evidence(Q1_ALLOCATIONS, opening, profile, nadi_wear, prior_allocations=Q1_ALLOCATIONS)
        fact = _by_key(facts)["consistent_objective"]
        assert fact.weight_status == WEIGHT_CONFIRMED
        assert fact.weight == Decimal("2.0")
        assert fact.value["consistent"] is True
        assert fact.value["dropped_to_zero"] == ()

    def test_fires_false_when_a_compounding_line_drops_to_zero(self, opening, profile, nadi_wear):
        current = dataclasses.replace(Q1_ALLOCATIONS, content_seo=Decimal(0))
        facts = extract_evidence(current, opening, profile, nadi_wear, prior_allocations=Q1_ALLOCATIONS)
        fact = _by_key(facts)["consistent_objective"]
        assert fact.value["consistent"] is False
        assert "seo" in fact.value["dropped_to_zero"]


class TestCategoryAggregation:
    def test_collapses_across_departments_not_by_workspace(self, q1_facts):
        """The load-bearing rule: a Finance fact and a Marketing fact tagged the same category
        must land in the same bucket."""
        by_category = aggregate_by_category(q1_facts)
        capital_allocation_departments = {f.department for f in by_category["capital_allocation"]}
        assert {MARKETING, FINANCE_ADMIN}.issubset(capital_allocation_departments)
        assert len(capital_allocation_departments) >= 2

    def test_every_category_is_one_of_the_seven_trait_keys(self, q1_facts, profile):
        seven_traits = set(profile.scoring.traits.keys())
        seen = {category for fact in q1_facts for category in fact.categories}
        assert seen.issubset(seven_traits)


class TestFourProblemFlagsResolved:
    def test_high_channel_dependency_and_risk_level_merged_and_descriptive_only(self, q1_facts):
        keys = _by_key(q1_facts)
        assert "high_channel_dependency" not in keys
        assert "risk_level" not in keys
        fact = keys["marketing_channel_concentration"]
        assert fact.weight_status == WEIGHT_DESCRIPTIVE_ONLY
        assert fact.value["band"] in {"Low", "Medium", "High"}

    def test_unused_budget_is_retired_not_reinvented(self, q1_facts):
        assert "unused_budget" not in _by_key(q1_facts)

    def test_consistent_objective_is_now_emitted_with_a_sourced_weight(self, opening, profile, nadi_wear):
        facts = extract_evidence(Q1_ALLOCATIONS, opening, profile, nadi_wear, prior_allocations=Q1_ALLOCATIONS)
        fact = _by_key(facts)["consistent_objective"]
        assert fact.weight == Decimal("2.0")
        assert fact.weight_status == WEIGHT_CONFIRMED


class TestEveryLineProducesEvidence:
    """Zeroing any one of the 22 lines must change the evidence set -- mechanical proof that every
    line is actually read by something, not just asserted by name."""

    _LINE_FIELDS = [f.name for f in dataclasses.fields(QuarterAllocations) if f.name != "warranty_years"]

    @pytest.mark.parametrize("line", _LINE_FIELDS)
    def test_zeroing_one_line_changes_the_evidence(self, line, opening, profile, nadi_wear, q1_facts):
        zeroed = dataclasses.replace(Q1_ALLOCATIONS, **{line: Decimal(0)})
        changed_facts = extract_evidence(zeroed, opening, profile, nadi_wear)
        assert changed_facts != q1_facts, f"zeroing '{line}' produced identical evidence"

    def test_warranty_years_is_also_covered(self, opening, profile, nadi_wear, q1_facts):
        no_warranty = dataclasses.replace(Q1_ALLOCATIONS, warranty_years=0)
        changed_facts = extract_evidence(no_warranty, opening, profile, nadi_wear)
        assert _by_key(changed_facts)["rnd_warranty_offered"].value != _by_key(q1_facts)["rnd_warranty_offered"].value


class TestPurity:
    def test_deterministic(self, opening, profile, nadi_wear):
        first = extract_evidence(Q1_ALLOCATIONS, opening, profile, nadi_wear)
        second = extract_evidence(Q1_ALLOCATIONS, opening, profile, nadi_wear)
        assert first == second

    def test_no_evidence_value_is_a_bare_numeric_score(self, q1_facts):
        """Evidence records facts, never a 0-100 style score -- the load-bearing distinction from
        the mechanical scoring engine (`engines/scoring.py`)."""
        for fact in q1_facts:
            assert not isinstance(fact.value, (int, float, Decimal)), (
                f"{fact.evidence_key} carries a bare number ({fact.value!r}) -- evidence must be a "
                f"structured fact, not a score"
            )


class TestDepartmentCoverage:
    def test_all_six_canonical_departments_are_represented(self, q1_facts):
        departments = {f.department for f in q1_facts if f.department is not None}
        assert departments == {MARKETING, SALES, RND, OPERATIONS, HR, FINANCE_ADMIN}

    def test_typical_quarter_produces_twenty_two_records(self, q1_facts):
        """21 department facts (6 marketing + 3 sales + 3 rnd + 3 operations + 3 hr + 3 finance)
        plus the one cross-quarter fact."""
        assert len(q1_facts) == 22

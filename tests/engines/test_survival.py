"""Survival evaluation -- Phase 6.

Synthetic histories are built by taking the real Nadi Wear Q1 result and `replace`-ing only the
two fields the survival rules read (`closing_cash_inr`, `net_cash_flow_inr`). That keeps every
other field internally consistent with a quarter the engine actually produced, rather than
hand-assembling a 40-field QuarterResult whose values could not co-occur.
"""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.config.loader import load_profile
from app.engines.quarter import compute_quarter
from app.engines.state import CompanyState
from app.engines.survival import RunStatus, evaluate_survival, is_terminal, tier_assignment_quarter
from tests.engines.test_quarter_q1 import Q1_ALLOCATIONS

BUFFER = Decimal("1000000")  # Nadi Wear's working capital buffer
# nadi_wear_standard runs 4 quarters, so Tier Assignment lands on Q3.
TIER_QUARTER = tier_assignment_quarter(4)


@pytest.fixture(scope="module")
def rules():
    return load_profile().survival


@pytest.fixture(scope="module")
def q1(nadi_wear, profile):
    return compute_quarter(CompanyState.opening(nadi_wear), Q1_ALLOCATIONS, profile, nadi_wear)


def _quarter(q1, *, number: int, cash: str, ncf: str):
    """A quarter with the given closing cash and net cash flow, everything else left real."""
    return replace(
        q1,
        closing_cash_inr=Decimal(cash),
        net_cash_flow_inr=Decimal(ncf),
        closing_state=replace(q1.closing_state, quarter_number=number + 1),
    )


class TestNadiWearQ1IsNotAFailure:
    """The most likely wrong implementation: treating a loss-making quarter as failure.

    Q1 loses Rs 31,27,837 and still closes at Rs 1,18,72,163 -- nearly 12x the Rs 10,00,000
    buffer. A startup burning cash to build assets is the expected shape of Q1, not a company
    in trouble.
    """

    def test_q1_alone_is_active(self, q1, rules):
        outcome = evaluate_survival([q1], rules)

        assert outcome.status is RunStatus.ACTIVE
        assert outcome.triggered_by is None

    def test_the_quarter_it_is_evaluating_really_did_lose_money(self, q1):
        """Guards the test above from passing for the wrong reason -- if Q1 ever stopped being
        loss-making, `test_q1_alone_is_active` would no longer prove anything."""
        assert q1.net_cash_flow_inr < 0
        assert abs(q1.net_cash_flow_inr - Decimal("-3127837")) < Decimal("1")
        assert q1.closing_cash_inr > q1.working_capital_buffer_inr

    def test_one_negative_quarter_is_not_a_sustained_decline(self, q1, rules):
        """The streak needs two. A single down quarter must not trip it."""
        assert evaluate_survival([q1], rules).status is RunStatus.ACTIVE


class TestCashExhausted:
    def test_zero_or_below_closing_cash_fails_the_run(self, q1, rules):
        history = [_quarter(q1, number=1, cash="-50000", ncf="-15050000")]
        outcome = evaluate_survival(history, rules)

        assert outcome.status is RunStatus.FAILED
        assert outcome.triggered_by == "cash_exhausted"
        assert "at or below zero" in outcome.detail

    def test_exactly_zero_counts_as_exhausted(self, q1, rules):
        history = [_quarter(q1, number=1, cash="0", ncf="-15000000")]

        assert evaluate_survival(history, rules).status is RunStatus.FAILED

    def test_failure_outranks_distress_when_both_fire(self, q1, rules):
        """Cash below zero is also below the buffer, so both conditions match. The run has
        failed -- reporting DISTRESSED because it happened to be checked first would be wrong.
        """
        history = [_quarter(q1, number=1, cash="-1", ncf="-15000001")]
        outcome = evaluate_survival(history, rules)

        assert outcome.status is RunStatus.FAILED
        assert outcome.triggered_by == "cash_exhausted"


class TestBufferBreached:
    def test_below_buffer_but_still_positive_is_distressed_not_failed(self, q1, rules):
        history = [_quarter(q1, number=1, cash="900000", ncf="-14100000")]
        outcome = evaluate_survival(history, rules)

        assert outcome.status is RunStatus.DISTRESSED
        assert outcome.triggered_by == "buffer_breached"
        assert is_terminal(outcome.status) is False

    def test_exactly_at_the_buffer_is_not_a_breach(self, q1, rules):
        """The rule is `closing_cash < buffer`, so landing exactly on it is not below it."""
        history = [_quarter(q1, number=1, cash=str(BUFFER), ncf="-14000000")]

        assert evaluate_survival(history, rules).status is RunStatus.ACTIVE

    def test_a_breach_marks_the_run_even_after_recovery(self, q1, rules):
        """The designer's wording is "breached at any point" -- Q2 recovering does not clear it."""
        history = [
            _quarter(q1, number=1, cash="900000", ncf="-14100000"),
            _quarter(q1, number=2, cash="9000000", ncf="8100000"),
        ]
        outcome = evaluate_survival(history, rules)

        assert outcome.status is RunStatus.DISTRESSED
        assert outcome.triggered_by == "buffer_breached"


class TestSustainedDecline:
    """Evaluated once, at the tier-assignment quarter (Q3 of a four-quarter scenario) -- it is a
    Tier Assignment input, not a running health check. See `_sustained_decline`'s docstring."""

    def test_two_consecutive_falling_quarters_is_distress_at_the_tier_quarter(self, q1, rules):
        history = [
            _quarter(q1, number=1, cash="14000000", ncf="-1000000"),
            _quarter(q1, number=2, cash="13000000", ncf="-1000000"),
            _quarter(q1, number=3, cash="12000000", ncf="-1000000"),
        ]
        outcome = evaluate_survival(history, rules, TIER_QUARTER)

        assert outcome.status is RunStatus.DISTRESSED
        assert outcome.triggered_by == "sustained_decline"
        assert "3 consecutive quarters" in outcome.detail

    def test_a_fall_that_recovers_by_the_tier_quarter_does_not_trigger(self, q1, rules):
        """The control case: cash falls in Q1 and Q2, recovers in Q3. The streak is broken at
        the quarter that counts, so the run is healthy."""
        history = [
            _quarter(q1, number=1, cash="14000000", ncf="-1000000"),
            _quarter(q1, number=2, cash="13000000", ncf="-1000000"),
            _quarter(q1, number=3, cash="15000000", ncf="2000000"),
        ]

        assert evaluate_survival(history, rules, TIER_QUARTER).status is RunStatus.ACTIVE

    def test_does_not_fire_before_the_run_reaches_the_tier_quarter(self, q1, rules):
        """Two losing quarters at Q1-Q2 is a startup burning cash, not a distressed company."""
        history = [
            _quarter(q1, number=1, cash="14000000", ncf="-1000000"),
            _quarter(q1, number=2, cash="13000000", ncf="-1000000"),
        ]

        assert evaluate_survival(history, rules, TIER_QUARTER).status is RunStatus.ACTIVE

    def test_a_verdict_raised_at_the_tier_quarter_survives_into_q4(self, q1, rules):
        """Q4 must not silently clear a distress signal Q3 legitimately raised -- Phase 11's
        tiering reads it. The streak is measured as it stood at Q3, from wherever we now are."""
        history = [
            _quarter(q1, number=1, cash="14000000", ncf="-1000000"),
            _quarter(q1, number=2, cash="13000000", ncf="-1000000"),
            _quarter(q1, number=3, cash="12000000", ncf="-1000000"),
            _quarter(q1, number=4, cash="20000000", ncf="8000000"),
        ]
        outcome = evaluate_survival(history, rules, TIER_QUARTER)

        assert outcome.status is RunStatus.DISTRESSED
        assert outcome.triggered_by == "sustained_decline"

    def test_alternating_losses_never_build_a_streak(self, q1, rules):
        history = [
            _quarter(q1, number=1, cash="14000000", ncf="-1000000"),
            _quarter(q1, number=2, cash="14500000", ncf="500000"),
            _quarter(q1, number=3, cash="13500000", ncf="-1000000"),
        ]

        assert evaluate_survival(history, rules, TIER_QUARTER).status is RunStatus.ACTIVE

    def test_stays_dormant_without_scenario_context(self, q1, rules):
        """No tier quarter supplied means the caller has no scenario context; the condition sits
        out rather than guessing a quarter to fire at."""
        history = [
            _quarter(q1, number=1, cash="14000000", ncf="-1000000"),
            _quarter(q1, number=2, cash="13000000", ncf="-1000000"),
            _quarter(q1, number=3, cash="12000000", ncf="-1000000"),
        ]

        assert evaluate_survival(history, rules).status is RunStatus.ACTIVE


class TestProfitableBurnIsNotDistressed:
    """The contradiction this scoping exists to prevent.

    `docs/13` §4's Efficiency-Final variant is scored **82/100** by the source -- a good quarter.
    Under a per-quarter reading of `sustained_decline` it came out DISTRESSED at Q2, on two
    consecutive negative-NCF quarters, while holding 11x its working capital buffer. An 82/100
    company is not distressed; that reading was wrong, and this is the regression that keeps it
    from coming back.
    """

    def test_profitable_burn_not_distressed_at_q2(self, nadi_wear, profile, q1, rules):
        from tests.engines.test_q2_conversion import Q2_EFFICIENCY_ALLOCATIONS

        q2 = compute_quarter(q1.closing_state, Q2_EFFICIENCY_ALLOCATIONS, profile, nadi_wear)
        outcome = evaluate_survival([q1, q2], rules, TIER_QUARTER)

        # both quarters really are loss-making, so this is not passing for a trivial reason
        assert q1.net_cash_flow_inr < 0 and q2.net_cash_flow_inr < 0
        # ...while sitting on many multiples of the buffer
        assert q2.closing_cash_inr > q2.working_capital_buffer_inr * 10

        assert outcome.status is RunStatus.ACTIVE
        assert outcome.triggered_by is None


class TestConfigDrivesTheConditions:
    def test_all_three_conditions_are_configured_and_implemented(self, rules):
        from app.engines.survival import PREDICATES

        assert [c.id for c in rules.conditions] == ["cash_exhausted", "buffer_breached", "sustained_decline"]
        assert all(c.id in PREDICATES for c in rules.conditions)

    def test_outcomes_map_to_real_statuses(self, rules):
        assert {c.id: c.outcome for c in rules.conditions} == {
            "cash_exhausted": "FAILED",
            "buffer_breached": "DISTRESSED",
            "sustained_decline": "DISTRESSED",
        }

    def test_the_rule_is_flagged_as_designer_specified(self, rules):
        assert rules.status == "designer_specified"
        assert "17-designer-resolutions" in rules.source

    def test_a_configured_condition_with_no_predicate_raises(self, q1, rules):
        """A check that is configured but silently does nothing is worse than one that is absent."""
        from app.config.schema import SurvivalCondition

        unimplemented = SurvivalCondition(id="runway_months", rule="runway < 2 quarters", outcome="FAILED")
        broken = rules.model_copy(update={"conditions": [*rules.conditions, unimplemented]})

        with pytest.raises(NotImplementedError, match="runway_months"):
            evaluate_survival([q1], broken)


class TestTerminality:
    def test_distressed_is_not_terminal(self):
        assert is_terminal(RunStatus.DISTRESSED) is False
        assert is_terminal(RunStatus.ACTIVE) is False

    def test_failed_and_completed_are_terminal(self):
        assert is_terminal(RunStatus.FAILED) is True
        assert is_terminal(RunStatus.COMPLETED) is True

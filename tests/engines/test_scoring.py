"""`engines/scoring.py` against `docs/10-scoring-methodology.md` and the Phase 7 acceptance list.

The mechanical half -- the 8 standard modifiers, the 4 crisis modifiers (Phase 10), the 6 Q4
modifiers (Phase 11), and the 6 MECHANICAL sub-criteria -- is what's asserted here. The JUDGMENT
sub-criteria (Leadership entirely, plus most of Strategic/Adaptability/Risk/Capital/Long-Term,
plus all of Q4's Exit & Growth trait) come back UNSCORED by design; no test here should ever
assert a numeric score for one.
"""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.config.schema import ScoringCriterion, ScoringModifier
from app.engines.endgame import EndgameFacts, Tier
from app.engines.quarter import compute_quarter
from app.engines.scoring import (
    CriterionKind,
    CriterionResult,
    _CRITERION_PREDICATES,
    _band,
    score_quarter,
)
from app.engines.state import CompanyState, CrisisEvent
from tests.engines.test_quarter_q1 import Q1_ALLOCATIONS
from tests.engines.test_quarter_q3 import (  # noqa: F401 -- q2_growth/q3_opening are fixture imports
    Q3_BASELINE,
    q2_growth,
    q3_opening,
)


@pytest.fixture(scope="module")
def rubric(profile):
    return profile.scoring


@pytest.fixture(scope="module")
def q1(nadi_wear, profile):
    return compute_quarter(CompanyState.opening(nadi_wear), Q1_ALLOCATIONS, profile, nadi_wear)


class TestCompleteness:
    """`docs/17-designer-resolutions.md` P3 and the phase spec both require every one of the 21
    sub-criteria to carry an explicit kind, checkable rather than assumed."""

    def test_all_21_sub_criteria_are_classified(self, rubric):
        assert len(rubric.criteria) == 21
        assert all(c.kind in ("MECHANICAL", "JUDGMENT") for c in rubric.criteria)

    def test_every_judgment_criterion_has_a_reason(self, rubric):
        judgment = [c for c in rubric.criteria if c.kind == "JUDGMENT"]
        assert judgment  # guards the test below from vacuously passing
        assert all(c.reason for c in judgment)

    def test_every_mechanical_criterion_has_a_registered_predicate(self, rubric):
        """A MECHANICAL criterion with no predicate must fail loudly, not silently score nothing."""
        mechanical = [c for c in rubric.criteria if c.kind == "MECHANICAL"]
        assert mechanical  # guards the assertion below from vacuously passing
        assert all(c.id in _CRITERION_PREDICATES for c in mechanical)

    def test_an_unclassified_kind_raises(self, rubric, q1):
        bogus = ScoringCriterion(
            id="bogus_criterion", trait="systems_thinking", kind="MAYBE", description="not a real kind"
        )
        broken = rubric.model_copy(update={"criteria": [*rubric.criteria, bogus]})

        with pytest.raises(NotImplementedError, match="bogus_criterion"):
            score_quarter(q1, None, Q1_ALLOCATIONS, broken)

    def test_a_mechanical_criterion_with_no_predicate_raises(self, rubric, q1):
        unimplemented = ScoringCriterion(
            id="not_a_real_criterion", trait="systems_thinking", kind="MECHANICAL", description="no predicate exists"
        )
        broken = rubric.model_copy(update={"criteria": [*rubric.criteria, unimplemented]})

        with pytest.raises(NotImplementedError, match="not_a_real_criterion"):
            score_quarter(q1, None, Q1_ALLOCATIONS, broken)

    def test_a_configured_modifier_with_no_predicate_raises(self, rubric, q1):
        unimplemented = ScoringModifier(id="not_a_real_modifier", points=Decimal(1), rule="never checked")
        broken = rubric.model_copy(
            update={"modifier_sets": {"standard": [*rubric.modifier_sets["standard"], unimplemented]}}
        )

        with pytest.raises(NotImplementedError, match="not_a_real_modifier"):
            score_quarter(q1, None, Q1_ALLOCATIONS, broken)

    def test_traits_sum_to_exactly_100(self, rubric):
        assert sum(rubric.traits.values()) == Decimal(100)

    def test_mechanical_vs_judgment_counts(self, rubric):
        """Documents the actual split so a future change to the classification is a visible diff,
        not a silent one. 6 MECHANICAL (Systems Thinking x2, Risk Management x1, Capital
        Allocation x2, Long-Term Thinking x1); the remaining 15 are JUDGMENT."""
        mechanical = sorted(c.id for c in rubric.criteria if c.kind == "MECHANICAL")
        judgment = [c.id for c in rubric.criteria if c.kind == "JUDGMENT"]

        assert mechanical == [
            "capital_allocation_2",
            "capital_allocation_3",
            "long_term_thinking_1",
            "risk_management_1",
            "systems_thinking_2",
            "systems_thinking_3",
        ]
        assert len(judgment) == 15

    def test_leadership_is_entirely_judgment(self, rubric):
        leadership = [c for c in rubric.criteria if c.trait == "leadership"]
        assert len(leadership) == 3
        assert all(c.kind == "JUDGMENT" for c in leadership)


class TestNadiWearQ1:
    """docs/12-quarter-1-reference.md: NCF = -Rs 31,27,837 (a loss), Referral hit its cap
    (Rs 2,40,000) exactly."""

    def test_profitability_fires_negative(self, q1, rubric):
        score = score_quarter(q1, None, Q1_ALLOCATIONS, rubric)
        modifier = next(m for m in score.modifiers if m.id == "profitability_achieved")

        assert q1.net_cash_flow_inr < 0
        assert modifier.fired is False
        assert modifier.applied_points == 0

    def test_perfect_channel_match_fires_positive(self, q1, rubric):
        score = score_quarter(q1, None, Q1_ALLOCATIONS, rubric)
        modifier = next(m for m in score.modifiers if m.id == "perfect_channel_match")

        assert q1.channel_leads["referral"] == q1.referral_lead_cap == Decimal(800)
        assert q1.referral_wasted_spend_inr == 0
        assert modifier.fired is True
        assert modifier.applied_points == 2


class TestStandardModifiers:
    """Every modifier checked both ways -- Q1 alone doesn't exercise every branch (e.g. Q1 is
    always capacity-bound, so zero_capacity_waste never fires there)."""

    def test_zero_capacity_waste_fires_when_leads_used_equals_effective_leads(self, q1, rubric):
        uncapped = replace(q1, leads_used=q1.effective_leads, capacity_bound=False)
        score = score_quarter(uncapped, None, Q1_ALLOCATIONS, rubric)

        assert next(m for m in score.modifiers if m.id == "zero_capacity_waste").fired is True

    def test_zero_capacity_waste_does_not_fire_in_q1(self, q1, rubric):
        """Q1 really is capacity-bound (docs/12 §4): 216 leads' worth of demand wasted."""
        score = score_quarter(q1, None, Q1_ALLOCATIONS, rubric)

        assert q1.capacity_bound is True
        assert next(m for m in score.modifiers if m.id == "zero_capacity_waste").fired is False

    def test_zero_supply_waste_fires_within_the_configured_buffer(self, q1, rubric):
        tight = replace(q1, available_to_sell=q1.units_sold + rubric.thresholds.supply_waste_units)
        score = score_quarter(tight, None, Q1_ALLOCATIONS, rubric)

        assert next(m for m in score.modifiers if m.id == "zero_supply_waste").fired is True

    def test_zero_supply_waste_does_not_fire_past_the_buffer(self, q1, rubric):
        loose = replace(q1, available_to_sell=q1.units_sold + rubric.thresholds.supply_waste_units + 1)
        score = score_quarter(loose, None, Q1_ALLOCATIONS, rubric)

        assert next(m for m in score.modifiers if m.id == "zero_supply_waste").fired is False

    def test_ceiling_undershot_fires_in_q1(self, q1, rubric):
        """Q1's raw conversion clears the R&D ceiling by more than the configured 3-point
        threshold (docs/12 §4)."""
        score = score_quarter(q1, None, Q1_ALLOCATIONS, rubric)
        gap = q1.raw_conversion_pct - q1.conversion_ceiling_pct

        assert gap > rubric.thresholds.ceiling_undershoot_points
        assert next(m for m in score.modifiers if m.id == "ceiling_undershot").fired is True
        assert next(m for m in score.modifiers if m.id == "ceiling_undershot").applied_points == -2

    def test_ceiling_undershot_does_not_fire_within_the_threshold(self, q1, rubric):
        close_to_ceiling = replace(q1, raw_conversion_pct=q1.conversion_ceiling_pct + Decimal("2.9"))
        score = score_quarter(close_to_ceiling, None, Q1_ALLOCATIONS, rubric)

        assert next(m for m in score.modifiers if m.id == "ceiling_undershot").fired is False

    def test_cash_buffer_breached_fires_when_spent_into_buffer(self, q1, rubric):
        breached = replace(q1, spent_into_buffer=True)
        score = score_quarter(breached, None, Q1_ALLOCATIONS, rubric)

        assert next(m for m in score.modifiers if m.id == "cash_buffer_breached").fired is True
        assert next(m for m in score.modifiers if m.id == "cash_buffer_breached").applied_points == -3

    def test_debt_without_justification_never_fires(self, q1, rubric):
        """No debt/loan mechanic exists in the 22-line chain -- flagged in config, not guessed."""
        score = score_quarter(q1, None, Q1_ALLOCATIONS, rubric)

        assert next(m for m in score.modifiers if m.id == "debt_without_justification").fired is False

    def test_compounding_asset_cut_needs_prior_allocations(self, q1, rubric):
        score = score_quarter(q1, None, Q1_ALLOCATIONS, rubric, prior_allocations=None)

        modifier = next(m for m in score.modifiers if m.id == "compounding_asset_cut")
        assert modifier.fired is False
        assert "no prior_allocations" in modifier.detail

    def test_compounding_asset_cut_fires_when_a_line_drops_materially(self, q1, rubric):
        cut_next_quarter = replace(Q1_ALLOCATIONS, innovation=Q1_ALLOCATIONS.innovation * Decimal("0.5"))
        score = score_quarter(q1, None, cut_next_quarter, rubric, prior_allocations=Q1_ALLOCATIONS)

        modifier = next(m for m in score.modifiers if m.id == "compounding_asset_cut")
        assert modifier.fired is True
        assert modifier.applied_points == -2

    def test_compounding_asset_cut_does_not_fire_on_a_maintained_or_increased_line(self, q1, rubric):
        score = score_quarter(q1, None, Q1_ALLOCATIONS, rubric, prior_allocations=Q1_ALLOCATIONS)

        assert next(m for m in score.modifiers if m.id == "compounding_asset_cut").fired is False


class TestScenarioDDecoupling:
    """docs/15-q3-noob-vs-expert.md Scenario D: novice NCF +Rs 13,76,454 > expert NCF
    +Rs 10,66,033, yet the expert scores 26 points higher. Crisis modifiers (Phase 10) and the
    trait/judgment layer both contribute to that 26-point gap and aren't implemented yet, so this
    doesn't try to reproduce 68 vs 94 -- it asserts the one thing the mechanical layer must already
    guarantee for that result to be possible at all: the profitability modifier is a flat +3 for
    "profitable", not a number that scales with how profitable. If this fails, the engine is
    measuring profit with extra steps.
    """

    def test_a_bigger_profit_does_not_earn_more_modifier_points(self, q1, rubric):
        novice = replace(q1, net_cash_flow_inr=Decimal("1376454"))
        expert = replace(q1, net_cash_flow_inr=Decimal("1066033"))

        novice_score = score_quarter(novice, None, Q1_ALLOCATIONS, rubric)
        expert_score = score_quarter(expert, None, Q1_ALLOCATIONS, rubric)

        novice_profitability = next(m for m in novice_score.modifiers if m.id == "profitability_achieved")
        expert_profitability = next(m for m in expert_score.modifiers if m.id == "profitability_achieved")

        assert novice.net_cash_flow_inr > expert.net_cash_flow_inr
        assert novice_profitability.fired is True
        assert expert_profitability.fired is True
        assert novice_profitability.applied_points == expert_profitability.applied_points == 3
        # Every other modifier is driven by facts unrelated to NCF magnitude, so with everything
        # else held equal the two runs' total modifier points must be identical too.
        assert novice_score.modifier_points == expert_score.modifier_points


class TestTraitScoring:
    def test_unscored_judgment_criteria_are_excluded_from_numerator_and_denominator(self, q1, rubric):
        score = score_quarter(q1, None, Q1_ALLOCATIONS, rubric)
        leadership = next(t for t in score.traits if t.trait == "leadership")

        assert leadership.weight == 10
        assert leadership.weight_scored == 0
        assert leadership.points_earned == 0
        assert all(c.result == CriterionResult.UNSCORED and c.points is None for c in leadership.criteria)

    def test_mechanical_points_available_plus_unscored_equals_100(self, q1, rubric):
        score = score_quarter(q1, None, Q1_ALLOCATIONS, rubric)

        assert score.mechanical_points_available + score.unscored_points == 100

    def test_raw_score_is_trait_points_plus_modifiers(self, q1, rubric):
        score = score_quarter(q1, None, Q1_ALLOCATIONS, rubric)

        assert score.raw_score == score.trait_points_earned + score.modifier_points

    def test_normalised_score_rescales_the_scoreable_trait_portion(self, q1, rubric):
        score = score_quarter(q1, None, Q1_ALLOCATIONS, rubric)
        expected_trait_component = score.trait_points_earned / score.mechanical_points_available * 100

        assert score.normalised_score == expected_trait_component + score.modifier_points

    def test_a_perfect_mechanical_quarter_normalises_toward_100_before_modifiers(self, q1, rubric):
        """Held-out Leadership weight must not depress the band for a quarter that aced every
        MECHANICAL check -- that's the entire reason normalisation exists."""
        perfect = replace(
            q1,
            capacity_bound=False,
            ceiling_bound=False,
            supply_bound=False,
            leads_used=q1.effective_leads,
            effective_sales_capacity=q1.effective_leads,
            total_units_demanded=q1.available_to_sell,
            discretionary_ceiling_inr=q1.total_discretionary_inr + Decimal(1),
            raw_conversion_pct=q1.conversion_ceiling_pct,
        )
        score = score_quarter(perfect, None, Q1_ALLOCATIONS, rubric)

        trait_component = score.trait_points_earned / score.mechanical_points_available * 100
        assert trait_component == Decimal(100)


class TestBands:
    def test_band_boundaries_are_inclusive_on_the_minimum(self, rubric):
        assert _band(Decimal(90), rubric) == "Exceptional"
        assert _band(Decimal("89.99"), rubric) == "Strong"
        assert _band(Decimal(75), rubric) == "Strong"
        assert _band(Decimal(60), rubric) == "Competent"
        assert _band(Decimal(40), rubric) == "Weak"
        assert _band(Decimal(0), rubric) == "Poor"
        assert _band(Decimal(-500), rubric) == "Poor"


class TestPureAndDeterministic:
    def test_scoring_the_same_inputs_twice_gives_an_identical_result(self, q1, rubric):
        first = score_quarter(q1, None, Q1_ALLOCATIONS, rubric)
        second = score_quarter(q1, None, Q1_ALLOCATIONS, rubric)

        assert first == second


@pytest.fixture(scope="module")
def crisis_result_a(q3_opening, profile, nadi_wear):
    allocations = replace(Q3_BASELINE, crisis_choice="C", comparison_ads=Decimal("10.0"))
    return compute_quarter(q3_opening, allocations, profile, nadi_wear, CrisisEvent(scenario="A"))


@pytest.fixture(scope="module")
def crisis_result_b(q3_opening, profile, nadi_wear):
    allocations = replace(
        Q3_BASELINE, crisis_choice="B",
        price_match_fund=Decimal("1.0"), comparison_ads=Decimal("4.0"), retention_offers=Decimal("1.0"),
    )
    return compute_quarter(q3_opening, allocations, profile, nadi_wear, CrisisEvent(scenario="B"))


@pytest.fixture(scope="module")
def crisis_result_c(q3_opening, profile, nadi_wear):
    allocations = replace(Q3_BASELINE, crisis_choice="C")
    return compute_quarter(q3_opening, allocations, profile, nadi_wear, CrisisEvent(scenario="C"))


@pytest.fixture(scope="module")
def crisis_result_d(q3_opening, profile, nadi_wear):
    allocations = replace(Q3_BASELINE, crisis_choice="B", emergency_supply_fund=Decimal("2.0"))
    return compute_quarter(q3_opening, allocations, profile, nadi_wear, CrisisEvent(scenario="D"))


class TestCrisisModifiers:
    """docs/14 §7's modifier table, scenario by scenario -- registering `modifier_sets.crisis`
    (Phase 10) needed no change to `score_quarter` itself, exactly per Phase 7's own design."""

    @staticmethod
    def _modifiers(result, rubric, allocations):
        score = score_quarter(
            result, None, allocations, rubric, modifier_sets=("standard", "crisis")
        )
        return {m.id: m for m in score.modifiers}

    def test_scenario_a_no_crisis_modifier_fires_net_zero(self, crisis_result_a, rubric):
        mods = self._modifiers(
            crisis_result_a, rubric, replace(Q3_BASELINE, crisis_choice="C", comparison_ads=Decimal("10.0"))
        )
        assert mods["crisis_fully_neutralized"].fired is False
        assert mods["crisis_proofed_by_prior_investment"].fired is False
        assert mods["structural_improvement_made"].fired is False
        assert mods["crisis_ignored"].fired is False
        net = sum((m.applied_points for k, m in mods.items() if k.startswith("crisis") or k == "structural_improvement_made"), Decimal(0))
        assert net == 0  # docs/14 §7: Net Modifier = 0

    def test_scenario_b_is_the_documented_binary_residual(self, crisis_result_b, rubric):
        """docs/14 gives B a 'Partial (+1)' -- docs/11 states no such tier, so
        crisis_fully_neutralized is strictly binary here and does not fire (see
        default.json's status: binary_only note). Net modifier is 0, not the doc's +1."""
        mods = self._modifiers(
            crisis_result_b, rubric,
            replace(
                Q3_BASELINE, crisis_choice="B",
                price_match_fund=Decimal("1.0"), comparison_ads=Decimal("4.0"), retention_offers=Decimal("1.0"),
            ),
        )
        assert mods["crisis_fully_neutralized"].fired is False
        assert mods["crisis_proofed_by_prior_investment"].fired is False
        assert mods["structural_improvement_made"].fired is False
        assert mods["crisis_ignored"].fired is False

    def test_scenario_c_neutralized_and_proofed_net_plus_six(self, crisis_result_c, rubric):
        mods = self._modifiers(crisis_result_c, rubric, replace(Q3_BASELINE, crisis_choice="C"))
        assert mods["crisis_fully_neutralized"].fired is True
        assert mods["crisis_proofed_by_prior_investment"].fired is True
        assert mods["structural_improvement_made"].fired is False
        assert mods["crisis_ignored"].fired is False
        net = mods["crisis_fully_neutralized"].applied_points + mods["crisis_proofed_by_prior_investment"].applied_points
        assert net == 6  # docs/14 §7: Net Modifier = +6

    def test_scenario_d_all_three_positive_modifiers_net_plus_eight(self, crisis_result_d, rubric):
        mods = self._modifiers(
            crisis_result_d, rubric, replace(Q3_BASELINE, crisis_choice="B", emergency_supply_fund=Decimal("2.0"))
        )
        assert mods["crisis_fully_neutralized"].fired is True
        assert mods["crisis_proofed_by_prior_investment"].fired is True
        assert mods["structural_improvement_made"].fired is True
        assert mods["crisis_ignored"].fired is False
        net = (
            mods["crisis_fully_neutralized"].applied_points
            + mods["crisis_proofed_by_prior_investment"].applied_points
            + mods["structural_improvement_made"].applied_points
        )
        assert net == 8  # docs/14 §7: Net Modifier = +8

    def test_crisis_ignored_fires_when_nothing_is_spent_and_nothing_is_proofed(self, q3_opening, profile, nadi_wear, rubric):
        # Choice C ("Hold Price") does nothing automatically for Scenario A (unlike Choice A,
        # which removes the conversion penalty by itself) -- zero response spend on top leaves
        # the crisis genuinely unaddressed, the case crisis_ignored exists to catch.
        allocations = replace(Q3_BASELINE, crisis_choice="C")
        result = compute_quarter(q3_opening, allocations, profile, nadi_wear, CrisisEvent(scenario="A"))
        mods = self._modifiers(result, rubric, allocations)
        assert mods["crisis_ignored"].fired is True
        assert mods["crisis_ignored"].applied_points == -4

    def test_crisis_modifiers_are_inert_off_the_crisis_quarter(self, q1, rubric):
        """None of the four crisis modifiers should ever fire for a crisis-free QuarterResult."""
        mods = self._modifiers(q1, rubric, Q1_ALLOCATIONS)
        assert all(
            mods[k].fired is False
            for k in ("crisis_fully_neutralized", "crisis_proofed_by_prior_investment", "structural_improvement_made", "crisis_ignored")
        )


class TestQ4Modifiers:
    """docs/16 section 5's 6 Q4 modifiers, registered under `modifier_sets.q4` (Phase 11).
    `score_quarter`'s own math needed no change to support them -- only the predicates and an
    `endgame_facts` parameter, per that module's own docstring."""

    @staticmethod
    def _modifiers(q1, rubric, endgame_facts):
        score = score_quarter(
            q1, None, Q1_ALLOCATIONS, rubric, modifier_sets=("standard", "q4"), endgame_facts=endgame_facts
        )
        return {m.id: m for m in score.modifiers}

    def test_all_six_q4_modifiers_are_registered(self, rubric):
        assert {m.id for m in rubric.modifier_sets["q4"]} == {
            "covenant_hit",
            "covenant_missed",
            "correct_rejection",
            "correct_acceptance",
            "value_left_on_table",
            "deliberate_independence",
        }

    def test_no_q4_modifier_fires_without_endgame_facts(self, q1, rubric):
        """A student who never reaches the Q4 decision screen still locks the quarter -- see
        quarter_run_service.py -- with every Q4 modifier configured but inert. (Standard-set
        modifiers unrelated to Q4, like perfect_channel_match, can still fire on Q1's own numbers
        -- only the 6 Q4-specific ids are asserted here.)"""
        mods = self._modifiers(q1, rubric, endgame_facts=None)
        q4_ids = {m.id for m in rubric.modifier_sets["q4"]}
        assert all(not mods[q4_id].fired for q4_id in q4_ids)

    def test_covenant_hit_fires_for_path_a_when_covenant_was_hit(self, q1, rubric):
        facts = EndgameFacts(
            path="A", tier=Tier.THRIVING, covenant_hit=True, path_b_accepted=None,
            offer_known=False, true_continuation_value_exceeds_offer=None,
        )
        mods = self._modifiers(q1, rubric, facts)
        assert mods["covenant_hit"].fired is True
        assert mods["covenant_hit"].applied_points == 5
        assert mods["covenant_missed"].fired is False

    def test_covenant_missed_fires_for_path_a_when_covenant_was_missed(self, q1, rubric):
        facts = EndgameFacts(
            path="A", tier=Tier.STABLE, covenant_hit=False, path_b_accepted=None,
            offer_known=False, true_continuation_value_exceeds_offer=None,
        )
        mods = self._modifiers(q1, rubric, facts)
        assert mods["covenant_missed"].fired is True
        assert mods["covenant_missed"].applied_points == -8
        assert mods["covenant_hit"].fired is False

    def test_covenant_modifiers_do_not_fire_outside_path_a(self, q1, rubric):
        facts = EndgameFacts(
            path="C", tier=Tier.STABLE, covenant_hit=None, path_b_accepted=False,
            offer_known=False, true_continuation_value_exceeds_offer=None,
        )
        mods = self._modifiers(q1, rubric, facts)
        assert mods["covenant_hit"].fired is False
        assert mods["covenant_missed"].fired is False

    def test_value_left_on_table_fires_for_thriving_tier_accepted_offer(self, q1, rubric):
        facts = EndgameFacts(
            path="B", tier=Tier.THRIVING, covenant_hit=None, path_b_accepted=True,
            offer_known=True, true_continuation_value_exceeds_offer=True,
        )
        mods = self._modifiers(q1, rubric, facts)
        assert mods["value_left_on_table"].fired is True
        assert mods["value_left_on_table"].applied_points == -3

    def test_value_left_on_table_does_not_fire_when_the_offer_is_unknown(self, q1, rubric):
        """Stable/Distressed tiers' Path B offers have no stated ratio -- offer_known is False,
        so there is nothing to compare against, regardless of what the caller guesses."""
        facts = EndgameFacts(
            path="B", tier=Tier.STABLE, covenant_hit=None, path_b_accepted=True,
            offer_known=False, true_continuation_value_exceeds_offer=None,
        )
        mods = self._modifiers(q1, rubric, facts)
        assert mods["value_left_on_table"].fired is False

    def test_value_left_on_table_does_not_fire_when_path_b_was_rejected(self, q1, rubric):
        facts = EndgameFacts(
            path="C", tier=Tier.THRIVING, covenant_hit=None, path_b_accepted=False,
            offer_known=True, true_continuation_value_exceeds_offer=True,
        )
        mods = self._modifiers(q1, rubric, facts)
        assert mods["value_left_on_table"].fired is False

    def test_reasoning_gated_modifiers_never_fire_even_when_every_other_condition_is_met(self, q1, rubric):
        """correct_rejection, correct_acceptance, and deliberate_independence all name a
        'correct'/'explicit' reasoning condition this engine has no signal for. Crafted here to
        look like they satisfy every checkable half of their own rule -- and still must not fire,
        proving these are genuinely gated on reasoning, not just untested."""
        rejection_leaning = EndgameFacts(
            path="C", tier=Tier.THRIVING, covenant_hit=None, path_b_accepted=False,
            offer_known=True, true_continuation_value_exceeds_offer=True,
        )
        acceptance_leaning = EndgameFacts(
            path="B", tier=Tier.STABLE, covenant_hit=None, path_b_accepted=True,
            offer_known=False, true_continuation_value_exceeds_offer=None,
        )
        independence_leaning = EndgameFacts(
            path="C", tier=Tier.STABLE, covenant_hit=None, path_b_accepted=False,
            offer_known=False, true_continuation_value_exceeds_offer=None,
        )
        assert self._modifiers(q1, rubric, rejection_leaning)["correct_rejection"].fired is False
        assert self._modifiers(q1, rubric, acceptance_leaning)["correct_acceptance"].fired is False
        assert self._modifiers(q1, rubric, independence_leaning)["deliberate_independence"].fired is False

    def test_exit_growth_trait_is_entirely_judgment_when_spliced_onto_the_rubric(self, q1, rubric):
        """`endgame.build_q4_rubric` is what actually splices this trait on (see
        test_endgame.py) -- confirms score_quarter treats it exactly like Leadership: zero
        MECHANICAL criteria, so it contributes nothing to mechanical_points_available and every
        sub-criterion comes back UNSCORED."""
        from app.engines.endgame import build_q4_rubric

        q4_rubric = build_q4_rubric(rubric)
        score = score_quarter(q1, None, Q1_ALLOCATIONS, q4_rubric, modifier_sets=("standard", "q4"))
        exit_growth = next(t for t in score.traits if t.trait == "exit_growth")

        assert exit_growth.weight == 15
        assert exit_growth.weight_scored == 0
        assert exit_growth.points_earned == 0
        assert all(c.result == CriterionResult.UNSCORED for c in exit_growth.criteria)

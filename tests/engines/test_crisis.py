"""Phase 10: pure crisis-effect formulas (`app/engines/crisis.py`) against
`docs/11-crisis-system.md`'s own worked examples. No database -- every number here is checked
directly against the source doc's arithmetic, independent of the full `compute_quarter` chain
(see `test_quarter_q3.py` for the end-to-end reproduction of the four expert/three novice targets).
"""

from decimal import Decimal

import pytest

from app.engines import crisis


@pytest.fixture(scope="module")
def cfg(profile):
    return profile.crisis


class TestPriceWarriorDampening:
    """docs/11 §3."""

    def test_unaddressed_dampening_stays_at_the_flat_075(self, cfg):
        outcome = crisis.price_warrior_dampening(
            Decimal("5000"), "C", Decimal(0), Decimal(0), cfg.price_warrior, cfg.response_lines
        )
        assert outcome.dampened_raw_leads == Decimal("3750")  # docs/11 §3's own worked example
        assert outcome.recovery_multiplier == Decimal("0.75")
        assert outcome.fully_recovered is False

    def test_price_match_fund_recovers_to_the_full_cap(self, cfg):
        # docs/11 §3: MIN(1.0, 0.75 + 0.15 * 3.0^0.5) = MIN(1.0, 1.01) = 1.00
        outcome = crisis.price_warrior_dampening(
            Decimal("5000"), "C", Decimal("3.0"), Decimal(0), cfg.price_warrior, cfg.response_lines
        )
        assert outcome.recovery_multiplier == Decimal(1)
        assert outcome.dampened_raw_leads == Decimal("5000")
        assert outcome.fully_recovered is True

    def test_choice_d_contract_surge_uses_its_own_stronger_rate(self, cfg):
        # 0.75 + 0.20 * 4.0^0.5 = 0.75 + 0.40 = 1.15 -> capped 1.00
        outcome = crisis.price_warrior_dampening(
            Decimal("5000"), "D", Decimal(0), Decimal("4.0"), cfg.price_warrior, cfg.response_lines
        )
        assert outcome.recovery_multiplier == Decimal(1)


class TestPriceWarriorConversionPenalty:
    """docs/11 §3's full worked recovery: Rs 10,00,000 on Comparison Ads."""

    def test_choice_a_removes_the_penalty_entirely(self, cfg):
        outcome = crisis.price_warrior_conversion_penalty(
            "A", Decimal(0), cfg.price_warrior, cfg.response_lines
        )
        assert outcome.net_penalty_pts == 0
        assert outcome.fully_recovered is True

    def test_comparison_ads_recovers_632_of_8_points(self, cfg):
        outcome = crisis.price_warrior_conversion_penalty(
            "C", Decimal("10.0"), cfg.price_warrior, cfg.response_lines
        )
        assert abs(outcome.net_penalty_pts - Decimal("1.68")) < Decimal("0.01")
        assert outcome.fully_recovered is False

    def test_recovery_never_goes_past_zero(self, cfg):
        outcome = crisis.price_warrior_conversion_penalty(
            "C", Decimal("100.0"), cfg.price_warrior, cfg.response_lines
        )
        assert outcome.net_penalty_pts == 0


class TestMarketingBlitzDampening:
    """docs/11 §4."""

    def test_unaddressed_dampening_is_the_steepest_of_any_variant(self, cfg):
        outcome = crisis.marketing_blitz_dampening(
            Decimal("5000"), "B", Decimal(0), Decimal(0), cfg.marketing_blitz, cfg.response_lines
        )
        assert outcome.dampened_raw_leads == Decimal("3000")  # docs/11 §4's own worked example
        assert outcome.recovery_multiplier == Decimal("0.60")

    def test_choice_d_contract_agency_surge_worked_example(self, cfg):
        # docs/11 §4: MIN(1.0, 0.60 + 0.25 * 4.0^0.5) = MIN(1.0, 1.10) = 1.00
        outcome = crisis.marketing_blitz_dampening(
            Decimal("5000"), "D", Decimal(0), Decimal("4.0"), cfg.marketing_blitz, cfg.response_lines
        )
        assert outcome.recovery_multiplier == Decimal(1)
        assert outcome.fully_recovered is True


class TestMarketingBlitzConversionPenalty:
    """docs/11 §4 + docs/14 §4's "Choice B Qualification" worked instance."""

    def test_choice_a_removes_the_penalty_entirely(self, cfg):
        outcome = crisis.marketing_blitz_conversion_penalty(
            "A", Decimal(0), Decimal("35.9"), cfg.marketing_blitz, cfg.response_lines
        )
        assert outcome.net_penalty_pts == 0
        assert outcome.fully_recovered is True

    def test_choice_b_qualification_reduces_penalty_when_quality_clears_25(self, cfg):
        # docs/14 §4: Quality Score 35.9 >= 25 -> base -3 becomes -1.2, then Rs 4,00,000 on
        # Comparison Ads (min(1.2, 2*4.0^0.5)=1.2) fully recovers the reduced penalty.
        outcome = crisis.marketing_blitz_conversion_penalty(
            "B", Decimal("4.0"), Decimal("35.9"), cfg.marketing_blitz, cfg.response_lines
        )
        assert outcome.net_penalty_pts == 0
        assert outcome.fully_recovered is True

    def test_choice_b_qualification_does_not_apply_below_the_threshold(self, cfg):
        outcome = crisis.marketing_blitz_conversion_penalty(
            "B", Decimal(0), Decimal("10.0"), cfg.marketing_blitz, cfg.response_lines
        )
        assert outcome.net_penalty_pts == cfg.marketing_blitz.conversion_penalty_pts  # flat -3, unqualified

    def test_no_choice_b_no_qualification_flat_penalty_applies(self, cfg):
        outcome = crisis.marketing_blitz_conversion_penalty(
            "C", Decimal(0), Decimal("35.9"), cfg.marketing_blitz, cfg.response_lines
        )
        assert outcome.net_penalty_pts == cfg.marketing_blitz.conversion_penalty_pts


class TestFeatureLeapfrogDampening:
    """docs/11 §5: mildest of the 3 competitor variants, no documented recovery mechanism."""

    def test_dampening_applies_flatly_with_no_recovery(self, cfg):
        outcome = crisis.feature_leapfrog_dampening(Decimal("5000"), cfg.feature_leapfrog)
        assert outcome.dampened_raw_leads == Decimal("4000")
        assert outcome.recovery_multiplier == Decimal("0.80")
        assert outcome.fully_recovered is False


class TestFeatureLeapfrogPenalties:
    """docs/11 §5's own worked example: carried-in Innovation Score 17.5, Choice D sprint."""

    def test_below_threshold_double_penalty_applies(self, cfg):
        outcome = crisis.feature_leapfrog_penalties("C", Decimal("17.5"), Decimal(0), cfg.feature_leapfrog)
        assert outcome.threshold_cleared is False
        assert outcome.conversion_penalty_pts == cfg.feature_leapfrog.conversion_penalty_pts  # -6
        assert outcome.ceiling_penalty_pts == cfg.feature_leapfrog.ceiling_penalty_pts  # -2

    def test_choice_d_sprint_crosses_the_threshold_exactly_as_worked(self, cfg):
        # docs/11 §5: Innovation Boost = 3 * 3.0^0.5 = 5.20; 17.5 + 5.20 = 22.70 >= 20
        outcome = crisis.feature_leapfrog_penalties("D", Decimal("17.5"), Decimal("3.0"), cfg.feature_leapfrog)
        assert abs(outcome.innovation_score_after_crisis - Decimal("22.70")) < Decimal("0.01")
        assert outcome.threshold_cleared is True
        assert outcome.conversion_penalty_pts == cfg.feature_leapfrog.conversion_penalty_reduced_pts  # -2
        assert outcome.ceiling_penalty_pts == 0  # waived entirely

    def test_already_cleared_threshold_needs_no_response(self, cfg):
        # docs/14 §5: baseline R&D already pushed Innovation to 25.4 -- threshold cleared before
        # any crisis-specific spend.
        outcome = crisis.feature_leapfrog_penalties("C", Decimal("25.4"), Decimal(0), cfg.feature_leapfrog)
        assert outcome.threshold_cleared is True
        assert outcome.conversion_penalty_pts == cfg.feature_leapfrog.conversion_penalty_reduced_pts
        assert outcome.ceiling_penalty_pts == 0

    def test_dropping_innovation_back_under_20_flips_the_penalties_back(self, cfg):
        outcome = crisis.feature_leapfrog_penalties("C", Decimal("19.99"), Decimal(0), cfg.feature_leapfrog)
        assert outcome.threshold_cleared is False
        assert outcome.conversion_penalty_pts == cfg.feature_leapfrog.conversion_penalty_pts
        assert outcome.ceiling_penalty_pts == cfg.feature_leapfrog.ceiling_penalty_pts


class TestSupplyShockCapacityMultiplier:
    """docs/11 §6 -- "the most important single formula in the entire crisis system"."""

    def test_the_headline_worked_example_hits_the_cap(self, cfg):
        # docs/11 §6: reliability 79.8, Choice B, Rs 2,00,000 fund -> 1.040, capped at 1.00.
        outcome = crisis.supply_shock_capacity_multiplier("B", Decimal("79.8"), Decimal("2.0"), cfg.supply_shock)
        assert outcome.multiplier == Decimal("1.00")
        assert outcome.capped_at_one is True

    def test_the_docs_14_expert_worked_example_also_hits_the_cap(self, cfg):
        # docs/14 §6: actual Q3 reliability 84.7 (post Q3 Ops spend), same Choice B + fund.
        outcome = crisis.supply_shock_capacity_multiplier("B", Decimal("84.7"), Decimal("2.0"), cfg.supply_shock)
        assert outcome.multiplier == Decimal("1.00")
        assert outcome.capped_at_one is True

    def test_the_docs_15_novice_worked_example(self, cfg):
        # docs/15: Choice A ("Absorb the shock"), Rs 0 fund -> 0.674 (offset 0, confirmed by this
        # exact worked arithmetic -- see this module's own docstring on the Choice-A-offset finding).
        outcome = crisis.supply_shock_capacity_multiplier("A", Decimal("84.7"), Decimal(0), cfg.supply_shock)
        assert abs(outcome.multiplier - Decimal("0.674")) < Decimal("0.001")
        assert outcome.capped_at_one is False

    def test_no_choice_submitted_defaults_to_the_same_offset_as_absorb_the_shock(self, cfg):
        with_none = crisis.supply_shock_capacity_multiplier(None, Decimal("84.7"), Decimal(0), cfg.supply_shock)
        with_a = crisis.supply_shock_capacity_multiplier("A", Decimal("84.7"), Decimal(0), cfg.supply_shock)
        assert with_none.multiplier == with_a.multiplier

    @pytest.mark.parametrize(
        "reliability,expected",
        [
            ("79.8", "1.00"),   # capped
            ("70", "0.991"),
            ("50", "0.891"),
        ],
    )
    def test_the_reliability_comparison_table_proves_the_design_thesis(self, cfg, reliability, expected):
        """docs/11 §6's own comparison table: the same Choice B + Rs 2,00,000 fund produces very
        different outcomes purely as a function of how much Supplier Reliability was built up in
        prior quarters."""
        outcome = crisis.supply_shock_capacity_multiplier(
            "B", Decimal(reliability), Decimal("2.0"), cfg.supply_shock
        )
        assert abs(outcome.multiplier - Decimal(expected)) < Decimal("0.001")

    def test_the_floor_engages_at_extreme_low_reliability(self, cfg):
        outcome = crisis.supply_shock_capacity_multiplier("A", Decimal("-50"), Decimal(0), cfg.supply_shock)
        assert outcome.multiplier == cfg.supply_shock.floor
        assert outcome.floored_at_floor is True

    def test_choice_d_is_not_a_valid_input_here(self, cfg):
        with pytest.raises(NotImplementedError, match="Contract Manufacturing"):
            crisis.supply_shock_capacity_multiplier("D", Decimal("79.8"), Decimal(0), cfg.supply_shock)

    def test_an_unknown_letter_raises(self, cfg):
        with pytest.raises(NotImplementedError):
            crisis.supply_shock_capacity_multiplier("Z", Decimal("79.8"), Decimal(0), cfg.supply_shock)


class TestSupplyShockContractManufacturing:
    """docs/11 §6 Choice D -- not exercised by any required acceptance target, so only formula
    sanity is checked here, not a source-confirmed number."""

    def test_zero_spend_adds_nothing(self, cfg):
        outcome = crisis.supply_shock_contract_manufacturing(Decimal(0), Decimal("1000"), cfg.supply_shock)
        assert outcome.extra_capacity == 0
        assert outcome.blended_cost_premium_inr == 0

    def test_positive_spend_adds_capacity_at_three_quarters_effectiveness(self, cfg):
        # Contract Capacity = 320 * 3.0^0.7; Effective = that * (1 - 0.25)
        outcome = crisis.supply_shock_contract_manufacturing(Decimal("3.0"), Decimal("1000"), cfg.supply_shock)
        assert outcome.extra_capacity > 0
        assert outcome.blended_cost_premium_inr > 0
        assert outcome.blended_cost_premium_inr < cfg.supply_shock.choice_d_cost_premium_inr  # blended, not flat


class TestBrandErosionAndChurn:
    def test_erosion_fires_only_when_nothing_was_spent(self, cfg):
        assert crisis.brand_erosion_pts(Decimal(0), cfg.price_warrior.brand_erosion_pts) == cfg.price_warrior.brand_erosion_pts
        assert crisis.brand_erosion_pts(Decimal("0.01"), cfg.price_warrior.brand_erosion_pts) == 0

    def test_churn_formula_matches_the_worked_example(self, cfg):
        # docs/11 §3: MAX(0%, 8% - 1.5*1.0^0.5) = 6.5%
        pct = crisis.customer_churn_pct(Decimal("1.0"), cfg.response_lines)
        assert pct == Decimal("6.5")

    def test_churn_floors_at_zero(self, cfg):
        pct = crisis.customer_churn_pct(Decimal("100.0"), cfg.response_lines)
        assert pct == 0


class TestScoringFacingReductions:
    """docs/14 §7's modifier table, scenario by scenario, for the expert branches."""

    def test_scenario_a_expert_neither_neutralized_nor_proofed(self, cfg):
        conversion = crisis.price_warrior_conversion_penalty("C", Decimal("10.0"), cfg.price_warrior, cfg.response_lines)
        assert crisis.is_fully_neutralized("A", conversion=conversion) is False

    def test_scenario_b_expert_is_binary_false_the_documented_residual(self, cfg):
        """docs/14 gives B a 'Partial (+1)' -- docs/11 states no such tier, so this strict
        binary check returns False here (net_penalty=0 but dampening=0.80, not both fully
        recovered). See default.json's crisis_fully_neutralized status flag."""
        conversion = crisis.marketing_blitz_conversion_penalty("B", Decimal("4.0"), Decimal("35.9"), cfg.marketing_blitz, cfg.response_lines)
        dampening = crisis.marketing_blitz_dampening(Decimal("3601"), "B", Decimal("1.0"), Decimal(0), cfg.marketing_blitz, cfg.response_lines)
        assert crisis.is_fully_neutralized("B", conversion=conversion, dampening=dampening) is False

    def test_scenario_c_expert_is_both_neutralized_and_proofed(self, cfg):
        fl = crisis.feature_leapfrog_penalties("C", Decimal("25.4"), Decimal(0), cfg.feature_leapfrog)
        assert crisis.is_fully_neutralized("C", feature_leapfrog=fl) is True
        assert crisis.is_proofed_by_prior_investment("C", feature_leapfrog=fl, choice_d_spend=Decimal(0)) is True

    def test_scenario_d_expert_is_neutralized_proofed_and_structural(self, cfg):
        capacity = crisis.supply_shock_capacity_multiplier("B", Decimal("84.7"), Decimal("2.0"), cfg.supply_shock)
        assert crisis.is_fully_neutralized("D", capacity=capacity) is True
        assert crisis.is_proofed_by_prior_investment("D", capacity=capacity) is True
        assert crisis.is_structural_improvement("D", "B") is True
        assert crisis.is_structural_improvement("D", "A") is False
        assert crisis.is_structural_improvement("C", "B") is False

    def test_scenario_c_expert_spent_zero_but_is_not_ignored(self, cfg):
        """docs/14 §7's own modifier table: C's expert spends Rs 0 and is explicitly 'No' for
        Crisis Ignored, because the crisis was already proofed by prior investment."""
        fl = crisis.feature_leapfrog_penalties("C", Decimal("25.4"), Decimal(0), cfg.feature_leapfrog)
        neutralized = crisis.is_fully_neutralized("C", feature_leapfrog=fl)
        proofed = crisis.is_proofed_by_prior_investment("C", feature_leapfrog=fl, choice_d_spend=Decimal(0))
        assert crisis.is_ignored(Decimal(0), neutralized, proofed) is False

    def test_zero_spend_with_no_neutralization_or_proofing_is_ignored(self):
        assert crisis.is_ignored(Decimal(0), False, False) is True

    def test_any_spend_at_all_is_not_ignored(self):
        assert crisis.is_ignored(Decimal("1"), False, False) is False


class TestResponseSpendTotal:
    def test_scenario_a_sums_the_three_standard_lines_plus_choice_d(self):
        from app.engines.state import QuarterAllocations

        alloc = QuarterAllocations(
            price_match_fund=Decimal("1"), comparison_ads=Decimal("2"), retention_offers=Decimal("3"),
            crisis_choice_d_spend=Decimal("4"), emergency_supply_fund=Decimal("99"),  # not counted for A
        )
        assert crisis.response_spend_total("A", alloc) == Decimal("10")

    def test_scenario_d_sums_only_emergency_fund_and_choice_d(self):
        from app.engines.state import QuarterAllocations

        alloc = QuarterAllocations(
            emergency_supply_fund=Decimal("2"), crisis_choice_d_spend=Decimal("3"),
            comparison_ads=Decimal("99"),  # not counted for D
        )
        assert crisis.response_spend_total("D", alloc) == Decimal("5")

    def test_no_scenario_is_zero(self):
        from app.engines.state import QuarterAllocations

        assert crisis.response_spend_total(None, QuarterAllocations(comparison_ads=Decimal("99"))) == 0

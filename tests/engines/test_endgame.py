"""Phase 11: the Q4 endgame -- `docs/16-quarter-4-endgame.md` + `docs/17-designer-resolutions.md`.

## Reusing Phase 10's fixtures as the docs/17 worked-example regression target

docs/17 P1's own worked example (59.9% momentum, a 2,556-unit covenant, a Rs 20,61,89,028 true
continuation value, a Rs 14,82,56,189 "Acquisition Trap" offer) turns out to chain exactly through
this project's own Q1 -> Q2 Growth -> Q3 Scenario-C-expert fixtures (`test_quarter_q1.py`'s `q1`,
`test_quarter_q3.py`'s `q2_growth`/`result_c_expert`) -- 562 units in Q1, 1,437 units and a ~Rs
12.9 Cr valuation in Q3. Running the actual numbers through `engines/endgame.py` reproduces every
one of docs/17's stated figures within ~0.5%, the same small reconstruction drift
`test_quarter_q3.py`'s own module docstring already documents and tolerates for Q3 (its baseline is
a solved reconstruction from department *totals*, not a channel-exact source fixture) -- so the
tolerances below are relative (~1%), not the +/-1 unit Q1's channel-exact fixture affords.
"""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.engines import endgame
from app.engines.endgame import Tier, TierOutcome
from app.engines.survival import RunStatus, SurvivalOutcome
from tests.engines.test_quarter_q1 import q1  # noqa: F401 -- fixture import
from tests.engines.test_quarter_q3 import q2_growth, q3_opening, result_c_expert  # noqa: F401 -- fixture import

_ACTIVE = SurvivalOutcome(status=RunStatus.ACTIVE, triggered_by=None, detail=None)
_DISTRESSED = SurvivalOutcome(status=RunStatus.DISTRESSED, triggered_by="buffer_breached", detail="cash below buffer")


def _relative_close(actual: Decimal, expected: str, tolerance_pct: str = "1") -> bool:
    expected_d = Decimal(expected)
    return abs(actual - expected_d) <= expected_d * Decimal(tolerance_pct) / 100


class TestFormulasAgainstDocs17WorkedExample:
    def test_momentum_score(self, q1, result_c_expert):  # noqa: F811 -- fixture, not redefinition
        momentum = endgame.momentum_score(q1.units_sold, result_c_expert.units_sold)
        assert _relative_close(momentum, "0.599", tolerance_pct="2")

    def test_covenant_units(self, q1, result_c_expert, profile):  # noqa: F811
        momentum = endgame.momentum_score(q1.units_sold, result_c_expert.units_sold)
        covenant = endgame.covenant_units(result_c_expert.units_sold, momentum, profile.endgame)
        assert _relative_close(covenant, "2556")

    def test_true_continuation_value(self, q1, result_c_expert, profile):  # noqa: F811
        momentum = endgame.momentum_score(q1.units_sold, result_c_expert.units_sold)
        tcv = endgame.true_continuation_value_inr(result_c_expert.valuation.blended_inr, momentum)
        assert _relative_close(tcv, "206189028")

    def test_acquisition_trap_offer(self, q1, result_c_expert, profile):  # noqa: F811
        momentum = endgame.momentum_score(q1.units_sold, result_c_expert.units_sold)
        tcv = endgame.true_continuation_value_inr(result_c_expert.valuation.blended_inr, momentum)
        offer = endgame.acquisition_offer_inr(
            profile.endgame.thriving.path_b_name, Tier.THRIVING, tcv, profile.endgame
        )
        assert _relative_close(offer, "148256189")

    def test_offer_raises_for_every_other_term_sheet(self, q1, result_c_expert, profile):  # noqa: F811
        momentum = endgame.momentum_score(q1.units_sold, result_c_expert.units_sold)
        tcv = endgame.true_continuation_value_inr(result_c_expert.valuation.blended_inr, momentum)
        with pytest.raises(NotImplementedError, match="Fair-Value Acquisition"):
            endgame.acquisition_offer_inr(profile.endgame.stable.path_b_name, Tier.STABLE, tcv, profile.endgame)
        with pytest.raises(NotImplementedError, match="Fire-Sale"):
            endgame.acquisition_offer_inr(
                profile.endgame.distressed.path_b_name, Tier.DISTRESSED, tcv, profile.endgame
            )
        # Even the Thriving tier's own name only works for its own Path-B term sheet -- swapping
        # in Path A's name at the same tier must still raise, not silently reuse the ratio.
        with pytest.raises(NotImplementedError):
            endgame.acquisition_offer_inr(profile.endgame.thriving.path_a_name, Tier.THRIVING, tcv, profile.endgame)


class TestAssignTier:
    """docs/17 P1's Tier Assignment: Distressed reuses evaluate_survival's own status unchanged;
    Thriving is `Q3 NCF > 0 AND valuation grew Q1->Q2 AND Q2->Q3`; everything else is Stable."""

    def test_distressed_short_circuits_regardless_of_the_numbers(self, q1, q2_growth, result_c_expert):  # noqa: F811
        # Even a company with a thriving-looking Q3 is Distressed if evaluate_survival says so --
        # Tier Assignment never re-derives Distressed from NCF/valuation itself.
        outcome = endgame.assign_tier(q1, q2_growth, result_c_expert, _DISTRESSED)
        assert outcome.tier == Tier.DISTRESSED
        assert outcome.detail == _DISTRESSED.detail

    def test_thriving_when_ncf_positive_and_valuation_grew_both_steps(self, q1, q2_growth, result_c_expert):  # noqa: F811
        # The real Q2->Q3 chain (Q2's much larger marketing spend against Q3's reconstructed,
        # smaller baseline) actually dips in valuation -- see
        # test_stable_when_q2_to_q3_valuation_actually_dips_in_this_project_s_own_fixtures below
        # for that honest, unmodified result. This test isolates Thriving's own condition with a
        # synthetically boosted Q3 valuation, since Q1-Q3 doesn't happen to land there naturally.
        assert result_c_expert.net_cash_flow_inr > 0
        assert q2_growth.valuation.blended_inr > q1.valuation.blended_inr
        boosted_q3 = replace(
            result_c_expert, valuation=replace(result_c_expert.valuation, blended_inr=q2_growth.valuation.blended_inr * 2)
        )
        outcome = endgame.assign_tier(q1, q2_growth, boosted_q3, _ACTIVE)
        assert outcome.tier == Tier.THRIVING

    def test_stable_when_q2_to_q3_valuation_actually_dips_in_this_project_s_own_fixtures(self, q1, q2_growth, result_c_expert):  # noqa: F811
        """Honest, unmodified regression: this project's own Q1->Q2 Growth->Q3 Scenario-C-expert
        chain reproduces docs/17's momentum/covenant/TCV numbers closely (see
        TestFormulasAgainstDocs17WorkedExample), but its valuation actually declines from Q2 to Q3
        (Q2's much larger marketing spend against Q3's reconstructed, smaller baseline) -- so the
        real, mechanical Tier Assignment lands this company in Stable, not the Thriving docs/17's
        own worked example assumes. Reported rather than adjusted, per this project's own
        "report the residual" precedent (see test_quarter_q3.py's module docstring)."""
        assert result_c_expert.valuation.blended_inr < q2_growth.valuation.blended_inr
        outcome = endgame.assign_tier(q1, q2_growth, result_c_expert, _ACTIVE)
        assert outcome.tier == Tier.STABLE

    def test_stable_when_active_but_valuation_did_not_grow_every_step(self, q1, q2_growth, result_c_expert):  # noqa: F811
        flat_q3 = replace(result_c_expert, valuation=replace(result_c_expert.valuation, blended_inr=q2_growth.valuation.blended_inr))
        outcome = endgame.assign_tier(q1, q2_growth, flat_q3, _ACTIVE)
        assert outcome.tier == Tier.STABLE

    def test_stable_when_active_but_q3_ncf_not_positive(self, q1, q2_growth, result_c_expert):  # noqa: F811
        lossy_q3 = replace(result_c_expert, net_cash_flow_inr=Decimal("-1"))
        outcome = endgame.assign_tier(q1, q2_growth, lossy_q3, _ACTIVE)
        assert outcome.tier == Tier.STABLE

    def test_raises_when_valuation_growth_check_needs_a_missing_blended_valuation(self, q1, q2_growth, result_c_expert):  # noqa: F811
        no_valuation_q3 = replace(result_c_expert, valuation=replace(result_c_expert.valuation, blended_inr=None))
        with pytest.raises(NotImplementedError, match="blended valuation"):
            endgame.assign_tier(q1, q2_growth, no_valuation_q3, _ACTIVE)


class TestTermSheetMenu:
    def test_menu_matches_the_assigned_tier(self, profile):
        assert endgame.term_sheet_menu(Tier.THRIVING, profile.endgame) == profile.endgame.thriving
        assert endgame.term_sheet_menu(Tier.STABLE, profile.endgame) == profile.endgame.stable
        assert endgame.term_sheet_menu(Tier.DISTRESSED, profile.endgame) == profile.endgame.distressed


class TestBuildEndgameFacts:
    """The flat facts `engines/scoring.py`'s 6 Q4 modifiers read -- see that module's own tests
    (`test_scoring.py`) for how each modifier actually fires off these facts."""

    def test_path_a_covenant_hit(self, q1, result_c_expert, profile):  # noqa: F811
        tier_outcome = TierOutcome(Tier.THRIVING, "thriving")
        generous_units_sold = result_c_expert.units_sold * 3  # comfortably clears any covenant
        facts = endgame.build_endgame_facts(
            "A", profile.endgame.thriving.path_a_name, tier_outcome, q1, result_c_expert,
            generous_units_sold, profile.endgame,
        )
        assert facts.covenant_hit is True
        assert facts.path_b_accepted is False

    def test_path_a_covenant_missed(self, q1, result_c_expert, profile):  # noqa: F811
        tier_outcome = TierOutcome(Tier.THRIVING, "thriving")
        facts = endgame.build_endgame_facts(
            "A", profile.endgame.thriving.path_a_name, tier_outcome, q1, result_c_expert,
            Decimal(0), profile.endgame,
        )
        assert facts.covenant_hit is False

    def test_path_b_accepted_thriving_tier_offer_known(self, q1, result_c_expert, profile):  # noqa: F811
        tier_outcome = TierOutcome(Tier.THRIVING, "thriving")
        facts = endgame.build_endgame_facts(
            "B", profile.endgame.thriving.path_b_name, tier_outcome, q1, result_c_expert,
            result_c_expert.units_sold, profile.endgame,
        )
        assert facts.path_b_accepted is True
        assert facts.offer_known is True
        assert facts.true_continuation_value_exceeds_offer is True  # Acquisition Trap ratio < 1

    def test_path_b_accepted_stable_tier_offer_unknown(self, q1, result_c_expert, profile):  # noqa: F811
        tier_outcome = TierOutcome(Tier.STABLE, "stable")
        facts = endgame.build_endgame_facts(
            "B", profile.endgame.stable.path_b_name, tier_outcome, q1, result_c_expert,
            result_c_expert.units_sold, profile.endgame,
        )
        assert facts.offer_known is False
        assert facts.true_continuation_value_exceeds_offer is None

    def test_path_c(self, q1, result_c_expert, profile):  # noqa: F811
        tier_outcome = TierOutcome(Tier.STABLE, "stable")
        facts = endgame.build_endgame_facts(
            "C", profile.endgame.stable.path_c_name, tier_outcome, q1, result_c_expert,
            result_c_expert.units_sold, profile.endgame,
        )
        assert facts.covenant_hit is None
        assert facts.path_b_accepted is False
        assert facts.offer_known is False

    def test_rejects_a_path_outside_a_b_c(self, q1, result_c_expert, profile):  # noqa: F811
        tier_outcome = TierOutcome(Tier.STABLE, "stable")
        with pytest.raises(NotImplementedError, match="not one of A/B/C"):
            endgame.build_endgame_facts(
                "D", "nonsense", tier_outcome, q1, result_c_expert, result_c_expert.units_sold, profile.endgame
            )


class TestBuildQ4Rubric:
    def test_exit_growth_trait_added_without_mutating_the_standard_rubric(self, profile):
        original_trait_count = len(profile.scoring.traits)
        original_criteria_count = len(profile.scoring.criteria)

        q4_rubric = endgame.build_q4_rubric(profile.scoring)

        assert q4_rubric.traits["exit_growth"] == Decimal(15)
        assert len(q4_rubric.criteria) == original_criteria_count + 3
        # The standard rubric object itself (frozen, pydantic) is untouched -- model_copy never
        # mutates in place.
        assert len(profile.scoring.traits) == original_trait_count
        assert "exit_growth" not in profile.scoring.traits

    def test_all_three_exit_growth_criteria_are_judgment(self, profile):
        q4_rubric = endgame.build_q4_rubric(profile.scoring)
        exit_growth_criteria = [c for c in q4_rubric.criteria if c.trait == "exit_growth"]
        assert len(exit_growth_criteria) == 3
        assert all(c.kind == "JUDGMENT" for c in exit_growth_criteria)


class TestBuildEndgamePreview:
    def test_preview_reproduces_docs17s_worked_numbers_for_the_natural_stable_tier(self, q1, q2_growth, result_c_expert, profile):  # noqa: F811
        """Unmodified fixture chain (see TestAssignTier's own documented Stable finding): the
        preview's momentum/covenant/TCV numbers still reproduce docs/17 closely even though the
        real tier this run lands in is Stable, not Thriving -- so no Acquisition Trap offer is
        known (Stable's own Path B term sheet, Fair-Value Acquisition, has no stated ratio)."""
        preview = endgame.build_endgame_preview(q1, q2_growth, result_c_expert, _ACTIVE, profile.endgame)
        assert preview.tier == Tier.STABLE
        assert preview.term_sheet_menu == profile.endgame.stable
        assert _relative_close(preview.momentum_score * 100, "59.9", tolerance_pct="2")
        assert _relative_close(preview.covenant_units, "2556")
        assert _relative_close(preview.true_continuation_value_inr, "206189028")
        assert preview.acquisition_trap_offer_inr is None

    def test_preview_shows_the_acquisition_trap_offer_for_a_genuinely_thriving_tier(self, q1, q2_growth, result_c_expert, profile):  # noqa: F811
        boosted_q3 = replace(
            result_c_expert, valuation=replace(result_c_expert.valuation, blended_inr=q2_growth.valuation.blended_inr * 2)
        )
        preview = endgame.build_endgame_preview(q1, q2_growth, boosted_q3, _ACTIVE, profile.endgame)
        assert preview.tier == Tier.THRIVING
        assert preview.term_sheet_menu == profile.endgame.thriving
        assert preview.acquisition_trap_offer_inr is not None
        assert preview.acquisition_trap_offer_inr == preview.true_continuation_value_inr * profile.endgame.acquisition_trap_offer_ratio

    def test_preview_offer_is_none_for_a_non_thriving_tier(self, q1, q2_growth, result_c_expert, profile):  # noqa: F811
        flat_q3 = replace(result_c_expert, valuation=replace(result_c_expert.valuation, blended_inr=q2_growth.valuation.blended_inr))
        preview = endgame.build_endgame_preview(q1, q2_growth, flat_q3, _ACTIVE, profile.endgame)
        assert preview.tier == Tier.STABLE
        assert preview.acquisition_trap_offer_inr is None

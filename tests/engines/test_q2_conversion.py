"""Regression target for the raw-conversion composition -- Phase 3.5 item 1.

`docs/00-formula-index.md` states raw conversion as `base + Reps + CRM`, which is exact in Q1 but
understates both Q2 variants in `docs/13-quarter-2-reference.md` §4/§5 by an amount that matches HR's
CX Team `Repeat Purchase Rate` bonus almost exactly. See the CX-in-raw-conversion entry in
`docs/10-implementation-gaps.md` for the derivation. Both variants here chain off Q1's own closing
state (`tests/engines/test_quarter_q1.py`'s `q1` fixture) rather than reconstructing Q2's opening
position by hand, so this doubles as a Q1->Q2 chaining check.
"""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.engines.lines import sales as sales_lines
from app.engines.quarter import compute_quarter
from app.engines.state import CompanyState
from tests.engines.conftest import close
from tests.engines.test_quarter_q1 import Q1_ALLOCATIONS, q1  # noqa: F401 -- fixture import

# docs/13-quarter-2-reference.md §4: Variant A, Efficiency-Final (Rs 42,73,200).
Q2_EFFICIENCY_ALLOCATIONS = replace(
    Q1_ALLOCATIONS,
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

# docs/13-quarter-2-reference.md §5: Variant B, Growth & Profit (Rs 82,63,600).
# Marketing's channel spends here (12.00/5.00/6.00/2.00/1.00/2.00) are independently confirmed by
# the lead totals in §5's own channel table (2,032+569+817+115+90+117+912 = 4,652, matching the
# doc's stated raw total exactly); the doc's Marketing department subtotal (Rs 29,23,600) does not
# match either that or the doc's own grand total (Rs 82,63,600) and is a source-document typo --
# Rs 31,23,600 is the figure consistent with everything else in the section.
Q2_GROWTH_ALLOCATIONS = replace(
    Q1_ALLOCATIONS,
    google_ads=Decimal("12.00"),
    meta_ads=Decimal("5.00"),
    social_influencer=Decimal("6.00"),
    content_seo=Decimal("2.00"),
    events_pr=Decimal("1.00"),
    email_marketing=Decimal("2.00"),
    referral=Decimal("2.736"),
    prelaunch_buzz=Decimal("0.50"),
    reps=Decimal("14.00"),
    crm_tools=Decimal("3.00"),
    onboarding=Decimal("3.00"),
    quality_qa=Decimal("6.00"),
    innovation=Decimal("4.00"),
    manufacturing=Decimal("8.40"),
    supplier_qc=Decimal("1.50"),
    logistics=Decimal("1.50"),
    culture_benefits=Decimal("1.50"),
    training_development=Decimal("2.00"),
    cx_team=Decimal("1.50"),
    compliance_legal=Decimal("2.00"),
    financial_planning=Decimal("1.80"),
    audit_prep=Decimal("1.20"),
    warranty_years=2,
)


@pytest.fixture(scope="module")
def q2_efficiency(q1, profile, nadi_wear):
    return compute_quarter(q1.closing_state, Q2_EFFICIENCY_ALLOCATIONS, profile, nadi_wear)


@pytest.fixture(scope="module")
def q2_growth(q1, profile, nadi_wear):
    return compute_quarter(q1.closing_state, Q2_GROWTH_ALLOCATIONS, profile, nadi_wear)


class TestRawConversionComposition:
    """`raw = base + Reps + CRM + CX Team + Buzz Q+2 bonus` -- verified component by component so
    a future change to any one line's formula fails here before it fails a rounded doc comparison."""

    def test_q1_raw_is_base_plus_reps_plus_crm_plus_cx(self, q1):
        assert close(q1.raw_conversion_pct, "27.25", tolerance="0.05")

    def test_q2_efficiency_reproduces_the_doc(self, q2_efficiency):
        """docs/13-quarter-2-reference.md §4: 'Raw uncapped conversion (Sales+HR alone) = 28.4%'."""
        assert close(q2_efficiency.raw_conversion_pct, "28.4", tolerance="0.05")
        assert q2_efficiency.ceiling_bound is True

    def test_q2_growth_reproduces_the_doc(self, q2_growth):
        """docs/13-quarter-2-reference.md §5: 'Raw uncapped conversion = 31.2%'."""
        assert close(q2_growth.raw_conversion_pct, "31.2", tolerance="0.05")
        assert q2_growth.ceiling_bound is True

    def test_q2_efficiency_final_conversion_rate(self, q2_efficiency):
        """Ceiling 24.0% + Warranty 3.0% = 27.0%, per §4's worked P&L."""
        assert close(q2_efficiency.conversion_ceiling_pct, "24.0", tolerance="0.1")
        assert close(q2_efficiency.conversion_rate_pct, "27.0", tolerance="0.1")

    def test_q2_growth_final_conversion_rate(self, q2_growth):
        """Ceiling 25.0% + Warranty 3.0% = 28.0%, per §5's worked P&L."""
        assert close(q2_growth.conversion_ceiling_pct, "25.0", tolerance="0.1")
        assert close(q2_growth.conversion_rate_pct, "28.0", tolerance="0.1")


class TestCompoundingAssetsCarryForward:
    """Q1's own closing values are the only ones the Q1 suite can check, and every cumulative
    score opens Q1 at a baseline that makes "carried forward" and "recomputed from this quarter's
    spend alone" indistinguishable there. SEO Asset opens at 0, so Q1 could not tell the two
    apart at all -- and the engine was in fact replacing it, silently capping the compounding
    mechanic at one quarter deep. These pin the second link of the chain, where the difference
    is observable.
    """

    def test_seo_asset_accumulates_across_q1_to_q2(self, q1, q2_efficiency, q2_growth):
        """docs/13 §4: `+5.25 -> 9.75`. §5/§8: `+7.0 -> 11.5`, the stated Q3 opening value.
        Both are Q1's 4.5 plus that variant's own Rs 3.5/lakh contribution."""
        assert close(q1.closing_state.seo_asset, "4.5", tolerance="0.05")
        assert close(q2_efficiency.closing_state.seo_asset, "9.75", tolerance="0.05")
        assert close(q2_growth.closing_state.seo_asset, "11.5", tolerance="0.05")

    def test_seo_payout_reads_the_accumulated_balance(self, q2_growth, q1, profile, nadi_wear):
        """The payout is `prior asset x 25`, so a dropped carry-forward shows up as missing free
        leads a quarter later, not as a wrong score in the quarter that built it."""
        q3 = compute_quarter(q2_growth.closing_state, Q2_GROWTH_ALLOCATIONS, profile, nadi_wear)

        assert close(q2_growth.seo_payout_leads, "113", tolerance="1")  # from Q1's 4.5
        assert close(q3.seo_payout_leads, "288", tolerance="1")  # from Q2 Growth's 11.5

    def test_zero_seo_spend_preserves_the_asset_rather_than_zeroing_it(
        self, q1, profile, nadi_wear
    ):
        """A quarter that skips Content/SEO keeps the balance it already built -- the asset is a
        stock, not a per-quarter flow."""
        result = compute_quarter(
            q1.closing_state, replace(Q2_GROWTH_ALLOCATIONS, content_seo=Decimal(0)), profile, nadi_wear
        )

        assert result.closing_state.seo_asset == q1.closing_state.seo_asset

    def test_brand_and_quality_and_innovation_also_accumulate(self, q1, q2_growth):
        """The three other cumulative scores, checked at the same link for the same reason --
        docs/13 §5/§8: Brand 8.7 -> 31.2, Quality 9.95 -> 24.65, Innovation 7.5 -> 17.5."""
        assert q2_growth.closing_state.brand_score > q1.closing_state.brand_score
        assert close(q2_growth.closing_state.brand_score, "31.2", tolerance="0.1")
        assert close(q2_growth.closing_state.quality_score, "24.65", tolerance="0.1")
        assert close(q2_growth.closing_state.innovation_score, "17.5", tolerance="0.1")


class TestGate2BothBranchesOfTheMinAreExercised:
    """Every other Q1/Q2 fixture keeps the ceiling binding, so `MIN(raw, ceiling)` only ever
    selects `ceiling` in the rest of the suite. This constructs the other branch."""

    def test_ceiling_binds_in_every_other_fixture(self, q1, q2_efficiency, q2_growth):
        assert q1.ceiling_bound is True
        assert q2_efficiency.ceiling_bound is True
        assert q2_growth.ceiling_bound is True

    def test_raw_binds_when_rnd_spend_is_high_and_sales_spend_is_low(self, nadi_wear, profile):
        """High Quality/Innovation spend lifts the ceiling far above a deliberately small raw
        conversion (minimal Reps/CRM/CX), so this time `MIN` must select raw, not ceiling."""
        opening = CompanyState.opening(nadi_wear)
        allocations = replace(
            Q1_ALLOCATIONS,
            reps=Decimal("0.20"),
            crm_tools=Decimal("0.10"),
            cx_team=Decimal("0.10"),
            quality_qa=Decimal("40.00"),
            innovation=Decimal("40.00"),
        )
        result = compute_quarter(opening, allocations, profile, nadi_wear)

        assert result.ceiling_bound is False
        assert result.raw_conversion_pct < result.conversion_ceiling_pct
        assert result.conversion_rate_pct == result.raw_conversion_pct + result.warranty_bonus_pts


class TestCxContributionShape:
    """Every other test in this suite exercises CX Team at a single spend level (Rs 1,50,000 --
    both Q2 variants used it, so two runs are one data point). This proves the relationship
    holds across a range, not just at that one figure."""

    @staticmethod
    def _raw_conversion_at(cx_spend: Decimal, nadi_wear, profile) -> Decimal:
        opening = CompanyState.opening(nadi_wear)
        allocations = replace(Q1_ALLOCATIONS, cx_team=cx_spend)
        return compute_quarter(opening, allocations, profile, nadi_wear).raw_conversion_pct

    def test_raw_conversion_increases_monotonically_with_cx_spend(self, nadi_wear, profile):
        levels = [Decimal("0.50"), Decimal("1.50"), Decimal("3.00"), Decimal("6.00")]
        raw_values = [self._raw_conversion_at(x, nadi_wear, profile) for x in levels]

        assert raw_values == sorted(raw_values)
        assert len(set(raw_values)) == len(raw_values)  # strictly increasing, no ties

    def test_zero_cx_spend_recovers_the_pre_phase_3_5_formula(self, nadi_wear, profile):
        """At cx_team=0, raw conversion must equal exactly `base + Reps + CRM` -- proof the CX
        term is cleanly additive, not entangled with the rest of the composition."""
        raw_without_cx = self._raw_conversion_at(Decimal("0"), nadi_wear, profile)

        assert close(raw_without_cx, "25.34", tolerance="0.01")


class TestOnboardingDoesNotFeedConversion:
    """CX Team's Repeat Purchase Rate bonus feeds raw conversion; Sales' Onboarding produces the
    same dimensional quantity (`Repeat Purchase Rate += pts`) but does not. Nothing in docs/ says
    why one does and the other doesn't -- it looks exactly like the kind of asymmetry a future
    "these are the same shape, unify them" refactor would silently erase, so it's locked here."""

    def test_onboarding_spend_does_not_move_raw_conversion(self, nadi_wear, profile):
        opening = CompanyState.opening(nadi_wear)
        low = compute_quarter(opening, replace(Q1_ALLOCATIONS, onboarding=Decimal("0")), profile, nadi_wear)
        high = compute_quarter(opening, replace(Q1_ALLOCATIONS, onboarding=Decimal("20.00")), profile, nadi_wear)

        assert low.raw_conversion_pct == high.raw_conversion_pct

    def test_including_onboarding_would_have_broken_q2_efficiency(self, q2_efficiency, profile):
        """If Onboarding's `3 x^0.4` repeat bonus fed conversion the way CX Team's does, Q2
        Efficiency's raw conversion would land near 32.4%, not the doc's 28.4% -- the asymmetry
        is load-bearing, not an oversight."""
        onboarding_repeat_bonus = sales_lines.onboarding(Decimal("2.00"), profile).repeat_rate_pts
        hypothetical_raw = q2_efficiency.raw_conversion_pct + onboarding_repeat_bonus

        assert close(hypothetical_raw, "32.4", tolerance="0.05")

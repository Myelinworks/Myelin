"""Every Marketing line against its Q1 worked value (docs/12-quarter-1-reference.md §2)."""

from decimal import Decimal

import pytest

from app.engines.lines import marketing
from tests.engines.conftest import close

L = Decimal  # spend in Rs lakhs


def test_google_ads_q1(profile):
    """Rs 4,00,000 -> 963 leads."""
    assert close(marketing.google_ads(L("4.00"), profile), "963")


def test_meta_ads_q1(profile):
    """Rs 1,92,000 -> 306 leads, 76,800 impressions, +2.30 brand."""
    result = marketing.meta_ads(L("1.92"), profile)

    assert close(result.leads, "306")
    assert result.impressions == Decimal("76800.00")
    assert close(result.brand_score, "2.30", tolerance="0.01")


def test_social_influencer_q1(profile):
    """Rs 2,08,000 -> 381 leads, +5.20 brand."""
    result = marketing.social_influencer(L("2.08"), profile)

    assert close(result.leads, "381")
    assert close(result.brand_score, "5.20", tolerance="0.01")


def test_content_seo_q1(profile):
    """Rs 1,28,000 -> 87 leads, +4.48 SEO asset."""
    result = marketing.content_seo(L("1.28"), profile)

    assert close(result.leads, "87")
    assert close(result.seo_asset, "4.48", tolerance="0.01")


def test_seo_asset_payout_is_read_from_prior_state(profile):
    """Q1's 4.5 asset -> 113 free leads in Q2. Never recomputed from spend."""
    assert close(marketing.seo_asset_payout(Decimal("4.5"), profile), "113")


def test_events_pr_q1(profile):
    """Rs 80,000 -> 78 leads, +1.20 brand."""
    result = marketing.events_pr(L("0.80"), profile)

    assert close(result.leads, "78")
    assert close(result.brand_score, "1.20", tolerance="0.01")


def test_email_marketing_q1(profile):
    """Rs 1,60,000 -> 104 leads, +3.8 repeat rate points."""
    result = marketing.email_marketing(L("1.60"), profile)

    assert close(result.leads, "104")
    assert close(result.repeat_rate_pts, "3.8", tolerance="0.05")


def test_q1_raw_leads_total(profile):
    """All 8 channels at Q1's allocation sum to 2,719 raw leads."""
    total = (
        marketing.google_ads(L("4.00"), profile)
        + marketing.meta_ads(L("1.92"), profile).leads
        + marketing.social_influencer(L("2.08"), profile).leads
        + marketing.content_seo(L("1.28"), profile).leads
        + marketing.events_pr(L("0.80"), profile).leads
        + marketing.email_marketing(L("1.60"), profile).leads
        + Decimal(800)  # Referral, capped -- see test_referral_q1
        + marketing.prelaunch_buzz(L("1.92"), profile).leads
    )

    assert close(total, "2719", tolerance="2")


def test_q1_brand_score_built(profile):
    """Meta + Social + Events brand contributions total 8.7, applied as a multiplier from Q2."""
    built = (
        marketing.meta_ads(L("1.92"), profile).brand_score
        + marketing.social_influencer(L("2.08"), profile).brand_score
        + marketing.events_pr(L("0.80"), profile).brand_score
    )

    assert close(built, "8.7", tolerance="0.01")


class TestReferral:
    """The only line with no exponent -- a hard cap against a finite customer base."""

    def test_q1_spend_exactly_matches_the_cap(self, profile, nadi_wear):
        """4,000 customers -> 800 lead cap; Rs 2,40,000 buys exactly 800 with nothing wasted."""
        result = marketing.referral(L("2.40"), Decimal(4000), nadi_wear)

        assert result.lead_cap == Decimal(800)
        assert result.leads == Decimal(800)
        assert result.cost_inr == Decimal(240000)
        assert result.wasted_spend_inr == Decimal(0)

    def test_spend_beyond_the_cap_is_reported_not_absorbed(self, nadi_wear):
        """Over-spending buys nothing extra; the excess must surface as wasted_spend."""
        result = marketing.referral(L("5.00"), Decimal(4000), nadi_wear)

        assert result.leads == Decimal(800)
        assert result.cost_inr == Decimal(240000)
        assert result.wasted_spend_inr == Decimal(260000)

    def test_under_the_cap_spend_is_fully_used(self, nadi_wear):
        result = marketing.referral(L("1.20"), Decimal(4000), nadi_wear)

        assert result.leads == Decimal(400)
        assert result.wasted_spend_inr == Decimal(0)

    def test_cap_grows_with_the_customer_base(self, nadi_wear):
        """Q2 opens at 4,562 customers -> a 912 cap. This is why Referral compounds."""
        assert marketing.referral(L("10.00"), Decimal(4562), nadi_wear).lead_cap == Decimal("912.40")

    def test_unstated_seed_constants_fail_loudly(self, pulsewear):
        """PulseWear has no referral constants; borrowing Nadi Wear's would be the P0 conflict."""
        with pytest.raises(NotImplementedError, match="referral_cap_ratio"):
            marketing.referral(L("2.40"), Decimal(530), pulsewear)


class TestPreLaunchBuzz:
    def test_q1_returns_zero_leads_by_design(self, profile):
        """Rs 1,92,000 -> Buzz 5.5 and zero leads. Zero is the mechanic, not a bug."""
        result = marketing.prelaunch_buzz(L("1.92"), profile)

        assert result.leads == Decimal(0)
        assert close(result.buzz_score, "5.5", tolerance="0.05")

    def test_payout_at_q_plus_1(self, profile):
        """Q1's 5.5 -> 83 free leads in Q2, no conversion bonus yet."""
        payout = marketing.buzz_payout(Decimal("5.5"), 1, profile)

        assert close(payout.free_leads, "83", tolerance="1")
        assert payout.conversion_bonus_pts == Decimal(0)

    def test_payout_at_q_plus_2(self, profile):
        """Q1's 5.5 -> 138 free leads in Q3 plus a one-time +1.65 conversion bonus."""
        payout = marketing.buzz_payout(Decimal("5.5"), 2, profile)

        assert close(payout.free_leads, "138", tolerance="1")
        assert close(payout.conversion_bonus_pts, "1.65", tolerance="0.01")

    @pytest.mark.parametrize("offset", [0, 3, 4])
    def test_payout_only_lands_in_the_two_specified_quarters(self, profile, offset):
        payout = marketing.buzz_payout(Decimal("5.5"), offset, profile)

        assert payout.free_leads == Decimal(0)
        assert payout.conversion_bonus_pts == Decimal(0)


def test_brand_multiplier_matches_the_three_known_points(profile):
    """Fitted, not stated -- docs/13-quarter-2-reference.md §2.1."""
    assert marketing.brand_multiplier(Decimal("8.7"), profile) == Decimal("1.174")
    assert marketing.brand_multiplier(Decimal("31.2"), profile) == Decimal("1.624")
    assert marketing.brand_multiplier(Decimal("34.0"), profile) == Decimal("1.68")


@pytest.mark.parametrize(
    "line",
    [
        lambda p: marketing.google_ads(L("0"), p),
        lambda p: marketing.meta_ads(L("0"), p).leads,
        lambda p: marketing.social_influencer(L("0"), p).leads,
        lambda p: marketing.content_seo(L("0"), p).leads,
        lambda p: marketing.events_pr(L("0"), p).leads,
        lambda p: marketing.email_marketing(L("0"), p).leads,
        lambda p: marketing.prelaunch_buzz(L("0"), p).buzz_score,
    ],
)
def test_zero_spend_produces_zero(profile, line):
    assert line(profile) == Decimal(0)


def test_negative_spend_is_rejected(profile):
    with pytest.raises(ValueError, match="cannot be negative"):
        marketing.google_ads(L("-1"), profile)

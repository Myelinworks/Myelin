"""Marketing -- 8 spend lines, plus the two deferred payouts and the brand multiplier they feed.

Every function is pure: spend in Rs lakhs, whatever prior-quarter state it needs, and the profile.
Formulas from `docs/00-formula-index.md`, worked values in `docs/12-quarter-1-reference.md` §2.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.config.schema import CompanySeed, SimulationProfile
from app.engines.lines._shared import RUPEES_PER_LAKH, diminishing, require


@dataclass(frozen=True)
class MetaAdsResult:
    leads: Decimal
    impressions: Decimal
    brand_score: Decimal


@dataclass(frozen=True)
class SocialInfluencerResult:
    leads: Decimal
    brand_score: Decimal


@dataclass(frozen=True)
class ContentSeoResult:
    leads: Decimal
    seo_asset: Decimal


@dataclass(frozen=True)
class EventsPrResult:
    leads: Decimal
    brand_score: Decimal


@dataclass(frozen=True)
class EmailMarketingResult:
    leads: Decimal
    repeat_rate_pts: Decimal


@dataclass(frozen=True)
class ReferralResult:
    leads: Decimal
    lead_cap: Decimal
    cost_inr: Decimal
    wasted_spend_inr: Decimal


@dataclass(frozen=True)
class PreLaunchBuzzResult:
    leads: Decimal
    buzz_score: Decimal


@dataclass(frozen=True)
class BuzzPayout:
    free_leads: Decimal
    conversion_bonus_pts: Decimal


def google_ads(spend_lakhs: Decimal, profile: SimulationProfile) -> Decimal:
    """`Leads = 375 * x^0.68`. Highest exponent of any paid channel -- search intent renews daily
    rather than exhausting a fixed pool."""
    line = profile.marketing.google_ads
    return diminishing(line.leads_constant, spend_lakhs, line.leads_exponent)


def meta_ads(spend_lakhs: Decimal, profile: SimulationProfile) -> MetaAdsResult:
    """`Leads = 200 * x^0.65` · `Impressions = 40,000 * x` · `Brand Score += 1.2 * x`."""
    line = profile.marketing.meta_ads
    return MetaAdsResult(
        leads=diminishing(line.leads_constant, spend_lakhs, line.leads_exponent),
        impressions=line.impressions_per_lakh * spend_lakhs,
        brand_score=line.brand_per_lakh * spend_lakhs,
    )


def social_influencer(spend_lakhs: Decimal, profile: SimulationProfile) -> SocialInfluencerResult:
    """`Leads = 225 * x^0.72` · `Brand Score += 2.5 * x`. Both the highest exponent and the
    highest brand rate of any channel -- third-party endorsement carries more trust per rupee."""
    line = profile.marketing.social_influencer
    return SocialInfluencerResult(
        leads=diminishing(line.leads_constant, spend_lakhs, line.leads_exponent),
        brand_score=line.brand_per_lakh * spend_lakhs,
    )


def content_seo(
    spend_lakhs: Decimal, prior_seo_asset: Decimal, profile: SimulationProfile
) -> ContentSeoResult:
    """`Leads = 75 * x^0.62` · `SEO Asset += 3.5 * x` (cumulative, never resets).

    Immediate leads are deliberately the weakest of any paid channel; the real value arrives next
    quarter through the asset, via `seo_asset_payout`.

    The asset accumulates like every other carried score, and takes `prior_seo_asset` for the same
    reason `quality_qa`/`supplier_qc`/`logistics` take theirs: returning a bare per-quarter delta
    is what let the caller drop the carried balance. `docs/13-quarter-2-reference.md` states both
    Q2 variants' closing totals as prior-plus-contribution -- Efficiency `+5.25 -> 9.75` (§4) and
    Growth `+7.0 -> 11.5` (§5), each from Q1's 4.5 -- and §8 carries that 11.5 into Q3 as the
    canonical opening value.
    """
    line = profile.marketing.content_seo
    return ContentSeoResult(
        leads=diminishing(line.leads_constant, spend_lakhs, line.leads_exponent),
        seo_asset=prior_seo_asset + line.asset_per_lakh * spend_lakhs,
    )


def seo_asset_payout(prior_seo_asset: Decimal, profile: SimulationProfile) -> Decimal:
    """`Free leads this quarter = prior quarter's SEO Asset * 25`.

    Deferred payout: reads prior-quarter state, never recomputed from this quarter's spend.
    """
    return prior_seo_asset * profile.marketing.content_seo.asset_payout_per_point


def events_pr(spend_lakhs: Decimal, profile: SimulationProfile) -> EventsPrResult:
    """`Leads = 90 * x^0.62` · `Brand Score += 1.5 * x`."""
    line = profile.marketing.events_pr
    return EventsPrResult(
        leads=diminishing(line.leads_constant, spend_lakhs, line.leads_exponent),
        brand_score=line.brand_per_lakh * spend_lakhs,
    )


def email_marketing(spend_lakhs: Decimal, profile: SimulationProfile) -> EmailMarketingResult:
    """`Leads = 80 * x^0.55` · `Repeat Purchase Rate += 3 * x^0.5` (pts).

    The only Marketing channel that feeds Repeat Purchase Rate -- it speaks to people who already
    know the brand, so it is a retention tool as much as an acquisition one.
    """
    line = profile.marketing.email_marketing
    return EmailMarketingResult(
        leads=diminishing(line.leads_constant, spend_lakhs, line.leads_exponent),
        repeat_rate_pts=diminishing(line.repeat_rate_constant, spend_lakhs, line.repeat_rate_exponent),
    )


def referral(spend_lakhs: Decimal, existing_customers: Decimal, seed: CompanySeed) -> ReferralResult:
    """`Lead Cap = 0.20 * existing customers`, flat Rs 300 per lead.

    The only line with no exponent: it scales against the company's own finite customer base, so
    it is a hard cap rather than a diminishing curve. Spend beyond `cap * cost_per_lead` buys
    nothing and is returned as `wasted_spend_inr` rather than silently absorbed.

    Both constants are company data, so they come from the seed. This is also the one place that
    converts lakhs to rupees, because cost-per-lead is inherently rupee-denominated.
    """
    if spend_lakhs < 0:
        raise ValueError(f"spend cannot be negative (got {spend_lakhs} lakhs)")

    cap_ratio = require(seed.referral_cap_ratio, "referral_cap_ratio", seed.name)
    cost_per_lead = require(seed.referral_cost_per_lead_inr, "referral_cost_per_lead_inr", seed.name)

    spend_inr = spend_lakhs * RUPEES_PER_LAKH
    lead_cap = cap_ratio * existing_customers
    affordable_leads = spend_inr / cost_per_lead

    leads = min(lead_cap, affordable_leads)
    cost_inr = leads * cost_per_lead
    return ReferralResult(
        leads=leads,
        lead_cap=lead_cap,
        cost_inr=cost_inr,
        wasted_spend_inr=spend_inr - cost_inr,
    )


def prelaunch_buzz(spend_lakhs: Decimal, profile: SimulationProfile) -> PreLaunchBuzzResult:
    """`Buzz Score = 4 * x^0.5`, and **zero leads this quarter**.

    Zero is the mechanic working as intended, not a bug -- the entire payoff is deferred to the
    next two quarters via `buzz_payout`.
    """
    line = profile.marketing.prelaunch_buzz
    return PreLaunchBuzzResult(
        leads=Decimal(0),
        buzz_score=diminishing(line.buzz_constant, spend_lakhs, line.buzz_exponent),
    )


def buzz_payout(
    prior_buzz_score: Decimal, quarters_since_investment: int, profile: SimulationProfile
) -> BuzzPayout:
    """Q+1: `Buzz * 15`. Q+2: `Buzz * 25` plus a one-time `Buzz * 0.3` pt conversion bonus.

    Deferred payout: reads prior-quarter state. Any other offset pays nothing.
    """
    line = profile.marketing.prelaunch_buzz

    if quarters_since_investment == 1:
        return BuzzPayout(
            free_leads=prior_buzz_score * line.payout_next_quarter_per_point,
            conversion_bonus_pts=Decimal(0),
        )
    if quarters_since_investment == 2:
        return BuzzPayout(
            free_leads=prior_buzz_score * line.payout_second_quarter_per_point,
            conversion_bonus_pts=prior_buzz_score * line.conversion_bonus_per_point,
        )
    return BuzzPayout(free_leads=Decimal(0), conversion_bonus_pts=Decimal(0))


def brand_multiplier(brand_score: Decimal, profile: SimulationProfile) -> Decimal:
    """`Lead Multiplier = 1 + 0.02 * Brand Score`, applied from Q2 onward.

    Fitted, not stated -- see `docs/10-implementation-gaps.md` P1 and the profile's
    `fitted_not_confirmed` status flag.
    """
    return profile.marketing.brand_multiplier.multiplier(brand_score)

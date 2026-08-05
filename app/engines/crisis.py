"""Crisis effects -- Phase 10 (`docs/11-crisis-system.md`).

Pure functions, no I/O, no DB, no RNG -- same discipline as every other `engines/` module. Each
function computes exactly one effect, called from the specific point in `compute_quarter`'s chain
docs/11 names for it (dampening before the Brand/HR multipliers, the conversion penalty at the
ceiling step, the ceiling penalty before warranty, the capacity multiplier feeding the supply
gate) -- never bolted on at the end.

## The Scenario D Choice-A-offset finding

`docs/17-designer-resolutions.md` claims "Choice A carries +0.50" for Scenario D's Strategic
Choice offset. This is contradicted by `docs/15-q3-noob-vs-expert.md`'s own worked arithmetic: the
Scenario D novice run picks Choice A ("Absorb the shock") and the source itself computes
`0.50 + 0.005*(84.7-50) + 0 + 0 = 0.674` -- using **zero** for the choice term. That matches
docs/11's own summary table (`Choice A / C | 0`), not docs/17. Since no worked example anywhere
exercises the mystery "+0.50 (highest tier)" row, `SupplyShockConfig.choice_unassigned_high_tier`
is never read below -- selecting it would need a designer decision this project has no reliable
source for, so `supply_shock_capacity_multiplier` raises rather than guess which letter it belongs
to.

## Two known gaps, both flagged rather than guessed

- Scenario B's "Choice B Qualification" (Quality Score >= 25 reduces -3 to -1.2) is implemented as
  the exact stated pair (`MarketingBlitzConfig.choice_b_quality_threshold` /
  `choice_b_qualified_penalty_pts`) -- the only data point `docs/14` gives, not generalised to a
  formula for other Quality Score values.
- Scenario C's Choice A (price cut) has no stated price anywhere in any source document --
  `compute_quarter` raises `NotImplementedError` for that specific combination rather than invent
  one. This function module only ever computes the conversion/ceiling side of Scenario C (which
  Choice A leaves untouched, per docs/15's own novice narrative: a price lever doesn't address a
  credibility/threshold penalty) -- the price itself is `compute_quarter`'s concern.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.config.schema import (
    CrisisResponseLinesConfig,
    FeatureLeapfrogConfig,
    MarketingBlitzConfig,
    PriceWarriorConfig,
    SupplyShockConfig,
)

ZERO = Decimal(0)
ONE = Decimal(1)
HALF = Decimal("0.5")
PROOFED_THRESHOLD = Decimal("0.90")


def _sqrt_recovery(intercept: Decimal, rate: Decimal, spend_lakhs: Decimal) -> Decimal:
    """`MIN(1.0, intercept + rate * x^0.5)` -- the shape every dampening-recovery formula in
    docs/11 shares (the standard response lines and every scenario's own Choice D)."""
    if spend_lakhs <= 0:
        return intercept
    return min(ONE, intercept + rate * spend_lakhs**HALF)


# ---- Demand Dampening (A/B/C) ------------------------------------------------------------------


@dataclass(frozen=True)
class DampeningOutcome:
    dampened_raw_leads: Decimal
    recovery_multiplier: Decimal
    fully_recovered: bool  # multiplier reached 1.0 -- the dampening's net effect is zero


def price_warrior_dampening(
    raw_leads: Decimal,
    choice: str | None,
    price_match_fund: Decimal,
    choice_d_spend: Decimal,
    config: PriceWarriorConfig,
    response: CrisisResponseLinesConfig,
) -> DampeningOutcome:
    """docs/11 §3: `Raw Leads * 0.75`, recovered by the Price-Match Fund (`0.75 + 0.15*x^0.5`) or,
    on Choice D, Contract Sales/Promo Surge (`0.75 + 0.20*x^0.5`, stronger per rupee)."""
    if choice == "D" and choice_d_spend > 0:
        multiplier = _sqrt_recovery(config.dampening_multiplier, config.choice_d_dampening_rate, choice_d_spend)
    else:
        multiplier = _sqrt_recovery(config.dampening_multiplier, response.price_match_fund_rate, price_match_fund)
    return DampeningOutcome(raw_leads * multiplier, multiplier, multiplier >= ONE)


def marketing_blitz_dampening(
    raw_leads: Decimal,
    choice: str | None,
    price_match_fund: Decimal,
    choice_d_spend: Decimal,
    config: MarketingBlitzConfig,
    response: CrisisResponseLinesConfig,
) -> DampeningOutcome:
    """docs/11 §4: `Raw Leads * 0.60` (steepest of any variant), recovered by the Price-Match Fund
    or, on Choice D, Contract Marketing Agency Surge (`0.60 + 0.25*x^0.5`, faster per rupee)."""
    if choice == "D" and choice_d_spend > 0:
        multiplier = _sqrt_recovery(config.dampening_multiplier, config.choice_d_dampening_rate, choice_d_spend)
    else:
        multiplier = _sqrt_recovery(config.dampening_multiplier, response.price_match_fund_rate, price_match_fund)
    return DampeningOutcome(raw_leads * multiplier, multiplier, multiplier >= ONE)


def feature_leapfrog_dampening(raw_leads: Decimal, config: FeatureLeapfrogConfig) -> DampeningOutcome:
    """docs/11 §5: `Raw Leads * 0.80` (mildest of the 3 competitor variants). No recovery
    mechanism is documented anywhere for Scenario C's dampening -- it applies flatly."""
    multiplier = config.dampening_multiplier
    return DampeningOutcome(raw_leads * multiplier, multiplier, False)


# ---- Conversion penalty (A/B) and the combined conversion+ceiling penalty (C) ------------------


@dataclass(frozen=True)
class ConversionPenaltyOutcome:
    net_penalty_pts: Decimal
    fully_recovered: bool


def _comparison_ads_recovery(comparison_ads: Decimal, response: CrisisResponseLinesConfig) -> Decimal:
    if comparison_ads <= 0:
        return ZERO
    return min(response.comparison_ads_cap_pts, response.comparison_ads_rate * comparison_ads**HALF)


def price_warrior_conversion_penalty(
    choice: str | None, comparison_ads: Decimal, config: PriceWarriorConfig, response: CrisisResponseLinesConfig
) -> ConversionPenaltyOutcome:
    """docs/11 §3: -8 points; Choice A removes it entirely (cutting price directly closes the gap
    the penalty models). Otherwise clawed back by Comparison Ads, never past zero -- recovering
    more than the penalty produces no bonus."""
    if choice == "A":
        return ConversionPenaltyOutcome(ZERO, True)
    net = max(ZERO, config.conversion_penalty_pts - _comparison_ads_recovery(comparison_ads, response))
    return ConversionPenaltyOutcome(net, net == 0)


def marketing_blitz_conversion_penalty(
    choice: str | None,
    comparison_ads: Decimal,
    quality_score: Decimal,
    config: MarketingBlitzConfig,
    response: CrisisResponseLinesConfig,
) -> ConversionPenaltyOutcome:
    """docs/11 §4: -3 points; Choice A removes it entirely (docs/15 B-novice: "Choice A removes
    it"). Otherwise, the "Choice B Qualification" (see module docstring) reduces the base penalty
    to `choice_b_qualified_penalty_pts` once Quality Score clears `choice_b_quality_threshold`.
    Comparison Ads then claws back whatever base penalty remains, never past zero."""
    if choice == "A":
        return ConversionPenaltyOutcome(ZERO, True)
    base = config.conversion_penalty_pts
    if choice == "B" and quality_score >= config.choice_b_quality_threshold:
        base = config.choice_b_qualified_penalty_pts
    net = max(ZERO, base - _comparison_ads_recovery(comparison_ads, response))
    return ConversionPenaltyOutcome(net, net == 0)


@dataclass(frozen=True)
class FeatureLeapfrogPenaltyOutcome:
    conversion_penalty_pts: Decimal
    ceiling_penalty_pts: Decimal
    threshold_cleared: bool
    innovation_score_after_crisis: Decimal


def feature_leapfrog_penalties(
    choice: str | None,
    innovation_score_after_rnd: Decimal,
    choice_d_spend: Decimal,
    config: FeatureLeapfrogConfig,
) -> FeatureLeapfrogPenaltyOutcome:
    """docs/11 §5: -6 conversion + -2 ceiling, both waived down to -2/0 once Innovation Score
    clears 20 -- checked *after* this quarter's regular R&D and any Choice D Contract R&D Sprint
    boost (docs/11's own worked example crosses the threshold via exactly that spend, 17.5 + 3 *
    3.0^0.5 = 22.7). `innovation_score_after_rnd` is the value the R&D line already computed this
    quarter (`rnd.innovation(...).innovation_score`), not the opening/prior-quarter value.
    """
    boost = (
        config.choice_d_innovation_rate * choice_d_spend**HALF
        if choice == "D" and choice_d_spend > 0
        else ZERO
    )
    innovation_after = innovation_score_after_rnd + boost
    cleared = innovation_after >= config.innovation_threshold
    conversion = config.conversion_penalty_reduced_pts if cleared else config.conversion_penalty_pts
    ceiling = ZERO if cleared else config.ceiling_penalty_pts
    return FeatureLeapfrogPenaltyOutcome(conversion, ceiling, cleared, innovation_after)


# ---- Brand erosion and customer churn (A/B) ----------------------------------------------------


def brand_erosion_pts(response_spend_total: Decimal, erosion_pts: Decimal) -> Decimal:
    """docs/11: a one-time erosion applied only if *zero* was spent on this scenario's response
    lines -- any response spend at all, even on the "wrong" lever, avoids it."""
    return ZERO if response_spend_total > 0 else erosion_pts


def customer_churn_pct(retention_offers: Decimal, response: CrisisResponseLinesConfig) -> Decimal:
    """docs/11 §3: `MAX(0%, 8% - 1.5*x^0.5)` -- Retention Offers claws back customer loss."""
    if retention_offers <= 0:
        return response.retention_base_pct
    recovery = response.retention_rate * retention_offers**HALF
    return max(ZERO, response.retention_base_pct - recovery)


# ---- Supply Shock (D) ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CapacityMultiplierOutcome:
    multiplier: Decimal
    capped_at_one: bool
    floored_at_floor: bool


def supply_shock_capacity_multiplier(
    choice: str | None, supplier_reliability: Decimal, emergency_fund_spend: Decimal, config: SupplyShockConfig
) -> CapacityMultiplierOutcome:
    """docs/11 §6 -- "the most important single formula in the entire crisis system":
    `MIN(1.0, MAX(0.10, 0.50 + 0.005*(Reliability-50) + choice_offset + 0.10*fund^0.5))`.

    Choice offsets: A=0, B=+0.25, C=0 -- all three confirmed against worked arithmetic (see this
    module's docstring on the Choice-A-offset finding). Choice D bypasses this formula entirely
    (`supply_shock_contract_manufacturing` below), so it is not a valid input here.
    """
    offsets = {"A": config.choice_a_offset, "B": config.choice_b_offset, "C": config.choice_c_offset}
    if choice not in offsets:
        raise NotImplementedError(
            f"Supply Shock choice {choice!r} has no capacity-multiplier offset -- Choice D uses "
            f"Contract Manufacturing's own separate formula (supply_shock_contract_manufacturing), "
            f"and no other letter is defined"
        )
    fund_offset = (
        config.emergency_fund_rate * emergency_fund_spend**HALF if emergency_fund_spend > 0 else ZERO
    )
    raw = (
        config.base_cut
        + config.reliability_coefficient * (supplier_reliability - config.reliability_centre)
        + offsets[choice]
        + fund_offset
    )
    multiplier = min(config.cap, max(config.floor, raw))
    return CapacityMultiplierOutcome(multiplier, multiplier >= config.cap, multiplier <= config.floor)


@dataclass(frozen=True)
class ContractManufacturingOutcome:
    extra_capacity: Decimal
    blended_cost_premium_inr: Decimal  # per-unit premium, weighted by contract's share of supply


def supply_shock_contract_manufacturing(
    choice_d_spend: Decimal, normal_capacity_after_multiplier: Decimal, config: SupplyShockConfig
) -> ContractManufacturingOutcome:
    """docs/11 §6: `Contract Capacity = 320*x^0.7`, `Effective = Contract Capacity * (1 - 0.25)`
    (only half the base 0.50 cut applies -- a genuinely diversified third-party is structurally
    less exposed to the same regional shock). `+Rs 350/unit` premium for contract-sourced units.

    No worked example anywhere exercises this Choice, so the per-unit cost blend below is a
    documented, reasoned convention -- proportional to the contract capacity's share of total
    available supply -- not a value confirmed against a source number.
    """
    if choice_d_spend <= 0:
        return ContractManufacturingOutcome(ZERO, ZERO)
    contract_capacity = config.choice_d_capacity_constant * choice_d_spend**config.choice_d_capacity_exponent
    extra_capacity = contract_capacity * (ONE - config.choice_d_contract_penalty)
    total_supply = normal_capacity_after_multiplier + extra_capacity
    premium_share = (
        (extra_capacity / total_supply) * config.choice_d_cost_premium_inr if total_supply > 0 else ZERO
    )
    return ContractManufacturingOutcome(extra_capacity, premium_share)


# ---- Scoring-facing summary: reduces the per-effect outcomes above to the 4 plain facts ---------
# `engines/scoring.py`'s crisis modifiers read straight off `QuarterResult`, exactly like every
# existing modifier -- these functions are where that reduction happens, once, in the module that
# already holds the scenario-specific context, so scoring.py's predicates stay simple field reads.


def response_spend_total(scenario: str | None, allocations) -> Decimal:
    """Every response line relevant to `scenario`, plus whichever Choice-D line is active."""
    if scenario in ("A", "B"):
        return (
            allocations.price_match_fund
            + allocations.comparison_ads
            + allocations.retention_offers
            + allocations.crisis_choice_d_spend
        )
    if scenario == "C":
        return allocations.crisis_choice_d_spend
    if scenario == "D":
        return allocations.emergency_supply_fund + allocations.crisis_choice_d_spend
    return ZERO


def is_fully_neutralized(
    scenario: str | None,
    *,
    conversion: ConversionPenaltyOutcome | None = None,
    dampening: DampeningOutcome | None = None,
    feature_leapfrog: FeatureLeapfrogPenaltyOutcome | None = None,
    capacity: CapacityMultiplierOutcome | None = None,
) -> bool:
    """"The event's core mechanism... reduced to zero net effect" (docs/11 §7). The core mechanism
    is scenario-specific, following what each scenario's own KPI table in `docs/14` actually
    measures as "Crisis Penalty Neutralized":

    - A: the conversion penalty alone (A's dampening is never addressed in the expert run and
      docs/14 doesn't count it -- "79% (6.32 of 8 conversion points recovered)").
    - B: docs/14 reports *both* a 100%-recovered conversion penalty and an 80%-recovered
      dampening, and scores this "Partial (+1)" -- a tier docs/11 (the spec of record) never
      states. This function is strictly binary (both must be fully recovered), so it returns
      `False` for B's expert case; the resulting one-point gap against docs/14's own scoring table
      is a documented, reported residual, not a guessed partial-credit rule.
    - C: whether the Innovation Score threshold was cleared -- clearing it caps the double
      penalty at its mildest tier, which `docs/14` counts as "100%" neutralized even though a -2
      conversion penalty still technically remains.
    - D: the Capacity Multiplier hitting its 1.00 cap exactly.
    """
    if scenario == "A":
        return conversion is not None and conversion.fully_recovered
    if scenario == "B":
        return (
            conversion is not None
            and conversion.fully_recovered
            and dampening is not None
            and dampening.fully_recovered
        )
    if scenario == "C":
        return feature_leapfrog is not None and feature_leapfrog.threshold_cleared
    if scenario == "D":
        return capacity is not None and capacity.capped_at_one
    return False


def is_proofed_by_prior_investment(
    scenario: str | None,
    *,
    feature_leapfrog: FeatureLeapfrogPenaltyOutcome | None = None,
    capacity: CapacityMultiplierOutcome | None = None,
    choice_d_spend: Decimal = ZERO,
) -> bool:
    """"Crisis-proofed by prior investment" (docs/11 §7): the crisis was substantially handled by
    investment made *before* this quarter's crisis-specific reaction, not by spending the
    expensive crisis-only response line. Scenario-specific because the "prior investment" signal
    differs (Innovation Score for C, Supplier Reliability for D); A/B have no documented
    prior-investment-alone path, so this is always `False` there.
    """
    if scenario == "C":
        return (
            feature_leapfrog is not None and feature_leapfrog.threshold_cleared and choice_d_spend == 0
        )
    if scenario == "D":
        return capacity is not None and capacity.multiplier >= PROOFED_THRESHOLD
    return False


def is_structural_improvement(scenario: str | None, choice: str | None) -> bool:
    """docs/11 §7: Choice B on Supply Shock converts the crisis into a permanent Supplier
    Reliability gain (docs/14 §6: +10, forever) -- the only scenario/choice combination with a
    stated permanent-asset outcome."""
    return scenario == "D" and choice == "B"


def is_ignored(response_spend: Decimal, fully_neutralized: bool, proofed: bool) -> bool:
    """docs/11 §7: Rs 0 spent on the relevant response line during a severe event -- but not when
    the crisis was already handled without it (Scenario C's expert spends Rs 0 and is *not*
    "ignored", per `docs/14` §7's own modifier table)."""
    return response_spend == 0 and not fully_neutralized and not proofed

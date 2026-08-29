"""
Demand Dynamics Engine - Market Addressable Demand Calculation

This module implements the sophisticated demand allocation system that calculates
how many buyers are realistically interested based on:
- Product attributes (brand, innovation, quality, satisfaction)
- Market position vs competitors
- Quarter-by-quarter market growth
- Investment impact on buyer interest

Pure functions - no I/O, deterministic output for same inputs.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Dict

# Market constants
TAM_CUSTOMERS = Decimal("250000")  # Total addressable market
MARKET_PENETRATION = [
    Decimal("0.048"),  # Q1: 4.8% = 12,000 units
    Decimal("0.054"),  # Q2: 5.4% = 13,500 units
    Decimal("0.061"),  # Q3: 6.1% = 15,250 units
    Decimal("0.068"),  # Q4: 6.8% = 17,000 units
]

# Competitor baseline strengths
RIVALS = [
    {"id": "kalpa", "name": "Kalpa Labs", "base_strength": Decimal("52")},
    {"id": "vega", "name": "Vega Health", "base_strength": Decimal("46")},
    {"id": "zenith", "name": "Zenith", "base_strength": Decimal("58")},
    {"id": "tail", "name": "Long tail", "base_strength": Decimal("84")},
]
RIVAL_GROWTH_RATE = Decimal("0.05")  # 5% per quarter


@dataclass(frozen=True)
class MarketState:
    """Current market conditions and company position"""
    quarter: int
    brand_score: Decimal
    innovation_score: Decimal
    quality_score: Decimal
    satisfaction_score: Decimal
    fill_rate: Decimal  # 0-1, how well we meet demand
    market_share_prior: Decimal  # Previous quarter's actual share


@dataclass(frozen=True)
class MarketingInvestment:
    """Marketing spend by channel (in lakhs)"""
    google_ads: Decimal = Decimal("0")
    meta_ads: Decimal = Decimal("0")
    social_influencer: Decimal = Decimal("0")
    content_seo: Decimal = Decimal("0")
    events_pr: Decimal = Decimal("0")
    email: Decimal = Decimal("0")
    direct_marketing: Decimal = Decimal("0")
    referral: Decimal = Decimal("0")


@dataclass(frozen=True)
class DemandResult:
    """Complete demand calculation breakdown"""
    # Market size
    total_market_demand: Decimal  # Total category units this quarter
    
    # Competitive position
    product_pull_score: Decimal  # Our product attractiveness
    our_strength: Decimal  # After price/voice/fill adjustments
    rival_total_strength: Decimal
    attractive_share: Decimal  # % of market we could reach
    
    # Addressable demand
    addressable_demand_units: Decimal  # Realistic buyer count
    
    # Lead generation (for frontend display)
    channel_leads: Dict[str, Decimal]
    total_raw_leads: Decimal
    effective_leads: Decimal  # After brand/morale multipliers
    
    # Conversion factors
    conversion_ceiling_pct: Decimal
    expected_conversion_pct: Decimal


def power(base: Decimal, exponent: float) -> Decimal:
    """Safe power function for Decimal with float exponent"""
    if base <= 0:
        return Decimal("0")
    return Decimal(float(base) ** exponent)


def clamp(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    """Constrain value between min and max"""
    return max(minimum, min(maximum, value))


def calculate_market_demand(quarter: int) -> Decimal:
    """
    Calculate total market demand for this quarter.
    
    Market grows naturally each quarter as category matures.
    This is the pie everyone is fighting over.
    """
    q_index = clamp(Decimal(quarter - 1), Decimal("0"), Decimal("3"))
    penetration = MARKET_PENETRATION[int(q_index)]
    return TAM_CUSTOMERS * penetration


def calculate_rival_strength(quarter: int) -> Decimal:
    """
    Competitors don't stand still - they grow 5% each quarter.
    
    This creates natural competitive pressure even if you do nothing.
    """
    growth_factor = power(
        Decimal("1") + RIVAL_GROWTH_RATE, 
        float(quarter - 1)
    )
    
    total_strength = Decimal("0")
    for rival in RIVALS:
        total_strength += rival["base_strength"] * growth_factor
    
    return total_strength


def calculate_product_pull(
    brand: Decimal,
    innovation: Decimal,
    quality: Decimal,
    satisfaction: Decimal
) -> Decimal:
    """
    How attractive is your product vs competitors?
    
    Formula: 16 + brand + 0.6*innovation + 0.5*quality + 0.25*(satisfaction-50)
    
    Base of 16 = minimum viable product
    Each attribute pulls buyers differently:
    - Brand: 1:1 (pure awareness)
    - Innovation: 0.6x (features matter but aren't everything)
    - Quality: 0.5x (reliability is baseline expectation)
    - Satisfaction: 0.25x differential from neutral 50
    """
    base = Decimal("16")
    sat_differential = (satisfaction - Decimal("50")) * Decimal("0.25")
    
    pull = (
        base +
        brand +
        innovation * Decimal("0.6") +
        quality * Decimal("0.5") +
        sat_differential
    )
    
    # Floor at 4 (even terrible product has some pull)
    return max(Decimal("4"), pull)


def calculate_our_strength(
    product_pull: Decimal,
    fill_rate: Decimal,
    price_index: Decimal = Decimal("1.0"),
    voice_index: Decimal = Decimal("1.0")
) -> Decimal:
    """
    Our competitive strength = product pull * modifiers
    
    - fill_rate: 0.75-1.0 based on how well we meet demand
    - price_index: elasticity effect (cheaper = more demand)
    - voice_index: 0.55-1.0 based on marketing spend reaching threshold
    """
    fill_idx = Decimal("0.75") + Decimal("0.25") * clamp(fill_rate, Decimal("0"), Decimal("1"))
    
    return product_pull * price_index * voice_index * fill_idx


def estimate_addressable_demand(
    market_state: MarketState,
    marketing_spend_total_lakhs: Decimal = Decimal("0")
) -> Decimal:
    """
    MAIN FUNCTION: Estimate how many buyers you could realistically reach this quarter.
    
    This is the number shown BEFORE allocation, so teams can size Sales and Operations
    intelligently rather than guessing.
    
    Returns: Number of units the market would realistically demand from you.
    """
    # Step 1: Calculate total market demand this quarter
    market_demand = calculate_market_demand(market_state.quarter)
    
    # Step 2: Calculate competitive landscape
    rival_strength = calculate_rival_strength(market_state.quarter)
    
    # Step 3: Calculate our product's pull
    product_pull = calculate_product_pull(
        market_state.brand_score,
        market_state.innovation_score,
        market_state.quality_score,
        market_state.satisfaction_score
    )
    
    # Step 4: Estimate voice index from marketing spend
    # Full voice achieved around 18L spend
    voice_idx = Decimal("0.55") + Decimal("0.45") * min(
        Decimal("1.0"),
        marketing_spend_total_lakhs / Decimal("18")
    )
    
    # Step 5: Calculate our competitive strength
    our_strength = calculate_our_strength(
        product_pull,
        market_state.fill_rate,
        price_index=Decimal("1.0"),  # Assume market price for estimate
        voice_index=voice_idx
    )
    
    # Step 6: Calculate market share we could attract
    total_strength = our_strength + rival_strength
    if total_strength == 0:
        attractive_share = Decimal("0")
    else:
        attractive_share = our_strength / total_strength
    
    # Step 7: Calculate addressable demand
    addressable = market_demand * attractive_share
    
    return addressable.quantize(Decimal("1"))  # Round to whole units


def calculate_channel_leads(investment: MarketingInvestment) -> Dict[str, Decimal]:
    """
    Calculate leads generated by each marketing channel.
    
    Each channel has diminishing returns (power < 1), meaning
    doubling spend doesn't double leads.
    
    Formulas from reference simulation - battle-tested coefficients.
    """
    leads = {}
    
    # Paid acquisition channels
    leads["google"] = Decimal("375") * power(investment.google_ads, 0.68)
    leads["meta"] = Decimal("200") * power(investment.meta_ads, 0.65)
    leads["social"] = Decimal("225") * power(investment.social_influencer, 0.72)
    leads["content"] = Decimal("75") * power(investment.content_seo, 0.62)
    leads["events"] = Decimal("90") * power(investment.events_pr, 0.62)
    leads["email"] = Decimal("80") * power(investment.email, 0.55)
    leads["direct"] = Decimal("160") * power(investment.direct_marketing, 0.60)
    
    # Referral is capped differently (handled separately)
    # Formula: ₹300 per lead, capped at 20% of customer base
    
    return leads


def calculate_brand_impact(investment: MarketingInvestment) -> Decimal:
    """
    Some marketing builds brand score (long-term asset), not just immediate leads.
    
    Returns: Brand score increase this quarter
    """
    brand_gain = (
        investment.meta_ads * Decimal("1.2") +
        investment.social_influencer * Decimal("2.5") +
        investment.events_pr * Decimal("1.5")
    )
    return brand_gain


def calculate_full_demand(
    market_state: MarketState,
    investment: MarketingInvestment,
    current_customers: int,
    sales_capacity: Decimal,
    production_capacity: Decimal
) -> DemandResult:
    """
    Complete demand calculation including all dynamics.
    
    This is the full engine version used during quarter execution.
    Returns detailed breakdown for analysis and frontend display.
    """
    # Market sizing
    market_demand = calculate_market_demand(market_state.quarter)
    rival_strength = calculate_rival_strength(market_state.quarter)
    
    # Product pull
    product_pull = calculate_product_pull(
        market_state.brand_score,
        market_state.innovation_score,
        market_state.quality_score,
        market_state.satisfaction_score
    )
    
    # Marketing voice
    total_marketing = sum([
        investment.google_ads,
        investment.meta_ads,
        investment.social_influencer,
        investment.content_seo,
        investment.events_pr,
        investment.email,
        investment.direct_marketing,
        investment.referral
    ])
    
    voice_idx = Decimal("0.55") + Decimal("0.45") * min(
        Decimal("1.0"),
        total_marketing / Decimal("18")
    )
    
    # Our competitive strength
    our_strength = calculate_our_strength(
        product_pull,
        market_state.fill_rate,
        voice_index=voice_idx
    )
    
    # Market share we could attract
    total_strength = our_strength + rival_strength
    attractive_share = our_strength / total_strength if total_strength > 0 else Decimal("0")
    
    addressable = market_demand * attractive_share
    
    # Lead generation
    channel_leads = calculate_channel_leads(investment)
    total_raw_leads = sum(channel_leads.values())
    
    # Brand multiplier (future quarter effect)
    brand_mult = Decimal("1") + market_state.brand_score / Decimal("50")
    effective_leads = total_raw_leads * brand_mult
    
    # Conversion ceiling
    ceiling_base = Decimal("22")
    ceiling_quality = (market_state.quality_score + 
                      Decimal("0.6") * market_state.innovation_score) * Decimal("0.3")
    conversion_ceiling = ceiling_base + ceiling_quality
    
    # Expected conversion (simplified for estimate)
    expected_conversion = min(
        Decimal("25"),  # typical sales-driven rate
        conversion_ceiling
    )
    
    return DemandResult(
        total_market_demand=market_demand,
        product_pull_score=product_pull,
        our_strength=our_strength,
        rival_total_strength=rival_strength,
        attractive_share=attractive_share,
        addressable_demand_units=addressable.quantize(Decimal("1")),
        channel_leads=channel_leads,
        total_raw_leads=total_raw_leads,
        effective_leads=effective_leads,
        conversion_ceiling_pct=conversion_ceiling,
        expected_conversion_pct=expected_conversion
    )

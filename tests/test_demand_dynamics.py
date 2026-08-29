"""
Unit tests for demand dynamics engine.

Tests the core formulas that calculate addressable demand, lead generation,
and competitive positioning.
"""

import pytest
from decimal import Decimal

from app.engines.demand_dynamics import (
    MarketState,
    MarketingInvestment,
    calculate_market_demand,
    calculate_rival_strength,
    calculate_product_pull,
    calculate_our_strength,
    estimate_addressable_demand,
    calculate_channel_leads,
    calculate_brand_impact,
    calculate_full_demand,
    power,
    clamp,
)


class TestUtilityFunctions:
    """Test helper functions"""

    def test_power_positive(self):
        result = power(Decimal("2"), 0.5)
        assert abs(result - Decimal("1.414")) < Decimal("0.01")

    def test_power_zero_base(self):
        result = power(Decimal("0"), 0.5)
        assert result == Decimal("0")

    def test_power_negative_base(self):
        # Should handle gracefully by returning 0
        result = power(Decimal("-5"), 0.5)
        assert result == Decimal("0")

    def test_clamp_within_range(self):
        result = clamp(Decimal("5"), Decimal("0"), Decimal("10"))
        assert result == Decimal("5")

    def test_clamp_below_minimum(self):
        result = clamp(Decimal("-5"), Decimal("0"), Decimal("10"))
        assert result == Decimal("0")

    def test_clamp_above_maximum(self):
        result = clamp(Decimal("15"), Decimal("0"), Decimal("10"))
        assert result == Decimal("10")


class TestMarketDemand:
    """Test market demand calculations"""

    def test_q1_market_demand(self):
        """Q1: 250,000 × 4.8% = 12,000 units"""
        result = calculate_market_demand(1)
        assert result == Decimal("12000")

    def test_q2_market_demand(self):
        """Q2: 250,000 × 5.4% = 13,500 units"""
        result = calculate_market_demand(2)
        assert result == Decimal("13500")

    def test_q3_market_demand(self):
        """Q3: 250,000 × 6.1% = 15,250 units"""
        result = calculate_market_demand(3)
        assert result == Decimal("15250")

    def test_q4_market_demand(self):
        """Q4: 250,000 × 6.8% = 17,000 units"""
        result = calculate_market_demand(4)
        assert result == Decimal("17000")

    def test_invalid_quarter_clamps_to_q1(self):
        """Quarter 0 or negative should use Q1 data"""
        result = calculate_market_demand(0)
        assert result == Decimal("12000")


class TestRivalStrength:
    """Test competitor strength calculations"""

    def test_q1_rival_strength(self):
        """Q1: No growth yet, sum of base strengths"""
        result = calculate_rival_strength(1)
        # 52 + 46 + 58 + 84 = 240
        assert result == Decimal("240")

    def test_q2_rival_strength(self):
        """Q2: Base × 1.05"""
        result = calculate_rival_strength(2)
        # 240 × 1.05 = 252
        assert result == Decimal("252")

    def test_q4_rival_strength(self):
        """Q4: Base × (1.05)^3"""
        result = calculate_rival_strength(4)
        # 240 × 1.157625 ≈ 277.83
        assert abs(result - Decimal("277.83")) < Decimal("0.1")


class TestProductPull:
    """Test product attractiveness calculations"""

    def test_baseline_product_pull(self):
        """All attributes at zero, satisfaction at 50 (neutral)"""
        result = calculate_product_pull(
            brand=Decimal("0"),
            innovation=Decimal("0"),
            quality=Decimal("0"),
            satisfaction=Decimal("50")
        )
        # Base of 16
        assert result == Decimal("16")

    def test_product_pull_with_brand(self):
        """Brand has 1:1 impact"""
        result = calculate_product_pull(
            brand=Decimal("20"),
            innovation=Decimal("0"),
            quality=Decimal("0"),
            satisfaction=Decimal("50")
        )
        # 16 + 20 = 36
        assert result == Decimal("36")

    def test_product_pull_with_innovation(self):
        """Innovation weighted 0.6×"""
        result = calculate_product_pull(
            brand=Decimal("0"),
            innovation=Decimal("30"),
            quality=Decimal("0"),
            satisfaction=Decimal("50")
        )
        # 16 + (30 × 0.6) = 16 + 18 = 34
        assert result == Decimal("34")

    def test_product_pull_with_quality(self):
        """Quality weighted 0.5×"""
        result = calculate_product_pull(
            brand=Decimal("0"),
            innovation=Decimal("0"),
            quality=Decimal("40"),
            satisfaction=Decimal("50")
        )
        # 16 + (40 × 0.5) = 16 + 20 = 36
        assert result == Decimal("36")

    def test_product_pull_with_high_satisfaction(self):
        """Satisfaction differential from 50, weighted 0.25×"""
        result = calculate_product_pull(
            brand=Decimal("0"),
            innovation=Decimal("0"),
            quality=Decimal("0"),
            satisfaction=Decimal("70")
        )
        # 16 + ((70-50) × 0.25) = 16 + 5 = 21
        assert result == Decimal("21")

    def test_product_pull_with_low_satisfaction(self):
        """Low satisfaction reduces pull"""
        result = calculate_product_pull(
            brand=Decimal("0"),
            innovation=Decimal("0"),
            quality=Decimal("0"),
            satisfaction=Decimal("30")
        )
        # 16 + ((30-50) × 0.25) = 16 - 5 = 11
        assert result == Decimal("11")

    def test_product_pull_comprehensive(self):
        """All attributes contributing"""
        result = calculate_product_pull(
            brand=Decimal("25"),
            innovation=Decimal("20"),
            quality=Decimal("30"),
            satisfaction=Decimal("60")
        )
        # 16 + 25 + (20×0.6) + (30×0.5) + ((60-50)×0.25)
        # = 16 + 25 + 12 + 15 + 2.5 = 70.5
        assert result == Decimal("70.5")

    def test_product_pull_floor_at_4(self):
        """Even terrible product has minimum pull of 4"""
        result = calculate_product_pull(
            brand=Decimal("-100"),  # Impossible but testing floor
            innovation=Decimal("0"),
            quality=Decimal("0"),
            satisfaction=Decimal("0")  # Very low
        )
        # Should be floored at 4
        assert result == Decimal("4")


class TestOurStrength:
    """Test competitive strength calculation"""

    def test_strength_at_baseline(self):
        """Product pull of 30, all modifiers neutral"""
        result = calculate_our_strength(
            product_pull=Decimal("30"),
            fill_rate=Decimal("1.0"),
            price_index=Decimal("1.0"),
            voice_index=Decimal("1.0")
        )
        # 30 × 1.0 × 1.0 × (0.75 + 0.25×1.0) = 30
        assert result == Decimal("30")

    def test_strength_with_poor_fill_rate(self):
        """Low fill rate penalizes strength"""
        result = calculate_our_strength(
            product_pull=Decimal("40"),
            fill_rate=Decimal("0.5"),
            price_index=Decimal("1.0"),
            voice_index=Decimal("1.0")
        )
        # 40 × 1.0 × 1.0 × (0.75 + 0.25×0.5) = 40 × 0.875 = 35
        assert result == Decimal("35")

    def test_strength_with_high_price(self):
        """High price reduces strength"""
        result = calculate_our_strength(
            product_pull=Decimal("40"),
            fill_rate=Decimal("1.0"),
            price_index=Decimal("0.8"),  # Priced 20% above market
            voice_index=Decimal("1.0")
        )
        # 40 × 0.8 × 1.0 × 1.0 = 32
        assert result == Decimal("32")

    def test_strength_with_low_voice(self):
        """Low marketing voice reduces reach"""
        result = calculate_our_strength(
            product_pull=Decimal("40"),
            fill_rate=Decimal("1.0"),
            price_index=Decimal("1.0"),
            voice_index=Decimal("0.7")
        )
        # 40 × 1.0 × 0.7 × 1.0 = 28
        assert result == Decimal("28")


class TestAddressableDemandEstimate:
    """Test the main addressable demand calculation"""

    def test_opening_quarter_no_marketing(self):
        """Q1, minimal product, no marketing"""
        market_state = MarketState(
            quarter=1,
            brand_score=Decimal("0"),
            innovation_score=Decimal("0"),
            quality_score=Decimal("0"),
            satisfaction_score=Decimal("50"),
            fill_rate=Decimal("1.0"),
            market_share_prior=Decimal("0")
        )

        result = estimate_addressable_demand(market_state, Decimal("0"))

        # Should get some demand from base product pull (16)
        # But low vs rivals (240), so small share
        # Expected: ~12,000 × (16 × 0.55) / (16 × 0.55 + 240) ≈ 350 units
        assert result > Decimal("300")
        assert result < Decimal("500")

    def test_with_strong_product_no_marketing(self):
        """Strong product, but no marketing voice"""
        market_state = MarketState(
            quarter=1,
            brand_score=Decimal("30"),
            innovation_score=Decimal("25"),
            quality_score=Decimal("20"),
            satisfaction_score=Decimal("60"),
            fill_rate=Decimal("1.0"),
            market_share_prior=Decimal("0")
        )

        result = estimate_addressable_demand(market_state, Decimal("0"))

        # Product pull ≈ 16 + 30 + 15 + 10 + 2.5 = 73.5
        # But voice_idx = 0.55 (minimal), so strength = 73.5 × 0.55 = 40.4
        # Share ≈ 40.4 / (40.4 + 240) = 14.4%
        # Demand ≈ 12,000 × 0.144 = 1,728
        assert result > Decimal("1500")
        assert result < Decimal("2000")

    def test_with_strong_marketing_weak_product(self):
        """Heavy marketing but weak product"""
        market_state = MarketState(
            quarter=1,
            brand_score=Decimal("5"),
            innovation_score=Decimal("5"),
            quality_score=Decimal("5"),
            satisfaction_score=Decimal("50"),
            fill_rate=Decimal("1.0"),
            market_share_prior=Decimal("0")
        )

        # 20L marketing (above voice threshold)
        result = estimate_addressable_demand(market_state, Decimal("20"))

        # Product pull ≈ 16 + 5 + 3 + 2.5 + 0 = 26.5
        # Voice_idx = 1.0 (saturated), strength = 26.5
        # Share ≈ 26.5 / (26.5 + 240) = 9.9%
        # Demand ≈ 12,000 × 0.099 = 1,188
        assert result > Decimal("1000")
        assert result < Decimal("1400")

    def test_balanced_quarter_2(self):
        """Balanced approach in Q2"""
        market_state = MarketState(
            quarter=2,
            brand_score=Decimal("20"),
            innovation_score=Decimal("15"),
            quality_score=Decimal("20"),
            satisfaction_score=Decimal("55"),
            fill_rate=Decimal("0.95"),
            market_share_prior=Decimal("0.08")
        )

        # 12L marketing (decent voice)
        result = estimate_addressable_demand(market_state, Decimal("12"))

        # Market = 13,500
        # Product pull ≈ 16 + 20 + 9 + 10 + 1.25 = 56.25
        # Voice ≈ 0.55 + 0.45×(12/18) = 0.85
        # Fill idx ≈ 0.75 + 0.25×0.95 = 0.9875
        # Strength ≈ 56.25 × 0.85 × 0.9875 = 47.2
        # Rivals in Q2 = 252
        # Share ≈ 47.2 / (47.2 + 252) = 15.8%
        # Demand ≈ 13,500 × 0.158 = 2,133
        assert result > Decimal("1900")
        assert result < Decimal("2400")


class TestChannelLeads:
    """Test lead generation formulas"""

    def test_no_spend_generates_no_leads(self):
        investment = MarketingInvestment()
        leads = calculate_channel_leads(investment)

        for channel, count in leads.items():
            assert count == Decimal("0")

    def test_google_ads_formula(self):
        """Google: 375 × spend^0.68"""
        investment = MarketingInvestment(google_ads=Decimal("5"))
        leads = calculate_channel_leads(investment)

        # 375 × 5^0.68 ≈ 375 × 3.02 ≈ 1,133
        assert leads["google"] > Decimal("1000")
        assert leads["google"] < Decimal("1200")

    def test_meta_ads_formula(self):
        """Meta: 200 × spend^0.65"""
        investment = MarketingInvestment(meta_ads=Decimal("5"))
        leads = calculate_channel_leads(investment)

        # 200 × 5^0.65 ≈ 200 × 2.85 ≈ 570
        assert leads["meta"] > Decimal("500")
        assert leads["meta"] < Decimal("650")

    def test_diminishing_returns(self):
        """Doubling spend should NOT double leads"""
        inv_5 = MarketingInvestment(google_ads=Decimal("5"))
        inv_10 = MarketingInvestment(google_ads=Decimal("10"))

        leads_5 = calculate_channel_leads(inv_5)["google"]
        leads_10 = calculate_channel_leads(inv_10)["google"]

        ratio = leads_10 / leads_5

        # Should be < 2.0 due to diminishing returns
        assert ratio < Decimal("2.0")
        assert ratio > Decimal("1.5")  # But still meaningful increase

    def test_multiple_channels(self):
        """Multiple channels should sum correctly"""
        investment = MarketingInvestment(
            google_ads=Decimal("3"),
            meta_ads=Decimal("2"),
            social_influencer=Decimal("4")
        )
        leads = calculate_channel_leads(investment)

        total = sum(leads.values())

        # Should have leads from all three channels
        assert leads["google"] > 0
        assert leads["meta"] > 0
        assert leads["social"] > 0
        assert total > Decimal("1000")


class TestBrandImpact:
    """Test brand score accumulation"""

    def test_no_brand_building_spend(self):
        investment = MarketingInvestment()
        brand_gain = calculate_brand_impact(investment)
        assert brand_gain == Decimal("0")

    def test_meta_builds_brand(self):
        """Meta: 1.2 × spend"""
        investment = MarketingInvestment(meta_ads=Decimal("5"))
        brand_gain = calculate_brand_impact(investment)
        # 1.2 × 5 = 6
        assert brand_gain == Decimal("6.0")

    def test_social_builds_most_brand(self):
        """Social: 2.5 × spend (highest multiplier)"""
        investment = MarketingInvestment(social_influencer=Decimal("4"))
        brand_gain = calculate_brand_impact(investment)
        # 2.5 × 4 = 10
        assert brand_gain == Decimal("10.0")

    def test_combined_brand_building(self):
        """Multiple channels build brand"""
        investment = MarketingInvestment(
            meta_ads=Decimal("5"),
            social_influencer=Decimal("3"),
            events_pr=Decimal("2")
        )
        brand_gain = calculate_brand_impact(investment)
        # (1.2×5) + (2.5×3) + (1.5×2) = 6 + 7.5 + 3 = 16.5
        assert brand_gain == Decimal("16.5")


class TestFullDemandCalculation:
    """Integration test for complete demand calculation"""

    def test_full_demand_opening_quarter(self):
        """Complete calculation for opening quarter"""
        market_state = MarketState(
            quarter=1,
            brand_score=Decimal("0"),
            innovation_score=Decimal("0"),
            quality_score=Decimal("0"),
            satisfaction_score=Decimal("50"),
            fill_rate=Decimal("1.0"),
            market_share_prior=Decimal("0")
        )

        investment = MarketingInvestment(
            google_ads=Decimal("5"),
            meta_ads=Decimal("3"),
            social_influencer=Decimal("2")
        )

        result = calculate_full_demand(
            market_state=market_state,
            investment=investment,
            current_customers=4000,
            sales_capacity=Decimal("5000"),
            production_capacity=Decimal("3000")
        )

        # Basic sanity checks
        assert result.total_market_demand == Decimal("12000")
        assert result.addressable_demand_units > 0
        assert result.addressable_demand_units < result.total_market_demand
        assert result.total_raw_leads > 0
        assert result.conversion_ceiling_pct == Decimal("22")  # Base ceiling

    def test_full_demand_with_strong_position(self):
        """Q3 with established position"""
        market_state = MarketState(
            quarter=3,
            brand_score=Decimal("35"),
            innovation_score=Decimal("25"),
            quality_score=Decimal("30"),
            satisfaction_score=Decimal("65"),
            fill_rate=Decimal("0.95"),
            market_share_prior=Decimal("0.12")
        )

        investment = MarketingInvestment(
            google_ads=Decimal("6"),
            meta_ads=Decimal("4"),
            social_influencer=Decimal("5"),
            content_seo=Decimal("3")
        )

        result = calculate_full_demand(
            market_state=market_state,
            investment=investment,
            current_customers=8000,
            sales_capacity=Decimal("8000"),
            production_capacity=Decimal("6000")
        )

        # Should have higher addressable demand
        assert result.total_market_demand == Decimal("15250")
        assert result.addressable_demand_units > Decimal("3000")
        
        # Product improvements should raise ceiling
        ceiling = result.conversion_ceiling_pct
        assert ceiling > Decimal("30")  # Above base of 22


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

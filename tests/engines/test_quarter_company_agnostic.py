"""The engine must read every company number from the seed, never from code.

The PulseWear seed cannot complete a quarter -- `docs/03-company-load-state.md` never states
several constants the chain needs. That is the P0 baseline conflict, and it is the reason this
file also runs a fully-populated alternate seed: a company-agnostic engine has to be provable
against a second company, and PulseWear cannot serve as that proof today.
"""

from decimal import Decimal

import pytest

from app.config.schema import CompanySeed, OpeningScores
from app.engines.quarter import compute_quarter
from app.engines.state import CompanyState
from tests.engines.test_quarter_q1 import Q1_ALLOCATIONS

ALTERNATE_SEED = CompanySeed(
    name="alternate",
    display_name="Alternate Co (test fixture)",
    source="synthetic -- deliberately unlike Nadi Wear on every number",
    opening_cash_inr=Decimal("25000000"),
    selling_price_inr=Decimal("14999"),
    base_conversion_rate_pct=Decimal("12"),
    base_manufacturing_cost_inr=Decimal("5000"),
    manufacturing_cost_floor_inr=Decimal("4100"),
    fixed_costs_inr=Decimal("3100000"),
    working_capital_buffer_inr=Decimal("1500000"),
    holding_cost_per_unit_inr=Decimal("220"),
    warranty_claim_cost_inr=Decimal("2400"),
    referral_cost_per_lead_inr=Decimal("450"),
    referral_cap_ratio=Decimal("0.15"),
    cost_per_hire_inr=Decimal("300000"),
    core_team_size=9,
    opening_inventory_units=1100,
    opening_customers=2500,
    opening_scores=OpeningScores(
        supplier_reliability=Decimal("82"),
        logistics_efficiency=Decimal("55"),
        employee_satisfaction=Decimal("58"),
        employee_engagement=Decimal("71"),
        compliance_score=Decimal("44"),
        forecast_accuracy=Decimal("62"),
        audit_readiness=Decimal("47"),
        brand_score=Decimal("3"),
        seo_asset=Decimal("1.5"),
        buzz_score=Decimal("0"),
        quality_score=Decimal("4"),
        innovation_score=Decimal("2"),
        feature_completeness=Decimal("30"),
    ),
)


@pytest.fixture(scope="module")
def result(profile):
    opening = CompanyState.opening(ALTERNATE_SEED)
    return compute_quarter(opening, Q1_ALLOCATIONS, profile, ALTERNATE_SEED)


class TestAlternateSeedRunsTheSameChain:
    """Zero code changes to add a company -- the architecture rule in CLAUDE.md."""

    def test_the_quarter_completes(self, result):
        assert result.units_sold > 0
        assert result.revenue_inr > 0

    def test_results_differ_from_nadi_wear(self, result, nadi_wear, profile):
        """Same allocations, different company -- if any number were hardcoded these would match."""
        nadi = compute_quarter(CompanyState.opening(nadi_wear), Q1_ALLOCATIONS, profile, nadi_wear)

        assert result.units_sold != nadi.units_sold
        assert result.revenue_inr != nadi.revenue_inr
        assert result.net_cash_flow_inr != nadi.net_cash_flow_inr

    def test_seed_constants_reach_the_chain(self, result):
        """Spot-check the values most likely to be accidentally hardcoded."""
        assert result.revenue_inr == result.units_sold * Decimal("14999")
        assert result.discretionary_ceiling_inr == Decimal("25000000") - Decimal("3100000") - Decimal("1500000")

    def test_referral_cap_follows_this_company_s_ratio(self, result):
        """0.15 x 2,500 customers = 375 leads, well under Nadi Wear's 800."""
        assert result.channel_leads["referral"] == Decimal("375.00")

    def test_valuation_is_skipped_without_assets_and_liabilities(self, result):
        """No formula in docs/ derives them, so the blended figure is withheld, not invented."""
        assert result.valuation.asset_based_inr is None
        assert result.valuation.blended_inr is None
        assert "no formula in docs/" in result.valuation.gap_reason

    def test_still_deterministic_on_a_different_seed(self, profile):
        opening = CompanyState.opening(ALTERNATE_SEED)

        assert compute_quarter(opening, Q1_ALLOCATIONS, profile, ALTERNATE_SEED) == compute_quarter(
            opening, Q1_ALLOCATIONS, profile, ALTERNATE_SEED
        )


class TestPulseWearCannotRunYet:
    """Not an engine defect -- the seed is incomplete, and it says which value is missing."""

    def test_opening_state_names_the_first_missing_baseline(self, pulsewear):
        with pytest.raises(NotImplementedError, match="opening_scores"):
            CompanyState.opening(pulsewear)

    def test_the_error_says_it_cannot_be_borrowed(self, pulsewear):
        """The failure mode this guards against is silently inheriting Nadi Wear's economics."""
        with pytest.raises(NotImplementedError, match="cannot be defaulted or borrowed"):
            CompanyState.opening(pulsewear)

    def test_every_missing_value_is_enumerable(self, pulsewear):
        """What the designer has to supply before PulseWear can run a quarter."""
        missing_scores = [
            field for field, value in pulsewear.opening_scores.model_dump().items() if value is None
        ]
        missing_constants = [
            field
            for field in (
                "base_conversion_rate_pct",
                "manufacturing_cost_floor_inr",
                "working_capital_buffer_inr",
                "holding_cost_per_unit_inr",
                "warranty_claim_cost_inr",
                "referral_cost_per_lead_inr",
                "referral_cap_ratio",
                "cost_per_hire_inr",
                "core_team_size",
            )
            if getattr(pulsewear, field) is None
        ]

        # 12 of the 15 opening scores; only supplier reliability, logistics efficiency and
        # feature completeness are stated in docs/03.
        assert len(missing_scores) == 12
        assert len(missing_constants) == 9

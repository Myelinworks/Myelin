from decimal import Decimal

import pytest

from app.config.loader import load_seed

# The constants that read like formula constants but are company data, and so must resolve
# from the seed rather than the profile (docs/12-quarter-1-reference.md §2.7, §4.4, §5.1, §5.4, §6.4).
COMPANY_CONSTANTS = {
    "base_manufacturing_cost_inr": Decimal("3250"),
    "manufacturing_cost_floor_inr": Decimal("2600"),
    "selling_price_inr": Decimal("9999"),
    "holding_cost_per_unit_inr": Decimal("150"),
    "warranty_claim_cost_inr": Decimal("1500"),
    "referral_cost_per_lead_inr": Decimal("300"),
    "referral_cap_ratio": Decimal("0.20"),
    "cost_per_hire_inr": Decimal("200000"),
}

# Baselines the Q1 reference states per line (§5.2, §5.3, §6.1, §6.2, §7.1, §7.2, §7.3).
NADI_WEAR_BASELINES = {
    "supplier_reliability": Decimal("70"),
    "logistics_efficiency": Decimal("60"),
    "employee_satisfaction": Decimal("65"),
    "employee_engagement": Decimal("60"),
    "compliance_score": Decimal("50"),
    "forecast_accuracy": Decimal("55"),
    "audit_readiness": Decimal("50"),
}


def test_both_seeds_load_and_validate():
    assert load_seed("nadi_wear").display_name == "Nadi Wear Pvt. Ltd."
    assert load_seed("pulsewear").display_name == "PulseWear"


def test_loader_is_cached():
    assert load_seed("nadi_wear") is load_seed("nadi_wear")


def test_unknown_seed_names_what_is_available():
    with pytest.raises(FileNotFoundError, match="nadi_wear, pulsewear"):
        load_seed("does_not_exist")


@pytest.mark.parametrize(("field", "expected"), COMPANY_CONSTANTS.items())
def test_nadi_wear_company_constants(field, expected):
    assert getattr(load_seed("nadi_wear"), field) == expected


def test_nadi_wear_opening_position():
    seed = load_seed("nadi_wear")

    assert seed.opening_cash_inr == Decimal("15000000")
    assert seed.fixed_costs_inr == Decimal("2350000")
    assert seed.working_capital_buffer_inr == Decimal("1000000")
    assert seed.opening_inventory_units == 600
    assert seed.opening_customers == 4000
    assert seed.core_team_size == 14


def test_nadi_wear_baselines():
    scores = load_seed("nadi_wear").opening_scores

    assert {field: getattr(scores, field) for field in NADI_WEAR_BASELINES} == NADI_WEAR_BASELINES


def test_nadi_wear_cumulative_scores_open_at_zero():
    """Q2 opens at exactly what Q1 built (docs/13 §1), so Q1 opened at zero for each."""
    scores = load_seed("nadi_wear").opening_scores

    assert scores.brand_score == 0
    assert scores.seo_asset == 0
    assert scores.buzz_score == 0
    assert scores.quality_score == 0
    assert scores.innovation_score == 0
    assert scores.feature_completeness == 0


def test_pulsewear_opening_position():
    seed = load_seed("pulsewear")

    assert seed.opening_cash_inr == Decimal("15600000")
    assert seed.selling_price_inr == Decimal("10000")
    assert seed.base_manufacturing_cost_inr == Decimal("4500")
    assert seed.fixed_costs_inr == Decimal("7800000")
    assert seed.opening_inventory_units == 1920
    assert seed.opening_customers == 530
    assert seed.opening_scores.supplier_reliability == Decimal("87")
    assert seed.opening_scores.logistics_efficiency == Decimal("76")
    assert seed.opening_scores.feature_completeness == Decimal("78")


@pytest.mark.parametrize(
    "field",
    [
        "manufacturing_cost_floor_inr",
        "working_capital_buffer_inr",
        "holding_cost_per_unit_inr",
        "warranty_claim_cost_inr",
        "referral_cost_per_lead_inr",
        "referral_cap_ratio",
        "cost_per_hire_inr",
        "core_team_size",
    ],
)
def test_pulsewear_unstated_constants_stay_null(field):
    """docs/03 states none of these. Borrowing Nadi Wear's values would silently import
    another company's economics -- the P0 conflict in docs/10-implementation-gaps.md."""
    assert getattr(load_seed("pulsewear"), field) is None


def test_every_null_seed_value_is_explained():
    """A gap is only useful if it says why it's a gap."""
    for name in ("nadi_wear", "pulsewear"):
        seed = load_seed(name)
        missing = [f for f, v in seed.model_dump().items() if v is None]
        missing += [f for f, v in seed.opening_scores.model_dump().items() if v is None]

        assert missing, f"{name} has no gaps -- update this test if that is genuinely true"
        assert seed.notes, f"{name} leaves {missing} null with no explanatory note"

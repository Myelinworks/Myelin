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


class TestNadiWearOpeningRepeatPurchaseRate:
    """10.0% is not stated anywhere -- it is back-solved from docs/13-quarter-2-reference.md §1's
    stated Q2 opening of 19.0% minus what Q1's three contributing lines build."""

    def test_the_derivation_reproduces_q2s_stated_opening(self):
        """Asserts the arithmetic, not the constant: if Email's, Onboarding's or CX Team's repeat
        formula ever changes, 10.0 stops being the right opening value and this fails loudly.
        Hardcoding `== 10.0` would keep passing while silently invalidating the derivation.
        """
        from app.config.loader import load_profile
        from app.engines.lines import hr, marketing
        from app.engines.lines import sales as sales_lines

        profile = load_profile()
        opening = load_seed("nadi_wear").opening_scores.repeat_purchase_rate_pct

        # Q1 spends in Rs lakhs, docs/12-quarter-1-reference.md §12.
        built_in_q1 = (
            marketing.email_marketing(Decimal("1.60"), profile).repeat_rate_pts
            + sales_lines.onboarding(Decimal("1.25"), profile).repeat_rate_pts
            + hr.cx_team(Decimal("0.90"), profile).repeat_rate_pts
        )

        assert abs(opening + built_in_q1 - Decimal("19.0")) < Decimal("0.01")

    def test_provenance_is_flagged_as_derived_not_stated(self):
        derivation = load_seed("nadi_wear").repeat_purchase_rate_derivation

        assert derivation is not None
        assert derivation.status == "derived_from_q2_opening"
        assert "13-quarter-2-reference" in derivation.note


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


def _null_fields(name: str) -> list[str]:
    seed = load_seed(name)
    return [f for f, v in seed.model_dump().items() if v is None] + [
        f for f, v in seed.opening_scores.model_dump().items() if v is None
    ]


@pytest.mark.parametrize("name", ["nadi_wear", "pulsewear"])
def test_every_null_seed_value_is_explained(name):
    """A gap is only useful if it says why it's a gap."""
    missing = _null_fields(name)

    if missing:
        assert load_seed(name).notes, f"{name} leaves {missing} null with no explanatory note"


def test_nadi_wear_has_no_remaining_gaps():
    """Every Nadi Wear value the chain needs is now stated or derived -- the last one, the
    opening Repeat Purchase Rate, closed in Phase 5 (see TestNadiWearOpeningRepeatPurchaseRate).
    Guards the parametrised test above from going vacuous for this seed without anyone noticing.
    """
    assert _null_fields("nadi_wear") == []


def test_pulsewear_still_has_gaps():
    """The P0 baseline conflict in docs/10-implementation-gaps.md: docs/03 simply does not state
    what the chain needs, so this seed cannot run a quarter (see tests/engines/
    test_quarter_company_agnostic.py::TestPulseWearCannotRunYet)."""
    assert _null_fields("pulsewear")

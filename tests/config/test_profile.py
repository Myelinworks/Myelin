"""Config-layer tests. Deliberately imports nothing from app/engines/ -- Phase 1 ships config only."""

from decimal import Decimal

import pytest

from app.config.loader import load_profile

# Spend lines per department: Marketing 8, Sales 3, R&D 2, Operations 3, HR 3, Finance/Admin 3.
SPEND_LINE_COUNTS = {"marketing": 8, "sales": 3, "rnd": 2, "operations": 3, "hr": 3, "finance_admin": 3}

# Sections that hold constants but are not spend lines: a fitted multiplier, a strategic choice,
# and two derived quantities.
DERIVED_SECTIONS = {"brand_multiplier", "warranty", "conversion_ceiling", "penalty_risk"}


def test_default_profile_loads_and_validates():
    profile = load_profile()

    assert profile.name == "default"
    assert profile.marketing.google_ads.leads_constant == Decimal("375")
    assert profile.marketing.google_ads.leads_exponent == Decimal("0.68")


def test_loader_is_cached():
    assert load_profile() is load_profile("default")


def test_unknown_profile_names_what_is_available():
    with pytest.raises(FileNotFoundError, match="available: default"):
        load_profile("does_not_exist")


def test_profile_covers_all_22_spend_lines():
    profile = load_profile()

    counts = {
        dept: len([f for f in getattr(profile, dept).__class__.model_fields if f not in DERIVED_SECTIONS])
        for dept in SPEND_LINE_COUNTS
    }

    assert counts == SPEND_LINE_COUNTS
    assert sum(counts.values()) == 22


def test_referral_records_why_it_has_no_curve():
    """The one line with no exponent -- a hard cap whose two constants are both company data."""
    assert "seed" in load_profile().marketing.referral.note


def test_valuation_constants():
    valuation = load_profile().valuation

    assert valuation.revenue_multiple == Decimal("3.0")
    assert valuation.annualisation_factor == Decimal("4")
    assert valuation.revenue_weight == Decimal("0.70")
    assert valuation.asset_weight == Decimal("0.20")
    assert valuation.intangible_per_score_point_inr == Decimal("20000")
    assert valuation.intangible_per_customer_inr == Decimal("300")


class TestBrandMultiplier:
    """The one fitted formula in the profile -- docs/13-quarter-2-reference.md §2.1."""

    def test_reproduces_all_three_known_data_points(self):
        """Also proves coefficients survive JSON as Decimal: float 0.02 * 8.7 != 1.174."""
        brand = load_profile().marketing.brand_multiplier

        assert brand.multiplier(Decimal("8.7")) == Decimal("1.174")
        assert brand.multiplier(Decimal("31.2")) == Decimal("1.624")
        assert brand.multiplier(Decimal("34.0")) == Decimal("1.68")

    def test_is_flagged_as_unconfirmed(self):
        """It must not read as authoritative until the designer confirms it."""
        brand = load_profile().marketing.brand_multiplier

        assert brand.status == "fitted_not_confirmed"
        assert brand.formula == "1 + 0.02 * brand_score"
        assert "13-quarter-2-reference" in brand.note


class TestRawConversionComposition:
    """CX Team's contribution to raw conversion -- see docs/10-implementation-gaps.md."""

    def test_is_flagged_as_unconfirmed(self):
        composition = load_profile().raw_conversion_composition

        assert composition.status == "inferred_not_confirmed"
        assert "CX Team" in composition.formula
        assert "10-implementation-gaps" in composition.note

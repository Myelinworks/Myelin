"""R&D lines against their Q1 worked values (docs/12-quarter-1-reference.md §4)."""

from decimal import Decimal

import pytest

from app.engines.lines import rnd
from tests.engines.conftest import close

L = Decimal  # spend in Rs lakhs


class TestRnd:
    def test_quality_qa_q1(self, profile):
        """Rs 2,75,000 -> Quality 9.95, Defect Rate 6.0%."""
        result = rnd.quality_qa(L("2.75"), Decimal(0), profile)

        assert close(result.quality_score, "9.95", tolerance="0.01")
        assert close(result.defect_rate_pct, "6.0", tolerance="0.05")

    def test_quality_score_is_cumulative(self, profile):
        """It represents accumulated engineering knowledge -- it never resets."""
        first = rnd.quality_qa(L("2.75"), Decimal(0), profile).quality_score
        second = rnd.quality_qa(L("2.75"), first, profile).quality_score

        assert second == first * 2

    def test_defect_rate_floors_at_2_pct(self, profile):
        """Even world-class manufacturing has an irreducible failure rate."""
        assert rnd.quality_qa(L("1000"), Decimal(0), profile).defect_rate_pct == Decimal(2)

    def test_innovation_q1(self, profile):
        """Rs 2,25,000 -> Innovation 7.5, Feature Completeness 12.0, no launch."""
        result = rnd.innovation(L("2.25"), Decimal(0), Decimal(0), profile)

        assert close(result.innovation_score, "7.5", tolerance="0.01")
        assert close(result.feature_completeness, "12.0", tolerance="0.01")
        assert result.launched is False

    def test_innovation_score_never_decays(self, profile):
        first = rnd.innovation(L("2.25"), Decimal(0), Decimal(0), profile).innovation_score
        second = rnd.innovation(L("0"), first, Decimal(0), profile).innovation_score

        assert second == first

    def test_feature_completeness_resets_at_100(self, profile):
        """On shipping, the next round of feature work starts from zero (§4.2)."""
        result = rnd.innovation(L("2.25"), Decimal(0), Decimal("95"), profile)

        assert result.launched is True
        assert result.feature_completeness == Decimal(0)

    def test_conversion_ceiling_q1(self, profile):
        """Quality 9.95 + half of Innovation 7.5 -> a 19.1% ceiling."""
        ceiling = rnd.conversion_ceiling(Decimal("9.949874"), Decimal("7.5"), profile)

        assert close(ceiling, "19.1", tolerance="0.05")

    def test_conversion_ceiling_floors_at_15_pct_with_no_rnd(self, profile):
        """A product needs baseline functional quality just to be sellable."""
        assert rnd.conversion_ceiling(Decimal(0), Decimal(0), profile) == Decimal(15)

    def test_innovation_counts_at_half_weight(self, profile):
        """Full weighting would double-count the same R&D effort."""
        from_quality = rnd.conversion_ceiling(Decimal(10), Decimal(0), profile)
        from_innovation = rnd.conversion_ceiling(Decimal(0), Decimal(20), profile)

        assert from_quality == from_innovation

    @pytest.mark.parametrize(("years", "expected"), [(0, "0"), (1, "1.5"), (2, "3.0")])
    def test_warranty_conversion_bonus(self, profile, years, expected):
        assert rnd.warranty_conversion_bonus(years, profile) == Decimal(expected)

    def test_warranty_cost_q1(self, profile, nadi_wear):
        """562 units at a 6.01% defect rate on a 1-year term -> Rs 50,630."""
        cost = rnd.warranty_cost(Decimal("561.6215"), Decimal("6.010025"), 1, nadi_wear, profile)

        assert close(cost, "50630", tolerance="1")

    def test_two_year_warranty_costs_1_8x(self, profile, nadi_wear):
        one_year = rnd.warranty_cost(Decimal(500), Decimal(6), 1, nadi_wear, profile)
        two_year = rnd.warranty_cost(Decimal(500), Decimal(6), 2, nadi_wear, profile)

        assert two_year == one_year * Decimal("1.8")

    def test_no_warranty_costs_nothing(self, profile, nadi_wear):
        assert rnd.warranty_cost(Decimal(500), Decimal(6), 0, nadi_wear, profile) == Decimal(0)

"""Operations lines against their Q1 worked values (docs/12-quarter-1-reference.md §5)."""

from decimal import Decimal

import pytest

from app.engines.lines import operations
from tests.engines.conftest import close

L = Decimal  # spend in Rs lakhs


class TestOperations:
    def test_manufacturing_q1(self, profile, nadi_wear):
        """Rs 3,30,000 -> 923 units of capacity and a Rs 3,087 unit cost."""
        result = operations.manufacturing(L("3.30"), nadi_wear, profile)

        assert close(result.production_capacity, "923")
        assert close(result.unit_cost_inr, "3087", tolerance="1")

    def test_unit_cost_floors_at_the_seeded_floor(self, profile, nadi_wear):
        """Components set a physical floor regardless of assembly efficiency."""
        assert operations.manufacturing(L("10000"), nadi_wear, profile).unit_cost_inr == Decimal(2600)

    def test_supplier_qc_q1(self, profile):
        """Rs 1,50,000 on a baseline of 70 -> 74.9."""
        assert close(operations.supplier_qc(L("1.50"), Decimal(70), profile), "74.9", tolerance="0.05")

    def test_logistics_q1(self, profile):
        """Rs 1,20,000 on a baseline of 60 -> 65.5 efficiency, +3.3 satisfaction."""
        result = operations.logistics(L("1.20"), Decimal(60), profile)

        assert close(result.logistics_efficiency, "65.5", tolerance="0.05")
        assert close(result.satisfaction_pts, "3.3", tolerance="0.05")

    def test_available_to_sell_q1(self, profile):
        """923 capacity discounted by 74.9% reliability, plus 600 carried in -> 1,291.

        Q1 attrition is zero -- there is no prior quarter to have lost anyone from -- so the
        attrition term is inert here, exactly as it is for Sales capacity.
        """
        available = operations.available_to_sell(
            Decimal("922.6133814"), Decimal("74.8989795"), Decimal(600), Decimal(0), profile
        )

        assert close(available, "1291")

    def test_attrition_discounts_production_capacity_too(self, profile):
        """docs/13 §2.5: the attrition discount applies to "both Sales Capacity and Production
        Capacity". §4's Efficiency-Final variant is the arithmetic proof -- Rs 1,02,400 of
        Manufacturing at 7.1% attrition and 79.4% reliability gives the 300 units it quotes.
        Reliability alone would give 323, which is what this engine produced before Phase 5.
        """
        capacity = Decimal("400") * (Decimal("1.024") ** Decimal("0.7"))

        available = operations.available_to_sell(
            capacity, Decimal("79.4"), Decimal(0), Decimal("7.1"), profile
        )

        assert close(available, "300", tolerance="0.5")

    def test_pulsewear_has_no_cost_floor_and_says_so(self, profile, pulsewear):
        with pytest.raises(NotImplementedError, match="manufacturing_cost_floor_inr"):
            operations.manufacturing(L("3.30"), pulsewear, profile)


class TestBothDiscountsAreLoadBearingOnProductionCapacity:
    """docs/13 §4: `400 * 1.024^0.7 * 0.929 * 0.794 = 300`. Two audit errors already happened by
    dropping one of these two factors (docs/13 §2.5, `39af328`) -- this fixes the regression test
    that only checked the correct value, which cannot tell "both factors present" apart from
    "one factor present and the other silently compensating". Each factor going missing must
    produce its own distinct, wrong number, not just any number that isn't 300.
    """

    CAPACITY = Decimal("400") * (Decimal("1.024") ** Decimal("0.7"))
    ATTRITION_PCT = Decimal("7.1")
    RELIABILITY = Decimal("79.4")

    def test_both_factors_present_gives_the_documented_300(self, profile):
        available = operations.available_to_sell(
            self.CAPACITY, self.RELIABILITY, Decimal(0), self.ATTRITION_PCT, profile
        )
        assert close(available, "300", tolerance="0.5")

    def test_dropping_reliability_alone_overstates_capacity(self, profile):
        """Reliability missing (treated as 100, i.e. no discount) leaves only the attrition
        factor -- capacity comes out higher than 300, and distinctly different from what
        dropping attrition instead would give."""
        available = operations.available_to_sell(
            self.CAPACITY, Decimal(100), Decimal(0), self.ATTRITION_PCT, profile
        )
        assert not close(available, "300", tolerance="0.5")
        assert close(available, "377.8", tolerance="0.5")

    def test_dropping_attrition_alone_overstates_capacity_differently(self, profile):
        """Attrition missing (treated as 0%, i.e. no discount) leaves only the reliability
        factor -- this is the historical bug docs/13 §2.5 warns about (322.9 instead of 300,
        the ~1,052-vs-1,029 discrepancy at the Q2 available-to-sell level)."""
        available = operations.available_to_sell(
            self.CAPACITY, self.RELIABILITY, Decimal(0), Decimal(0), profile
        )
        assert not close(available, "300", tolerance="0.5")
        assert close(available, "322.9", tolerance="0.5")

    def test_the_two_wrong_values_are_distinct_from_each_other(self, profile):
        """Guards against a broken implementation where both factors silently collapse into the
        same discount -- if they did, the two "one factor missing" cases above would coincide."""
        reliability_only = operations.available_to_sell(
            self.CAPACITY, Decimal(100), Decimal(0), self.ATTRITION_PCT, profile
        )
        attrition_only = operations.available_to_sell(
            self.CAPACITY, self.RELIABILITY, Decimal(0), Decimal(0), profile
        )
        assert abs(reliability_only - attrition_only) > Decimal(50)

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

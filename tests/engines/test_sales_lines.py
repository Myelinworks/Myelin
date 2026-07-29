"""Sales lines against their Q1 worked values (docs/12-quarter-1-reference.md §3)."""

from decimal import Decimal

from app.engines.lines import sales
from tests.engines.conftest import close

L = Decimal  # spend in Rs lakhs


class TestSales:
    def test_reps_q1(self, profile):
        """Rs 5,45,000 -> 2,725 capacity (linear) and +4.7 conversion points (not linear)."""
        result = sales.reps(L("5.45"), profile)

        assert result.capacity == Decimal("2725.00")
        assert close(result.conversion_bonus_pts, "4.7", tolerance="0.05")

    def test_reps_capacity_is_linear(self, profile):
        """Doubling the spend doubles capacity exactly -- no exponent on this one output."""
        single = sales.reps(L("5.45"), profile).capacity
        double = sales.reps(L("10.90"), profile).capacity

        assert double == single * 2

    def test_reps_conversion_bonus_is_not_linear(self, profile):
        single = sales.reps(L("5.45"), profile).conversion_bonus_pts
        double = sales.reps(L("10.90"), profile).conversion_bonus_pts

        assert double < single * 2

    def test_crm_tools_q1(self, profile):
        """Rs 1,30,000 -> +1.7 conversion points."""
        assert close(sales.crm_tools(L("1.30"), profile), "1.7", tolerance="0.05")

    def test_onboarding_q1(self, profile):
        """Rs 1,25,000 -> +3.4 satisfaction, +3.3 repeat rate points."""
        result = sales.onboarding(L("1.25"), profile)

        assert close(result.satisfaction_pts, "3.4", tolerance="0.05")
        assert close(result.repeat_rate_pts, "3.3", tolerance="0.05")

    def test_attrition_has_no_bite_in_q1(self, profile):
        """Q1 has no prior quarter, so nothing erodes the capacity it builds."""
        assert sales.effective_capacity(Decimal("2725"), Decimal(0)) == Decimal("2725")

    def test_attrition_discounts_capacity_from_q2(self):
        """Q2 applies Q1's 7.1% attrition: 2,725 -> 2,532."""
        assert close(sales.effective_capacity(Decimal("2725"), Decimal("7.1")), "2532", tolerance="1")

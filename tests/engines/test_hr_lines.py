"""HR lines against their Q1 worked values (docs/12-quarter-1-reference.md §6)."""

from decimal import Decimal

from app.engines.lines import hr
from tests.engines.conftest import close

L = Decimal  # spend in Rs lakhs


class TestHr:
    def test_culture_benefits_q1(self, profile):
        """Rs 1,20,000 on a baseline of 65 -> 70.5 satisfaction, 1.082 productivity multiplier."""
        result = hr.culture_benefits(L("1.20"), Decimal(65), profile)

        assert close(result.employee_satisfaction, "70.5", tolerance="0.05")
        assert close(result.productivity_multiplier, "1.082", tolerance="0.001")

    def test_productivity_multiplier_is_neutral_at_50(self, profile):
        assert hr.culture_benefits(L("0"), Decimal(50), profile).productivity_multiplier == Decimal(1)

    def test_productivity_multiplier_penalises_below_50(self, profile):
        assert hr.culture_benefits(L("0"), Decimal(40), profile).productivity_multiplier < 1

    def test_training_development_q1(self, profile):
        """Rs 90,000 on a baseline of 60 -> 65.7 engagement, 7.1% attrition."""
        result = hr.training_development(L("0.90"), Decimal(60), profile)

        assert close(result.employee_engagement, "65.7", tolerance="0.05")
        assert close(result.attrition_rate_pct, "7.1", tolerance="0.05")

    def test_attrition_floors_at_3_pct(self, profile):
        """Some turnover is unavoidable in any real company."""
        assert hr.training_development(L("1000"), Decimal(60), profile).attrition_rate_pct == Decimal(3)

    def test_cx_team_q1(self, profile):
        """Rs 90,000 -> +3.8 satisfaction, +1.9 repeat rate points."""
        result = hr.cx_team(L("0.90"), profile)

        assert close(result.satisfaction_pts, "3.8", tolerance="0.05")
        assert close(result.repeat_rate_pts, "1.9", tolerance="0.05")

    def test_total_employees_q1(self, profile, nadi_wear):
        """14 core + decentralised hires across 5 departments -> ~31 employees.

        §6.4 shows 30.65, but reaches it by rounding 5,45,000/2,00,000 = 2.725 to 2.7 mid-sum.
        Unrounded the term is 2.725 and the total is 30.675 -- a display artefact, not a
        disagreement, and both round to the 31 employees the document reports.
        """
        total = hr.total_employees(
            marketing_lakhs=L("16.00"),
            sales_reps_lakhs=L("5.45"),
            rnd_lakhs=L("5.00"),
            operations_lakhs=L("6.00"),
            cx_team_lakhs=L("0.90"),
            seed=nadi_wear,
        )

        assert total == Decimal("30.675")
        assert close(total, "30.65")

"""Finance/Admin lines against their Q1 worked values (docs/12-quarter-1-reference.md §7)."""

from decimal import Decimal

from app.engines.lines import finance_admin
from tests.engines.conftest import close

L = Decimal  # spend in Rs lakhs


class TestFinanceAdmin:
    def test_compliance_legal_q1(self, profile):
        """Rs 2,80,000 on a baseline of 50 -> 58.4."""
        assert close(finance_admin.compliance_legal(L("2.80"), Decimal(50), profile), "58.4", tolerance="0.05")

    def test_financial_planning_q1(self, profile):
        """Rs 2,10,000 on a baseline of 55 -> 63.7 accuracy, a 1.37% cash efficiency bonus."""
        result = finance_admin.financial_planning(L("2.10"), Decimal(55), profile)

        assert close(result.forecast_accuracy, "63.7", tolerance="0.05")
        assert close(result.cash_efficiency_bonus_pct, "1.37", tolerance="0.01")

    def test_audit_prep_q1(self, profile):
        """Rs 2,10,000 on a baseline of 50 -> 57.2."""
        assert close(finance_admin.audit_prep(L("2.10"), Decimal(50), profile), "57.2", tolerance="0.05")

    def test_penalty_risk_q1(self, profile):
        """Compliance 58.4 and Audit Readiness 57.2 -> 19.7% risk, down from a 40% baseline."""
        risk = finance_admin.penalty_risk(Decimal("58.3666"), Decimal("57.2474"), profile)

        assert close(risk, "19.7", tolerance="0.05")

    def test_penalty_risk_floors_at_5_pct(self, profile):
        assert finance_admin.penalty_risk(Decimal(100), Decimal(100), profile) == Decimal(5)

    def test_penalty_risk_is_40_pct_if_finance_is_skipped(self, profile):
        assert finance_admin.penalty_risk(Decimal(0), Decimal(0), profile) == Decimal(40)

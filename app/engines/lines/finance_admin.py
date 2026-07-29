"""Finance/Admin -- 3 spend lines, plus the Penalty Risk they feed.

Fundamentally different from every other department: its spend affects almost nothing about this
quarter's sales. Its entire value is reducing future risk and future cost.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.config.schema import SimulationProfile
from app.engines.lines._shared import diminishing


@dataclass(frozen=True)
class FinancialPlanningResult:
    forecast_accuracy: Decimal
    cash_efficiency_bonus_pct: Decimal


def compliance_legal(
    spend_lakhs: Decimal, prior_compliance_score: Decimal, profile: SimulationProfile
) -> Decimal:
    """`Compliance Score += 5 * x^0.5`."""
    line = profile.finance_admin.compliance_legal
    return prior_compliance_score + diminishing(
        line.compliance_constant, spend_lakhs, line.compliance_exponent
    )


def financial_planning(
    spend_lakhs: Decimal, prior_forecast_accuracy: Decimal, profile: SimulationProfile
) -> FinancialPlanningResult:
    """`Forecast Accuracy += 6 * x^0.5` ·
    `Cash Efficiency Bonus = (Forecast Accuracy - 50) * 0.1%`.

    The bonus discounts NEXT quarter's fixed costs, never this quarter's -- better forecasting
    doesn't sell more units, it makes existing money go further.
    """
    line = profile.finance_admin.financial_planning
    accuracy = prior_forecast_accuracy + diminishing(
        line.forecast_accuracy_constant, spend_lakhs, line.forecast_accuracy_exponent
    )
    return FinancialPlanningResult(
        forecast_accuracy=accuracy,
        cash_efficiency_bonus_pct=(accuracy - line.cash_efficiency_centre)
        * line.cash_efficiency_pct_per_point,
    )


def audit_prep(
    spend_lakhs: Decimal, prior_audit_readiness: Decimal, profile: SimulationProfile
) -> Decimal:
    """`Audit Readiness += 5 * x^0.5`."""
    line = profile.finance_admin.audit_prep
    return prior_audit_readiness + diminishing(
        line.audit_readiness_constant, spend_lakhs, line.audit_readiness_exponent
    )


def penalty_risk(
    compliance_score: Decimal, audit_readiness: Decimal, profile: SimulationProfile
) -> Decimal:
    """`Risk % = max(5%, 40% - 0.25 * Compliance - 0.10 * Audit Readiness)`.

    Compliance is weighted more heavily because compliance failures are the direct, common trigger
    for a penalty event; audit prep mainly reduces severity once something has gone wrong.
    """
    line = profile.finance_admin.penalty_risk
    return max(
        line.floor_pct,
        line.base_pct - line.compliance_coefficient * compliance_score - line.audit_coefficient * audit_readiness,
    )

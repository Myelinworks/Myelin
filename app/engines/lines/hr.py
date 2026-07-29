"""HR -- 3 spend lines, plus the derived headcount read-out.

Satisfaction and Engagement deliberately drive different mechanics rather than both being generic
morale: Satisfaction feeds the company-wide Productivity Multiplier now, Engagement feeds
Attrition, which protects capacity already built.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.config.schema import CompanySeed, SimulationProfile
from app.engines.lines._shared import RUPEES_PER_LAKH, diminishing, require


@dataclass(frozen=True)
class CultureBenefitsResult:
    employee_satisfaction: Decimal
    productivity_multiplier: Decimal


@dataclass(frozen=True)
class TrainingDevelopmentResult:
    employee_engagement: Decimal
    attrition_rate_pct: Decimal


@dataclass(frozen=True)
class CxTeamResult:
    satisfaction_pts: Decimal
    repeat_rate_pts: Decimal


def culture_benefits(
    spend_lakhs: Decimal, prior_satisfaction: Decimal, profile: SimulationProfile
) -> CultureBenefitsResult:
    """`Employee Satisfaction += 5 * x^0.5` ·
    `Productivity Multiplier = 1 + (Satisfaction - 50) * 0.004`.

    The multiplier is centred on 50 -- a neutral, adequate-but-unremarkable baseline. It only
    helps once satisfaction rises clearly above that, and actively hurts below it.
    """
    line = profile.hr.culture_benefits
    satisfaction = prior_satisfaction + diminishing(
        line.satisfaction_constant, spend_lakhs, line.satisfaction_exponent
    )
    return CultureBenefitsResult(
        employee_satisfaction=satisfaction,
        productivity_multiplier=line.productivity_intercept
        + (satisfaction - line.productivity_centre) * line.productivity_coefficient,
    )


def training_development(
    spend_lakhs: Decimal, prior_engagement: Decimal, profile: SimulationProfile
) -> TrainingDevelopmentResult:
    """`Employee Engagement += 6 * x^0.5` · `Attrition Rate = max(3%, 15% - 0.12 * Engagement)`.

    The 3% floor exists because some turnover is unavoidable in any real company.
    """
    line = profile.hr.training_development
    engagement = prior_engagement + diminishing(
        line.engagement_constant, spend_lakhs, line.engagement_exponent
    )
    return TrainingDevelopmentResult(
        employee_engagement=engagement,
        attrition_rate_pct=max(
            line.attrition_floor_pct, line.attrition_base_pct - line.attrition_coefficient * engagement
        ),
    )


def cx_team(spend_lakhs: Decimal, profile: SimulationProfile) -> CxTeamResult:
    """`Satisfaction += 4 * x^0.5` · `Repeat Purchase Rate += 2 * x^0.4` (pts).

    The third leg of the Repeat Rate stool, alongside Marketing's Email line and Sales'
    Onboarding line.
    """
    line = profile.hr.cx_team
    return CxTeamResult(
        satisfaction_pts=diminishing(line.satisfaction_constant, spend_lakhs, line.satisfaction_exponent),
        repeat_rate_pts=diminishing(line.repeat_rate_constant, spend_lakhs, line.repeat_rate_exponent),
    )


def total_employees(
    *,
    marketing_lakhs: Decimal,
    sales_reps_lakhs: Decimal,
    rnd_lakhs: Decimal,
    operations_lakhs: Decimal,
    cx_team_lakhs: Decimal,
    seed: CompanySeed,
) -> Decimal:
    """`core team + sum(department spend / cost per hire)`.

    A derived read-out, not a decision: hiring is decentralised, so every department funds its own
    headcount from its own spend. The five contributing lines are named explicitly because
    `docs/12-quarter-1-reference.md` §6.4 counts Sales *Reps* rather than total Sales, and excludes
    HR and Finance/Admin entirely.
    """
    core = require(seed.core_team_size, "core_team_size", seed.name)
    cost_per_hire = require(seed.cost_per_hire_inr, "cost_per_hire_inr", seed.name)

    hired_spend_inr = (
        marketing_lakhs + sales_reps_lakhs + rnd_lakhs + operations_lakhs + cx_team_lakhs
    ) * RUPEES_PER_LAKH
    return core + hired_spend_inr / cost_per_hire

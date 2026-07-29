"""Sales -- 3 spend lines, plus the attrition discount applied to the capacity they build.

Marketing produces interest; Sales converts it and provides the bandwidth to handle it. Those are
two different jobs, and only one line buys hard capacity.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.config.schema import SimulationProfile
from app.engines.lines._shared import diminishing, linear


@dataclass(frozen=True)
class RepsResult:
    capacity: Decimal
    conversion_bonus_pts: Decimal


@dataclass(frozen=True)
class OnboardingResult:
    satisfaction_pts: Decimal
    repeat_rate_pts: Decimal


def reps(spend_lakhs: Decimal, profile: SimulationProfile) -> RepsResult:
    """`Capacity = 500 * x` (linear) · `Conversion Bonus = 2 * x^0.5` (pts).

    Capacity is linear because hiring reps to handle volume scales roughly linearly; making each
    rep better at closing has the usual diminishing returns. This is the only line that builds
    hard Sales Capacity, which is what makes the Reps-vs-CRM split a genuine trade-off.
    """
    line = profile.sales.reps
    return RepsResult(
        capacity=linear(line.capacity_per_lakh, spend_lakhs),
        conversion_bonus_pts=diminishing(
            line.conversion_bonus_constant, spend_lakhs, line.conversion_bonus_exponent
        ),
    )


def crm_tools(spend_lakhs: Decimal, profile: SimulationProfile) -> Decimal:
    """`Conversion Bonus = 1.5 * x^0.4` (pts). Lower exponent than Reps -- software hits its
    useful ceiling faster than human skill development."""
    line = profile.sales.crm_tools
    return diminishing(line.conversion_bonus_constant, spend_lakhs, line.conversion_bonus_exponent)


def onboarding(spend_lakhs: Decimal, profile: SimulationProfile) -> OnboardingResult:
    """`Satisfaction += 3 * x^0.5` · `Repeat Purchase Rate += 3 * x^0.4` (pts).

    Payoff is entirely next quarter -- the customer has already bought by the time onboarding
    happens. Both outputs are shared with other departments, so no one department can max either.
    """
    line = profile.sales.onboarding
    return OnboardingResult(
        satisfaction_pts=diminishing(line.satisfaction_constant, spend_lakhs, line.satisfaction_exponent),
        repeat_rate_pts=diminishing(line.repeat_rate_constant, spend_lakhs, line.repeat_rate_exponent),
    )


def effective_capacity(capacity: Decimal, prior_attrition_rate_pct: Decimal) -> Decimal:
    """`Effective Capacity = Capacity * (1 - prior quarter Attrition Rate)`.

    Attrition erodes capacity built in a *previous* quarter, so it has no effect in Q1 -- pass 0.
    """
    return capacity * (1 - prior_attrition_rate_pct / 100)

"""Operations -- 3 spend lines, plus the Available to Sell gate they feed.

Available to Sell is the most literal constraint in the model: however many leads exist and
however favourable the conversion rate, a company cannot sell units it hasn't built.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.config.schema import CompanySeed, SimulationProfile
from app.engines.lines._shared import diminishing, require


@dataclass(frozen=True)
class ManufacturingResult:
    production_capacity: Decimal
    unit_cost_inr: Decimal


@dataclass(frozen=True)
class LogisticsResult:
    logistics_efficiency: Decimal
    satisfaction_pts: Decimal


def manufacturing(
    spend_lakhs: Decimal, seed: CompanySeed, profile: SimulationProfile
) -> ManufacturingResult:
    """`Production Capacity = 400 * x^0.7` · `Unit Cost = max(floor, base - 90 * x^0.5)`.

    One spend, two outputs: investment in production lines both builds capacity and lowers unit
    cost. Splitting them would imply capacity could be bought without economies of scale. The
    base cost and its floor are company data, so they come from the seed.
    """
    line = profile.operations.manufacturing
    base_cost = seed.base_manufacturing_cost_inr
    cost_floor = require(seed.manufacturing_cost_floor_inr, "manufacturing_cost_floor_inr", seed.name)

    reduction = diminishing(line.unit_cost_reduction_constant, spend_lakhs, line.unit_cost_reduction_exponent)
    return ManufacturingResult(
        production_capacity=diminishing(line.capacity_constant, spend_lakhs, line.capacity_exponent),
        unit_cost_inr=max(cost_floor, base_cost - reduction),
    )


def supplier_qc(
    spend_lakhs: Decimal, prior_supplier_reliability: Decimal, profile: SimulationProfile
) -> Decimal:
    """`Supplier Reliability += 4 * x^0.5` (0-100 scale).

    A risk multiplier, not an output: it doesn't build anything new, it protects capacity already
    built from shortages, late shipments and component quality issues.
    """
    line = profile.operations.supplier_qc
    return prior_supplier_reliability + diminishing(
        line.reliability_constant, spend_lakhs, line.reliability_exponent
    )


def logistics(
    spend_lakhs: Decimal, prior_logistics_efficiency: Decimal, profile: SimulationProfile
) -> LogisticsResult:
    """`Logistics Efficiency += 5 * x^0.5` · `Satisfaction += 0.05 * Logistics Efficiency`.

    Satisfaction is driven by the resulting efficiency level, not by the spend directly -- delivery
    speed and packaging are what the customer actually experiences.
    """
    line = profile.operations.logistics
    efficiency = prior_logistics_efficiency + diminishing(
        line.efficiency_constant, spend_lakhs, line.efficiency_exponent
    )
    return LogisticsResult(
        logistics_efficiency=efficiency,
        satisfaction_pts=line.satisfaction_per_efficiency_point * efficiency,
    )


def available_to_sell(
    production_capacity: Decimal,
    supplier_reliability: Decimal,
    carried_inventory: Decimal,
    prior_attrition_rate_pct: Decimal,
    profile: SimulationProfile,
) -> Decimal:
    """`(Production Capacity * (1 - Attrition) * Supplier Reliability / 100) + carried inventory`.

    A strict ceiling on Units Sold with no exceptions.

    Attrition discounts production capacity as well as Sales capacity -- `docs/13` §2.5 states
    the rule applies to "**both** Sales Capacity (`500 x`) and Production Capacity
    (`400 x^0.7`)", and §4's worked Efficiency-Final variant confirms it arithmetically:
    `400 * 1.024^0.7 * 0.929 * 0.794 = 299.99`, the 300 that section quotes. Reliability alone
    would give 322.9. Like Sales, it has no effect in Q1, where there is no prior quarter to
    have lost anyone from.
    """
    line = profile.operations.supplier_qc
    effective = (
        production_capacity
        * (1 - prior_attrition_rate_pct / 100)
        * (supplier_reliability / line.effective_capacity_divisor)
    )
    return effective + carried_inventory

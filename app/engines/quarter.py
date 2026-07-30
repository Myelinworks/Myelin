"""`compute_quarter` -- the full execution chain and its three hard gates.

Pure: no I/O, no DB session, no clock, no RNG. Same inputs produce byte-identical output; the one
place a collection is summed iterates it in sorted key order.

The order below is load-bearing. Each department produces a number that feeds another
department's formula, and calculating them out of order is exactly how the two audit errors in
`docs/12-quarter-1-reference.md` §9 happened.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.config.schema import CompanySeed, SimulationProfile
from app.engines.lines import finance_admin, hr, marketing, operations, rnd, sales
from app.engines.lines._shared import require
from app.engines.state import ZERO, CompanyState, CrisisEvent, QuarterAllocations

RUPEES_PER_LAKH = Decimal(100_000)


@dataclass(frozen=True)
class Valuation:
    """`0.70 x RevenueMultiple + 0.20 x AssetBased + IntangiblePremium`.

    The intangible premium is added in full, not weighted -- it captures goodwill the other two
    methods miss. `blended_inr` is `None` when the asset-based method cannot be computed, because
    no formula in `docs/` derives total assets or liabilities.
    """

    revenue_multiple_inr: Decimal
    intangible_premium_inr: Decimal
    asset_based_inr: Decimal | None
    blended_inr: Decimal | None
    gap_reason: str | None = None


@dataclass(frozen=True)
class QuarterResult:
    """Every step of the chain, so ordering can be asserted rather than inferred from the total."""

    # Demand
    channel_leads: dict[str, Decimal]
    raw_leads: Decimal
    seo_payout_leads: Decimal
    buzz_payout_leads: Decimal
    brand_multiplier: Decimal
    productivity_multiplier: Decimal
    effective_leads: Decimal

    # Gate 1 -- sales capacity
    sales_capacity: Decimal
    effective_sales_capacity: Decimal
    leads_used: Decimal
    capacity_bound: bool

    # Gate 2 -- conversion
    raw_conversion_pct: Decimal
    conversion_ceiling_pct: Decimal
    warranty_bonus_pts: Decimal
    conversion_rate_pct: Decimal
    ceiling_bound: bool

    # Gate 3 -- supply
    units_from_funnel: Decimal
    free_repeat_units: Decimal
    total_units_demanded: Decimal
    available_to_sell: Decimal
    units_sold: Decimal
    supply_bound: bool

    # P&L
    revenue_inr: Decimal
    cogs_inr: Decimal
    gross_profit_inr: Decimal
    warranty_cost_inr: Decimal
    holding_cost_inr: Decimal
    adjusted_gross_profit_inr: Decimal
    fixed_costs_inr: Decimal
    total_discretionary_inr: Decimal
    net_cash_flow_inr: Decimal
    closing_cash_inr: Decimal

    # Budget discipline
    discretionary_ceiling_inr: Decimal
    # `spent_into_buffer` is about this quarter's *discretionary spend* eating into the buffer.
    # It is a different question from "did closing cash end below the buffer", which is the
    # survival engine's `buffer_breached` condition -- hence carrying the buffer itself, so
    # `engines/survival.py` can answer that from a QuarterResult alone.
    working_capital_buffer_inr: Decimal
    spent_into_buffer: bool
    buffer_overspend_inr: Decimal

    # Carry-forward
    cash_efficiency_bonus_pct: Decimal
    next_quarter_fixed_costs_inr: Decimal
    penalty_risk_pct: Decimal
    total_employees: Decimal
    referral_wasted_spend_inr: Decimal

    valuation: Valuation
    closing_state: CompanyState


def compute_quarter(
    opening_state: CompanyState,
    allocations: QuarterAllocations,
    profile: SimulationProfile,
    seed: CompanySeed,
    crisis_event: CrisisEvent | None = None,
) -> QuarterResult:
    """Run one quarter end to end.

    `seed` carries the company constants the lines need (selling price, cost floor, warranty claim
    cost, referral cap). `crisis_event` exists so the signature is stable for Phase 10; passing a
    non-`None` value raises rather than silently returning a quarter with the crisis ignored.
    """
    if crisis_event is not None:
        raise NotImplementedError(
            f"crisis scenario '{crisis_event.scenario}' is not implemented until Phase 10; "
            f"running the quarter would silently ignore it"
        )

    # ---- Marketing: raw leads from all 8 channels -----------------------------------------
    meta = marketing.meta_ads(allocations.meta_ads, profile)
    social = marketing.social_influencer(allocations.social_influencer, profile)
    seo = marketing.content_seo(allocations.content_seo, profile)
    events = marketing.events_pr(allocations.events_pr, profile)
    email = marketing.email_marketing(allocations.email_marketing, profile)
    referral = marketing.referral(allocations.referral, opening_state.customers, seed)
    buzz = marketing.prelaunch_buzz(allocations.prelaunch_buzz, profile)

    channel_leads = {
        "google_ads": marketing.google_ads(allocations.google_ads, profile),
        "meta_ads": meta.leads,
        "social_influencer": social.leads,
        "content_seo": seo.leads,
        "events_pr": events.leads,
        "email_marketing": email.leads,
        "referral": referral.leads,
        "prelaunch_buzz": buzz.leads,
    }
    raw_leads = sum((channel_leads[key] for key in sorted(channel_leads)), start=ZERO)

    # ---- Deferred payouts: read prior-quarter state, never recomputed from spend -----------
    seo_payout_leads = marketing.seo_asset_payout(opening_state.seo_asset, profile)
    buzz_payout = marketing.buzz_payout(
        opening_state.buzz_score, opening_state.buzz_quarters_since_investment, profile
    )

    leads_before_multipliers = raw_leads + seo_payout_leads + buzz_payout.free_leads

    # ---- Multipliers ----------------------------------------------------------------------
    # Brand built in a quarter applies from the NEXT one, so Q1 runs at 1.0.
    brand_multiplier = (
        Decimal(1)
        if opening_state.quarter_number == 1
        else marketing.brand_multiplier(opening_state.brand_score, profile)
    )
    culture = hr.culture_benefits(
        allocations.culture_benefits, opening_state.employee_satisfaction, profile
    )
    effective_leads = leads_before_multipliers * brand_multiplier * culture.productivity_multiplier

    # ---- GATE 1: sales capacity, re-checked AFTER all multipliers --------------------------
    # A productivity multiplier makes each lead easier to convert; it cannot make Sales' phones
    # ring longer. Applying it without re-checking capacity was Error 2 in §9.
    reps = sales.reps(allocations.reps, profile)
    effective_sales_capacity = sales.effective_capacity(reps.capacity, opening_state.attrition_rate_pct)
    leads_used = min(effective_leads, effective_sales_capacity)

    # ---- GATE 2: conversion, ceiling-bound then warranty added on top ----------------------
    quality = rnd.quality_qa(allocations.quality_qa, opening_state.quality_score, profile)
    innovation = rnd.innovation(
        allocations.innovation, opening_state.innovation_score, opening_state.feature_completeness, profile
    )
    crm_bonus = sales.crm_tools(allocations.crm_tools, profile)
    # CX Team's Repeat Purchase Rate bonus does double duty: it carries forward as next quarter's
    # free-repeat-unit rate (see `closing_state.advance` below) AND applies to THIS quarter's raw
    # conversion. Not stated in docs/06.3, but it is the term that reproduces both Q2 raw-conversion
    # figures in docs/13 §4/§5 (see the CX-in-raw-conversion entry in docs/10-implementation-gaps.md).
    cx = hr.cx_team(allocations.cx_team, profile)

    base_conversion = require(seed.base_conversion_rate_pct, "base_conversion_rate_pct", seed.name)
    raw_conversion_pct = (
        base_conversion
        + reps.conversion_bonus_pts
        + crm_bonus
        + cx.repeat_rate_pts
        + buzz_payout.conversion_bonus_pts
    )
    ceiling_pct = rnd.conversion_ceiling(quality.quality_score, innovation.innovation_score, profile)
    warranty_bonus = rnd.warranty_conversion_bonus(allocations.warranty_years, profile)

    # Warranty is additive AFTER the ceiling, never bounded by it: the ceiling is a build-quality
    # limit, warranty is a trust signal layering on top.
    conversion_rate_pct = min(raw_conversion_pct, ceiling_pct) + warranty_bonus

    # ---- GATE 3: supply --------------------------------------------------------------------
    units_from_funnel = leads_used * conversion_rate_pct / 100
    free_repeat_units = opening_state.repeat_purchase_rate_pct / 100 * opening_state.prior_units_sold
    total_units_demanded = units_from_funnel + free_repeat_units

    manufacturing = operations.manufacturing(allocations.manufacturing, seed, profile)
    supplier_reliability = operations.supplier_qc(
        allocations.supplier_qc, opening_state.supplier_reliability, profile
    )
    available_to_sell = operations.available_to_sell(
        manufacturing.production_capacity,
        supplier_reliability,
        opening_state.inventory_units,
        opening_state.attrition_rate_pct,
        profile,
    )
    units_sold = min(total_units_demanded, available_to_sell)

    # ---- P&L --------------------------------------------------------------------------------
    revenue = units_sold * seed.selling_price_inr
    cogs = units_sold * manufacturing.unit_cost_inr
    gross_profit = revenue - cogs

    warranty_cost = rnd.warranty_cost(
        units_sold, quality.defect_rate_pct, allocations.warranty_years, seed, profile
    )
    holding_cost = (available_to_sell - units_sold) * require(
        seed.holding_cost_per_unit_inr, "holding_cost_per_unit_inr", seed.name
    )
    adjusted_gross_profit = gross_profit - warranty_cost - holding_cost

    total_discretionary_inr = allocations.total_discretionary * RUPEES_PER_LAKH
    net_cash_flow = adjusted_gross_profit - opening_state.fixed_costs_inr - total_discretionary_inr
    closing_cash = opening_state.cash_inr + net_cash_flow

    # ---- Budget discipline ------------------------------------------------------------------
    # Spending into the working capital buffer is allowed but flagged: it is a -3 scoring
    # modifier, not a hard block.
    buffer = require(seed.working_capital_buffer_inr, "working_capital_buffer_inr", seed.name)
    discretionary_ceiling = opening_state.cash_inr - opening_state.fixed_costs_inr - buffer
    buffer_overspend = max(ZERO, total_discretionary_inr - discretionary_ceiling)

    # ---- Remaining lines and carry-forward ---------------------------------------------------
    logistics = operations.logistics(allocations.logistics, opening_state.logistics_efficiency, profile)
    training = hr.training_development(
        allocations.training_development, opening_state.employee_engagement, profile
    )
    onboarding = sales.onboarding(allocations.onboarding, profile)

    compliance = finance_admin.compliance_legal(
        allocations.compliance_legal, opening_state.compliance_score, profile
    )
    planning = finance_admin.financial_planning(
        allocations.financial_planning, opening_state.forecast_accuracy, profile
    )
    audit = finance_admin.audit_prep(allocations.audit_prep, opening_state.audit_readiness, profile)

    next_quarter_fixed_costs = opening_state.fixed_costs_inr * (
        1 - planning.cash_efficiency_bonus_pct / 100
    )

    # Depreciation, like the fixed-cost discount above, only affects what the NEXT quarter
    # inherits -- this quarter's own valuation below uses the un-depreciated opening balance.
    closing_equipment_nbv = (
        opening_state.equipment_nbv_inr
        - require(seed.equipment_depreciation, "equipment_depreciation", seed.name).per_quarter_inr
        if opening_state.equipment_nbv_inr is not None
        else None
    )

    closing_customers = opening_state.customers + units_sold
    valuation = _value_company(
        revenue,
        opening_state,
        brand_score=opening_state.brand_score + meta.brand_score + social.brand_score + events.brand_score,
        innovation_score=innovation.innovation_score,
        quality_score=quality.quality_score,
        customers=closing_customers,
        profile=profile,
        closing_cash_inr=closing_cash,
        carried_inventory_units=available_to_sell - units_sold,
        unit_cost_inr=manufacturing.unit_cost_inr,
    )

    closing_state = opening_state.advance(
        cash_inr=closing_cash,
        fixed_costs_inr=next_quarter_fixed_costs,
        inventory_units=available_to_sell - units_sold,
        customers=closing_customers,
        prior_units_sold=units_sold,
        supplier_reliability=supplier_reliability,
        logistics_efficiency=logistics.logistics_efficiency,
        employee_satisfaction=culture.employee_satisfaction,
        employee_engagement=training.employee_engagement,
        compliance_score=compliance,
        forecast_accuracy=planning.forecast_accuracy,
        audit_readiness=audit,
        brand_score=opening_state.brand_score
        + meta.brand_score
        + social.brand_score
        + events.brand_score,
        seo_asset=seo.seo_asset,
        buzz_score=buzz.buzz_score if allocations.prelaunch_buzz > 0 else opening_state.buzz_score,
        quality_score=quality.quality_score,
        innovation_score=innovation.innovation_score,
        feature_completeness=innovation.feature_completeness,
        repeat_purchase_rate_pct=opening_state.repeat_purchase_rate_pct
        + email.repeat_rate_pts
        + onboarding.repeat_rate_pts
        + cx.repeat_rate_pts,
        attrition_rate_pct=training.attrition_rate_pct,
        buzz_quarters_since_investment=_next_buzz_offset(opening_state, allocations),
        equipment_nbv_inr=closing_equipment_nbv,
        product_ip_inr=opening_state.product_ip_inr,
        accounts_receivable_inr=opening_state.accounts_receivable_inr,
        liabilities_inr=opening_state.liabilities_inr,
    )

    return QuarterResult(
        channel_leads=channel_leads,
        raw_leads=raw_leads,
        seo_payout_leads=seo_payout_leads,
        buzz_payout_leads=buzz_payout.free_leads,
        brand_multiplier=brand_multiplier,
        productivity_multiplier=culture.productivity_multiplier,
        effective_leads=effective_leads,
        sales_capacity=reps.capacity,
        effective_sales_capacity=effective_sales_capacity,
        leads_used=leads_used,
        capacity_bound=effective_sales_capacity < effective_leads,
        raw_conversion_pct=raw_conversion_pct,
        conversion_ceiling_pct=ceiling_pct,
        warranty_bonus_pts=warranty_bonus,
        conversion_rate_pct=conversion_rate_pct,
        ceiling_bound=ceiling_pct < raw_conversion_pct,
        units_from_funnel=units_from_funnel,
        free_repeat_units=free_repeat_units,
        total_units_demanded=total_units_demanded,
        available_to_sell=available_to_sell,
        units_sold=units_sold,
        supply_bound=available_to_sell < total_units_demanded,
        revenue_inr=revenue,
        cogs_inr=cogs,
        gross_profit_inr=gross_profit,
        warranty_cost_inr=warranty_cost,
        holding_cost_inr=holding_cost,
        adjusted_gross_profit_inr=adjusted_gross_profit,
        fixed_costs_inr=opening_state.fixed_costs_inr,
        total_discretionary_inr=total_discretionary_inr,
        net_cash_flow_inr=net_cash_flow,
        closing_cash_inr=closing_cash,
        discretionary_ceiling_inr=discretionary_ceiling,
        working_capital_buffer_inr=buffer,
        spent_into_buffer=buffer_overspend > 0,
        buffer_overspend_inr=buffer_overspend,
        cash_efficiency_bonus_pct=planning.cash_efficiency_bonus_pct,
        next_quarter_fixed_costs_inr=next_quarter_fixed_costs,
        penalty_risk_pct=finance_admin.penalty_risk(compliance, audit, profile),
        total_employees=hr.total_employees(
            marketing_lakhs=allocations.marketing_total,
            sales_reps_lakhs=allocations.reps,
            rnd_lakhs=allocations.rnd_total,
            operations_lakhs=allocations.operations_total,
            cx_team_lakhs=allocations.cx_team,
            seed=seed,
        ),
        referral_wasted_spend_inr=referral.wasted_spend_inr,
        valuation=valuation,
        closing_state=closing_state,
    )


def _total_assets_inr(
    closing_cash_inr: Decimal,
    inventory_value_inr: Decimal,
    equipment_nbv_inr: Decimal,
    product_ip_inr: Decimal,
    accounts_receivable_inr: Decimal,
) -> Decimal:
    """`Total Assets = closing cash + carried inventory value + equipment NBV + product IP + AR`.

    Not stated as a formula anywhere in `docs/00-formula-index.md` -- derived from the balance
    sheets in `docs/12-quarter-1-reference.md` §11 and `docs/14-quarter-3-reference.md` §1, both of
    which this identity reproduces exactly (Rs 1,84,22,586 and Rs 1,84,41,515).
    """
    return closing_cash_inr + inventory_value_inr + equipment_nbv_inr + product_ip_inr + accounts_receivable_inr


def _value_company(
    revenue: Decimal,
    opening_state: CompanyState,
    *,
    brand_score: Decimal,
    innovation_score: Decimal,
    quality_score: Decimal,
    customers: Decimal,
    profile: SimulationProfile,
    closing_cash_inr: Decimal,
    carried_inventory_units: Decimal,
    unit_cost_inr: Decimal,
) -> Valuation:
    line = profile.valuation

    revenue_multiple = revenue * line.annualisation_factor * line.revenue_multiple
    intangible = (brand_score + innovation_score + quality_score) * line.intangible_per_score_point_inr + (
        customers * line.intangible_per_customer_inr
    )

    if (
        opening_state.equipment_nbv_inr is None
        or opening_state.product_ip_inr is None
        or opening_state.accounts_receivable_inr is None
        or opening_state.liabilities_inr is None
    ):
        return Valuation(
            revenue_multiple_inr=revenue_multiple,
            intangible_premium_inr=intangible,
            asset_based_inr=None,
            blended_inr=None,
            gap_reason=(
                "asset-based valuation needs equipment NBV, product IP, accounts receivable and "
                "liabilities, and no formula in docs/ derives any of them -- the Q1 and Q3 "
                "references quote them directly, so they must be supplied on CompanySeed"
            ),
        )

    total_assets = _total_assets_inr(
        closing_cash_inr,
        carried_inventory_units * unit_cost_inr,
        opening_state.equipment_nbv_inr,
        opening_state.product_ip_inr,
        opening_state.accounts_receivable_inr,
    )
    asset_based = total_assets - opening_state.liabilities_inr
    return Valuation(
        revenue_multiple_inr=revenue_multiple,
        intangible_premium_inr=intangible,
        asset_based_inr=asset_based,
        blended_inr=line.revenue_weight * revenue_multiple + line.asset_weight * asset_based + intangible,
    )


def _next_buzz_offset(opening_state: CompanyState, allocations: QuarterAllocations) -> int:
    """A fresh Buzz investment restarts the two-quarter payout clock; otherwise it advances until
    the Q+2 payout is spent."""
    if allocations.prelaunch_buzz > 0:
        return 1
    if opening_state.buzz_quarters_since_investment in (1, 2):
        return opening_state.buzz_quarters_since_investment + 1
    return 0

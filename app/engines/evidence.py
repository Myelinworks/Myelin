"""`extract_evidence` -- the Phase 8 producer half of the dual pipeline (`docs/02` §10).

Pure, same discipline as `engines/scoring.py`: no I/O, no DB session, no clock, no RNG. Turns the
22 department spend lines + opening state into category-tagged behavioural facts -- never a score,
never a judgment word. Interpreting these facts (including the 15 `JUDGMENT` scoring criteria that
have no other input, per `docs/19-work-split.md` T1) is explicitly out of scope here; this module
only produces the evidence a future scorer would read.

**Independence from the business-impact pipeline.** Every fact here is computed by calling the
same pure `app/engines/lines/*` functions `compute_quarter` itself calls -- never by reading a
`QuarterResult`. Two facts the phase spec's own worked examples name (R&D's raw-conversion-vs-
ceiling gap, Finance's closing-cash-vs-buffer) need numbers that only exist after the full
cross-department chain runs (Sales+HR+Marketing+Buzz feed raw conversion; revenue/COGS/gates feed
closing cash). Both are replaced below with proxies derivable from this department's own lines (or,
for Finance, from opening state + this quarter's allocations alone, matching the pre-revenue
`discretionary_ceiling` check `compute_quarter` itself does) -- so a bug in the business pipeline's
assembly order can never silently change what evidence reports, and vice versa.

Categories are the same 7 trait keys already declared in `ScoringConfig.traits`
(`app/config/profiles/default.json`) -- reusing sourced vocabulary rather than inventing a second
taxonomy for the same seven cognitive dimensions `docs/02` §6 names.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.config.schema import CompanySeed, SimulationProfile
from app.engines.lines import finance_admin, hr, marketing, operations, rnd, sales
from app.engines.lines._shared import RUPEES_PER_LAKH, require
from app.engines.state import ZERO, CompanyState, QuarterAllocations

# The 6 CLAUDE.md-canonical department buckets -- exactly `QuarterAllocations`'s `*_total`
# groupings. `None` is reserved for facts that genuinely span more than one department (only
# `consistent_objective`, below).
MARKETING = "marketing"
SALES = "sales"
RND = "rnd"
OPERATIONS = "operations"
HR = "hr"
FINANCE_ADMIN = "finance_admin"

WEIGHT_CONFIRMED = "confirmed"
WEIGHT_DESCRIPTIVE_ONLY = "descriptive_only"
WEIGHT_NOT_APPLICABLE = "not_applicable"

# docs/02 §5's worked "Example weighting" table is the only place any evidence weight is sourced
# in `docs/` -- four rows, all feeding Strategic Thinking. Nothing else carries a sourced weight;
# everything else is `descriptive_only` rather than silently weightless (phase item 3).
_DIVERSIFIED_MARKETING_WEIGHT = Decimal("2.0")
_LONG_TERM_INVESTMENT_WEIGHT = Decimal("3.0")
_BALANCED_BUDGET_WEIGHT = Decimal("3.0")
_CONSISTENT_OBJECTIVE_WEIGHT = Decimal("2.0")

# "funded >= 4 channels" is the phase spec's own stated threshold for Diversification (§1 worked
# example), not an invented default.
_DIVERSIFICATION_THRESHOLD = 4

# Undocumented anywhere in `docs/` (same gap the legacy evidence_engine.py flagged) -- carried only
# to band `marketing_channel_concentration`'s value, and the fact stays `descriptive_only` because
# of it, never scored off these numbers.
_HIGH_CONCENTRATION_THRESHOLD = Decimal("0.7")
_MEDIUM_CONCENTRATION_THRESHOLD = Decimal("0.4")

# The 7 diminishing-curve Marketing channels -- Referral is deliberately excluded (docs/12 §2.7:
# "the only channel with no exponent", a hard cap scored on its own terms by CAC Discipline).
_DIVERSIFIABLE_MARKETING_LINES = (
    "google_ads",
    "meta_ads",
    "social_influencer",
    "content_seo",
    "events_pr",
    "email_marketing",
    "prelaunch_buzz",
)
# Deferred-payoff channels named explicitly in the phase spec's §1 worked example ("funded Buzz/SEO").
_LONG_TERM_MARKETING_LINES = ("content_seo", "prelaunch_buzz")


@dataclass(frozen=True)
class EvidenceFact:
    """One behavioural flag. `value` is a fact, never a score: bool / Decimal / str / dict / tuple.

    `department` is `None` only for `consistent_objective`, which spans Marketing's brand/SEO/Buzz
    lines and R&D's Innovation line and is not owned by either alone.
    """

    department: str | None
    evidence_key: str
    value: Any
    categories: tuple[str, ...]
    detail: str
    weight: Decimal | None
    weight_status: str


def _marketing_facts(allocations: QuarterAllocations, opening_state: CompanyState, profile: SimulationProfile,
                      seed: CompanySeed) -> list[EvidenceFact]:
    channel_spend: dict[str, Decimal] = {
        line: getattr(allocations, line) for line in _DIVERSIFIABLE_MARKETING_LINES
    }
    funded = tuple(sorted(c for c, spend in channel_spend.items() if spend > 0))
    diversified = len(funded) >= _DIVERSIFICATION_THRESHOLD

    total_channel_spend = sum(channel_spend.values(), start=ZERO)
    max_channel = max(channel_spend, key=lambda c: channel_spend[c]) if total_channel_spend > 0 else None
    max_share = channel_spend[max_channel] / total_channel_spend if max_channel is not None else ZERO
    if max_share >= _HIGH_CONCENTRATION_THRESHOLD:
        band = "High"
    elif max_share >= _MEDIUM_CONCENTRATION_THRESHOLD:
        band = "Medium"
    else:
        band = "Low"
    high_concentration = band == "High"

    long_term_funded = tuple(c for c in _LONG_TERM_MARKETING_LINES if channel_spend.get(c, ZERO) > 0)

    meta = marketing.meta_ads(allocations.meta_ads, profile)
    social = marketing.social_influencer(allocations.social_influencer, profile)
    events = marketing.events_pr(allocations.events_pr, profile)
    brand_funded = tuple(
        c for c, spend in (("meta_ads", allocations.meta_ads), ("social_influencer", allocations.social_influencer),
                           ("events_pr", allocations.events_pr))
        if spend > 0
    )
    brand_score_built = meta.brand_score + social.brand_score + events.brand_score

    referral = marketing.referral(allocations.referral, opening_state.customers, seed)
    at_cap = referral.leads == referral.lead_cap

    return [
        EvidenceFact(
            department=MARKETING,
            evidence_key="marketing_diversification",
            value={"channels_funded": len(funded), "channels": funded, "diversified": diversified},
            categories=("strategic_thinking", "capital_allocation"),
            detail=f"{len(funded)} of {len(_DIVERSIFIABLE_MARKETING_LINES)} diminishing-curve "
                   f"channels funded (>= {_DIVERSIFICATION_THRESHOLD} required): {', '.join(funded) or 'none'}",
            weight=_DIVERSIFIED_MARKETING_WEIGHT,
            weight_status=WEIGHT_CONFIRMED,
        ),
        EvidenceFact(
            department=MARKETING,
            evidence_key="marketing_long_term_investment",
            value={"channels_funded": long_term_funded},
            categories=("long_term_thinking", "strategic_thinking"),
            detail=f"deferred-payoff channels funded: {', '.join(long_term_funded) or 'none'} "
                   f"(of {', '.join(_LONG_TERM_MARKETING_LINES)})",
            weight=_LONG_TERM_INVESTMENT_WEIGHT,
            weight_status=WEIGHT_CONFIRMED,
        ),
        EvidenceFact(
            department=MARKETING,
            evidence_key="marketing_balanced_budget",
            value={"diversified": diversified, "high_concentration": high_concentration,
                   "balanced": diversified and not high_concentration},
            categories=("strategic_thinking", "capital_allocation"),
            detail=f"diversified={diversified} and not high_concentration={high_concentration}",
            weight=_BALANCED_BUDGET_WEIGHT,
            weight_status=WEIGHT_CONFIRMED,
        ),
        EvidenceFact(
            department=MARKETING,
            evidence_key="marketing_channel_concentration",
            value={"max_channel": max_channel, "max_channel_share": max_share, "band": band},
            categories=("risk_management",),
            detail=f"largest single channel ({max_channel}) is {max_share:.1%} of diversifiable "
                   f"marketing spend -- band {band} (resolves high_channel_dependency + risk_level, "
                   f"no sourced weight in docs/ for either)",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
        EvidenceFact(
            department=MARKETING,
            evidence_key="marketing_cac_discipline",
            value={"leads": referral.leads, "lead_cap": referral.lead_cap, "at_cap": at_cap,
                   "wasted_spend_inr": referral.wasted_spend_inr},
            categories=("capital_allocation", "risk_management"),
            detail=f"Referral funded {referral.leads} of a {referral.lead_cap} lead cap "
                   f"(wasted spend Rs {referral.wasted_spend_inr:,.2f})",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
        EvidenceFact(
            department=MARKETING,
            evidence_key="marketing_brand_building",
            value={"channels_funded": brand_funded, "brand_score_built": brand_score_built},
            categories=("long_term_thinking",),
            detail=f"brand-building channels funded: {', '.join(brand_funded) or 'none'} "
                   f"(+{brand_score_built} Brand Score this quarter)",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
    ]


def _sales_facts(allocations: QuarterAllocations, profile: SimulationProfile) -> list[EvidenceFact]:
    reps_result = sales.reps(allocations.reps, profile)
    crm_bonus = sales.crm_tools(allocations.crm_tools, profile)
    onboarding_result = sales.onboarding(allocations.onboarding, profile)

    return [
        EvidenceFact(
            department=SALES,
            evidence_key="sales_capacity_investment",
            value={"capacity_built": reps_result.capacity, "spend_lakhs": allocations.reps},
            categories=("systems_thinking", "capital_allocation"),
            detail=f"Reps funded: +{reps_result.capacity} units/quarter Sales Capacity",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
        EvidenceFact(
            department=SALES,
            evidence_key="sales_conversion_investment",
            value={"conversion_bonus_pts": crm_bonus, "funded": allocations.crm_tools > 0},
            categories=("capital_allocation",),
            detail=f"CRM Tools funded: +{crm_bonus} conversion points",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
        EvidenceFact(
            department=SALES,
            evidence_key="sales_retention_investment",
            value={"repeat_rate_pts": onboarding_result.repeat_rate_pts,
                   "satisfaction_pts": onboarding_result.satisfaction_pts},
            categories=("long_term_thinking",),
            detail=f"Onboarding funded: +{onboarding_result.repeat_rate_pts} Repeat Purchase Rate points",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
    ]


def _rnd_facts(allocations: QuarterAllocations, opening_state: CompanyState, profile: SimulationProfile) -> list[EvidenceFact]:
    quality_after = rnd.quality_qa(allocations.quality_qa, opening_state.quality_score, profile)
    innovation_after = rnd.innovation(
        allocations.innovation, opening_state.innovation_score, opening_state.feature_completeness, profile
    )
    ceiling_before = rnd.conversion_ceiling(opening_state.quality_score, opening_state.innovation_score, profile)
    ceiling_after = rnd.conversion_ceiling(quality_after.quality_score, innovation_after.innovation_score, profile)
    lift = ceiling_after - ceiling_before

    return [
        EvidenceFact(
            department=RND,
            evidence_key="rnd_quality_ceiling_lift",
            value={"ceiling_before_pct": ceiling_before, "ceiling_after_pct": ceiling_after, "lift_pts": lift},
            categories=("systems_thinking", "capital_allocation"),
            detail=f"Quality QA + Innovation spend lifted the Conversion Ceiling by {lift} points "
                   f"this quarter ({ceiling_before}% -> {ceiling_after}%) -- the R&D-only analogue of "
                   f"the ceiling-undershot fact, computed without raw_conversion_pct (needs "
                   f"Sales+HR+Marketing, off-limits here)",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
        EvidenceFact(
            department=RND,
            evidence_key="rnd_innovation_investment",
            value={"innovation_score_built": innovation_after.innovation_score - opening_state.innovation_score,
                   "feature_completeness": innovation_after.feature_completeness,
                   "launched": innovation_after.launched},
            categories=("long_term_thinking", "strategic_thinking"),
            detail=f"Innovation spend built +{innovation_after.innovation_score - opening_state.innovation_score} "
                   f"Innovation Score this quarter (launched={innovation_after.launched})",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
        EvidenceFact(
            department=RND,
            evidence_key="rnd_warranty_offered",
            value={"warranty_years": allocations.warranty_years},
            categories=("risk_management",),
            detail=f"warranty term selected: {allocations.warranty_years} year(s)",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
    ]


def _operations_facts(allocations: QuarterAllocations, opening_state: CompanyState, seed: CompanySeed,
                       profile: SimulationProfile) -> list[EvidenceFact]:
    manufacturing_result = operations.manufacturing(allocations.manufacturing, seed, profile)
    supplier_reliability_after = operations.supplier_qc(
        allocations.supplier_qc, opening_state.supplier_reliability, profile
    )
    available = operations.available_to_sell(
        manufacturing_result.production_capacity, supplier_reliability_after, opening_state.inventory_units,
        opening_state.attrition_rate_pct, profile,
    )
    logistics_result = operations.logistics(allocations.logistics, opening_state.logistics_efficiency, profile)

    return [
        EvidenceFact(
            department=OPERATIONS,
            evidence_key="operations_capacity_planning",
            value={"production_capacity": manufacturing_result.production_capacity,
                   "supplier_reliability_after": supplier_reliability_after, "available_to_sell": available},
            categories=("systems_thinking", "capital_allocation"),
            detail=f"Manufacturing + Supplier QC funded: {available} units available to sell this quarter",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
        EvidenceFact(
            department=OPERATIONS,
            evidence_key="operations_inventory_planning",
            value={"opening_inventory_units": opening_state.inventory_units,
                   "carrying_stock": opening_state.inventory_units > 0},
            categories=("risk_management",),
            detail=f"opened the quarter carrying {opening_state.inventory_units} unsold units",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
        EvidenceFact(
            department=OPERATIONS,
            evidence_key="operations_process_efficiency",
            value={"logistics_efficiency_after": logistics_result.logistics_efficiency,
                   "satisfaction_pts": logistics_result.satisfaction_pts},
            categories=("capital_allocation",),
            detail=f"Logistics funded: efficiency now {logistics_result.logistics_efficiency}",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
    ]


def _hr_facts(allocations: QuarterAllocations, opening_state: CompanyState, profile: SimulationProfile) -> list[EvidenceFact]:
    culture_result = hr.culture_benefits(allocations.culture_benefits, opening_state.employee_satisfaction, profile)
    training_result = hr.training_development(
        allocations.training_development, opening_state.employee_engagement, profile
    )
    cx_result = hr.cx_team(allocations.cx_team, profile)

    return [
        EvidenceFact(
            department=HR,
            evidence_key="hr_culture_investment",
            value={"employee_satisfaction_after": culture_result.employee_satisfaction,
                   "productivity_multiplier": culture_result.productivity_multiplier},
            categories=("leadership", "long_term_thinking"),
            detail=f"Culture & Benefits funded: Employee Satisfaction now {culture_result.employee_satisfaction}",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
        EvidenceFact(
            department=HR,
            evidence_key="hr_training_investment",
            value={"employee_engagement_after": training_result.employee_engagement,
                   "attrition_rate_pct_after": training_result.attrition_rate_pct},
            categories=("long_term_thinking",),
            detail=f"Training & Development funded: Engagement now {training_result.employee_engagement}, "
                   f"Attrition {training_result.attrition_rate_pct}%",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
        EvidenceFact(
            department=HR,
            evidence_key="hr_cx_team_investment",
            value={"satisfaction_pts": cx_result.satisfaction_pts, "repeat_rate_pts": cx_result.repeat_rate_pts},
            categories=("long_term_thinking",),
            detail=f"CX Team funded: +{cx_result.repeat_rate_pts} Repeat Purchase Rate points",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
    ]


def _finance_admin_facts(allocations: QuarterAllocations, opening_state: CompanyState, seed: CompanySeed,
                          profile: SimulationProfile) -> list[EvidenceFact]:
    buffer = require(seed.working_capital_buffer_inr, "working_capital_buffer_inr", seed.name)
    discretionary_ceiling = opening_state.cash_inr - opening_state.fixed_costs_inr - buffer
    total_discretionary_inr = allocations.total_discretionary * RUPEES_PER_LAKH
    margin = discretionary_ceiling - total_discretionary_inr

    compliance_after = finance_admin.compliance_legal(
        allocations.compliance_legal, opening_state.compliance_score, profile
    )
    audit_after = finance_admin.audit_prep(allocations.audit_prep, opening_state.audit_readiness, profile)
    risk_after = finance_admin.penalty_risk(compliance_after, audit_after, profile)
    planning_result = finance_admin.financial_planning(
        allocations.financial_planning, opening_state.forecast_accuracy, profile
    )

    return [
        EvidenceFact(
            department=FINANCE_ADMIN,
            evidence_key="finance_cash_preservation",
            value={"discretionary_ceiling_inr": discretionary_ceiling,
                   "total_discretionary_inr": total_discretionary_inr, "margin_inr": margin,
                   "buffer_preserved": margin >= 0},
            categories=("risk_management", "capital_allocation"),
            detail=(
                f"pre-revenue margin = (opening cash - fixed costs - buffer) - this quarter's "
                f"discretionary spend = Rs {margin:,.2f} (buffer_preserved={margin >= 0}); a "
                f"proxy for closing-cash-vs-buffer that stays derivable from opening state + "
                f"allocations alone, same inputs `compute_quarter`'s own discretionary_ceiling check uses"
            ),
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
        EvidenceFact(
            department=FINANCE_ADMIN,
            evidence_key="finance_compliance_investment",
            value={"compliance_score_after": compliance_after, "audit_readiness_after": audit_after,
                   "penalty_risk_pct_after": risk_after},
            categories=("risk_management",),
            detail=f"Compliance & Legal + Audit Prep funded: Penalty Risk now {risk_after}%",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
        EvidenceFact(
            department=FINANCE_ADMIN,
            evidence_key="finance_planning_investment",
            value={"forecast_accuracy_after": planning_result.forecast_accuracy,
                   "cash_efficiency_bonus_pct": planning_result.cash_efficiency_bonus_pct},
            categories=("capital_allocation",),
            detail=f"Financial Planning funded: +{planning_result.cash_efficiency_bonus_pct}% next-quarter "
                   f"cash efficiency bonus",
            weight=None,
            weight_status=WEIGHT_DESCRIPTIVE_ONLY,
        ),
    ]


def _compounding_line_totals(allocations: QuarterAllocations) -> dict[str, Decimal]:
    """Same grouping `engines/scoring.py`'s `_compounding_asset_cut` modifier uses, reused here as
    a positive fact ("stayed consistent") rather than a penalty ("cut")."""
    return {
        "brand": allocations.meta_ads + allocations.social_influencer + allocations.events_pr,
        "seo": allocations.content_seo,
        "buzz": allocations.prelaunch_buzz,
        "innovation": allocations.innovation,
    }


def _consistent_objective_fact(
    allocations: QuarterAllocations, prior_allocations: QuarterAllocations | None
) -> EvidenceFact:
    if prior_allocations is None:
        return EvidenceFact(
            department=None,
            evidence_key="consistent_objective",
            value="no_prior_quarter",
            categories=("strategic_thinking",),
            detail="no prior quarter to compare against (e.g. Q1)",
            weight=_CONSISTENT_OBJECTIVE_WEIGHT,
            weight_status=WEIGHT_NOT_APPLICABLE,
        )

    current = _compounding_line_totals(allocations)
    prior = _compounding_line_totals(prior_allocations)
    dropped_to_zero = tuple(
        line for line, prior_spend in prior.items() if prior_spend > 0 and current[line] == 0
    )
    consistent = len(dropped_to_zero) == 0

    return EvidenceFact(
        department=None,
        evidence_key="consistent_objective",
        value={"consistent": consistent, "dropped_to_zero": dropped_to_zero},
        categories=("strategic_thinking",),
        detail=f"compounding lines funded last quarter that dropped to zero this quarter: "
               f"{', '.join(dropped_to_zero) or 'none'}",
        weight=_CONSISTENT_OBJECTIVE_WEIGHT,
        weight_status=WEIGHT_CONFIRMED,
    )


def extract_evidence(
    allocations: QuarterAllocations,
    opening_state: CompanyState,
    profile: SimulationProfile,
    seed: CompanySeed,
    prior_allocations: QuarterAllocations | None = None,
) -> tuple[EvidenceFact, ...]:
    """One call, one quarter: every fact derivable from this quarter's allocations, the opening
    state they were made against, and (for `consistent_objective` only) the prior quarter's
    allocations. Never reads a `QuarterResult`."""
    facts: list[EvidenceFact] = [
        *_marketing_facts(allocations, opening_state, profile, seed),
        *_sales_facts(allocations, profile),
        *_rnd_facts(allocations, opening_state, profile),
        *_operations_facts(allocations, opening_state, seed, profile),
        *_hr_facts(allocations, opening_state, profile),
        *_finance_admin_facts(allocations, opening_state, seed, profile),
        _consistent_objective_fact(allocations, prior_allocations),
    ]
    return tuple(facts)


def aggregate_by_category(facts: tuple[EvidenceFact, ...]) -> dict[str, tuple[EvidenceFact, ...]]:
    """Collapses facts across departments by cognitive-dimension category -- the load-bearing rule
    from CLAUDE.md ("Cognitive scoring reads only EvidenceRecord, aggregated by cognitive-dimension
    category, never by workspace"). A Finance fact and a Marketing fact tagged `capital_allocation`
    land in the same bucket here."""
    by_category: dict[str, list[EvidenceFact]] = {}
    for fact in facts:
        for category in fact.categories:
            by_category.setdefault(category, []).append(fact)
    return {category: tuple(items) for category, items in by_category.items()}

"""Pydantic schemas for the config layers.

`SimulationProfile` holds curve shapes -- every constant, coefficient, exponent, floor and cap
used by the 22 department spend lines, plus the valuation constants. `CompanySeed` holds opening
company state. Per `CLAUDE.md`'s company-agnostic rule, no company number appears in a profile
and no curve shape appears in a seed.

`Scenario` composes the two into what a student is actually dropped into -- which seed, which
profile, how many quarters, when a crisis fires -- plus the opening values for state that
belongs to the legacy pipeline rather than the 22-line chain. It is deliberately not a synonym
for a seed: several scenarios could run the same company with different quarter counts or crisis
timings.

Units convention (`docs/00-formula-index.md`): `x` = spend on that line in Rs lakhs. Money fields
carry an `_inr` suffix and are always rupees; conversion to lakhs happens at the input boundary,
never inside a formula. Every numeric is `Decimal` -- floats would make the fitted brand
multiplier fail to reproduce its own source data points exactly.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class _Frozen(BaseModel):
    """Config is immutable and cached; `extra="forbid"` turns a typo'd JSON key into a load error."""

    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------------------
# Marketing -- 8 spend lines
# --------------------------------------------------------------------------------------


class GoogleAdsConfig(_Frozen):
    """`Leads = 375 * x^0.68`"""

    leads_constant: Decimal
    leads_exponent: Decimal


class MetaAdsConfig(_Frozen):
    """`Leads = 200 * x^0.65` · `Impressions = 40,000 * x` · `Brand Score += 1.2 * x`"""

    leads_constant: Decimal
    leads_exponent: Decimal
    impressions_per_lakh: Decimal
    brand_per_lakh: Decimal


class SocialInfluencerConfig(_Frozen):
    """`Leads = 225 * x^0.72` · `Brand Score += 2.5 * x`"""

    leads_constant: Decimal
    leads_exponent: Decimal
    brand_per_lakh: Decimal


class ContentSeoConfig(_Frozen):
    """`Leads = 75 * x^0.62` · `SEO Asset += 3.5 * x` · `Free leads next quarter = SEO Asset * 25`"""

    leads_constant: Decimal
    leads_exponent: Decimal
    asset_per_lakh: Decimal
    asset_payout_per_point: Decimal


class EventsPrConfig(_Frozen):
    """`Leads = 90 * x^0.62` · `Brand Score += 1.5 * x`"""

    leads_constant: Decimal
    leads_exponent: Decimal
    brand_per_lakh: Decimal


class EmailMarketingConfig(_Frozen):
    """`Leads = 80 * x^0.55` · `Repeat Purchase Rate += 3 * x^0.5` (pts)"""

    leads_constant: Decimal
    leads_exponent: Decimal
    repeat_rate_constant: Decimal
    repeat_rate_exponent: Decimal


class ReferralConfig(_Frozen):
    """The one spend line with no curve: a hard cap, not a diminishing return.

    `Lead Cap = cap_ratio * existing customers`, flat cost per lead. Both constants are company
    data, so they live in the seed -- this section exists to record that the omission is deliberate.
    """

    note: str


class PreLaunchBuzzConfig(_Frozen):
    """`Buzz = 4 * x^0.5` (zero leads this quarter) · Q+1 `Buzz * 15` · Q+2 `Buzz * 25` and a
    one-time `Buzz * 0.3` pt conversion bonus."""

    buzz_constant: Decimal
    buzz_exponent: Decimal
    payout_next_quarter_per_point: Decimal
    payout_second_quarter_per_point: Decimal
    conversion_bonus_per_point: Decimal


class BrandMultiplierConfig(_Frozen):
    """`Lead Multiplier = 1 + 0.02 * Brand Score`, applied from Q2 onward.

    The source states three data points, not a function (`docs/13-quarter-2-reference.md` § 2.1,
    `docs/10-implementation-gaps.md` P1). `intercept`/`coefficient` are the machine-usable form of
    the `formula` string; without them nothing could consume this without an expression evaluator.
    """

    formula: str
    intercept: Decimal
    coefficient: Decimal
    status: str
    note: str

    def multiplier(self, brand_score: Decimal) -> Decimal:
        """Lead multiplier for a Brand Score. Fitted, not designer-confirmed -- see `status`."""
        return self.intercept + self.coefficient * brand_score


class MarketingConfig(_Frozen):
    google_ads: GoogleAdsConfig
    meta_ads: MetaAdsConfig
    social_influencer: SocialInfluencerConfig
    content_seo: ContentSeoConfig
    events_pr: EventsPrConfig
    email_marketing: EmailMarketingConfig
    referral: ReferralConfig
    prelaunch_buzz: PreLaunchBuzzConfig
    brand_multiplier: BrandMultiplierConfig


# --------------------------------------------------------------------------------------
# Sales -- 3 spend lines
# --------------------------------------------------------------------------------------


class SalesRepsConfig(_Frozen):
    """`Capacity = 500 * x` (linear -- the only line that buys hard capacity) ·
    `Conversion Bonus = 2 * x^0.5` (pts)"""

    capacity_per_lakh: Decimal
    conversion_bonus_constant: Decimal
    conversion_bonus_exponent: Decimal


class CrmToolsConfig(_Frozen):
    """`Conversion Bonus = 1.5 * x^0.4` (pts)"""

    conversion_bonus_constant: Decimal
    conversion_bonus_exponent: Decimal


class OnboardingConfig(_Frozen):
    """`Satisfaction += 3 * x^0.5` · `Repeat Purchase Rate += 3 * x^0.4` (pts)"""

    satisfaction_constant: Decimal
    satisfaction_exponent: Decimal
    repeat_rate_constant: Decimal
    repeat_rate_exponent: Decimal


class SalesConfig(_Frozen):
    reps: SalesRepsConfig
    crm_tools: CrmToolsConfig
    onboarding: OnboardingConfig


# --------------------------------------------------------------------------------------
# R&D -- 2 spend lines, plus the warranty choice and the conversion ceiling they feed
# --------------------------------------------------------------------------------------


class QualityQaConfig(_Frozen):
    """`Quality Score += 6 * x^0.5` (cumulative, never resets) ·
    `Defect Rate = max(2%, 8% - 1.2 * x^0.5)`"""

    quality_score_constant: Decimal
    quality_score_exponent: Decimal
    defect_rate_base_pct: Decimal
    defect_rate_constant: Decimal
    defect_rate_exponent: Decimal
    defect_rate_floor_pct: Decimal


class InnovationConfig(_Frozen):
    """`Feature Completeness += 8 * x^0.5` (resets at 100) ·
    `Innovation Score += 5 * x^0.5` (never decays)"""

    feature_completeness_constant: Decimal
    feature_completeness_exponent: Decimal
    feature_completeness_reset_at: Decimal
    innovation_score_constant: Decimal
    innovation_score_exponent: Decimal


class WarrantyConfig(_Frozen):
    """Conversion bonus is additive AFTER the ceiling, not subject to it
    (`docs/12-quarter-1-reference.md` § 9, Error 1). Claim cost per unit is company data -- seed."""

    one_year_conversion_bonus_pts: Decimal
    two_year_conversion_bonus_pts: Decimal
    two_year_cost_multiplier: Decimal


class ConversionCeilingConfig(_Frozen):
    """`Ceiling = 15% + (Quality Score + 0.5 * Innovation Score) * 0.3%`

    Innovation carries half weight because it only partially translates into this quarter's
    conversion; Quality is the direct measure and carries full weight.
    """

    base_pct: Decimal
    quality_weight: Decimal
    innovation_weight: Decimal
    pct_per_point: Decimal


class RndConfig(_Frozen):
    quality_qa: QualityQaConfig
    innovation: InnovationConfig
    warranty: WarrantyConfig
    conversion_ceiling: ConversionCeilingConfig


# --------------------------------------------------------------------------------------
# Operations -- 3 spend lines
# --------------------------------------------------------------------------------------


class ManufacturingConfig(_Frozen):
    """`Production Capacity = 400 * x^0.7` · `Unit Cost = max(floor, base - 90 * x^0.5)`

    `base` and `floor` are company data (seed); only the reduction curve is a profile constant.
    """

    capacity_constant: Decimal
    capacity_exponent: Decimal
    unit_cost_reduction_constant: Decimal
    unit_cost_reduction_exponent: Decimal


class SupplierQcConfig(_Frozen):
    """`Supplier Reliability += 4 * x^0.5` · `Effective Capacity = Capacity * Reliability / 100`"""

    reliability_constant: Decimal
    reliability_exponent: Decimal
    effective_capacity_divisor: Decimal


class LogisticsConfig(_Frozen):
    """`Logistics Efficiency += 5 * x^0.5` · `Satisfaction += 0.05 * Logistics Efficiency`"""

    efficiency_constant: Decimal
    efficiency_exponent: Decimal
    satisfaction_per_efficiency_point: Decimal


class OperationsConfig(_Frozen):
    manufacturing: ManufacturingConfig
    supplier_qc: SupplierQcConfig
    logistics: LogisticsConfig


# --------------------------------------------------------------------------------------
# HR -- 3 spend lines
# --------------------------------------------------------------------------------------


class CultureBenefitsConfig(_Frozen):
    """`Employee Satisfaction += 5 * x^0.5` ·
    `Productivity Multiplier = 1 + (Satisfaction - 50) * 0.004`"""

    satisfaction_constant: Decimal
    satisfaction_exponent: Decimal
    productivity_intercept: Decimal
    productivity_centre: Decimal
    productivity_coefficient: Decimal


class TrainingDevelopmentConfig(_Frozen):
    """`Employee Engagement += 6 * x^0.5` · `Attrition Rate = max(3%, 15% - 0.12 * Engagement)`"""

    engagement_constant: Decimal
    engagement_exponent: Decimal
    attrition_base_pct: Decimal
    attrition_coefficient: Decimal
    attrition_floor_pct: Decimal


class CxTeamConfig(_Frozen):
    """`Satisfaction += 4 * x^0.5` · `Repeat Purchase Rate += 2 * x^0.4` (pts)"""

    satisfaction_constant: Decimal
    satisfaction_exponent: Decimal
    repeat_rate_constant: Decimal
    repeat_rate_exponent: Decimal


class HrConfig(_Frozen):
    culture_benefits: CultureBenefitsConfig
    training_development: TrainingDevelopmentConfig
    cx_team: CxTeamConfig


# --------------------------------------------------------------------------------------
# Finance / Admin -- 3 spend lines, plus the penalty risk they feed
# --------------------------------------------------------------------------------------


class ComplianceLegalConfig(_Frozen):
    """`Compliance Score += 5 * x^0.5`"""

    compliance_constant: Decimal
    compliance_exponent: Decimal


class FinancialPlanningConfig(_Frozen):
    """`Forecast Accuracy += 6 * x^0.5` ·
    `Cash Efficiency Bonus = (Forecast Accuracy - 50) * 0.1%`, discounting NEXT quarter's fixed costs"""

    forecast_accuracy_constant: Decimal
    forecast_accuracy_exponent: Decimal
    cash_efficiency_centre: Decimal
    cash_efficiency_pct_per_point: Decimal


class AuditPrepConfig(_Frozen):
    """`Audit Readiness += 5 * x^0.5`"""

    audit_readiness_constant: Decimal
    audit_readiness_exponent: Decimal


class PenaltyRiskConfig(_Frozen):
    """`Risk % = max(5%, 40% - 0.25 * Compliance - 0.10 * Audit Readiness)`"""

    base_pct: Decimal
    compliance_coefficient: Decimal
    audit_coefficient: Decimal
    floor_pct: Decimal


class FinanceAdminConfig(_Frozen):
    compliance_legal: ComplianceLegalConfig
    financial_planning: FinancialPlanningConfig
    audit_prep: AuditPrepConfig
    penalty_risk: PenaltyRiskConfig


# --------------------------------------------------------------------------------------
# Valuation
# --------------------------------------------------------------------------------------


class ValuationConfig(_Frozen):
    """`Blended = 0.70 * (Quarterly Revenue * 4 * 3.0x) + 0.20 * (Assets - Liabilities)
    + (Brand + Innovation + Quality) * Rs 20,000 + Customers * Rs 300`

    The intangible premium is added in full, not weighted.
    """

    revenue_multiple: Decimal
    annualisation_factor: Decimal
    revenue_weight: Decimal
    asset_weight: Decimal
    intangible_per_score_point_inr: Decimal
    intangible_per_customer_inr: Decimal


class ScoringCriterion(_Frozen):
    """One of the 21 sub-criteria in `docs/10-scoring-methodology.md`.

    `kind` is the load-bearing field. `MECHANICAL` means the criterion is decidable from the
    quarter's numbers, and `engines/scoring.py` must hold a check keyed by `id`. `JUDGMENT` means
    it is not -- the criterion asks about something no input carries (a *stated* thesis, whether
    the student raised an issue unprompted, what evidence was available "at the time") -- and
    `reason` says which. A JUDGMENT criterion is returned UNSCORED and held out of the
    denominator; it is never inferred from spend, because a plausible-looking proxy for
    "did they own the trade-off" is exactly the kind of invented number this project refuses.
    """

    id: str
    trait: str
    kind: str
    description: str
    reason: str | None = None


class ScoringModifier(_Frozen):
    """An execution-precision adjustment, applied on top of trait points.

    `rule` documents the trigger; the predicate lives in `engines/scoring.py` keyed by `id`, for
    the same reason survival conditions work that way -- a rule string is never evaluated.
    `status` flags a modifier whose stated trigger cannot be fully checked from available inputs.
    """

    id: str
    points: Decimal
    rule: str
    status: str | None = None
    note: str | None = None


class ScoringBand(_Frozen):
    """`docs/10-scoring-methodology.md` score bands. `minimum` is inclusive."""

    name: str
    minimum: Decimal


class ScoringThresholds(_Frozen):
    """Numeric cut-offs the rubric's prose implies but does not always state.

    `ceiling_undershoot_points` is stated ("exceeds roughly 3 points"). The rest are not:
    the rubric says "a small, deliberate buffer" and "materially less investment" without
    numbers, so each carries its own status flag rather than being presented as sourced.
    """

    ceiling_undershoot_points: Decimal
    supply_waste_units: Decimal
    supply_waste_status: str
    capacity_waste_leads: Decimal
    capacity_waste_status: str
    compounding_cut_ratio: Decimal
    compounding_cut_status: str
    coordination_ratio: Decimal
    coordination_status: str


class ScoringConfig(_Frozen):
    """The evaluation matrix: 7 weighted traits x 3 sub-criteria each, plus modifier sets.

    `modifier_sets` is keyed by name so the crisis set (`docs/11-crisis-system.md`) and the Q4
    set (`docs/16`, `docs/17`) register as additional entries in Phases 10 and 11 without any
    change here -- `score_quarter` applies whichever sets it is asked for.
    """

    status: str
    source: str
    traits: dict[str, Decimal]
    criteria: list[ScoringCriterion]
    modifier_sets: dict[str, list[ScoringModifier]]
    bands: list[ScoringBand]
    thresholds: ScoringThresholds


class SurvivalCondition(_Frozen):
    """One survival check: which predicate runs, and what status it produces when it fires.

    `id` is the machine-usable part -- `engines/survival.py` keys its predicates off it, and an
    id with no registered predicate is a load-time error rather than a silently skipped check.
    `rule` is the human-readable statement of the same thing, kept alongside for the same reason
    `BrandMultiplierConfig` keeps `formula` next to its coefficients: so a reader can see what
    the code is supposed to be doing without reading the code.

    Config decides *which* conditions are active and what each produces; the predicate itself is
    code. A rule string is documentation, never evaluated.
    """

    id: str
    rule: str
    outcome: str


class SurvivalConfig(_Frozen):
    """When a run is failing, and when it is over.

    Only three conditions, all traceable: `cash_exhausted` is the unambiguous cash-zero line,
    and the other two are the designer's stated Distressed definition
    (`docs/17-designer-resolutions.md`, Tier Assignment). No runway thresholds or debt covenants
    -- nothing in the source specifies any.
    """

    status: str
    source: str
    conditions: list[SurvivalCondition]


class RawConversionCompositionConfig(_Frozen):
    """`raw = base + Reps bonus + CRM bonus + CX Team repeat-rate bonus + Buzz Q+2 bonus`.

    Not stated in `docs/00-formula-index.md`; derived from the gap between `base + Reps + CRM`
    and the stated raw figures in `docs/13-quarter-2-reference.md` §4/§5. `status` flags it the
    same way as the fitted brand multiplier and the equipment depreciation rate: implemented
    because it reproduces the doc's numbers, but resting on a single CX spend level (both Q2
    variants used the same Rs 1,50,000), so it is not designer-confirmed.
    """

    formula: str
    status: str
    note: str


# --------------------------------------------------------------------------------------
# Crisis system -- Phase 10, docs/11-crisis-system.md
# --------------------------------------------------------------------------------------


class CrisisResponseLinesConfig(_Frozen):
    """Price-Match Fund / Comparison Ads / Retention Offers -- shared across Scenarios A and B
    (docs/11 §3's table, confirmed identical for B by the docs/14 §4 worked example, which applies
    the same three formulas against B's own 0.60 dampening baseline). Scenario C has no documented
    recovery mechanism for its dampening or conversion penalty at all -- these lines don't apply
    there.

    `price_match_fund_rate` is the coefficient on `x^0.5` only -- the additive intercept is each
    scenario's own dampening multiplier, not a fixed 0.75 (confirmed by Scenario B's own Choice-D
    worked example, which starts from 0.60: `0.60 + 0.25 * x^0.5`).
    """

    price_match_fund_rate: Decimal
    comparison_ads_rate: Decimal
    comparison_ads_cap_pts: Decimal
    retention_base_pct: Decimal
    retention_rate: Decimal


class PriceWarriorConfig(_Frozen):
    """Scenario A (docs/11 §3). Choice A's price is the one crisis price-cut number stated
    explicitly anywhere in the source (docs/11 line 77: "Cut Price to Match (Rs 9,999 -> Rs
    7,999)")."""

    dampening_multiplier: Decimal
    conversion_penalty_pts: Decimal
    brand_erosion_pts: Decimal
    choice_a_price_inr: Decimal
    choice_d_dampening_rate: Decimal  # Contract Sales/Promo Surge


class MarketingBlitzConfig(_Frozen):
    """Scenario B (docs/11 §4). Two flagged special cases, neither a confirmed general rule:

    - `choice_a_price_inr` (Rs 8,149) appears only in `docs/15`'s worked novice example, never in
      `docs/11` (the spec of record) -- used because it is a real, stated number from a real
      source document, not invented, but flagged since the spec of record doesn't restate it.
    - `choice_b_qualified_penalty_pts` (-1.2, when Quality Score >= 25) is the "Choice B
      Qualification" that appears only in `docs/14` section 4's single worked instance, with no
      general formula stated anywhere -- implemented as the exact stated pair, not generalised to
      other Quality Score values.
    """

    dampening_multiplier: Decimal
    conversion_penalty_pts: Decimal
    brand_erosion_pts: Decimal
    choice_a_price_inr: Decimal
    choice_a_price_status: str
    choice_b_quality_threshold: Decimal
    choice_b_qualified_penalty_pts: Decimal
    choice_b_qualification_status: str
    choice_d_dampening_rate: Decimal  # Contract Marketing Agency Surge


class FeatureLeapfrogConfig(_Frozen):
    """Scenario C (docs/11 §5). Choice A's price cut is stated nowhere in any source document --
    not even reliably back-solvable from `docs/15`'s worked NCF (source-doc rounding drift of
    ~Rs 1,300 is already visible elsewhere, e.g. `docs/12` section 11's asset-based valuation).
    `engines/crisis.py` raises `NotImplementedError` for this specific combination rather than
    invent a price.
    """

    dampening_multiplier: Decimal
    conversion_penalty_pts: Decimal
    conversion_penalty_reduced_pts: Decimal
    ceiling_penalty_pts: Decimal
    innovation_threshold: Decimal
    choice_d_innovation_rate: Decimal  # Contract R&D Sprint


class SupplyShockConfig(_Frozen):
    """Scenario D (docs/11 §6) -- "the most important single formula in the entire crisis
    system". `choice_a_offset` is 0, confirmed by `docs/15`'s own novice worked arithmetic
    (`0.50 + 0.174 + 0 + 0 = 0.674`), which contradicts `docs/17-designer-resolutions.md`'s claim
    that Choice A carries +0.50 -- see `engines/crisis.py`'s module docstring for the full
    derivation. No worked example anywhere exercises a +0.50 branch, so which choice (if any)
    carries it stays genuinely unassigned; `choice_unassigned_high_tier_status` records that
    rather than silently picking one.
    """

    base_cut: Decimal
    reliability_coefficient: Decimal
    reliability_centre: Decimal
    choice_a_offset: Decimal
    choice_a_offset_status: str
    choice_b_offset: Decimal
    choice_c_offset: Decimal
    # docs/14 §6: "Permanent Supplier Reliability gain: 79.8 -> 94.7 (+10, forever)" when Choice B
    # is picked -- a flat addition on top of whatever this quarter's own Ops spend already
    # produced (84.7), confirmed exactly by 84.7 + 10 = 94.7, carried forward permanently.
    choice_b_permanent_reliability_gain: Decimal
    choice_unassigned_high_tier: Decimal
    choice_unassigned_high_tier_status: str
    emergency_fund_rate: Decimal
    floor: Decimal
    cap: Decimal
    manufacturing_cost_surcharge_inr: Decimal
    choice_d_contract_penalty: Decimal
    choice_d_capacity_constant: Decimal
    choice_d_capacity_exponent: Decimal
    choice_d_cost_premium_inr: Decimal


class CrisisConfig(_Frozen):
    """Scenario-specific constants for the four Q3 crisis events (`docs/11-crisis-system.md`)."""

    status: str
    source: str
    price_warrior: PriceWarriorConfig
    marketing_blitz: MarketingBlitzConfig
    feature_leapfrog: FeatureLeapfrogConfig
    supply_shock: SupplyShockConfig
    response_lines: CrisisResponseLinesConfig


# --------------------------------------------------------------------------------------
# Top-level profile
# --------------------------------------------------------------------------------------


class SimulationProfile(_Frozen):
    """Curve shapes for all 22 spend lines plus valuation. Contains no company numbers."""

    name: str
    source: str
    survival: SurvivalConfig
    scoring: ScoringConfig
    raw_conversion_composition: RawConversionCompositionConfig
    marketing: MarketingConfig
    sales: SalesConfig
    rnd: RndConfig
    operations: OperationsConfig
    hr: HrConfig
    finance_admin: FinanceAdminConfig
    valuation: ValuationConfig
    crisis: CrisisConfig


# --------------------------------------------------------------------------------------
# Company seed
# --------------------------------------------------------------------------------------


class OpeningScores(_Frozen):
    """Opening values for every score a spend line accumulates into.

    The first seven are the baselines the Q1 reference states explicitly (Supplier Reliability 70,
    Logistics 60, Employee Satisfaction 65, Engagement 60, Compliance 50, Forecast Accuracy 55,
    Audit Readiness 50). They read like formula constants but are company data -- a different
    company starts elsewhere, so they belong here, not in the profile.

    `None` means the value is not stated in `docs/` for that company. It is never a default.
    """

    supplier_reliability: Decimal | None = None
    logistics_efficiency: Decimal | None = None
    employee_satisfaction: Decimal | None = None
    employee_engagement: Decimal | None = None
    compliance_score: Decimal | None = None
    forecast_accuracy: Decimal | None = None
    audit_readiness: Decimal | None = None

    brand_score: Decimal | None = None
    seo_asset: Decimal | None = None
    buzz_score: Decimal | None = None
    quality_score: Decimal | None = None
    innovation_score: Decimal | None = None
    feature_completeness: Decimal | None = None

    repeat_purchase_rate_pct: Decimal | None = None
    attrition_rate_pct: Decimal | None = None


class EquipmentDepreciationConfig(_Frozen):
    """Straight-line reduction to Equipment NBV, applied once per quarter to what the NEXT
    quarter inherits -- this quarter's own valuation uses the un-depreciated opening balance, the
    same pattern Financial Planning uses for the Cash Efficiency Bonus (it discounts next
    quarter's fixed costs, not this quarter's own).

    Two data points only (`docs/12-quarter-1-reference.md` §11, `docs/14-quarter-3-reference.md`
    §1): Rs 25,00,000 (Q1 close) -> Rs 20,00,000 (Q3 start, two quarterly steps later) implies Rs
    2,50,000/quarter. No stated depreciation rule in docs/ -- see `status`.
    """

    per_quarter_inr: Decimal
    status: str
    note: str


class RepeatPurchaseRateDerivationConfig(_Frozen):
    """Provenance for `opening_scores.repeat_purchase_rate_pct`, which no source document states
    directly.

    Carries no value of its own -- the number lives in `opening_scores`, where the engine reads
    it -- because duplicating it here would create two sources of truth for one quantity. This
    records only *how* that number was arrived at.
    """

    status: str
    note: str


class CompanySeed(_Frozen):
    """Opening state for one company. Contains no curve shapes.

    Only the fields a quarter cannot start without are required. Everything else is optional
    because `docs/03-company-load-state.md` (PulseWear) simply does not state several values that
    `docs/12-quarter-1-reference.md` (Nadi Wear) does -- see `notes` and the P0 baseline conflict
    in `docs/10-implementation-gaps.md`.
    """

    name: str
    display_name: str
    source: str

    opening_cash_inr: Decimal
    selling_price_inr: Decimal
    base_conversion_rate_pct: Decimal | None = None
    base_manufacturing_cost_inr: Decimal
    manufacturing_cost_floor_inr: Decimal | None = None
    fixed_costs_inr: Decimal
    working_capital_buffer_inr: Decimal | None = None

    holding_cost_per_unit_inr: Decimal | None = None
    warranty_claim_cost_inr: Decimal | None = None
    referral_cost_per_lead_inr: Decimal | None = None
    referral_cap_ratio: Decimal | None = None
    cost_per_hire_inr: Decimal | None = None
    core_team_size: int | None = None

    opening_inventory_units: int
    opening_customers: int
    opening_scores: OpeningScores

    # Balance-sheet constants behind the asset-based valuation term. `docs/12-quarter-1-reference.md`
    # §11 and `docs/14-quarter-3-reference.md` §1 quote them directly for Nadi Wear; no formula in
    # docs/ derives any of the four, and `None` skips the asset-based valuation method rather than
    # guessing a company's balance sheet.
    equipment_nbv_inr: Decimal | None = None
    equipment_depreciation: EquipmentDepreciationConfig | None = None
    product_ip_inr: Decimal | None = None
    accounts_receivable_inr: Decimal | None = None
    liabilities_inr: Decimal | None = None

    repeat_purchase_rate_derivation: RepeatPurchaseRateDerivationConfig | None = None

    notes: dict[str, str] = Field(default_factory=dict)


# --------------------------------------------------------------------------------------
# Scenario -- what a student is dropped into
# --------------------------------------------------------------------------------------


class ScenarioModifier(_Frozen):
    """One of the four quarter-level modifiers the legacy percentage-matrix model multiplies
    into a decision's base impact (`app/engines/legacy_matrix/`).

    Both the opening values and the derivation from company state are unspecified in source
    (`docs/10-implementation-gaps.md`, P2 "Modifier derivation from company state not
    specified"), so they are seeded from config with a visible `status` rather than derived by
    invented arithmetic. `1.0` is the multiplicative identity: neutral, and obviously a
    placeholder rather than a real calibration.

    These are **not read by `compute_quarter`/`run_quarter()`** -- the 22-line chain has no
    modifier stage. They exist so the legacy path stays instantiable.
    """

    value: Decimal
    status: str


class OpeningWorkspaceState(_Frozen):
    """Opening values for the six legacy `*State` KPI snapshots.

    Same standing as `ScenarioModifier`: these rows belong to the legacy per-decision pipeline
    (`services/decision_engine.py`, the ~72-key Decision taxonomy), not to the 22-line chain,
    which reads `CompanySeed` and `CompanyStateSnapshot` instead. They live in scenario config
    rather than being computed at company-creation time so that no opening number is invented in
    code -- see `status`/`note` for which of these values are sourced and which are placeholders.
    """

    status: str
    note: str
    finance: dict[str, Decimal | None]
    marketing: dict[str, Decimal | None]
    product: dict[str, Decimal | None]
    sales: dict[str, Decimal | None]
    operations: dict[str, Decimal | None]
    cx: dict[str, Decimal | None]


class Scenario(_Frozen):
    """One runnable simulation setup. Adding a scenario is one JSON file and zero code."""

    scenario_id: str
    display_name: str
    source: str

    seed: str
    profile: str

    total_quarters: int
    # Which quarter fires a crisis, or `None` for a scenario with no crisis. `crisis_scenario`
    # picks the A/B/C/D branch (`docs/11-crisis-system.md`); `None` means assign at runtime.
    # Neither is consumed yet -- the crisis engine is Phase 10 and `compute_quarter` still
    # refuses a non-`None` CrisisEvent.
    crisis_quarter: int | None = None
    crisis_scenario: str | None = None

    modifiers: dict[str, ScenarioModifier]
    opening_workspace_state: OpeningWorkspaceState

    notes: dict[str, str] = Field(default_factory=dict)

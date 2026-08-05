"""Inputs to `compute_quarter` -- opening state, the quarter's allocations, and the crisis stub.

All plain frozen dataclasses. Nothing here touches a DB, a clock or the filesystem.
"""

from dataclasses import dataclass, replace
from decimal import Decimal

from app.config.schema import CompanySeed
from app.engines.lines._shared import require

ZERO = Decimal(0)

# Opening scores that must be stated: the seven per-line baselines, and the five cumulative
# scores plus feature completeness. None can be defaulted -- a missing baseline would silently
# skew the productivity multiplier, attrition and penalty risk, and a missing cumulative score
# would silently move the conversion ceiling. Sorted so construction order is deterministic.
REQUIRED_OPENING_SCORES = sorted(
    [
        "supplier_reliability",
        "logistics_efficiency",
        "employee_satisfaction",
        "employee_engagement",
        "compliance_score",
        "forecast_accuracy",
        "audit_readiness",
        "brand_score",
        "seo_asset",
        "buzz_score",
        "quality_score",
        "innovation_score",
        "feature_completeness",
    ]
)


@dataclass(frozen=True)
class CrisisEvent:
    """Placeholder for the Phase 10 crisis engine.

    `compute_quarter` accepts it so the signature does not change later, but refuses to run with a
    non-`None` value rather than silently producing a quarter with the crisis ignored.
    """

    scenario: str


@dataclass(frozen=True)
class QuarterAllocations:
    """The 22 department spend lines, each in Rs lakhs, plus the warranty term.

    Warranty is a strategic choice rather than a spend line: offering it costs nothing up front,
    and the cost materialises later in proportion to how many units fail.
    """

    google_ads: Decimal = ZERO
    meta_ads: Decimal = ZERO
    social_influencer: Decimal = ZERO
    content_seo: Decimal = ZERO
    events_pr: Decimal = ZERO
    email_marketing: Decimal = ZERO
    referral: Decimal = ZERO
    prelaunch_buzz: Decimal = ZERO

    reps: Decimal = ZERO
    crm_tools: Decimal = ZERO
    onboarding: Decimal = ZERO

    quality_qa: Decimal = ZERO
    innovation: Decimal = ZERO

    manufacturing: Decimal = ZERO
    supplier_qc: Decimal = ZERO
    logistics: Decimal = ZERO

    culture_benefits: Decimal = ZERO
    training_development: Decimal = ZERO
    cx_team: Decimal = ZERO

    compliance_legal: Decimal = ZERO
    financial_planning: Decimal = ZERO
    audit_prep: Decimal = ZERO

    warranty_years: int = 0

    # Crisis response (Phase 10, docs/11-crisis-system.md) -- only meaningful in the quarter a
    # crisis actually fires (`CrisisEvent.scenario` is not `None`); all-zero/`None` otherwise.
    # One `crisis_choice_d_spend` field, not one per scenario: only one crisis ever fires in a
    # given quarter, so it always means "this quarter's active scenario's own Choice-D line"
    # (Contract Sales/Promo Surge for A, Contract Marketing Agency Surge for B, Contract R&D
    # Sprint for C, Contract Manufacturing for D).
    crisis_choice: str | None = None  # "A" | "B" | "C" | "D"
    price_match_fund: Decimal = ZERO
    comparison_ads: Decimal = ZERO
    retention_offers: Decimal = ZERO
    emergency_supply_fund: Decimal = ZERO
    crisis_choice_d_spend: Decimal = ZERO

    @property
    def marketing_total(self) -> Decimal:
        return (
            self.google_ads
            + self.meta_ads
            + self.social_influencer
            + self.content_seo
            + self.events_pr
            + self.email_marketing
            + self.referral
            + self.prelaunch_buzz
        )

    @property
    def sales_total(self) -> Decimal:
        return self.reps + self.crm_tools + self.onboarding

    @property
    def rnd_total(self) -> Decimal:
        return self.quality_qa + self.innovation

    @property
    def operations_total(self) -> Decimal:
        return self.manufacturing + self.supplier_qc + self.logistics

    @property
    def hr_total(self) -> Decimal:
        return self.culture_benefits + self.training_development + self.cx_team

    @property
    def finance_admin_total(self) -> Decimal:
        return self.compliance_legal + self.financial_planning + self.audit_prep

    @property
    def crisis_total(self) -> Decimal:
        """Crisis response spend, in Rs lakhs -- zero in every non-crisis quarter."""
        return (
            self.price_match_fund
            + self.comparison_ads
            + self.retention_offers
            + self.emergency_supply_fund
            + self.crisis_choice_d_spend
        )

    @property
    def total_discretionary(self) -> Decimal:
        """Total discretionary spend for the quarter, in Rs lakhs.

        Crisis response is real cash spend added on top of the 6 departments' own totals -- every
        Q3 worked P&L in `docs/14-quarter-3-reference.md` adds it straight into Discretionary
        Spend (e.g. "Rs 58,85,980 + Rs 10,00,000 crisis").
        """
        return (
            self.marketing_total
            + self.sales_total
            + self.rnd_total
            + self.operations_total
            + self.hr_total
            + self.finance_admin_total
            + self.crisis_total
        )


@dataclass(frozen=True)
class CompanyState:
    """Opening state for one quarter. `compute_quarter` returns the closing equivalent.

    Cumulative scores (brand, SEO asset, buzz, quality, innovation) carry forward and are what
    make Q2 onward compound. `quarter_number` gates the brand multiplier, which applies from Q2.
    """

    quarter_number: int

    cash_inr: Decimal
    fixed_costs_inr: Decimal

    inventory_units: Decimal
    customers: Decimal
    prior_units_sold: Decimal

    supplier_reliability: Decimal
    logistics_efficiency: Decimal
    employee_satisfaction: Decimal
    employee_engagement: Decimal
    compliance_score: Decimal
    forecast_accuracy: Decimal
    audit_readiness: Decimal

    brand_score: Decimal
    seo_asset: Decimal
    buzz_score: Decimal
    quality_score: Decimal
    innovation_score: Decimal
    feature_completeness: Decimal

    repeat_purchase_rate_pct: Decimal = ZERO
    attrition_rate_pct: Decimal = ZERO

    # Quarters elapsed since the Pre-Launch Buzz investment: 1 pays leads, 2 pays leads plus a
    # one-time conversion bonus. 0 means nothing is pending.
    buzz_quarters_since_investment: int = 0

    # Total Assets is derived each quarter from `closing cash + carried inventory value +
    # equipment NBV + product IP + accounts receivable` (see `_total_assets_inr` in
    # `engines/quarter.py`), not stored directly. Equipment NBV depreciates quarter to quarter;
    # product IP, accounts receivable and liabilities have no stated formula and carry flat.
    # `None` skips the asset-based valuation method rather than guessing a company's balance sheet.
    equipment_nbv_inr: Decimal | None = None
    product_ip_inr: Decimal | None = None
    accounts_receivable_inr: Decimal | None = None
    liabilities_inr: Decimal | None = None

    @classmethod
    def opening(cls, seed: CompanySeed) -> "CompanyState":
        """Quarter 1 state for a seeded company.

        `prior_units_sold` is zero because Q1 has no prior quarter, which also makes the repeat
        purchase rate immaterial -- free repeat units are `prior rate x prior units sold`, so the
        term is provably zero however the rate is set. That is why a seed with a null opening
        repeat rate (Nadi Wear) can still open Q1.
        """
        scores = seed.opening_scores
        required = {
            field: require(getattr(scores, field), f"opening_scores.{field}", seed.name)
            for field in REQUIRED_OPENING_SCORES
        }
        return cls(
            quarter_number=1,
            cash_inr=seed.opening_cash_inr,
            fixed_costs_inr=seed.fixed_costs_inr,
            inventory_units=Decimal(seed.opening_inventory_units),
            customers=Decimal(seed.opening_customers),
            prior_units_sold=ZERO,
            # Immaterial in Q1 and only in Q1: repeat units are `prior rate x prior units sold`
            # and attrition erodes capacity built in a prior quarter. Both terms are provably
            # zero here, so an unstated seed value cannot change a Q1 result.
            repeat_purchase_rate_pct=scores.repeat_purchase_rate_pct or ZERO,
            attrition_rate_pct=scores.attrition_rate_pct or ZERO,
            equipment_nbv_inr=seed.equipment_nbv_inr,
            product_ip_inr=seed.product_ip_inr,
            accounts_receivable_inr=seed.accounts_receivable_inr,
            liabilities_inr=seed.liabilities_inr,
            **required,
        )

    def advance(self, **changes: object) -> "CompanyState":
        """Next quarter's opening state, incrementing the quarter number."""
        return replace(self, quarter_number=self.quarter_number + 1, **changes)  # type: ignore[arg-type]

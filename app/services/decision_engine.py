"""Business Impact pipeline: turns a submitted Decision into KPI/cash impact.

Two mechanisms are implemented here, matching what the source docs actually specify:

1. The generic "base impact x modifiers" pattern -- currently only Marketing's rule config
   uses this positional base-impact-table shape:

       Actual Impact % = Base Impact % x Brand Strength x Market Saturation
                          x Inventory Availability x Competitor Activity

   Verified against the worked example in marketing_rules.json (Increase Google Ads Budget,
   Sales field): 15 x 0.9 x 0.6 x 1.0 x 0.8 == 6.48.

2. Per-decision formula handlers for Finance/Product/Sales, dispatched by decision_key via
   WORKSPACE_HANDLERS. Each handler pulls its inputs from `payload` and/or a plain `state`
   dict (the caller's job to load and flatten the relevant *State row -- this module stays
   DB-session-agnostic) and calls the matching function in app.services.formulas.<workspace>.

   Coverage is intentionally narrow: FIN-001 to FIN-013 and PRO-001 to PRO-012 mostly do NOT
   have a decision-specific formula in the source docs (their "formula" fields are either
   validation constraints, vague labels, boolean gates, or simply absent -- see GAP_REASONS,
   one specific reason per uncovered decision_key rather than a blanket message). Sales and CX
   have almost no per-decision formulas at all -- SAL-011 is the one exception, handled by its
   own negotiation_score/acceptance_probability engine rather than forced through the generic
   formula shape.

TODO(source-doc-gap): the docs specify Marketing's Actual Impact as a *percentage* (e.g.
"Sales: 6.48%") but never state what absolute baseline that percentage is applied against.
Converting `actual_value` into an absolute delta on FinanceState/MarketingState/etc. is
deferred until that's confirmed with the product owner -- this module stops at computing the
value itself; nothing here writes to a *State table.
"""

from dataclasses import dataclass
from typing import Any

from app.config.rules import load_rules
from app.engines import gaps
from app.services.formulas import finance as finance_formulas
from app.services.formulas import product as product_formulas


@dataclass(frozen=True)
class FieldImpact:
    """A single computed business-impact value.

    For Marketing, base_value/actual_value are the pre/post-modifier-chain percentages.
    For every other workspace there's no modifier chain (none is specified in the source
    docs for Finance/Product/Sales), so base_value == actual_value -- that equality is
    honest (no modifier was applied), not a placeholder.
    """

    field: str
    base_value: float
    actual_value: float


def apply_modifier_chain(base_value: float, modifiers: dict[str, float]) -> float:
    """Actual value = base value x each modifier value, multiplied in turn."""
    actual = base_value
    for value in modifiers.values():
        actual *= value
    return actual


def _compute_marketing_table_impact(decision_key: str, modifiers: dict[str, float]) -> list[FieldImpact]:
    rules = load_rules("marketing")
    decision = rules["decisions"].get(decision_key)
    if decision is None or "base_impact" not in decision:
        raise KeyError(f"No base_impact table for decision '{decision_key}' in workspace 'marketing'")

    fields = rules["impact_fields"]
    base_impacts = decision["base_impact"]

    return [
        FieldImpact(field=field, base_value=base, actual_value=apply_modifier_chain(base, modifiers))
        for field, base in zip(fields, base_impacts, strict=True)
    ]


def _require_payload_fields(payload: dict[str, Any], fields: list[str], decision_key: str) -> dict[str, Any]:
    missing = [f for f in fields if f not in payload]
    if missing:
        raise ValueError(f"{decision_key} payload missing required field(s): {', '.join(missing)}")
    return {f: payload[f] for f in fields}


def _require_state_field(state: dict[str, Any] | None, field: str, decision_key: str) -> Any:
    if state is None:
        raise ValueError(
            f"{decision_key} requires a state snapshot for this quarter (need '{field}') -- none exists yet"
        )
    if field not in state:
        raise ValueError(f"{decision_key} requires '{field}' on the state snapshot, but it's missing")
    return state[field]


# --- Finance handlers --------------------------------------------------------------------


def handle_fin_002_emergency_cash_reserve(payload: dict[str, Any], state: dict[str, Any] | None) -> list[FieldImpact]:
    fields = _require_payload_fields(payload, ["reserve_cash"], "FIN-002")
    cash = _require_state_field(state, "cash_balance", "FIN-002")
    value = finance_formulas.reserve_ratio(float(fields["reserve_cash"]), float(cash))
    return [FieldImpact(field="reserve_ratio", base_value=value, actual_value=value)]


def handle_fin_003_capital_expenditure(payload: dict[str, Any], state: dict[str, Any] | None) -> list[FieldImpact]:
    fields = _require_payload_fields(payload, ["capex_amount"], "FIN-003")
    cash = _require_state_field(state, "cash_balance", "FIN-003")
    value = finance_formulas.remaining_cash_after_capex(float(cash), float(fields["capex_amount"]))
    return [FieldImpact(field="remaining_cash", base_value=value, actual_value=value)]


VALID_FIN_005_LOAN_AMOUNTS = {0, 1_000_000, 2_500_000, 5_000_000}  # FIN-005's dropdown options


def handle_fin_005_debt_utilisation(payload: dict[str, Any], state: dict[str, Any] | None) -> list[FieldImpact]:
    fields = _require_payload_fields(payload, ["loan"], "FIN-005")
    loan = fields["loan"]
    if loan not in VALID_FIN_005_LOAN_AMOUNTS:
        raise ValueError(f"FIN-005 'loan' must be one of {sorted(VALID_FIN_005_LOAN_AMOUNTS)}, got {loan!r}")
    cash = _require_state_field(state, "cash_balance", "FIN-005")
    value = finance_formulas.cash_after_debt_utilisation(float(cash), float(loan))
    return [FieldImpact(field="cash_after_debt", base_value=value, actual_value=value)]


def handle_fin_006_hiring_budget_approval(payload: dict[str, Any], state: dict[str, Any] | None) -> list[FieldImpact]:
    fields = _require_payload_fields(payload, ["payroll", "new_salaries"], "FIN-006")
    value = finance_formulas.total_hiring_budget(float(fields["payroll"]), float(fields["new_salaries"]))
    return [FieldImpact(field="total_hiring_budget", base_value=value, actual_value=value)]


FINANCE_HANDLERS = {
    "FIN-002": handle_fin_002_emergency_cash_reserve,
    "FIN-003": handle_fin_003_capital_expenditure,
    "FIN-005": handle_fin_005_debt_utilisation,
    "FIN-006": handle_fin_006_hiring_budget_approval,
}


# --- Product handlers ---------------------------------------------------------------------


def handle_pro_003_prioritize_features(payload: dict[str, Any], state: dict[str, Any] | None) -> list[FieldImpact]:
    fields = _require_payload_fields(payload, ["completed_features", "planned_features"], "PRO-003")
    value = product_formulas.feature_completion(
        float(fields["completed_features"]), float(fields["planned_features"])
    )
    return [FieldImpact(field="feature_completion_pct", base_value=value, actual_value=value)]


PRODUCT_HANDLERS = {
    "PRO-003": handle_pro_003_prioritize_features,
}


# --- Sales handlers ------------------------------------------------------------------------
#
# SAL-011 (negotiation_score + acceptance_probability) used to be wired here against the
# unbounded formulas in app.services.formulas.sales -- six differently-scaled quantities
# summed with no weights, then multiplied by two further unscaled factors, which cannot
# produce a real score or a 0-1 probability no matter what's fed in. Clamping the output
# would have been inventing bounds the source never specifies, so it raises instead (see the
# GAP_REASONS entry below, which reuses the exact reason engines/gaps.py already raises for
# the pure-engine equivalent of this same gap).

SALES_HANDLERS: dict[str, Any] = {}


WORKSPACE_HANDLERS: dict[str, dict[str, Any]] = {
    "finance": FINANCE_HANDLERS,
    "product": PRODUCT_HANDLERS,
    "sales": SALES_HANDLERS,
    "cx": {},  # no CX decision has a per-decision formula in the source doc -- see GAP_REASONS
}


# One specific reason per uncovered decision_key -- catalogued during the audit that found
# these gaps, not a blanket "not implemented" message.
GAP_REASONS: dict[tuple[str, str], str] = {
    ("finance", "FIN-001"): (
        "department_budget_allocation's formula ('budget <= available_cash') is a validation "
        "constraint, not a value-producing formula -- what business impact to report isn't "
        "specified in the source doc."
    ),
    ("finance", "FIN-004"): (
        "cost_optimisation's formula ('expenses * reduction_pct') requires a reduction_pct "
        "value per option (none/mild/moderate/aggressive) that the source doc never specifies "
        "numerically."
    ),
    ("finance", "FIN-007"): (
        "growth_investment_allocation's formula ('investment_distribution') isn't a concrete "
        "expression in the source doc."
    ),
    ("finance", "FIN-008"): "pricing_approval has no formula field in the source doc at all (only inferred scoring weights).",
    ("finance", "FIN-009"): "production_budget_approval has no formula field in the source doc at all (only inferred scoring weights).",
    ("finance", "FIN-010"): "inventory_investment has no formula field in the source doc at all (only inferred scoring weights).",
    ("finance", "FIN-011"): "founder_withdrawal_dividend has no formula field in the source doc at all (only inferred scoring weights).",
    ("finance", "FIN-012"): "vendor_payment_strategy has no formula field in the source doc at all (only inferred scoring weights).",
    ("finance", "FIN-013"): "quarter_financial_approval has no formula field in the source doc at all (only inferred scoring weights).",
    ("product", "PRO-001"): (
        "select_market_opportunity's formula ('opportunity_x_market_demand') isn't a concrete "
        "expression matching any core_formulas entry."
    ),
    ("product", "PRO-002"): (
        "create_new_product's formula ('creates_new_product') is a state-transition label, "
        "not a value-producing formula."
    ),
    ("product", "PRO-004"): (
        "rnd_investment's formula ('previous_innovation_score + rnd_investment') doesn't match "
        "core_formulas.innovation_score's actual terms (rnd_investment + new_features + "
        "technology_adoption) -- ambiguous which is correct, so neither is guessed."
    ),
    ("product", "PRO-005"): (
        "quality_strategy's formula ('base_quality + qa_investment') is a subset of "
        "core_formulas.product_quality's terms (which also has + rnd_bonus - technical_debt) "
        "-- unclear whether the missing terms should default to zero or this is a genuinely "
        "different formula, so neither is guessed."
    ),
    ("product", "PRO-006"): (
        "approve_prototype's formula ('development_status_eq_100') is a boolean gate check, "
        "not a value-producing formula."
    ),
    ("product", "PRO-007"): "beta_testing's formula ('feedback_collected') is not a value-producing formula.",
    ("product", "PRO-008"): (
        "launch_product's formula ('readiness_gte_threshold') is a threshold check against "
        "product_readiness, not itself a value-producing formula, and the threshold value "
        "isn't specified."
    ),
    ("product", "PRO-011"): "customer_feedback_prioritization's formula ('roadmap_priority_score') isn't defined anywhere in the source doc.",
    ("product", "PRO-012"): "retire_product's formula ('product_lifecycle') isn't defined anywhere in the source doc.",
    ("sales", "SAL-011"): gaps.NEGOTIATION_REASON,
}

_SALES_NO_FORMULA_DECISIONS = {
    "SAL-001": "sales_channel_prioritization",
    "SAL-002": "marketplace_strategy",
    "SAL-003": "enterprise_b2b_deals",
    "SAL-004": "pricing_execution",
    "SAL-005": "promotional_offers",
    "SAL-006": "customer_segment_strategy",
    "SAL-007": "distribution_expansion",
    "SAL-008": "sales_forecast",
    "SAL-009": "partnership_approval",
    "SAL-010": "customer_retention_strategy",
    "SAL-012": "quarter_sales_approval",
}
for _key, _name in _SALES_NO_FORMULA_DECISIONS.items():
    GAP_REASONS[("sales", _key)] = (
        f"{_name} ({_key}) has no per-decision formula field in sales_rules.json -- only "
        "general (non-decision-specific) sales metrics formulas and score_weight/affects tags."
    )

_CX_DECISIONS = {
    "CX-001": "customer_support_strategy",
    "CX-002": "complaint_resolution",
    "CX-003": "return_warranty_policy",
    "CX-004": "loyalty_program",
    "CX-005": "referral_program",
    "CX-006": "customer_feedback_prioritization",
    "CX-007": "community_strategy",
    "CX-008": "customer_education",
    "CX-009": "churn_prevention",
    "CX-010": "brand_crisis_response",
    "CX-011": "vip_customer_strategy",
    "CX-012": "quarter_cx_approval",
}
for _key, _name in _CX_DECISIONS.items():
    GAP_REASONS[("cx", _key)] = (
        f"{_name} ({_key}) has no per-decision formula field in cx_rules.json -- formulas "
        "exist workspace-wide (customer_satisfaction, churn_rate, etc.) but aren't wired to "
        "any specific decision_key in the source doc."
    )


def compute_decision_impact(
    workspace: str,
    decision_key: str,
    modifiers: dict[str, float],
    payload: dict[str, Any] | None = None,
    state: dict[str, Any] | None = None,
) -> list[FieldImpact]:
    """Compute the business impact of one decision.

    Marketing uses the base-impact-table + modifier-chain pattern. Every other workspace
    dispatches to a per-decision handler in WORKSPACE_HANDLERS, which reads what it needs
    from `payload` and/or `state` (a plain dict of the current *State row's scalar fields,
    or None if no snapshot exists yet -- loading and flattening it is the caller's job, to
    keep this module DB-session-agnostic).

    Raises KeyError for an unrecognized Marketing decision_key, NotImplementedError for any
    decision_key that isn't wired to a handler yet (with a specific reason from GAP_REASONS
    where one is catalogued), and ValueError for a wired handler missing a required
    payload/state input.
    """
    if workspace == "marketing":
        return _compute_marketing_table_impact(decision_key, modifiers)

    handlers = WORKSPACE_HANDLERS.get(workspace)
    if handlers is None:
        raise NotImplementedError(f"'{workspace}' has no wired decision handlers yet")

    handler = handlers.get(decision_key)
    if handler is not None:
        return handler(payload or {}, state)

    reason = GAP_REASONS.get((workspace, decision_key))
    if reason is not None:
        raise NotImplementedError(reason)

    raise NotImplementedError(
        f"No business-impact handler registered for {workspace}/{decision_key}, and it isn't in "
        "GAP_REASONS either -- this decision_key wasn't accounted for in the last audit."
    )

"""Business Impact pipeline: turns a submitted Decision into KPI/cash impact.

Two mechanisms are implemented here, matching what the source docs actually specify:

1. The generic "base impact x modifiers" pattern (currently only the Marketing workspace's
   rule config uses this positional base-impact-table shape):

       Actual Impact % = Base Impact % x Brand Strength x Market Saturation
                          x Inventory Availability x Competitor Activity

   Verified against the worked example in marketing_rules.json (Increase Google Ads Budget,
   Sales field): 15 x 0.9 x 0.6 x 1.0 x 0.8 == 6.48.

2. The concrete arithmetic formulas for Finance/Product/Sales/CX in app.services.formulas.*,
   which callers use directly with the inputs a decision/company-state provides.

TODO(source-doc-gap): the docs specify Actual Impact as a *percentage* (e.g. "Sales: 6.48%")
but never state what absolute baseline that percentage is applied against (current-quarter
value? prior-quarter? a fixed scale?). Converting `actual_impact_pct` into an absolute delta
on FinanceState/MarketingState/etc. is deferred until that's confirmed with the product
owner -- this module stops at the percentage-impact stage for the base-impact-table decisions.
"""

from dataclasses import dataclass

from app.config.rules import load_rules


@dataclass(frozen=True)
class FieldImpact:
    field: str
    base_impact_pct: float
    actual_impact_pct: float


def apply_modifier_chain(base_impact_pct: float, modifiers: dict[str, float]) -> float:
    """Actual Impact % = Base Impact % x each modifier value, multiplied in turn."""
    actual = base_impact_pct
    for value in modifiers.values():
        actual *= value
    return actual


def compute_decision_impact(workspace: str, decision_key: str, modifiers: dict[str, float]) -> list[FieldImpact]:
    """Look up a decision's base-impact row and run it through the modifier chain.

    Only implemented for workspaces whose rule config uses the positional
    `impact_fields` + `base_impact` array shape (currently: marketing). Other workspaces'
    rule configs express formulas as strings, not fixed base-impact tables -- use
    app.services.formulas.<workspace> for those instead.
    """
    rules = load_rules(workspace)
    if "impact_fields" not in rules:
        raise NotImplementedError(
            f"'{workspace}' rules do not use the positional base_impact table shape; "
            f"use app.services.formulas.{workspace} for this workspace's formulas instead."
        )

    decision = rules["decisions"].get(decision_key)
    if decision is None or "base_impact" not in decision:
        raise KeyError(f"No base_impact table for decision '{decision_key}' in workspace '{workspace}'")

    fields = rules["impact_fields"]
    base_impacts = decision["base_impact"]

    return [
        FieldImpact(
            field=field,
            base_impact_pct=base_pct,
            actual_impact_pct=apply_modifier_chain(base_pct, modifiers),
        )
        for field, base_pct in zip(fields, base_impacts, strict=True)
    ]

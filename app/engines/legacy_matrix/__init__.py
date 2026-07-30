"""The legacy percentage-influence matrix model.

`Actual Impact % = Base Impact % x Brand Strength x Market Saturation x Inventory Availability
x Competitor Activity` -- the model `docs/05-marketing-workspace.md` describes, and a genuinely
different shape from the power-law lead-generation model `app/engines/quarter.py` implements
(`Leads = 375 * x^0.68` etc.): one treats a decision as a discrete event with a percentage
effect, the other treats spend as a continuous input to a lead-count function. See the P0 "two
incompatible marketing models" entry in `docs/10-implementation-gaps.md`.

**Not wired into `compute_quarter`/`run_quarter()`.** Kept and tested -- including the
`15% x 0.9 x 0.6 x 1.0 x 0.8 = 6.48%` validation case from `marketing_rules.json` -- as a genuine
second model, in case the simulation designer picks it over the power-law model for Marketing.
`app/services/decision_engine.py`'s legacy per-decision Business Impact pipeline (itself not
wired into `run_quarter()` either) is this model's only caller today.
"""

from dataclasses import dataclass

from app.config.rules import load_rules


@dataclass(frozen=True)
class MatrixImpact:
    field: str
    base_value: float
    actual_value: float


def apply_modifier_chain(base_value: float, modifiers: dict[str, float]) -> float:
    """Actual value = base value x each modifier value, multiplied in turn."""
    actual = base_value
    for value in modifiers.values():
        actual *= value
    return actual


def compute_marketing_table_impact(decision_key: str, modifiers: dict[str, float]) -> list[MatrixImpact]:
    """The one workspace with a `base_impact` table per decision (`marketing_rules.json`'s 25
    Marketing decision keys) -- every other workspace has no modifier chain in the source docs.
    """
    rules = load_rules("marketing")
    decision = rules["decisions"].get(decision_key)
    if decision is None or "base_impact" not in decision:
        raise KeyError(f"No base_impact table for decision '{decision_key}' in workspace 'marketing'")

    fields = rules["impact_fields"]
    base_impacts = decision["base_impact"]

    return [
        MatrixImpact(field=field, base_value=base, actual_value=apply_modifier_chain(base, modifiers))
        for field, base in zip(fields, base_impacts, strict=True)
    ]

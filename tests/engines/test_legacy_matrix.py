"""The legacy percentage-influence matrix -- kept as a genuine second model, not wired into
compute_quarter()/run_quarter(). See app/engines/legacy_matrix/__init__.py's module docstring.
"""

import pytest

from app.engines.legacy_matrix import apply_modifier_chain, compute_marketing_table_impact

WORKED_EXAMPLE_MODIFIERS = {
    "brand_strength": 0.9,
    "market_saturation": 0.6,
    "inventory_availability": 1.0,
    "competitor_activity": 0.8,
}


def test_apply_modifier_chain_matches_worked_example():
    # marketing_rules.json worked example: Increase Google Ads Budget, Sales field.
    assert apply_modifier_chain(15, WORKED_EXAMPLE_MODIFIERS) == pytest.approx(6.48)


def test_apply_modifier_chain_no_modifiers_is_identity():
    assert apply_modifier_chain(20, {}) == 20


def test_compute_marketing_table_impact_sales_field():
    impacts = compute_marketing_table_impact("increase_google_ads_budget", WORKED_EXAMPLE_MODIFIERS)
    by_field = {i.field: i for i in impacts}

    assert by_field["sales"].base_value == 15
    assert by_field["sales"].actual_value == pytest.approx(6.48)
    assert by_field["marketing"].base_value == 20
    assert len(impacts) == 10  # one per impact_fields entry


def test_unknown_decision_raises_keyerror():
    with pytest.raises(KeyError):
        compute_marketing_table_impact("not_a_real_decision", WORKED_EXAMPLE_MODIFIERS)

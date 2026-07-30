import pytest

from app.services.decision_engine import (
    GAP_REASONS,
    apply_modifier_chain,
    compute_decision_impact,
)

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


def test_compute_decision_impact_marketing_sales_field():
    impacts = compute_decision_impact("marketing", "increase_google_ads_budget", WORKED_EXAMPLE_MODIFIERS)
    by_field = {i.field: i for i in impacts}

    assert by_field["sales"].base_value == 15
    assert by_field["sales"].actual_value == pytest.approx(6.48)
    assert by_field["marketing"].base_value == 20
    assert len(impacts) == 10  # one per impact_fields entry


def test_compute_decision_impact_unknown_marketing_decision_raises_keyerror():
    with pytest.raises(KeyError):
        compute_decision_impact("marketing", "not_a_real_decision", WORKED_EXAMPLE_MODIFIERS)


def test_compute_decision_impact_cataloged_gap_raises_not_implemented_with_specific_reason():
    with pytest.raises(NotImplementedError, match="validation constraint"):
        compute_decision_impact("finance", "FIN-001", {})


def test_gap_catalog_covers_every_unwired_decision_key():
    # Finance: 13 total, 4 wired (FIN-002/003/005/006) -> 9 gaps.
    assert sum(1 for (ws, _) in GAP_REASONS if ws == "finance") == 9
    # Product: 10 total, 1 wired (PRO-003) -> 9 gaps.
    assert sum(1 for (ws, _) in GAP_REASONS if ws == "product") == 9
    # Sales: 12 total, 0 wired (SAL-011's negotiation engine is unbounded, not implementable) -> 12 gaps.
    assert sum(1 for (ws, _) in GAP_REASONS if ws == "sales") == 12
    # CX: 12 total, 0 wired -> 12 gaps.
    assert sum(1 for (ws, _) in GAP_REASONS if ws == "cx") == 12


# --- FIN-002 Emergency Cash Reserve ---------------------------------------------------


def test_fin_002_reserve_ratio_value():
    impacts = compute_decision_impact(
        "finance", "FIN-002", {}, payload={"reserve_cash": 150000}, state={"cash_balance": 1000000}
    )
    assert len(impacts) == 1
    assert impacts[0].field == "reserve_ratio"
    assert impacts[0].base_value == pytest.approx(0.15)
    assert impacts[0].actual_value == pytest.approx(0.15)


def test_fin_002_missing_state_raises_value_error():
    with pytest.raises(ValueError, match="no.*exists yet|none exists yet"):
        compute_decision_impact("finance", "FIN-002", {}, payload={"reserve_cash": 150000}, state=None)


def test_fin_002_missing_payload_field_raises_value_error():
    with pytest.raises(ValueError, match="reserve_cash"):
        compute_decision_impact("finance", "FIN-002", {}, payload={}, state={"cash_balance": 1000000})


# --- FIN-003 Capital Expenditure -------------------------------------------------------


def test_fin_003_remaining_cash():
    impacts = compute_decision_impact(
        "finance", "FIN-003", {}, payload={"capex_amount": 30000}, state={"cash_balance": 100000}
    )
    assert impacts[0].field == "remaining_cash"
    assert impacts[0].actual_value == 70000


# --- FIN-005 Debt Utilisation -----------------------------------------------------------


def test_fin_005_valid_loan_amount():
    impacts = compute_decision_impact(
        "finance", "FIN-005", {}, payload={"loan": 1000000}, state={"cash_balance": 50000}
    )
    assert impacts[0].field == "cash_after_debt"
    assert impacts[0].actual_value == 1050000


def test_fin_005_invalid_loan_amount_raises_value_error():
    with pytest.raises(ValueError, match="loan"):
        compute_decision_impact("finance", "FIN-005", {}, payload={"loan": 999}, state={"cash_balance": 50000})


# --- FIN-006 Hiring Budget Approval ------------------------------------------------------


def test_fin_006_total_hiring_budget_no_state_needed():
    impacts = compute_decision_impact(
        "finance", "FIN-006", {}, payload={"payroll": 200000, "new_salaries": 50000}, state=None
    )
    assert impacts[0].field == "total_hiring_budget"
    assert impacts[0].actual_value == 250000


# --- PRO-003 Prioritize Features ---------------------------------------------------------


def test_pro_003_feature_completion():
    impacts = compute_decision_impact(
        "product", "PRO-003", {}, payload={"completed_features": 6, "planned_features": 10}, state=None
    )
    assert impacts[0].field == "feature_completion_pct"
    assert impacts[0].actual_value == 60.0


def test_pro_003_missing_payload_field_raises_value_error():
    with pytest.raises(ValueError, match="planned_features"):
        compute_decision_impact("product", "PRO-003", {}, payload={"completed_features": 6}, state=None)


# --- SAL-011 Negotiation stays gapped, like every other Sales decision ---------------------
#
# Negotiation Score sums six differently-scaled quantities with no stated weights, then
# Acceptance Probability multiplies that by two further unscaled factors -- it cannot produce
# a real score or a 0-1 probability for any input, so there is no bound that would make the
# computation meaningful. This used to be "wired" against exactly that unbounded arithmetic;
# raising is the honest behaviour, not a regression.


def test_sal_011_is_not_implemented_with_the_negotiation_engine_reason():
    with pytest.raises(NotImplementedError, match="Negotiation Score has no specified weights"):
        compute_decision_impact(
            "sales",
            "SAL-011",
            {},
            payload={"terms": {"price": 950}, "negotiation_inputs": {}},
            state=None,
        )


# --- Other Sales / CX decisions stay gapped -----------------------------------------------


def test_sal_001_not_implemented_with_specific_reason():
    with pytest.raises(NotImplementedError, match="sales_channel_prioritization"):
        compute_decision_impact("sales", "SAL-001", {}, payload={}, state=None)


def test_cx_001_not_implemented_with_specific_reason():
    with pytest.raises(NotImplementedError, match="customer_support_strategy"):
        compute_decision_impact("cx", "CX-001", {}, payload={}, state=None)

import pytest_asyncio

from app.models.finance import FinanceState

NEGOTIATION_INPUTS = {
    "price_competitiveness": 10,
    "relationship_score": 20,
    "inventory_availability": 15,
    "brand_strength": 25,
    "delivery_capability": 5,
    "risk": 8,
    "buyer_flexibility": 0.8,
    "market_demand": 0.9,
}


@pytest_asyncio.fixture
async def seeded_finance_state(db_session, company_and_quarter):
    """FIN-002/003/005 need a FinanceState row to read cash_balance from -- nothing in the
    app currently writes one (that's the flagged actual_impact_pct-to-absolute-delta gap),
    so tests seed it directly to exercise the otherwise-correct code path.
    """
    _, quarter = company_and_quarter
    state = FinanceState(
        quarter_id=quarter.id,
        cash_balance=1_000_000,
        revenue=0,
        expenses=0,
        burn_rate=0,
    )
    db_session.add(state)
    await db_session.flush()
    return state


async def test_fin_002_emergency_cash_reserve_happy_path(client, company_and_quarter, seeded_finance_state):
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/finance/decisions",
        json={"decision_key": "FIN-002", "payload": {"reserve_cash": 150000}},
    )
    assert response.status_code == 201
    body = response.json()
    impact = body["business_impact"][0]
    assert impact["field"] == "reserve_ratio"
    assert impact["actual_value"] == 0.15
    # no evidence extractor registered for FIN-002 -- business impact still succeeds (201),
    # evidence generation degrades non-fatally to zero rather than blocking the submission.
    assert body["evidence_generated"] == 0


async def test_fin_002_without_finance_state_422s(client, company_and_quarter):
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/finance/decisions",
        json={"decision_key": "FIN-002", "payload": {"reserve_cash": 150000}},
    )
    assert response.status_code == 422
    assert "exists yet" in response.json()["detail"]


async def test_fin_003_capital_expenditure_happy_path(client, company_and_quarter, seeded_finance_state):
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/finance/decisions",
        json={"decision_key": "FIN-003", "payload": {"capex_amount": 30000}},
    )
    assert response.status_code == 201
    impact = response.json()["business_impact"][0]
    assert impact["field"] == "remaining_cash"
    assert impact["actual_value"] == 970000


async def test_fin_005_debt_utilisation_happy_path(client, company_and_quarter, seeded_finance_state):
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/finance/decisions",
        json={"decision_key": "FIN-005", "payload": {"loan": 1000000}},
    )
    assert response.status_code == 201
    impact = response.json()["business_impact"][0]
    assert impact["field"] == "cash_after_debt"
    assert impact["actual_value"] == 2000000


async def test_fin_005_invalid_loan_amount_422s(client, company_and_quarter, seeded_finance_state):
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/finance/decisions",
        json={"decision_key": "FIN-005", "payload": {"loan": 42}},
    )
    assert response.status_code == 422


async def test_fin_006_hiring_budget_no_state_needed(client, company_and_quarter):
    """FIN-006 doesn't depend on FinanceState -- both inputs come from payload."""
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/finance/decisions",
        json={"decision_key": "FIN-006", "payload": {"payroll": 200000, "new_salaries": 50000}},
    )
    assert response.status_code == 201
    impact = response.json()["business_impact"][0]
    assert impact["field"] == "total_hiring_budget"
    assert impact["actual_value"] == 250000


async def test_pro_003_prioritize_features_happy_path(client, company_and_quarter):
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/product/decisions",
        json={"decision_key": "PRO-003", "payload": {"completed_features": 6, "planned_features": 10}},
    )
    assert response.status_code == 201
    impact = response.json()["business_impact"][0]
    assert impact["field"] == "feature_completion_pct"
    assert impact["actual_value"] == 60.0


async def test_pro_004_still_gapped(client, company_and_quarter):
    """PRO-004's formula doesn't match core_formulas.innovation_score's actual terms --
    stays a cataloged gap, not silently forced through the mismatched function.
    """
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/product/decisions",
        json={"decision_key": "PRO-004", "payload": {}},
    )
    assert response.status_code == 422


async def test_sal_011_still_gapped_unbounded_negotiation_engine(client, company_and_quarter):
    """Negotiation Score sums six differently-scaled quantities with no stated weights, then
    Acceptance Probability multiplies that by two further unscaled factors -- no bound would
    make the result meaningful, so this stays a cataloged gap rather than a computed value."""
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/sales/decisions",
        json={
            "decision_key": "SAL-011",
            "payload": {"terms": {"price": 950, "quantity": 100}, "negotiation_inputs": NEGOTIATION_INPUTS},
        },
    )
    assert response.status_code == 422


async def test_sal_011_invalid_term_key_422s_at_schema_layer(client, company_and_quarter):
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/sales/decisions",
        json={
            "decision_key": "SAL-011",
            "payload": {"terms": {"not_a_negotiable_term": 1}, "negotiation_inputs": NEGOTIATION_INPUTS},
        },
    )
    assert response.status_code == 422


async def test_sal_001_still_gapped_no_formula_field(client, company_and_quarter):
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/sales/decisions",
        json={"decision_key": "SAL-001", "payload": {}},
    )
    assert response.status_code == 422


async def test_cx_decision_still_gapped_no_formula_at_all(client, company_and_quarter):
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/cx/decisions",
        json={"decision_key": "CX-001", "payload": {}},
    )
    assert response.status_code == 422

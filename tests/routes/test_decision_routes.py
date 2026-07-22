async def test_marketing_happy_path_decision_submission(client, company_and_quarter):
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/marketing/decisions",
        json={"decision_key": "increase_google_ads_budget", "payload": {"amount": 5000}},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["decision_key"] == "increase_google_ads_budget"
    assert len(body["business_impact"]) == 10
    sales_impact = next(f for f in body["business_impact"] if f["field"] == "sales")
    assert sales_impact["base_impact_pct"] == 15
    # no evidence-extraction rule registered for this decision_key -- honest zero, not a 422
    assert body["evidence_generated"] == 0


async def test_decision_key_validation_rejects_unknown_key(client, company_and_quarter):
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/marketing/decisions",
        json={"decision_key": "not_a_real_decision", "payload": {}},
    )
    assert response.status_code == 422


async def test_finance_decision_422s_no_business_impact_formula(client, company_and_quarter):
    """Finance isn't a base-impact-table workspace (only Marketing is) -- decision_engine has
    nothing to compute yet, and that must surface as an explicit 422, not a silent zero.
    """
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/finance/decisions",
        json={"decision_key": "FIN-001", "payload": {}},
    )
    assert response.status_code == 422


async def test_marketing_evidence_only_decision_422s_no_base_impact_row(client, company_and_quarter):
    """marketing_budget_allocation has evidence rules but no base_impact row -- business
    impact is the hard requirement, so this must 422 even though evidence would succeed.
    """
    company, quarter = company_and_quarter
    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/marketing/decisions",
        json={
            "decision_key": "marketing_budget_allocation",
            "payload": {"total_budget": 100, "channel_spend": {"increase_seo_budget": 100}},
        },
    )
    assert response.status_code == 422


async def test_get_state_404s_before_any_state_snapshot_exists(client, company_and_quarter):
    company, quarter = company_and_quarter
    response = await client.get(f"/companies/{company.id}/quarters/{quarter.id}/marketing/state")
    assert response.status_code == 404


async def test_list_decisions_returns_submitted_decision(client, company_and_quarter):
    company, quarter = company_and_quarter
    await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/marketing/decisions",
        json={"decision_key": "increase_google_ads_budget", "payload": {}},
    )

    response = await client.get(f"/companies/{company.id}/quarters/{quarter.id}/marketing/decisions")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 1
    assert entries[0]["decision_key"] == "increase_google_ads_budget"


async def test_quarter_locked_blocks_further_decisions(client, company_and_quarter):
    company, quarter = company_and_quarter

    lock_response = await client.post(f"/companies/{company.id}/quarters/{quarter.id}/lock")
    assert lock_response.status_code == 200

    response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/marketing/decisions",
        json={"decision_key": "increase_google_ads_budget", "payload": {}},
    )
    assert response.status_code == 409


async def test_locking_an_already_locked_quarter_409s(client, company_and_quarter):
    company, quarter = company_and_quarter
    await client.post(f"/companies/{company.id}/quarters/{quarter.id}/lock")

    second_lock = await client.post(f"/companies/{company.id}/quarters/{quarter.id}/lock")
    assert second_lock.status_code == 409

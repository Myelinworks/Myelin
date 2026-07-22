async def test_full_submit_lock_report_leaderboard_flow(client, company_and_quarter):
    company, quarter = company_and_quarter

    submit_response = await client.post(
        f"/companies/{company.id}/quarters/{quarter.id}/marketing/decisions",
        json={"decision_key": "increase_google_ads_budget", "payload": {"amount": 5000}},
    )
    assert submit_response.status_code == 201

    lock_response = await client.post(f"/companies/{company.id}/quarters/{quarter.id}/lock")
    assert lock_response.status_code == 200
    lock_body = lock_response.json()
    assert lock_body["decisions_submitted"] == 1
    # no evidence rule registered for increase_google_ads_budget, so evidence-derived
    # dimensions sit at their Hidden Engine State baseline -- not fabricated numbers.
    assert lock_body["evidence_records_generated"] == 0
    assert lock_body["dimension_scores"]["investor_confidence"] == 60.0
    assert lock_body["dimension_scores"]["employee_burnout"] == 10.0
    assert lock_body["dimension_scores"]["strategic_thinking"] == 50.0

    report_response = await client.get(f"/companies/{company.id}/quarters/{quarter.id}/report")
    assert report_response.status_code == 200
    report_body = report_response.json()
    assert report_body["decisions_submitted"] == 1
    assert report_body["overall_score"] == lock_body["overall_score"]

    leaderboard_response = await client.get(f"/companies/{company.id}/leaderboard")
    assert leaderboard_response.status_code == 200
    entries = leaderboard_response.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["quarter_number"] == 1


async def test_report_404s_before_quarter_is_locked(client, company_and_quarter):
    company, quarter = company_and_quarter
    response = await client.get(f"/companies/{company.id}/quarters/{quarter.id}/report")
    assert response.status_code == 404

from decimal import Decimal


async def test_full_allocate_lock_report_leaderboard_flow(client, company_and_quarter):
    """POST /lock now runs the pure 22-line engine (compute_quarter via run_quarter), not the
    legacy Decision/Evidence/Cognitive-Score pipeline -- that pipeline is still implemented and
    tested (tests/services/test_quarter_engine.py), just no longer what this endpoint calls.
    """
    company, quarter = company_and_quarter
    base = f"/companies/{company.id}/quarters/{quarter.id}"

    marketing = await client.post(f"{base}/allocations/marketing", json={"google_ads": "4.00"})
    assert marketing.status_code == 200
    sales = await client.post(f"{base}/allocations/sales", json={"reps": "5.45"})
    assert sales.status_code == 200

    decision_submit = await client.post(
        f"{base}/marketing/decisions",
        json={"decision_key": "increase_google_ads_budget", "payload": {"amount": 5000}},
    )
    assert decision_submit.status_code == 201

    lock_response = await client.post(f"{base}/lock")
    assert lock_response.status_code == 200
    lock_body = lock_response.json()
    # the legacy Decision above is still counted (a read-only tally, no pipeline invoked for it)
    assert lock_body["decisions_submitted"] == 1
    assert lock_body["units_sold"] is not None
    assert Decimal(lock_body["units_sold"]) > 0
    assert lock_body["result_hash"] is not None
    # /lock no longer runs the cognitive-scoring pipeline, so this stays unpopulated
    assert lock_body["overall_score"] is None

    report_response = await client.get(f"{base}/report")
    assert report_response.status_code == 200
    report_body = report_response.json()
    assert report_body["decisions_submitted"] == 1
    assert report_body["units_sold"] == lock_body["units_sold"]
    assert report_body["result_hash"] == lock_body["result_hash"]

    leaderboard_response = await client.get(f"/companies/{company.id}/leaderboard")
    assert leaderboard_response.status_code == 200
    entries = leaderboard_response.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["quarter_number"] == 1
    assert entries[0]["overall_score"] is None


async def test_report_404s_before_quarter_is_locked(client, company_and_quarter):
    company, quarter = company_and_quarter
    response = await client.get(f"/companies/{company.id}/quarters/{quarter.id}/report")
    assert response.status_code == 404

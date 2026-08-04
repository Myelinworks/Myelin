from decimal import Decimal


async def test_full_allocate_lock_report_leaderboard_flow(client, company_and_quarter):
    """POST /lock now runs the pure 22-line engine (compute_quarter via run_quarter), not the
    legacy Decision/Evidence/Cognitive-Score pipeline -- that pipeline is still implemented and
    tested (tests/services/test_quarter_engine.py), just no longer what this endpoint calls.

    Phase 9: both /lock and /report now return the full student-facing report (`engines/report.py`,
    `schemas/quarter.py::QuarterReportResponse`), not the old 5-number stub -- `decisions_submitted`/
    `result_hash`/`overall_score` are gone from this response on purpose; they were internal/legacy
    audit fields, not part of the report's five sections.
    """
    company, quarter = company_and_quarter
    base = f"/companies/{company.id}/quarters/{quarter.id}"

    marketing = await client.post(f"{base}/allocations/marketing", json={"google_ads": "4.00"})
    assert marketing.status_code == 200
    sales = await client.post(f"{base}/allocations/sales", json={"reps": "5.45"})
    assert sales.status_code == 200

    # The legacy Decision pipeline still works alongside the 22-line one -- unaffected by /lock.
    decision_submit = await client.post(
        f"{base}/marketing/decisions",
        json={"decision_key": "increase_google_ads_budget", "payload": {"amount": 5000}},
    )
    assert decision_submit.status_code == 201

    lock_response = await client.post(f"{base}/lock")
    assert lock_response.status_code == 200
    lock_body = lock_response.json()
    assert Decimal(lock_body["outcome"]["units_sold"]["value"]) > 0
    assert lock_body["outcome"]["units_sold"]["delta"] is None  # Q1: no prior quarter
    assert lock_body["decision_quality"]["ceo_score"] is not None
    assert lock_body["run_status"] == "active"

    report_response = await client.get(f"{base}/report")
    assert report_response.status_code == 200
    report_body = report_response.json()
    assert report_body["outcome"]["units_sold"]["value"] == lock_body["outcome"]["units_sold"]["value"]
    assert report_body["decision_quality"]["ceo_score"] == lock_body["decision_quality"]["ceo_score"]

    leaderboard_response = await client.get(f"/companies/{company.id}/leaderboard")
    assert leaderboard_response.status_code == 200
    entries = leaderboard_response.json()["entries"]
    assert len(entries) == 1
    assert entries[0]["quarter_number"] == 1
    # The leaderboard still reads the legacy overall_score column -- untouched by Phase 9.
    assert entries[0]["overall_score"] is None


async def test_report_409s_before_quarter_is_locked(client, company_and_quarter):
    """Not-ready returns a status conflict, never a partial report -- matches
    routes/deps.py::get_open_quarter's existing 409 convention for "wrong quarter-lock state"."""
    company, quarter = company_and_quarter
    response = await client.get(f"/companies/{company.id}/quarters/{quarter.id}/report")
    assert response.status_code == 409

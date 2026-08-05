"""Phase 12 acceptance: the full run/session lifecycle over HTTP, no ORM seeding anywhere.

Every quarter, allocation, lock and read below goes through the public API exactly the way a
frontend would reach it -- same discipline as `test_company_routes.py::TestFullSimulationOverHttp`
and `test_endgame_routes.py`, just carried all the way from "no company yet" to a terminal run.
"""

from tests.routes.test_company_routes import (
    Q1_BY_DEPARTMENT,
    _create_company,
    _lock,
    _open_quarter,
    _submit_all_departments,
)


async def _play_through_q3(client) -> str:
    """Q1 -> Q2 -> Q3 (crisis choice C, universally valid), returning the company id with Q4 not
    yet open. Reuses the exact same helper `test_endgame_routes.py`'s own `_play_through_q3` does
    -- kept as a local copy rather than a cross-file import, matching this codebase's existing
    per-test-file constant/helper convention (e.g. `Q1_BY_DEPARTMENT` itself)."""
    company = await _create_company(client)
    company_id = company["id"]

    q1 = await _open_quarter(client, company_id)
    await _submit_all_departments(client, company_id, q1["id"], Q1_BY_DEPARTMENT)
    await _lock(client, company_id, q1["id"])

    q2 = await _open_quarter(client, company_id)
    await _submit_all_departments(client, company_id, q2["id"], Q1_BY_DEPARTMENT)
    await _lock(client, company_id, q2["id"])

    q3 = await _open_quarter(client, company_id)
    await _submit_all_departments(client, company_id, q3["id"], Q1_BY_DEPARTMENT)
    crisis_response = await client.post(
        f"/companies/{company_id}/quarters/{q3['id']}/allocations/crisis",
        json={"crisis_choice": "C", "comparison_ads": "5.0", "emergency_supply_fund": "1.0"},
    )
    assert crisis_response.status_code == 200, crisis_response.text
    await _lock(client, company_id, q3["id"])

    return company_id


class TestFullRunToCompletion:
    async def test_start_to_finish_reaches_completed_with_a_full_score_trajectory(self, client):
        company_id = await _play_through_q3(client)

        # ---- Q4: endgame decision, lock, final report ----
        q4 = await _open_quarter(client, company_id)

        run_state_at_q4 = (await client.get(f"/companies/{company_id}/run")).json()
        assert run_state_at_q4["current_quarter_number"] == 4
        assert "submit_endgame_decision" in run_state_at_q4["legal_moves"]
        assert run_state_at_q4["endgame_preview"] is not None
        term_sheet_menu = run_state_at_q4["endgame_preview"]["term_sheet_menu"]

        # Path C (deliberate independence) is offered at every tier -- the one choice that never
        # depends on which tier this randomly-assigned company/scenario landed in.
        submit = await client.post(
            f"/companies/{company_id}/quarters/{q4['id']}/endgame",
            json={
                "path": "C",
                "term_sheet_name": term_sheet_menu["path_c_name"],
                "reasoning": "staying independent based on the Q1-Q3 trend",
            },
        )
        assert submit.status_code == 200, submit.text

        await _submit_all_departments(client, company_id, q4["id"], Q1_BY_DEPARTMENT)
        q4_report = await _lock(client, company_id, q4["id"])

        assert q4_report["run_status"] == "completed"
        assert q4_report["run_summary"] is not None
        assert len(q4_report["run_summary"]["score_trajectory"]) == 4
        assert [p["quarter_number"] for p in q4_report["run_summary"]["score_trajectory"]] == [1, 2, 3, 4]

        final_state = (await client.get(f"/companies/{company_id}/run")).json()
        assert final_state["run_status"] == "completed"
        assert len(final_state["score_trajectory"]) == 4
        # Terminal: only reads remain legal.
        assert final_state["legal_moves"] == ["read_endgame_preview", "read_quarter_report"]


class TestFailedRun:
    async def test_cash_exhaustion_terminates_the_run_and_blocks_further_moves(self, client):
        company = await _create_company(client)
        company_id = company["id"]

        q1 = await _open_quarter(client, company_id)
        # Rs 5,00,00,000 on one channel against Rs 1,50,00,000 of opening cash -- guaranteed to
        # exhaust cash in a single quarter regardless of which scenario this company landed on.
        overspend = await client.post(
            f"/companies/{company_id}/quarters/{q1['id']}/allocations/marketing",
            json={"google_ads": "500"},
        )
        assert overspend.status_code == 200, overspend.text

        q1_report = await _lock(client, company_id, q1["id"])
        assert q1_report["run_status"] == "failed"
        assert q1_report["survival_triggered_by"] == "cash_exhausted"
        assert q1_report["survival_detail"] is not None

        run_state = (await client.get(f"/companies/{company_id}/run")).json()
        assert run_state["run_status"] == "failed"
        assert run_state["legal_moves"] == ["read_quarter_report"]

        # Every subsequent write is illegal, and every refusal takes the same shape.
        open_next = await client.post(f"/companies/{company_id}/quarters")
        assert open_next.status_code == 409
        open_next_body = open_next.json()
        assert open_next_body["error"] == "illegal_move"
        assert open_next_body["attempted_move"] == "open_next_quarter"
        assert "failed" in open_next_body["reason"]
        assert open_next_body["allowed_moves"] == ["read_quarter_report"]

        submit_more = await client.post(
            f"/companies/{company_id}/quarters/{q1['id']}/allocations/marketing",
            json={"google_ads": "1.0"},
        )
        assert submit_more.status_code == 409
        submit_more_body = submit_more.json()
        assert submit_more_body["error"] == "illegal_move"
        assert submit_more_body["attempted_move"] == "submit_allocation"

        relock = await client.post(f"/companies/{company_id}/quarters/{q1['id']}/lock")
        # Locking is exempt from the gatekeeper (idempotency guarantee) -- an already-locked
        # quarter returns its persisted result unchanged, not a refusal.
        assert relock.status_code == 200
        assert relock.json()["run_status"] == "failed"


class TestOrderingEnforcement:
    """The three acceptance-named cases, each returning the machine-readable refusal from the
    single gatekeeper -- not three differently-shaped errors."""

    async def test_opening_q3_before_q2_is_locked_is_refused(self, client):
        company = await _create_company(client)
        company_id = company["id"]
        await _open_quarter(client, company_id)  # Q1
        q1 = (await client.get(f"/companies/{company_id}/run")).json()
        await _submit_all_departments(client, company_id, q1["current_quarter_id"], Q1_BY_DEPARTMENT)
        await _lock(client, company_id, q1["current_quarter_id"])

        await _open_quarter(client, company_id)  # Q2, left open (not locked)

        response = await client.post(f"/companies/{company_id}/quarters")  # attempting Q3
        assert response.status_code == 409
        body = response.json()
        assert body["error"] == "illegal_move"
        assert body["attempted_move"] == "open_next_quarter"
        assert "lock it before opening the next one" in body["reason"]

    async def test_exceeding_four_quarters_is_refused(self, client):
        company = await _create_company(client)
        company_id = company["id"]
        for _ in range(4):
            quarter = await _open_quarter(client, company_id)
            await _submit_all_departments(client, company_id, quarter["id"], Q1_BY_DEPARTMENT)
            await _lock(client, company_id, quarter["id"])

        response = await client.post(f"/companies/{company_id}/quarters")
        assert response.status_code == 409
        body = response.json()
        assert body["error"] == "illegal_move"
        assert body["attempted_move"] == "open_next_quarter"

    async def test_submitting_a_q4_endgame_decision_at_q2_is_refused(self, client):
        company = await _create_company(client)
        company_id = company["id"]
        q1 = await _open_quarter(client, company_id)
        await _submit_all_departments(client, company_id, q1["id"], Q1_BY_DEPARTMENT)
        await _lock(client, company_id, q1["id"])

        q2 = await _open_quarter(client, company_id)

        response = await client.post(
            f"/companies/{company_id}/quarters/{q2['id']}/endgame",
            json={"path": "C", "term_sheet_name": "whatever"},
        )
        assert response.status_code == 409
        body = response.json()
        assert body["error"] == "illegal_move"
        assert body["attempted_move"] == "submit_endgame_decision"
        assert "quarter 4" in body["reason"]


class TestStateReadsArePure:
    async def test_rereading_run_state_is_byte_identical(self, client):
        company = await _create_company(client)
        company_id = company["id"]
        q1 = await _open_quarter(client, company_id)
        await _submit_all_departments(client, company_id, q1["id"], Q1_BY_DEPARTMENT)
        await _lock(client, company_id, q1["id"])

        first = await client.get(f"/companies/{company_id}/run")
        second = await client.get(f"/companies/{company_id}/run")
        assert first.json() == second.json()

    async def test_rereading_a_quarter_report_is_byte_identical(self, client):
        company = await _create_company(client)
        company_id = company["id"]
        q1 = await _open_quarter(client, company_id)
        await _submit_all_departments(client, company_id, q1["id"], Q1_BY_DEPARTMENT)
        await _lock(client, company_id, q1["id"])

        first = await client.get(f"/companies/{company_id}/quarters/{q1['id']}/report")
        second = await client.get(f"/companies/{company_id}/quarters/{q1['id']}/report")
        assert first.json() == second.json()

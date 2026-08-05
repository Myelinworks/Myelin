"""HTTP surface for the Q4 endgame (Phase 11) -- GET/POST `.../endgame`.

No ORM seeding: every row here is created through the public API, same discipline as
`test_company_routes.py::TestFullSimulationOverHttp` -- a real proof the deployed API can reach
Q4, not just that the pure engine/service layer can.
"""

from decimal import Decimal

from tests.routes.test_company_routes import (
    Q1_BY_DEPARTMENT,
    _create_company,
    _lock,
    _open_quarter,
    _submit_all_departments,
)


async def _play_through_q3(client) -> str:
    """Q1 -> Q2 -> Q3 (crisis choice C, universally valid for whichever scenario this company's id
    deterministically assigns), all through HTTP, returning the company id with Q4 not yet open."""
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


class TestEndgamePreview:
    async def test_get_endgame_404s_for_a_quarter_that_is_not_q4(self, client):
        company = await _create_company(client)
        q1 = await _open_quarter(client, company["id"])

        response = await client.get(f"/companies/{company['id']}/quarters/{q1['id']}/endgame")
        assert response.status_code == 404

    async def test_get_endgame_preview_after_q3_locks(self, client):
        company_id = await _play_through_q3(client)
        q4 = await _open_quarter(client, company_id)

        response = await client.get(f"/companies/{company_id}/quarters/{q4['id']}/endgame")
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["tier"] in ("thriving", "stable", "distressed")
        assert set(body["term_sheet_menu"].keys()) == {"path_a_name", "path_b_name", "path_c_name"}
        assert Decimal(body["covenant_units"]) > 0
        assert Decimal(body["true_continuation_value_inr"]) > 0
        # acquisition_trap_offer_inr is present only for the Thriving tier -- both are valid here.
        if body["tier"] != "thriving":
            assert body["acquisition_trap_offer_inr"] is None


class TestEndgameDecisionSubmission:
    async def test_post_then_get_reflects_the_submitted_decision(self, client):
        company_id = await _play_through_q3(client)
        q4 = await _open_quarter(client, company_id)
        preview = (await client.get(f"/companies/{company_id}/quarters/{q4['id']}/endgame")).json()

        submit = await client.post(
            f"/companies/{company_id}/quarters/{q4['id']}/endgame",
            json={
                "path": "A",
                "term_sheet_name": preview["term_sheet_menu"]["path_a_name"],
                "reasoning": "Q1-Q3 growth supports a debt-funded push.",
            },
        )
        assert submit.status_code == 200, submit.text
        body = submit.json()
        assert body["path"] == "A"
        assert body["term_sheet_name"] == preview["term_sheet_menu"]["path_a_name"]
        assert body["reasoning"] == "Q1-Q3 growth supports a debt-funded push."
        assert body["quarter_id"] == q4["id"]

    async def test_resubmitting_overwrites_not_duplicates(self, client):
        company_id = await _play_through_q3(client)
        q4 = await _open_quarter(client, company_id)
        preview = (await client.get(f"/companies/{company_id}/quarters/{q4['id']}/endgame")).json()

        await client.post(
            f"/companies/{company_id}/quarters/{q4['id']}/endgame",
            json={"path": "A", "term_sheet_name": preview["term_sheet_menu"]["path_a_name"]},
        )
        second = await client.post(
            f"/companies/{company_id}/quarters/{q4['id']}/endgame",
            json={"path": "C", "term_sheet_name": preview["term_sheet_menu"]["path_c_name"]},
        )
        assert second.status_code == 200, second.text
        assert second.json()["path"] == "C"

    async def test_an_invalid_path_letter_is_rejected(self, client):
        company_id = await _play_through_q3(client)
        q4 = await _open_quarter(client, company_id)

        response = await client.post(
            f"/companies/{company_id}/quarters/{q4['id']}/endgame",
            json={"path": "Z", "term_sheet_name": "whatever"},
        )
        assert response.status_code == 422

    async def test_submission_is_rejected_once_q4_is_locked(self, client):
        company_id = await _play_through_q3(client)
        q4 = await _open_quarter(client, company_id)
        await _submit_all_departments(client, company_id, q4["id"], Q1_BY_DEPARTMENT)
        await _lock(client, company_id, q4["id"])

        response = await client.post(
            f"/companies/{company_id}/quarters/{q4['id']}/endgame",
            json={"path": "C", "term_sheet_name": "Independent"},
        )
        assert response.status_code == 409


class TestEndgameAppliedAtLock:
    async def test_locking_q4_with_a_decision_applies_the_q4_modifier_set(self, client):
        company_id = await _play_through_q3(client)
        q4 = await _open_quarter(client, company_id)
        preview = (await client.get(f"/companies/{company_id}/quarters/{q4['id']}/endgame")).json()

        await client.post(
            f"/companies/{company_id}/quarters/{q4['id']}/endgame",
            json={"path": "A", "term_sheet_name": preview["term_sheet_menu"]["path_a_name"]},
        )
        await _submit_all_departments(client, company_id, q4["id"], Q1_BY_DEPARTMENT)
        lock_report = await _lock(client, company_id, q4["id"])

        modifier_ids = {m["id"] for m in lock_report["decision_quality"]["modifiers"]}
        assert "covenant_hit" in modifier_ids and "covenant_missed" in modifier_ids

    async def test_locking_q4_with_no_decision_omits_the_q4_modifier_set(self, client):
        company_id = await _play_through_q3(client)
        q4 = await _open_quarter(client, company_id)
        await _submit_all_departments(client, company_id, q4["id"], Q1_BY_DEPARTMENT)
        lock_report = await _lock(client, company_id, q4["id"])

        modifier_ids = {m["id"] for m in lock_report["decision_quality"]["modifiers"]}
        assert modifier_ids.isdisjoint(
            {
                "covenant_hit", "covenant_missed", "correct_rejection",
                "correct_acceptance", "value_left_on_table", "deliberate_independence",
            }
        )

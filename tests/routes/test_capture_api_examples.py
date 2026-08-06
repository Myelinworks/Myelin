"""Phase 14: captures real HTTP responses from the running app into
`docs/examples/captured_payloads.json` -- the single source every OpenAPI schema example and
every payload in `docs/frontend-integration-guide.md` is drawn from.

**No example JSON is hand-written anywhere in this codebase.** This test plays one full run
start-to-finish (the same sequence `test_run_flow.py::TestFullRunToCompletion` already proves
correct) plus the four refusal envelopes, and writes each response's real body to a named key in
the captured-payloads file. `app/schemas/_examples.py` loads that file at import time to populate
every response model's `json_schema_extra` example; the guide pastes straight from it, labelled.

**To regenerate after a schema change:** `uv run pytest tests/routes/test_capture_api_examples.py`
-- it runs as part of the normal suite, so the captured file can never drift silently out of sync
with what the API actually returns: if a captured shape stops matching its `response_model`,
FastAPI's own response validation (not this test) fails loudly first.
"""

import json
import uuid
from pathlib import Path

from app.main import app
from app.routes.deps import get_current_user
from app.services.auth_service import CurrentUser, get_supabase_auth_client
from tests.routes.test_company_routes import (
    Q1_BY_DEPARTMENT,
    _create_company,
    _lock,
    _open_quarter,
    _submit_all_departments,
)

CAPTURE_PATH = Path(__file__).resolve().parents[2] / "docs" / "examples" / "captured_payloads.json"


class _FakeSupabaseAuthClient:
    """Same fake used by `test_authorization.py` -- no network call to Supabase. Captures the
    proxy routes' real response *shape*, not Supabase's own token contents."""

    async def sign_up(self, *, email: str, password: str) -> dict:
        return {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.example-access-token",
            "refresh_token": "v1.Mnb3-example-refresh-token",
            "user_id": "3fae5a10-4b2e-4f0a-8f0a-1c2d3e4f5a6b",
            "email": email,
        }

    async def sign_in(self, *, email: str, password: str) -> dict:
        return await self.sign_up(email=email, password=password)


async def test_capture_all_examples(client, db_session, current_test_user: CurrentUser):
    captured: dict[str, dict] = {}

    def capture(name: str, response) -> dict:
        body = response.json()
        captured[name] = body
        return body

    # ---- Auth: register/login proxy (fake Supabase client, real proxy route) ------------------
    auth_request = {"email": "student@myelin.dev", "password": "correct horse battery staple"}
    captured["auth_register_request"] = auth_request
    captured["auth_login_request"] = auth_request
    app.dependency_overrides[get_supabase_auth_client] = lambda: _FakeSupabaseAuthClient()
    try:
        capture("auth_register_response", await client.post("/auth/register", json=auth_request))
        capture("auth_login_response", await client.post("/auth/login", json=auth_request))
    finally:
        del app.dependency_overrides[get_supabase_auth_client]

    # ---- Start a run ---------------------------------------------------------------------------
    company_create_request = {"name": "Nadi Wear Capture Co"}
    captured["company_create_request"] = company_create_request
    company = capture("company_create_response", await client.post("/companies", json=company_create_request))
    company_id = company["id"]

    capture("run_state_fresh", await client.get(f"/companies/{company_id}/run"))
    capture("company_detail_response", await client.get(f"/companies/{company_id}"))

    # ---- Q1 --------------------------------------------------------------------------------
    q1 = capture("quarter_open_response", await client.post(f"/companies/{company_id}/quarters"))
    capture("run_state_mid_quarter", await client.get(f"/companies/{company_id}/run"))

    marketing_submit = await client.post(
        f"/companies/{company_id}/quarters/{q1['id']}/allocations/marketing", json=Q1_BY_DEPARTMENT["marketing"]
    )
    capture("allocation_submit_response", marketing_submit)
    await _submit_all_departments(client, company_id, q1["id"], Q1_BY_DEPARTMENT)
    capture("quarter_detail_after_allocations", await client.get(f"/companies/{company_id}/quarters/{q1['id']}"))

    # ---- The legacy per-workspace decision pipeline (app/routes/_factory.py) -- a separate
    # system from the 22-line allocations above, feeding its own Decision/Evidence rows. Captured
    # here, while Q1 is still open, so its schemas get a real example too.
    decision_submit_request = {"decision_key": "increase_google_ads_budget", "payload": {"amount": 5000}}
    captured["decision_submit_request"] = decision_submit_request
    capture(
        "decision_submit_response",
        await client.post(
            f"/companies/{company_id}/quarters/{q1['id']}/marketing/decisions", json=decision_submit_request
        ),
    )
    capture(
        "decision_log_list_response",
        await client.get(f"/companies/{company_id}/quarters/{q1['id']}/marketing/decisions"),
    )

    q1_report = await _lock(client, company_id, q1["id"])
    captured["quarter_report_q1"] = q1_report
    capture("run_state_after_q1_locked", await client.get(f"/companies/{company_id}/run"))

    # ---- Q2 --------------------------------------------------------------------------------
    q2 = await _open_quarter(client, company_id)
    await _submit_all_departments(client, company_id, q2["id"], Q1_BY_DEPARTMENT)
    captured["quarter_report_q2"] = await _lock(client, company_id, q2["id"])

    # ---- Q3: the crisis quarter -------------------------------------------------------------
    q3 = await _open_quarter(client, company_id)
    await _submit_all_departments(client, company_id, q3["id"], Q1_BY_DEPARTMENT)
    crisis_allocation_submit_request = {
        "crisis_choice": "C", "comparison_ads": "5.0", "emergency_supply_fund": "1.0",
    }
    captured["crisis_allocation_submit_request"] = crisis_allocation_submit_request
    crisis_submit = await client.post(
        f"/companies/{company_id}/quarters/{q3['id']}/allocations/crisis",
        json=crisis_allocation_submit_request,
    )
    capture("crisis_allocation_submit_response", crisis_submit)
    captured["quarter_report_q3_with_crisis"] = await _lock(client, company_id, q3["id"])
    capture("run_state_mid_run_with_binding_constraint_hint", await client.get(f"/companies/{company_id}/run"))

    # ---- Q4: the endgame quarter -------------------------------------------------------------
    q4 = await _open_quarter(client, company_id)
    run_state_q4 = await client.get(f"/companies/{company_id}/run")
    capture("run_state_at_q4_with_endgame_preview", run_state_q4)
    term_sheet_menu = run_state_q4.json()["endgame_preview"]["term_sheet_menu"]

    capture(
        "endgame_preview_response", await client.get(f"/companies/{company_id}/quarters/{q4['id']}/endgame")
    )
    endgame_decision_submit_request = {
        "path": "C",
        "term_sheet_name": term_sheet_menu["path_c_name"],
        "reasoning": "staying independent based on the Q1-Q3 trend",
    }
    captured["endgame_decision_submit_request"] = endgame_decision_submit_request
    endgame_submit = await client.post(
        f"/companies/{company_id}/quarters/{q4['id']}/endgame", json=endgame_decision_submit_request
    )
    capture("endgame_decision_submit_response", endgame_submit)

    await _submit_all_departments(client, company_id, q4["id"], Q1_BY_DEPARTMENT)
    captured["quarter_report_q4_final"] = await _lock(client, company_id, q4["id"])
    capture("run_state_completed", await client.get(f"/companies/{company_id}/run"))

    capture("leaderboard_response", await client.get(f"/companies/{company_id}/leaderboard"))

    # ---- The four refusal envelopes --------------------------------------------------------
    unknown_id = uuid.uuid4()
    capture("error_not_found", await client.get(f"/companies/{unknown_id}"))

    illegal_move = await client.post(f"/companies/{company_id}/quarters")  # run is already completed
    capture("error_illegal_move", illegal_move)

    other_user = CurrentUser(id=uuid.uuid4(), email="other-student@myelin.dev", role="student")
    from app.models.app_user import AppUser

    db_session.add(AppUser(id=other_user.id, email=other_user.email, role="student"))
    await db_session.flush()
    app.dependency_overrides[get_current_user] = lambda: other_user
    try:
        capture("error_not_permitted", await client.get(f"/companies/{company_id}"))
    finally:
        app.dependency_overrides[get_current_user] = lambda: current_test_user

    app.dependency_overrides.pop(get_current_user, None)
    try:
        capture("error_not_authenticated", await client.get(f"/companies/{company_id}"))
    finally:
        app.dependency_overrides[get_current_user] = lambda: current_test_user

    # ---- Write ------------------------------------------------------------------------------
    CAPTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CAPTURE_PATH.write_text(json.dumps(captured, indent=2, sort_keys=True) + "\n")

    assert CAPTURE_PATH.exists()
    assert len(captured) >= 20

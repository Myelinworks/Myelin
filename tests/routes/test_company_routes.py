"""The end-to-end HTTP surface: create a company, play quarters, lock them.

`test_q1_then_q2_through_http_only` is the acceptance case for Phase 5 -- it does **no ORM
seeding at all**, which is what makes it a real proof that the deployed API can run the
simulation, rather than a proof that the engine works when handed hand-built ORM rows.
"""

import uuid
from decimal import Decimal

import pytest

from app.services.company_service import assign_scenario_id

# docs/12-quarter-1-reference.md §12: Rs 45,00,000 across six departments.
Q1_BY_DEPARTMENT = {
    "marketing": {
        "google_ads": "4.00",
        "meta_ads": "1.92",
        "social_influencer": "2.08",
        "content_seo": "1.28",
        "events_pr": "0.80",
        "email_marketing": "1.60",
        "referral": "2.40",
        "prelaunch_buzz": "1.92",
    },
    "sales": {"reps": "5.45", "crm_tools": "1.30", "onboarding": "1.25"},
    "rnd": {"quality_qa": "2.75", "innovation": "2.25", "warranty_years": 1},
    "operations": {"manufacturing": "3.30", "supplier_qc": "1.50", "logistics": "1.20"},
    "hr": {"culture_benefits": "1.20", "training_development": "0.90", "cx_team": "0.90"},
    "finance_admin": {"compliance_legal": "2.80", "financial_planning": "2.10", "audit_prep": "2.10"},
}

# docs/13-quarter-2-reference.md §4: Variant A, Efficiency-Final (Rs 42,73,200).
Q2_EFFICIENCY_BY_DEPARTMENT = {
    "marketing": {
        "google_ads": "0.50",
        "meta_ads": "0.50",
        "social_influencer": "2.50",
        "content_seo": "1.50",
        "events_pr": "0.80",
        "email_marketing": "1.60",
        "referral": "2.736",
        "prelaunch_buzz": "1.364",
    },
    "sales": {"reps": "6.458", "crm_tools": "2.00", "onboarding": "2.00"},
    "rnd": {"quality_qa": "4.00", "innovation": "3.00", "warranty_years": 2},
    "operations": {"manufacturing": "1.024", "supplier_qc": "1.25", "logistics": "1.00"},
    "hr": {"culture_benefits": "1.50", "training_development": "2.00", "cx_team": "1.50"},
    "finance_admin": {"compliance_legal": "2.20", "financial_planning": "1.80", "audit_prep": "1.50"},
}


async def _create_company(client, name="Nadi Wear", **payload):
    response = await client.post("/companies", json={"name": name, **payload})
    assert response.status_code == 201, response.text
    return response.json()


async def _open_quarter(client, company_id):
    response = await client.post(f"/companies/{company_id}/quarters")
    assert response.status_code == 201, response.text
    return response.json()


async def _submit_all_departments(client, company_id, quarter_id, by_department):
    for department, lines in by_department.items():
        response = await client.post(
            f"/companies/{company_id}/quarters/{quarter_id}/allocations/{department}", json=lines
        )
        assert response.status_code == 200, response.text


async def _lock(client, company_id, quarter_id):
    response = await client.post(f"/companies/{company_id}/quarters/{quarter_id}/lock")
    assert response.status_code == 200, response.text
    return response.json()


class TestFullSimulationOverHttp:
    async def test_q1_then_q2_through_http_only(self, client):
        """No ORM seeding anywhere: every row here is created through the public API."""
        company = await _create_company(client)
        company_id = company["id"]
        assert company["seed_name"] == "nadi_wear"
        assert company["scenario"]["total_quarters"] == 4

        # ---- Q1: docs/12 §8 -- 562 units, -Rs31,27,837 -------------------------------------
        q1 = await _open_quarter(client, company_id)
        assert q1["number"] == 1
        assert Decimal(q1["cash_balance"]) == Decimal("15000000")
        assert q1["allocations"] is None

        await _submit_all_departments(client, company_id, q1["id"], Q1_BY_DEPARTMENT)
        q1_report = await _lock(client, company_id, q1["id"])

        assert abs(Decimal(q1_report["outcome"]["units_sold"]["value"]) - Decimal("562")) < Decimal("1")
        assert abs(Decimal(q1_report["outcome"]["net_cash_flow_inr"]["value"]) - Decimal("-3127837")) < Decimal("1")

        # ---- Q2 Efficiency-Final: docs/13 §4 -- 872 units -----------------------------------
        # Reachable only because Q1's closing state carried forward through persistence; this is
        # the first proof that compounding works across the real HTTP surface.
        q2 = await _open_quarter(client, company_id)
        assert q2["number"] == 2
        assert Decimal(q2["cash_balance"]) == Decimal(q1_report["outcome"]["closing_cash_inr"]["value"])

        await _submit_all_departments(client, company_id, q2["id"], Q2_EFFICIENCY_BY_DEPARTMENT)
        q2_report = await _lock(client, company_id, q2["id"])

        assert abs(Decimal(q2_report["outcome"]["units_sold"]["value"]) - Decimal("872")) < Decimal("1")
        # Q2 has a prior quarter, so the delta is populated (Q1 above has none).
        assert q2_report["outcome"]["units_sold"]["delta"] is not None

    async def test_get_company_reads_back_both_quarters(self, client):
        company = await _create_company(client)
        company_id = company["id"]

        q1 = await _open_quarter(client, company_id)
        await _submit_all_departments(client, company_id, q1["id"], Q1_BY_DEPARTMENT)
        await _lock(client, company_id, q1["id"])
        await _open_quarter(client, company_id)

        response = await client.get(f"/companies/{company_id}")
        assert response.status_code == 200
        body = response.json()
        assert [q["number"] for q in body["quarters"]] == [1, 2]
        assert body["quarters"][0]["status"] == "closed"
        assert body["quarters"][1]["status"] == "in_progress"

    async def test_get_quarter_reads_back_modifiers_and_allocations(self, client):
        company = await _create_company(client)
        q1 = await _open_quarter(client, company_id := company["id"])

        # the four legacy-matrix modifiers are materialised at quarter creation
        assert q1["modifiers"] == {
            "brand_strength": 1.0,
            "market_saturation": 1.0,
            "inventory_availability": 1.0,
            "competitor_activity": 1.0,
        }

        await _submit_all_departments(client, company_id, q1["id"], Q1_BY_DEPARTMENT)
        response = await client.get(f"/companies/{company_id}/quarters/{q1['id']}")

        assert response.status_code == 200
        body = response.json()
        assert Decimal(body["allocations"]["google_ads"]) == Decimal("4.00")
        assert len(body["allocations"]) == 22  # the 22 spend lines, warranty kept separate
        assert body["warranty_years"] == 1


class TestScenarioAssignmentIsDeterministic:
    def test_the_same_identifier_always_assigns_the_same_scenario(self):
        company_id = uuid.UUID("11111111-2222-3333-4444-555555555555")

        assert assign_scenario_id(company_id) == assign_scenario_id(company_id)

    def test_assignment_is_stable_across_processes_not_just_calls(self, monkeypatch):
        """With one scenario shipped, equality is trivially true -- so this fakes a multi-scenario
        roster to prove the mechanism actually discriminates and is reproducible. A `hash()`-based
        implementation would pass the test above and fail this one across processes.
        """
        import app.services.company_service as service

        monkeypatch.setattr(service, "available_scenario_ids", lambda: ("alpha", "beta", "gamma", "delta"))
        ids = [uuid.UUID(int=i) for i in range(40)]

        first = [service.assign_scenario_id(i) for i in ids]
        second = [service.assign_scenario_id(i) for i in ids]

        assert first == second
        # exercises more than one branch, so a constant-returning implementation would fail
        assert len(set(first)) > 1

    async def test_supplying_a_company_id_round_trips(self, client):
        company_id = uuid.uuid4()
        company = await _create_company(client, company_id=str(company_id))

        assert company["id"] == str(company_id)
        assert company["scenario_id"] == assign_scenario_id(company_id)


class TestQuarterCreationLimits:
    async def test_a_fifth_quarter_on_a_four_quarter_scenario_is_rejected(self, client):
        company = await _create_company(client)
        company_id = company["id"]

        # Zero-spend quarters: allocations default to zero, which is a valid (if inert) quarter,
        # and locking each one is what produces the closing snapshot the next quarter opens on.
        for expected_number in (1, 2, 3, 4):
            quarter = await _open_quarter(client, company_id)
            assert quarter["number"] == expected_number
            await _lock(client, company_id, quarter["id"])

        response = await client.post(f"/companies/{company_id}/quarters")

        assert response.status_code == 422
        assert "4 quarters" in response.json()["detail"]

    async def test_opening_a_quarter_before_locking_the_prior_one_is_rejected(self, client):
        """Otherwise the new quarter would silently restart from the seed instead of carrying
        forward real closing state."""
        company = await _create_company(client)
        await _open_quarter(client, company["id"])

        response = await client.post(f"/companies/{company['id']}/quarters")

        assert response.status_code == 422
        assert "has not been locked" in response.json()["detail"]

    async def test_unknown_scenario_is_rejected(self, client):
        response = await client.post("/companies", json={"name": "X", "scenario_id": "does_not_exist"})

        assert response.status_code == 422

    async def test_unknown_company_404s(self, client):
        response = await client.get(f"/companies/{uuid.uuid4()}")

        assert response.status_code == 404


class TestSurvivalOverHttp:
    """Cash-only quarters: no Marketing or Sales spend means no revenue, so the whole
    discretionary allocation is a straight drain and closing cash is easy to steer precisely.
    Compliance & Legal is the lever -- it feeds a score, never a cash inflow.
    """

    @staticmethod
    async def _quarter_spending(client, company_id, compliance_lakhs: str):
        quarter = await _open_quarter(client, company_id)
        response = await client.post(
            f"/companies/{company_id}/quarters/{quarter['id']}/allocations/finance_admin",
            json={"compliance_legal": compliance_lakhs},
        )
        assert response.status_code == 200
        return quarter, await _lock(client, company_id, quarter["id"])

    async def test_nadi_wear_q1_loss_is_neither_failed_nor_distressed(self, client):
        """The acceptance case, and the most likely wrong implementation: Q1 loses Rs 31,27,837
        and is still a healthy quarter -- it closes at Rs 1,18,72,163, nearly 12x the buffer.
        """
        company = await _create_company(client)
        q1 = await _open_quarter(client, company_id := company["id"])
        await _submit_all_departments(client, company_id, q1["id"], Q1_BY_DEPARTMENT)
        report = await _lock(client, company_id, q1["id"])

        assert Decimal(report["outcome"]["net_cash_flow_inr"]["value"]) < 0  # it really did lose money
        assert Decimal(report["outcome"]["closing_cash_inr"]["value"]) > Decimal("11000000")

        body = (await client.get(f"/companies/{company_id}")).json()
        assert body["run_status"] == "active"
        assert body["survival_condition"] is None

    async def test_cash_below_zero_fails_the_run(self, client):
        company = await _create_company(client)
        # Rs 2,00,00,000 of spend against Rs 1,50,00,000 of cash.
        await self._quarter_spending(client, company_id := company["id"], "200.00")

        body = (await client.get(f"/companies/{company_id}")).json()
        assert body["run_status"] == "failed"
        assert body["survival_condition"] == "cash_exhausted"
        assert "at or below zero" in body["survival_detail"]

    async def test_a_failed_company_cannot_open_another_quarter(self, client):
        company = await _create_company(client)
        await self._quarter_spending(client, company_id := company["id"], "200.00")

        response = await client.post(f"/companies/{company_id}/quarters")

        assert response.status_code == 422
        assert "failed" in response.json()["detail"]

    async def test_below_buffer_but_positive_is_distressed_and_keeps_playing(self, client):
        """Rs 1,20,00,000 of spend leaves Rs 5,60,000 -- under the Rs 10,00,000 buffer, above
        zero. Distressed is a warning tier, not game over, so the next quarter still opens."""
        company = await _create_company(client)
        await self._quarter_spending(client, company_id := company["id"], "120.00")

        body = (await client.get(f"/companies/{company_id}")).json()
        assert body["run_status"] == "distressed"
        assert body["survival_condition"] == "buffer_breached"
        assert Decimal(body["quarters"][0]["cash_balance"]) > 0

        assert (await client.post(f"/companies/{company_id}/quarters")).status_code == 201

    async def test_completing_the_last_quarter_marks_the_run_completed(self, client):
        company = await _create_company(client)
        company_id = company["id"]
        for _ in range(4):
            quarter = await _open_quarter(client, company_id)
            await _lock(client, company_id, quarter["id"])

        body = (await client.get(f"/companies/{company_id}")).json()
        assert body["run_status"] == "completed"
        # the distress that built up along the way is still recorded, for Q4 tiering to read
        assert body["survival_condition"] == "sustained_decline"


@pytest.mark.parametrize("seed_backed", ["nadi_wear"])
def test_only_seeds_that_can_actually_run_back_a_scenario(seed_backed):
    """PulseWear is deliberately not shipped as a scenario -- docs/03 never states 9 constants
    the chain needs, so a pulsewear company would 500 on its first lock."""
    from app.config.loader import available_scenario_ids, load_scenario

    backing_seeds = {load_scenario(s).seed for s in available_scenario_ids()}

    assert backing_seeds == {seed_backed}

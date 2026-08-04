"""Phase 9: HTTP-level coverage for the report's individual sections, over the real
create-company -> allocate -> lock -> report surface. Complements the pure-layer proofs in
tests/engines/test_report.py (which already cover determinism and score/outcome separability in
detail) with the same acceptance numbers checked through the full persistence + serialization path.
"""

from decimal import Decimal

from tests.routes.test_company_routes import Q1_BY_DEPARTMENT, _create_company, _lock, _open_quarter, _submit_all_departments


async def _q1_report(client):
    company = await _create_company(client)
    quarter = await _open_quarter(client, company["id"])
    await _submit_all_departments(client, company["id"], quarter["id"], Q1_BY_DEPARTMENT)
    return company, quarter, await _lock(client, company["id"], quarter["id"])


class TestBindingConstraintSection:
    async def test_sales_capacity_named_with_216_leads_lost(self, client):
        _, _, report = await _q1_report(client)
        by_gate = {bc["gate"]: bc for bc in report["binding_constraints"]}
        assert "sales_capacity" in by_gate
        assert abs(Decimal(by_gate["sales_capacity"]["demand_lost"]) - Decimal("216")) < Decimal("1")
        assert by_gate["sales_capacity"]["demand_lost_unit"] == "leads"


class TestDecisionQualitySection:
    async def test_profitability_modifier_shown_negative(self, client):
        _, _, report = await _q1_report(client)
        modifiers = {m["id"]: m for m in report["decision_quality"]["modifiers"]}
        assert modifiers["profitability_achieved"]["fired"] is False
        assert "-3,127,8" in modifiers["profitability_achieved"]["detail"]

    async def test_perfect_channel_match_shown_positive_with_cap_reason(self, client):
        _, _, report = await _q1_report(client)
        modifiers = {m["id"]: m for m in report["decision_quality"]["modifiers"]}
        fact = modifiers["perfect_channel_match"]
        assert fact["fired"] is True
        assert Decimal(fact["applied_points"]) == 2
        assert "referral_lead_cap=800.00" in fact["detail"]

    async def test_leadership_criteria_are_unscored_with_reasons_not_zeroed_or_hidden(self, client):
        _, _, report = await _q1_report(client)
        leadership = [c for c in report["decision_quality"]["unscored_criteria"] if c["trait"] == "leadership"]
        assert {c["id"] for c in leadership} == {"leadership_1", "leadership_2", "leadership_3"}
        assert all(len(c["reason"]) > 0 for c in leadership)
        # Never appears in scored_criteria (which would imply a point value, even 0) either.
        scored_ids = {c["id"] for c in report["decision_quality"]["scored_criteria"]}
        assert scored_ids.isdisjoint({"leadership_1", "leadership_2", "leadership_3"})


class TestReportReadIsPureAndIdempotent:
    async def test_two_reads_of_the_same_locked_quarter_are_byte_identical(self, client):
        company, quarter, _ = await _q1_report(client)
        first = await client.get(f"/companies/{company['id']}/quarters/{quarter['id']}/report")
        second = await client.get(f"/companies/{company['id']}/quarters/{quarter['id']}/report")
        assert first.status_code == second.status_code == 200
        assert first.json() == second.json()


class TestFailedRunNamesTheConditionInPlainLanguage:
    async def test_massive_overspend_fails_the_run_and_the_report_names_why(self, client):
        company = await _create_company(client)
        quarter = await _open_quarter(client, company["id"])
        overspend = dict(Q1_BY_DEPARTMENT)
        overspend["finance_admin"] = {**overspend["finance_admin"], "financial_planning": "500.00"}
        await _submit_all_departments(client, company["id"], quarter["id"], overspend)

        report = await _lock(client, company["id"], quarter["id"])

        assert report["run_status"] == "failed"
        assert report["survival_triggered_by"] == "cash_exhausted"
        assert "closing cash" in report["survival_detail"]
        assert "zero" in report["survival_detail"]

        # Terminal quarter: the run-level summary is attached.
        assert report["run_summary"] is not None
        assert report["run_summary"]["terminal_status"] == "failed"
        assert len(report["run_summary"]["score_trajectory"]) == 1
        assert report["run_summary"]["score_trajectory"][0]["quarter_number"] == 1

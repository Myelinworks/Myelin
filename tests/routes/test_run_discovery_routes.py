"""`GET /companies` and the leaderboard's score column -- the two reads a client needs to answer
"which runs do I have, and how did they go" without keeping its own bookkeeping.

Both existed as gaps rather than bugs in the engine: ownership was always enforced server-side,
but nothing let a client *discover* the ids it owned, and the leaderboard reported a column the
shipped pipeline never writes.
"""

import uuid

from tests.routes.test_company_routes import (
    Q1_BY_DEPARTMENT,
    _create_company,
    _lock,
    _open_quarter,
    _submit_all_departments,
)


class TestListMyRuns:
    async def test_no_runs_yet_returns_an_empty_list(self, client):
        response = await client.get("/companies")

        assert response.status_code == 200
        assert response.json() == {"entries": []}

    async def test_a_created_run_is_discoverable_without_remembering_its_id(self, client):
        """The gap this closes: before it, a client that lost its localStorage copy of the
        company id could never reach that run again, even though it still owned it."""
        created = await _create_company(client, name="Discoverable Co")

        response = await client.get("/companies")

        assert response.status_code == 200
        entries = response.json()["entries"]
        assert [e["id"] for e in entries] == [created["id"]]
        assert entries[0]["name"] == "Discoverable Co"

    async def test_scenario_shape_is_included_so_a_list_needs_no_follow_up_request(self, client):
        await _create_company(client)

        entry = (await client.get("/companies")).json()["entries"][0]

        assert entry["total_quarters"] == 4
        assert entry["crisis_quarter"] == 3
        assert entry["scenario_id"] == "nadi_wear_standard"
        assert entry["run_status"] == "active"

    async def test_a_fresh_run_reports_no_quarter_and_no_score(self, client):
        await _create_company(client)

        entry = (await client.get("/companies")).json()["entries"][0]

        assert entry["current_quarter_number"] is None
        assert entry["current_quarter_status"] is None
        assert entry["quarters_locked"] == 0
        assert entry["latest_ceo_score"] is None
        assert entry["latest_band"] is None

    async def test_progress_and_latest_score_track_a_locked_quarter(self, client):
        company = await _create_company(client)
        quarter = await _open_quarter(client, company["id"])
        await _submit_all_departments(client, company["id"], quarter["id"], Q1_BY_DEPARTMENT)
        report = await _lock(client, company["id"], quarter["id"])

        entry = (await client.get("/companies")).json()["entries"][0]

        assert entry["quarters_locked"] == 1
        assert entry["current_quarter_number"] == 1
        assert entry["current_quarter_status"] == "closed"
        assert entry["latest_ceo_score"] == report["decision_quality"]["ceo_score"]
        assert entry["latest_band"] == report["decision_quality"]["band"]

    async def test_ordering_is_stable_across_repeated_reads(self, client):
        """Both runs are created inside one test transaction, so PostgreSQL's `now()` gives them
        an identical `created_at` -- exactly the tie the `id` tiebreaker exists for. Without it
        the same unchanged data could come back in a different order on the second read."""
        await _create_company(client, name="One")
        await _create_company(client, name="Two")

        first_read = [e["id"] for e in (await client.get("/companies")).json()["entries"]]
        second_read = [e["id"] for e in (await client.get("/companies")).json()["entries"]]

        assert len(first_read) == 2
        assert first_read == second_read

    async def test_another_users_run_is_never_listed(self, client, db_session):
        """Strictly owner-scoped -- `GET /companies` is "my runs", not a directory. A read that
        widened with the caller's role would make the same URL mean different things."""
        from app.models.app_user import AppUser
        from app.models.company import Company

        await _create_company(client, name="Mine")
        stranger = AppUser(id=uuid.uuid4(), email="stranger@myelin.dev", role="student")
        db_session.add(stranger)
        await db_session.flush()
        db_session.add(Company(name="Theirs", owner_id=stranger.id))
        await db_session.flush()

        entries = (await client.get("/companies")).json()["entries"]

        assert [e["name"] for e in entries] == ["Mine"]


class TestRunNumbersAreStablePerOwner:
    """`seq` is what a `/run/<n>` URL is built from, so the only thing that matters about it is
    that it never moves: the number a student sees today must open the same run tomorrow."""

    async def test_a_first_run_is_number_one(self, client):
        created = await _create_company(client, name="First")

        assert created["seq"] == 1

    async def test_each_new_run_takes_the_next_number(self, client):
        first = await _create_company(client, name="One")
        second = await _create_company(client, name="Two")
        third = await _create_company(client, name="Three")

        assert [first["seq"], second["seq"], third["seq"]] == [1, 2, 3]

    async def test_the_number_resolves_back_to_the_same_uuid_on_a_later_read(self, client):
        """The whole contract behind the URL: look up "run 2" in the owner's list and you get
        the id every API path actually takes. A client never has to store the mapping."""
        await _create_company(client, name="One")
        second = await _create_company(client, name="Two")

        entries = (await client.get("/companies")).json()["entries"]
        by_number = {e["seq"]: e["id"] for e in entries}

        assert by_number[2] == second["id"]

    async def test_numbering_is_per_owner_so_every_student_has_a_run_one(self, client, db_session):
        """Global numbering would leak how many runs the whole platform has ever had into every
        student's first URL, and make "my first run" a different number for everyone."""
        from app.models.app_user import AppUser
        from app.services.company_service import create_company

        stranger = AppUser(id=uuid.uuid4(), email="stranger-seq@myelin.dev", role="student")
        db_session.add(stranger)
        await db_session.flush()
        await create_company(db_session, name="Theirs", owner_id=stranger.id)
        await create_company(db_session, name="Theirs again", owner_id=stranger.id)

        mine = await _create_company(client, name="Mine")

        assert mine["seq"] == 1


class TestLeaderboardReportsTheScoreTheEngineWrites:
    async def test_locked_quarter_reports_its_real_ceo_score(self, client):
        """Regression: this returned `QuarterPerformance.overall_score`, which only the legacy
        per-decision cognitive pipeline writes. `run_quarter()` never invokes that pipeline, so
        the field was null for every quarter of every run the shipped flow produces -- the
        endpoint reported a permanent null as if it were a score."""
        company = await _create_company(client)
        quarter = await _open_quarter(client, company["id"])
        await _submit_all_departments(client, company["id"], quarter["id"], Q1_BY_DEPARTMENT)
        report = await _lock(client, company["id"], quarter["id"])

        response = await client.get(f"/companies/{company['id']}/leaderboard")

        assert response.status_code == 200
        entries = response.json()["entries"]
        assert len(entries) == 1
        assert entries[0]["ceo_score"] == report["decision_quality"]["ceo_score"]
        assert entries[0]["band"] == report["decision_quality"]["band"]
        assert entries[0]["ceo_score"] is not None

    async def test_an_open_quarter_does_not_appear_at_all(self, client):
        """`QuarterPerformance` is written by `run_quarter()`, so an open quarter has no row to
        report -- the endpoint omits it rather than listing it with a null score."""
        company = await _create_company(client)
        await _open_quarter(client, company["id"])

        entries = (await client.get(f"/companies/{company['id']}/leaderboard")).json()["entries"]

        assert entries == []


class TestCrisisBriefingRoute:
    """The read that closes `docs/frontend-integration-guide.md` section 4's flagged gap: which
    crisis fired, told the way `docs/11` says students are allowed to be told it."""

    async def _crisis_quarter(self, client, company_id):
        """Open and lock quarters until the scenario's crisis quarter is the open one."""
        quarter = None
        for _ in range(3):
            quarter = await _open_quarter(client, company_id)
            if quarter["number"] == 3:
                return quarter
            await _submit_all_departments(client, company_id, quarter["id"], Q1_BY_DEPARTMENT)
            await _lock(client, company_id, quarter["id"])
        return quarter

    async def test_briefing_is_readable_before_the_response_is_submitted(self, client):
        company = await _create_company(client)
        quarter = await self._crisis_quarter(client, company["id"])

        response = await client.get(
            f"/companies/{company['id']}/quarters/{quarter['id']}/crisis"
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["scenario_code"] in ("A", "B", "C", "D")
        assert body["narrative"] and body["title"]
        assert body["category"] in ("competitive", "operational")
        assert body["choices"], "a briefing with no choices tells a student nothing to act on"
        assert body["response_lines"], "every scenario has at least one line worth funding"
        assert body["ignoring_is_legal"] is True

    async def test_every_named_response_line_is_a_real_crisis_request_field(self, client):
        """The briefing's whole value is telling a student which of the five crisis spend fields
        actually matter -- a name that isn't a real field would be worse than saying nothing."""
        from app.schemas.allocation import CrisisAllocationSubmit

        company = await _create_company(client)
        quarter = await self._crisis_quarter(client, company["id"])

        body = (
            await client.get(f"/companies/{company['id']}/quarters/{quarter['id']}/crisis")
        ).json()

        submittable = set(CrisisAllocationSubmit.model_fields)
        assert {line["field"] for line in body["response_lines"]} <= submittable

    async def test_a_non_crisis_quarter_has_no_briefing(self, client):
        company = await _create_company(client)
        quarter = await _open_quarter(client, company["id"])

        response = await client.get(
            f"/companies/{company['id']}/quarters/{quarter['id']}/crisis"
        )

        assert response.status_code == 404
        assert "crisis quarter" in response.json()["detail"]

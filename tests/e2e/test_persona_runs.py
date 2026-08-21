"""End to end: three CEOs play the same four quarters, and the run is graded on the difference.

This is the only test that drives a whole run the way a browser does -- create the company,
preview and lock four quarters over HTTP, sign a term sheet between Q3 and Q4, and read the
finished run back. Everything the personas decide from arrives in a response body; nothing here
reaches into the engine to steer a result.

Why three of them rather than one: a single scripted run can only assert that the machinery
does not fall over. Three runs of the same scenario, played well and badly, assert that the
machinery *discriminates* -- that reading the constraint, answering the market event and
pricing the term sheet are worth more than spending the same money differently. If a novice
run ever scores like an expert one, the product has stopped measuring judgment, and no unit
test in this repo would notice.

All three face the identical market event on purpose (see `company_id_for`), so the only
variable between them is how they played.

    uv run pytest tests/e2e -s          # with the comparison table
    uv run pytest -m "not e2e"          # everything else; these are the slow ones
"""

import uuid
from dataclasses import dataclass, field

import pytest

from app.engines.simulation.catalog import ARCHETYPE_IDS, TOTAL_QUARTERS
from tests.e2e.personas import ALL_PERSONAS, EXPERT, Persona

pytestmark = pytest.mark.e2e

#: One event for all three runs. `price_war` has the widest spread between a right and a wrong
#: reading of it, which is exactly what this test is trying to see.
ARCHETYPE = "price_war"

#: Roughly one scoring band. A difference smaller than this is not a difference.
BAND = 10.0


def company_id_for(archetype: str, seed: str) -> uuid.UUID:
    """A company id that draws `archetype`.

    `assign_archetype` picks the event from `company_id.int % len(ARCHETYPE_IDS)` so a student
    cannot reroll their crisis by reloading. That makes the id the only lever for putting three
    runs in front of the same event -- so the id is built to land on it, deterministically
    per `seed`.
    """
    target = ARCHETYPE_IDS.index(archetype)
    base = uuid.uuid5(uuid.NAMESPACE_DNS, f"myelin-e2e.{archetype}.{seed}").int
    return uuid.UUID(int=base - (base % len(ARCHETYPE_IDS)) + target)


@dataclass
class Outcome:
    """One finished run, in the terms a board would ask about."""

    persona: Persona
    run: dict
    locks: list[dict]
    budgets: list[dict]
    term_sheet: dict
    path: str
    ceiling_breaches: int = 0
    quarters: list[dict] = field(default_factory=list)

    @property
    def scores(self) -> list[float]:
        return [float(lock["score"]["final"]) for lock in self.locks]

    @property
    def mean_score(self) -> float:
        return sum(self.scores) / len(self.scores)

    @property
    def final(self) -> dict:
        return self.locks[-1]["result"]

    @property
    def settlement(self) -> dict | None:
        return self.locks[-1]["settlement"]

    @property
    def final_valuation(self) -> float:
        settled = self.settlement
        return float(settled["final_valuation"]) if settled else float(self.final["valuation"])

    @property
    def closing_cash(self) -> float:
        return float(self.final["cash"])

    @property
    def units_sold(self) -> float:
        return sum(float(lock["result"]["units_sold"]) for lock in self.locks)


async def play_run(client, persona: Persona, seed: str) -> Outcome:
    """Drive one persona through a complete run over HTTP, exactly as the client does."""
    # The seed carries the persona: three runs of the same event need three companies.
    company_id = company_id_for(ARCHETYPE, f"{persona.name}.{seed}")
    created = await client.post(
        "/companies",
        json={"name": f"Nadi Wear - {persona.name}", "company_id": str(company_id)},
    )
    assert created.status_code == 201, created.text
    cid = created.json()["id"]

    locks: list[dict] = []
    budgets: list[dict] = []
    breaches = 0
    term_sheet: dict = {}
    path = ""

    for quarter in range(1, TOTAL_QUARTERS + 1):
        run = (await client.get(f"/companies/{cid}/simulation/run")).json()
        assert run["current_quarter"] == quarter
        assert "lock_quarter" in run["legal_moves"]

        # Draft, preview, revise on what the preview said, preview again -- the same two-pass
        # loop the decision screens run, so the plan that locks is one the CEO has seen priced.
        plan = persona.draft(quarter, run)
        preview = (await client.post(f"/companies/{cid}/simulation/preview", json=plan)).json()
        plan = persona.revise(plan, preview)
        response = await client.post(f"/companies/{cid}/simulation/preview", json=plan)
        assert response.status_code == 200, response.text
        preview = response.json()

        # Preview persists nothing: the quarter it reports on is still the open one.
        assert preview["quarter"] == quarter
        budgets.append(preview["budget"])
        if float(preview["budget"]["committed"]) > float(preview["budget"]["ceiling"]):
            breaches += 1

        locked = await client.post(f"/companies/{cid}/simulation/lock", json=plan)
        assert locked.status_code == 200, locked.text
        locks.append(locked.json())

        if quarter == TOTAL_QUARTERS - 1:
            # Q3 has closed: the term sheet is the gate into Q4 and has to be signed first.
            after_q3 = (await client.get(f"/companies/{cid}/simulation/run")).json()
            assert "submit_endgame_decision" in after_q3["legal_moves"]

            term_sheet = (await client.get(f"/companies/{cid}/simulation/endgame")).json()
            path = persona.choose_path(term_sheet, after_q3)
            signed = await client.post(
                f"/companies/{cid}/simulation/endgame",
                json={
                    "path": path,
                    "term_sheet_name": term_sheet["term_sheet_menu"][f"path_{path.lower()}_name"],
                    "reasoning": f"{persona.label}, on a {term_sheet['tier']} tier.",
                },
            )
            assert signed.status_code == 200, signed.text

    run = (await client.get(f"/companies/{cid}/simulation/run")).json()
    assert run["run_status"] == "completed"
    assert run["quarters_locked"] == TOTAL_QUARTERS
    assert run["current_quarter"] is None
    assert run["legal_moves"] == ["read_quarter_report", "read_endgame_preview"]

    return Outcome(persona, run, locks, budgets, term_sheet, path, breaches)


def assert_run_is_well_formed(outcome: Outcome) -> None:
    """What has to be true of any completed run, however it was played."""
    assert len(outcome.locks) == TOTAL_QUARTERS
    assert outcome.run["endgame_path"] == outcome.path
    assert outcome.term_sheet["tier"] in ("THRIVING", "STABLE", "DISTRESSED")

    for quarter, lock in enumerate(outcome.locks, start=1):
        score = lock["score"]
        assert lock["quarter"] == quarter
        # Seven weighted traits, the same rubric the 22-line engine is graded on.
        assert len(score["traits"]) == 7
        assert sum(float(t["weight"]) for t in score["traits"]) == 100
        # The traits are the 0-100 part; the modifiers are what move a score off it, and the
        # published total is exactly their sum. Deliberately not asserted to sit inside 0-100:
        # neither engine clamps, so a run that collects enough penalties reports a negative
        # score, and a test that pretended otherwise would be asserting a rule nothing enforces.
        assert 0 <= float(score["trait_total"]) <= 100
        assert float(score["final"]) == pytest.approx(
            float(score["trait_total"]) + float(score["modifier_total"]), abs=0.01
        )
        assert score["band"] in ("Exceptional", "Strong", "Competent", "Weak", "Poor")

    settled = outcome.settlement
    assert settled is not None, "Q4 has to settle the term sheet that was signed"
    assert settled["path"] == outcome.path
    # The cheque never survives the quarter it funded.
    assert float(outcome.run["state"]["pending_investment"]) == 0


async def test_three_ceos_play_the_same_scenario(client):
    """The whole run, three ways, and the comparison that is the point of running it.

    One test rather than four: every assertion below is about the *set* of runs, and playing
    twelve quarters over HTTP once is worth more than playing them four times to keep each
    claim in its own function.
    """
    outcomes = [await play_run(client, persona, seed="v1") for persona in ALL_PERSONAS]
    _print_report(outcomes)

    for outcome in outcomes:
        assert_run_is_well_formed(outcome)

    novice, intermediate, expert = outcomes

    # ── the product claim, as an assertion ───────────────────────────
    # Reading the constraint, answering the event and pricing the offer beat spending the same
    # balance sheet at the loudest channel. If this fails, the rubric has stopped rewarding
    # judgment and the DI Report means nothing.
    assert expert.mean_score > intermediate.mean_score > novice.mean_score
    assert expert.mean_score - novice.mean_score > BAND

    # ── and it shows up in the company, not only in the grade ────────
    assert novice.closing_cash < expert.closing_cash
    assert novice.final_valuation < expert.final_valuation

    # The expert plans inside the ceiling every quarter; buying leads with the whole balance
    # sheet does not.
    assert expert.ceiling_breaches == 0
    assert novice.ceiling_breaches > 0

    # ── the cheque the intermediate signed ───────────────────────────
    # Path A puts the investment on Q4's opening state, so it is in the budget the CEO plans
    # against before the cash arrives, and lands as financing cash flow when the quarter closes.
    assert intermediate.path == "A"
    q4_budget = intermediate.budgets[TOTAL_QUARTERS - 1]
    q3_closing_cash = float(intermediate.locks[TOTAL_QUARTERS - 2]["result"]["cash"])
    assert float(q4_budget["investment"]) > 0
    assert float(q4_budget["drawn"]) == 0, "this persona never draws, so the cheque is the only lift"
    # A ceiling above the bank balance the quarter opened with can only come from the cheque.
    assert float(q4_budget["ceiling"]) > q3_closing_cash
    # And it lands as financing cash flow in the quarter it funded, not before.
    assert float(intermediate.final["equity_raised"]) == float(q4_budget["investment"])


async def test_the_same_decisions_replay_to_the_same_run(client):
    """Determinism, end to end: no RNG anywhere in the chain.

    A second company playing the expert's exact quarters lands on the same scores and the same
    closing balance sheet as the first. This is what makes two students' results comparable at
    all, and it is asserted here rather than in an engine test because the HTTP path adds
    serialisation, storage and replay on top of the arithmetic.
    """
    first = await play_run(client, EXPERT, seed="v1")
    second = await play_run(client, EXPERT, seed="v2")

    assert first.scores == second.scores
    assert first.final_valuation == second.final_valuation
    assert first.closing_cash == second.closing_cash
    assert first.term_sheet["tier"] == second.term_sheet["tier"]


def _print_report(outcomes: list[Outcome]) -> None:
    """The comparison this test exists to produce. Visible with `pytest -s`."""
    print(f"\n\n  Four quarters of Nadi Wear, played three ways · market event: {ARCHETYPE}\n")
    header = (
        f"  {'CEO':<34}{'Q1':>7}{'Q2':>7}{'Q3':>7}{'Q4':>7}{'mean':>8}  {'band':<14}{'path':>5}"
    )
    print(header)
    print("  " + "-" * (len(header) - 2))
    for outcome in outcomes:
        q1, q2, q3, q4 = outcome.scores
        print(
            f"  {outcome.persona.label:<34}{q1:>7.1f}{q2:>7.1f}{q3:>7.1f}{q4:>7.1f}"
            f"{outcome.mean_score:>8.1f}  {outcome.locks[-1]['score']['band']:<14}{outcome.path:>5}"
        )

    print()
    print(
        f"  {'CEO':<34}{'closing cash':>16}{'valuation':>16}{'units':>9}"
        f"{'over ceiling':>14}{'tier':>12}"
    )
    print("  " + "-" * (len(header) - 2))
    for outcome in outcomes:
        print(
            f"  {outcome.persona.label:<34}{outcome.closing_cash:>16,.0f}"
            f"{outcome.final_valuation:>16,.0f}{outcome.units_sold:>9,.0f}"
            f"{outcome.ceiling_breaches:>14}{outcome.term_sheet['tier']:>12}"
        )
    print()

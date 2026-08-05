"""Phase 12: `services/run_service.py` -- the DB-facing half of the run/session model.

Uses the same `db_session` fixture the route tests use (root `tests/conftest.py`); genuinely needs
a session, so this lives beside `test_quarter_run_service.py`, not in `tests/engines/`.
"""

from decimal import Decimal

import pytest

from app.engines.run_state import Move
from app.models.company import Company
from app.models.quarter import Quarter, QuarterStatus
from app.models.quarter_allocation import QuarterAllocation
from app.services.quarter_run_service import run_quarter
from app.services.run_service import IllegalMoveError, get_run_state, load_run_facts, require_move
from tests.services.test_quarter_run_service import Q1_ALLOCATION_FIELDS


@pytest.fixture
async def nadi_wear_company(db_session):
    company = Company(name="Nadi Wear", seed_name="nadi_wear", profile_name="default")
    db_session.add(company)
    await db_session.flush()
    return company


async def _open_and_submit(db_session, company, number, **extra_fields):
    quarter = Quarter(
        company_id=company.id, number=number, status=QuarterStatus.IN_PROGRESS, cash_balance=0, revenue=0
    )
    db_session.add(quarter)
    await db_session.flush()
    db_session.add(
        QuarterAllocation(company_id=company.id, quarter_id=quarter.id, **Q1_ALLOCATION_FIELDS, **extra_fields)
    )
    await db_session.flush()
    return quarter


class TestLoadRunFacts:
    async def test_no_quarter_yet(self, db_session, nadi_wear_company):
        facts = await load_run_facts(db_session, nadi_wear_company)

        assert facts.current_quarter_number is None
        assert facts.current_quarter_status is None
        assert facts.total_quarters == 4
        assert facts.crisis_quarter == 3

    async def test_reflects_the_open_quarter(self, db_session, nadi_wear_company):
        await _open_and_submit(db_session, nadi_wear_company, 1)

        facts = await load_run_facts(db_session, nadi_wear_company)
        assert facts.current_quarter_number == 1
        assert facts.current_quarter_status == QuarterStatus.IN_PROGRESS

    async def test_reflects_the_locked_quarter(self, db_session, nadi_wear_company):
        q1 = await _open_and_submit(db_session, nadi_wear_company, 1)
        await run_quarter(db_session, q1.id)

        facts = await load_run_facts(db_session, nadi_wear_company)
        assert facts.current_quarter_status == QuarterStatus.CLOSED


class TestRequireMove:
    async def test_raises_illegal_move_error_with_the_allowed_set(self, db_session, nadi_wear_company):
        await _open_and_submit(db_session, nadi_wear_company, 1)

        with pytest.raises(IllegalMoveError) as exc_info:
            await require_move(db_session, nadi_wear_company, Move.SUBMIT_ENDGAME_DECISION)

        error = exc_info.value
        assert error.move == Move.SUBMIT_ENDGAME_DECISION
        assert "quarter 4" in error.reason
        assert Move.SUBMIT_ALLOCATION in error.allowed
        assert Move.SUBMIT_ENDGAME_DECISION not in error.allowed

    async def test_does_not_raise_for_a_legal_move(self, db_session, nadi_wear_company):
        await _open_and_submit(db_session, nadi_wear_company, 1)
        await require_move(db_session, nadi_wear_company, Move.SUBMIT_ALLOCATION)  # no raise


class TestGetRunState:
    async def test_before_any_quarter_only_open_next_quarter_is_legal(self, db_session, nadi_wear_company):
        state = await get_run_state(db_session, nadi_wear_company)

        assert state.current_quarter_number is None
        assert state.legal_moves == (Move.OPEN_NEXT_QUARTER,)
        assert state.binding_constraint_hint == ()
        assert state.score_trajectory == ()
        assert state.endgame_preview is None

    async def test_binding_constraint_hint_reflects_q1s_actual_bound_gates(self, db_session, nadi_wear_company):
        """docs/12-quarter-1-reference.md: Sales Capacity and the Conversion Ceiling both bind."""
        q1 = await _open_and_submit(db_session, nadi_wear_company, 1)
        await run_quarter(db_session, q1.id)

        state = await get_run_state(db_session, nadi_wear_company)
        gates = {c.gate for c in state.binding_constraint_hint}
        assert {"sales_capacity", "conversion_ceiling"}.issubset(gates)

    async def test_score_trajectory_grows_as_quarters_lock(self, db_session, nadi_wear_company):
        q1 = await _open_and_submit(db_session, nadi_wear_company, 1)
        await run_quarter(db_session, q1.id)

        state = await get_run_state(db_session, nadi_wear_company)
        assert [p.quarter_number for p in state.score_trajectory] == [1]

    async def test_endgame_preview_appears_only_at_q4(self, db_session, nadi_wear_company):
        for number in (1, 2):
            quarter = await _open_and_submit(db_session, nadi_wear_company, number)
            await run_quarter(db_session, quarter.id)

        q3 = await _open_and_submit(
            db_session, nadi_wear_company, 3,
            crisis_choice="C", comparison_ads=Decimal("5.0"), emergency_supply_fund=Decimal("1.0"),
        )
        await run_quarter(db_session, q3.id)

        mid_run_state = await get_run_state(db_session, nadi_wear_company)
        assert mid_run_state.endgame_preview is None

        q4 = await _open_and_submit(db_session, nadi_wear_company, 4)
        q4_state = await get_run_state(db_session, nadi_wear_company)
        assert q4_state.endgame_preview is not None
        assert q4_state.endgame_preview.tier in ("thriving", "stable", "distressed")
        assert Move.SUBMIT_ENDGAME_DECISION in q4_state.legal_moves
        assert Move.READ_ENDGAME_PREVIEW in q4_state.legal_moves

    async def test_run_state_is_a_pure_read_repeated_calls_are_identical(self, db_session, nadi_wear_company):
        q1 = await _open_and_submit(db_session, nadi_wear_company, 1)
        await run_quarter(db_session, q1.id)

        first = await get_run_state(db_session, nadi_wear_company)
        second = await get_run_state(db_session, nadi_wear_company)
        assert first == second

"""Phase 12: `engines/run_state.py`'s legal-move gatekeeper -- pure, no DB.

Every threshold asserted here already existed somewhere in the codebase before this phase
(`company_service.create_quarter`'s total_quarters/terminal checks, `_opening_cash`'s prior-lock
check, `routes/deps.py::get_open_quarter`'s open-quarter check, `endgame_service`'s Q4-only check).
This file is the truth table for the one place they now live.
"""

from app.engines.run_state import Move, RunFacts, check, explain, legal_moves
from app.engines.survival import RunStatus
from app.models.quarter import QuarterStatus

TOTAL_QUARTERS = 4
CRISIS_QUARTER = 3


def _facts(
    run_status=RunStatus.ACTIVE,
    total_quarters=TOTAL_QUARTERS,
    crisis_quarter=CRISIS_QUARTER,
    current_quarter_number=None,
    current_quarter_status=None,
) -> RunFacts:
    return RunFacts(
        run_status=run_status,
        total_quarters=total_quarters,
        crisis_quarter=crisis_quarter,
        current_quarter_number=current_quarter_number,
        current_quarter_status=current_quarter_status,
    )


class TestNoQuarterYet:
    def test_only_open_next_quarter_is_legal(self):
        assert legal_moves(_facts()) == frozenset({Move.OPEN_NEXT_QUARTER})


class TestQuarterOpen:
    def test_submit_and_lock_are_legal(self):
        facts = _facts(current_quarter_number=1, current_quarter_status=QuarterStatus.IN_PROGRESS)
        assert legal_moves(facts) == frozenset({Move.SUBMIT_ALLOCATION, Move.LOCK_QUARTER})

    def test_open_next_quarter_is_not_legal_while_open(self):
        facts = _facts(current_quarter_number=1, current_quarter_status=QuarterStatus.IN_PROGRESS)
        allowed, reason = check(Move.OPEN_NEXT_QUARTER, facts)
        assert allowed is False
        assert "still open" in reason

    def test_read_quarter_report_is_not_legal_while_open(self):
        facts = _facts(current_quarter_number=1, current_quarter_status=QuarterStatus.IN_PROGRESS)
        assert Move.READ_QUARTER_REPORT not in legal_moves(facts)


class TestQuarterLocked:
    def test_open_next_and_read_report_are_legal(self):
        facts = _facts(current_quarter_number=1, current_quarter_status=QuarterStatus.CLOSED)
        assert legal_moves(facts) == frozenset({Move.OPEN_NEXT_QUARTER, Move.READ_QUARTER_REPORT})

    def test_submit_allocation_is_not_legal_once_locked(self):
        facts = _facts(current_quarter_number=1, current_quarter_status=QuarterStatus.CLOSED)
        allowed, reason = check(Move.SUBMIT_ALLOCATION, facts)
        assert allowed is False
        assert "no quarter is currently open" in reason


class TestOpenNextQuarterPastTheEnd:
    def test_opening_a_5th_quarter_is_illegal(self):
        facts = _facts(current_quarter_number=4, current_quarter_status=QuarterStatus.CLOSED)
        allowed, reason = check(Move.OPEN_NEXT_QUARTER, facts)
        assert allowed is False
        assert "4 quarters" in reason


class TestCrisisQuarterGating:
    def test_submit_crisis_allocation_only_legal_on_the_crisis_quarter(self):
        on_crisis_quarter = _facts(current_quarter_number=3, current_quarter_status=QuarterStatus.IN_PROGRESS)
        assert Move.SUBMIT_CRISIS_ALLOCATION in legal_moves(on_crisis_quarter)

        off_crisis_quarter = _facts(current_quarter_number=2, current_quarter_status=QuarterStatus.IN_PROGRESS)
        assert Move.SUBMIT_CRISIS_ALLOCATION not in legal_moves(off_crisis_quarter)
        assert "quarter 3" in explain(Move.SUBMIT_CRISIS_ALLOCATION, off_crisis_quarter)

    def test_no_crisis_quarter_configured(self):
        facts = _facts(crisis_quarter=None, current_quarter_number=1, current_quarter_status=QuarterStatus.IN_PROGRESS)
        allowed, reason = check(Move.SUBMIT_CRISIS_ALLOCATION, facts)
        assert allowed is False
        assert "no crisis quarter" in reason


class TestQ4EndgameGating:
    def test_submit_endgame_decision_only_legal_at_the_last_quarter(self):
        at_q4 = _facts(current_quarter_number=4, current_quarter_status=QuarterStatus.IN_PROGRESS)
        assert Move.SUBMIT_ENDGAME_DECISION in legal_moves(at_q4)

        at_q2 = _facts(current_quarter_number=2, current_quarter_status=QuarterStatus.IN_PROGRESS)
        assert Move.SUBMIT_ENDGAME_DECISION not in legal_moves(at_q2)
        assert "quarter 4" in explain(Move.SUBMIT_ENDGAME_DECISION, at_q2)

    def test_read_endgame_preview_only_legal_at_the_last_quarter_open_or_locked(self):
        at_q4_open = _facts(current_quarter_number=4, current_quarter_status=QuarterStatus.IN_PROGRESS)
        at_q4_locked = _facts(current_quarter_number=4, current_quarter_status=QuarterStatus.CLOSED)
        at_q3 = _facts(current_quarter_number=3, current_quarter_status=QuarterStatus.IN_PROGRESS)

        assert Move.READ_ENDGAME_PREVIEW in legal_moves(at_q4_open)
        assert Move.READ_ENDGAME_PREVIEW in legal_moves(at_q4_locked)
        assert Move.READ_ENDGAME_PREVIEW not in legal_moves(at_q3)


class TestTerminalRunRefusesEveryWrite:
    def test_failed_run_has_no_write_moves(self):
        facts = _facts(run_status=RunStatus.FAILED, current_quarter_number=2, current_quarter_status=QuarterStatus.CLOSED)
        moves = legal_moves(facts)
        assert moves == frozenset({Move.READ_QUARTER_REPORT})

    def test_completed_run_at_q4_can_still_be_read(self):
        facts = _facts(
            run_status=RunStatus.COMPLETED, current_quarter_number=4, current_quarter_status=QuarterStatus.CLOSED
        )
        assert legal_moves(facts) == frozenset({Move.READ_QUARTER_REPORT, Move.READ_ENDGAME_PREVIEW})

    def test_open_next_quarter_reason_names_the_terminal_status(self):
        facts = _facts(run_status=RunStatus.FAILED, current_quarter_number=2, current_quarter_status=QuarterStatus.CLOSED)
        allowed, reason = check(Move.OPEN_NEXT_QUARTER, facts)
        assert allowed is False
        assert "failed" in reason

    def test_distressed_is_not_terminal_and_keeps_every_write_move(self):
        """DISTRESSED is a warning tier, not a terminal one -- the company keeps playing."""
        facts = _facts(
            run_status=RunStatus.DISTRESSED, current_quarter_number=2, current_quarter_status=QuarterStatus.CLOSED
        )
        assert Move.OPEN_NEXT_QUARTER in legal_moves(facts)


class TestExplainIsEmptyForALegalMove:
    def test_explain_returns_empty_string_when_the_move_is_legal(self):
        facts = _facts(current_quarter_number=1, current_quarter_status=QuarterStatus.IN_PROGRESS)
        assert explain(Move.SUBMIT_ALLOCATION, facts) == ""

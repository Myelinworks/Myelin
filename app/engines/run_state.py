"""Phase 12: the single legal-move gatekeeper.

Before this module, "can the student do X right now" was answered independently, and
inconsistently, in several places: `services/company_service.py::create_quarter` re-derived
"has the scenario ended" and "is the run terminal"; `services/company_service.py::_opening_cash`
re-derived "is the prior quarter locked"; `routes/deps.py::get_open_quarter` re-derived "is this
quarter still open"; `services/endgame_service.py` re-derived "is this quarter the scenario's
last one" for reads only, with no equivalent check on the write path at all (a real gap -- nothing
stopped `POST .../endgame` from accepting a decision at Q2). Every one of those facts is a
function of the same small set of numbers (run status, current quarter number and status, the
scenario's length and crisis quarter). This module is the one place that turns those numbers into
"what's legal right now" -- callers consult it instead of re-deriving the condition themselves.

Pure: no I/O, no DB session, no clock, no RNG, same discipline as every other `engines/` module.
The facts (`RunFacts`) are loaded by `services/run_service.py`; this module only decides, given
those facts, which moves are legal and why one that isn't.

No new game rules are introduced here -- every threshold below (total_quarters, crisis_quarter,
"lock before opening the next quarter", "the endgame only exists at the scenario's last quarter")
already existed somewhere in the codebase before this phase. This module gives each of them
exactly one definition.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Callable

from app.engines.survival import RunStatus, is_terminal
from app.models.quarter import QuarterStatus


class Move(StrEnum):
    OPEN_NEXT_QUARTER = "open_next_quarter"
    SUBMIT_ALLOCATION = "submit_allocation"
    SUBMIT_CRISIS_ALLOCATION = "submit_crisis_allocation"
    SUBMIT_ENDGAME_DECISION = "submit_endgame_decision"
    LOCK_QUARTER = "lock_quarter"
    READ_QUARTER_REPORT = "read_quarter_report"
    READ_ENDGAME_PREVIEW = "read_endgame_preview"


@dataclass(frozen=True)
class RunFacts:
    """Everything `legal_moves`/`explain` need, and nothing they compute for themselves.

    `current_quarter_number`/`current_quarter_status` are `None` only when the company has no
    quarter at all yet (before the first `POST .../quarters`).
    """

    run_status: RunStatus
    total_quarters: int
    crisis_quarter: int | None
    current_quarter_number: int | None
    current_quarter_status: QuarterStatus | None


def _quarter_is_open(facts: RunFacts) -> bool:
    return facts.current_quarter_status == QuarterStatus.IN_PROGRESS


def _check_open_next_quarter(facts: RunFacts) -> tuple[bool, str]:
    if _quarter_is_open(facts):
        return False, f"quarter {facts.current_quarter_number} is still open; lock it before opening the next one"
    next_number = (facts.current_quarter_number or 0) + 1
    if next_number > facts.total_quarters:
        return False, f"this scenario runs {facts.total_quarters} quarters; quarter {next_number} is past the end"
    return True, ""


def _check_submit_allocation(facts: RunFacts) -> tuple[bool, str]:
    if not _quarter_is_open(facts):
        return False, "no quarter is currently open for allocation submissions"
    return True, ""


def _check_submit_crisis_allocation(facts: RunFacts) -> tuple[bool, str]:
    if not _quarter_is_open(facts):
        return False, "no quarter is currently open for allocation submissions"
    if facts.crisis_quarter is None:
        return False, "this scenario has no crisis quarter"
    if facts.current_quarter_number != facts.crisis_quarter:
        return False, (
            f"the crisis only fires in quarter {facts.crisis_quarter}, not quarter "
            f"{facts.current_quarter_number}"
        )
    return True, ""


def _check_submit_endgame_decision(facts: RunFacts) -> tuple[bool, str]:
    if not _quarter_is_open(facts):
        return False, "no quarter is currently open for allocation submissions"
    if facts.current_quarter_number != facts.total_quarters:
        return False, (
            f"the endgame decision only exists in quarter {facts.total_quarters} (this scenario's "
            f"last), not quarter {facts.current_quarter_number}"
        )
    return True, ""


def _check_lock_quarter(facts: RunFacts) -> tuple[bool, str]:
    if not _quarter_is_open(facts):
        return False, "no quarter is currently open to lock"
    return True, ""


def _check_read_quarter_report(facts: RunFacts) -> tuple[bool, str]:
    if facts.current_quarter_status != QuarterStatus.CLOSED:
        return False, "the current quarter has not been locked yet -- there is no report before that"
    return True, ""


def _check_read_endgame_preview(facts: RunFacts) -> tuple[bool, str]:
    if facts.current_quarter_number != facts.total_quarters:
        return False, (
            f"the endgame preview only exists in quarter {facts.total_quarters} (this scenario's "
            f"last), not quarter {facts.current_quarter_number}"
        )
    return True, ""


_CHECKS: dict[Move, Callable[[RunFacts], tuple[bool, str]]] = {
    Move.OPEN_NEXT_QUARTER: _check_open_next_quarter,
    Move.SUBMIT_ALLOCATION: _check_submit_allocation,
    Move.SUBMIT_CRISIS_ALLOCATION: _check_submit_crisis_allocation,
    Move.SUBMIT_ENDGAME_DECISION: _check_submit_endgame_decision,
    Move.LOCK_QUARTER: _check_lock_quarter,
    Move.READ_QUARTER_REPORT: _check_read_quarter_report,
    Move.READ_ENDGAME_PREVIEW: _check_read_endgame_preview,
}

# The moves that change state. A terminated run refuses every one of these outright -- checked
# once, here, rather than duplicated inside each of the five predicates above. Reads are
# deliberately not in this set: the final quarter's report and the Q4 endgame preview must stay
# readable after the run ends (a FAILED/COMPLETED run's report is exactly what a student reads
# once nothing else is legal), so their own predicates decide their legality unconditionally.
_WRITE_MOVES = frozenset(
    {
        Move.OPEN_NEXT_QUARTER,
        Move.SUBMIT_ALLOCATION,
        Move.SUBMIT_CRISIS_ALLOCATION,
        Move.SUBMIT_ENDGAME_DECISION,
        Move.LOCK_QUARTER,
    }
)


def check(move: Move, facts: RunFacts) -> tuple[bool, str]:
    """Whether `move` is legal right now, and why not when it isn't."""
    if move in _WRITE_MOVES and is_terminal(facts.run_status):
        return False, f"the run is {facts.run_status.value}; a terminated run accepts no further submissions or locks"
    return _CHECKS[move](facts)


def legal_moves(facts: RunFacts) -> frozenset[Move]:
    return frozenset(move for move in Move if check(move, facts)[0])


def explain(move: Move, facts: RunFacts) -> str:
    """The reason `move` is illegal right now. Only meaningful when `check(move, facts)[0]` is
    `False` -- returns an empty string for a legal move."""
    return check(move, facts)[1]

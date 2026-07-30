"""Is the run still alive, and is it in trouble?

Pure: no I/O, no DB session, no clock, no RNG. Takes the company's quarter history and the
profile's survival config, returns a status and **the specific condition that produced it** --
never a bare boolean, because "this run failed" is not actionable without "because cash hit
zero in Q3".

Two of the three conditions come from the designer's stated Distressed definition
(`docs/17-designer-resolutions.md`, Tier Assignment):

    Distressed: Buffer breached at any point
                OR (NCF < 0 with cash declining 2+ consecutive quarters)

The third, `cash_exhausted`, is the unambiguous cash-zero line -- not a stated rule, but not a
judgement call either. Nothing else is invented: there are no runway-quarter thresholds and no
debt-covenant triggers here, because the source specifies none.

**DISTRESSED is not game over.** It is the designer's warning tier: it changes the Q4 term-sheet
menu and nothing else. Only `cash_exhausted` ends a run.
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from app.config.schema import SurvivalConfig
from app.engines.quarter import QuarterResult


class RunStatus(StrEnum):
    """Where a run stands. Persisted on `Company` and gates quarter creation.

    `COMPLETED` is decided by the persistence layer rather than here -- it depends on the
    scenario's `total_quarters`, which is not a property of any quarter's result.
    """

    ACTIVE = "active"
    DISTRESSED = "distressed"
    FAILED = "failed"
    COMPLETED = "completed"


# Only the three statuses this module can produce. Ranked so that a quarter tripping several
# conditions at once reports the most severe rather than whichever the config happens to list
# first -- a company that has both breached its buffer and run out of cash has FAILED.
_SEVERITY = {RunStatus.ACTIVE: 0, RunStatus.DISTRESSED: 1, RunStatus.FAILED: 2}


@dataclass(frozen=True)
class SurvivalOutcome:
    """`triggered_by` is the config condition's `id`; `detail` states the numbers that fired it.

    Both are `None` only when the status is ACTIVE -- nothing fired, so there is nothing to name.
    """

    status: RunStatus
    triggered_by: str | None = None
    detail: str | None = None


def _quarter_number(quarter: QuarterResult) -> int:
    """The quarter this result is *for*. `closing_state` is already the next quarter's opening
    state, so its number is one ahead."""
    return quarter.closing_state.quarter_number - 1


def _cash_exhausted(history: list[QuarterResult]) -> str | None:
    """Closing cash at or below zero, in any quarter. The run is over.

    Checked across the whole history rather than just the latest quarter so that a run which
    already died stays dead, even if a later evaluation is somehow handed more quarters.
    """
    for quarter in history:
        if quarter.closing_cash_inr <= 0:
            return (
                f"closing cash reached Rs {quarter.closing_cash_inr:,.2f} in Q{_quarter_number(quarter)}, "
                f"at or below zero"
            )
    return None


def _buffer_breached(history: list[QuarterResult]) -> str | None:
    """Closing cash below the working capital buffer -- "breached at any point", per the
    designer's wording, so one bad quarter marks the run even if it recovers later.

    Distinct from `QuarterResult.spent_into_buffer`, which asks whether *discretionary spend*
    exceeded the ceiling. A company can end below its buffer without overspending (a bad revenue
    quarter), and can overspend without ending below it (a big opening balance).
    """
    for quarter in history:
        if quarter.closing_cash_inr < quarter.working_capital_buffer_inr:
            return (
                f"closing cash Rs {quarter.closing_cash_inr:,.2f} in Q{_quarter_number(quarter)} fell below "
                f"the Rs {quarter.working_capital_buffer_inr:,.2f} working capital buffer"
            )
    return None


def _sustained_decline(history: list[QuarterResult]) -> str | None:
    """Negative NCF now, and cash falling for at least two consecutive quarters ending here.

    A quarter's cash falls exactly when its net cash flow is negative (`closing = opening +
    NCF`), so the streak is counted on NCF rather than on differenced balances -- same condition,
    one fewer place for an off-by-one to hide.

    Deliberately anchored to the *latest* quarter: this is the designer's "Q3 NCF < 0 with cash
    declining 2+ consecutive quarters", a statement about where the run currently stands, not
    about whether two bad quarters ever happened.
    """
    if not history or history[-1].net_cash_flow_inr >= 0:
        return None

    streak = 0
    for quarter in reversed(history):
        if quarter.net_cash_flow_inr >= 0:
            break
        streak += 1

    if streak < 2:
        return None
    return (
        f"net cash flow was negative for {streak} consecutive quarters, "
        f"through Q{_quarter_number(history[-1])}"
    )


PREDICATES: dict[str, Callable[[list[QuarterResult]], str | None]] = {
    "cash_exhausted": _cash_exhausted,
    "buffer_breached": _buffer_breached,
    "sustained_decline": _sustained_decline,
}


def evaluate_survival(company_history: list[QuarterResult], rules: SurvivalConfig) -> SurvivalOutcome:
    """Evaluate every configured condition over the run so far.

    `company_history` is every quarter computed to date, oldest first -- not just the current
    one, because `sustained_decline` is a multi-quarter condition and `buffer_breached` is
    "at any point".
    """
    if not company_history:
        return SurvivalOutcome(status=RunStatus.ACTIVE)

    outcome = SurvivalOutcome(status=RunStatus.ACTIVE)
    for condition in rules.conditions:
        predicate = PREDICATES.get(condition.id)
        if predicate is None:
            raise NotImplementedError(
                f"survival condition '{condition.id}' is configured but has no predicate in "
                f"engines/survival.py -- a configured check that silently does nothing is worse "
                f"than one that is absent"
            )

        detail = predicate(company_history)
        if detail is None:
            continue

        status = RunStatus(condition.outcome.lower())
        if _SEVERITY[status] > _SEVERITY[outcome.status]:
            outcome = SurvivalOutcome(status=status, triggered_by=condition.id, detail=detail)

    return outcome


def is_terminal(status: RunStatus) -> bool:
    """Whether the run is over. DISTRESSED is not -- the company keeps playing."""
    return status in (RunStatus.FAILED, RunStatus.COMPLETED)

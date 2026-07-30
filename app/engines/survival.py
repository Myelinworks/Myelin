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


def _cash_exhausted(history: list[QuarterResult], _tier_assignment_quarter: int | None) -> str | None:
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


def _buffer_breached(history: list[QuarterResult], _tier_assignment_quarter: int | None) -> str | None:
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


def _sustained_decline(history: list[QuarterResult], tier_assignment_quarter: int | None) -> str | None:
    """Negative NCF at the **tier-assignment quarter**, with cash falling for 2+ consecutive
    quarters ending there.

    Anchored to that one quarter, not to whichever quarter happens to be latest. The designer's
    rule is "**Q3** NCF < 0 with cash declining 2+ consecutive quarters" -- a Tier Assignment
    input evaluated once, not a running health check. Read as a per-quarter signal it flags a
    normal cash-burning startup distressed by construction: the canonical Efficiency-Final run,
    which the source scores 82/100, would be DISTRESSED at Q2 while holding 11x its buffer.
    An 82/100 company is not distressed, so that reading is wrong.

    Evaluating the streak *as it stood at* the tier-assignment quarter -- rather than only while
    that quarter is the latest -- also makes the verdict sticky: Q4 cannot silently clear a
    distress signal that Q3 legitimately raised, which is what Phase 11's tiering reads.

    A quarter's cash falls exactly when its net cash flow is negative (`closing = opening +
    NCF`), so the streak is counted on NCF rather than on differenced balances -- same condition,
    one fewer place for an off-by-one to hide.
    """
    if tier_assignment_quarter is None:
        return None

    quarters_to_tier = [q for q in history if _quarter_number(q) <= tier_assignment_quarter]
    if not quarters_to_tier or _quarter_number(quarters_to_tier[-1]) != tier_assignment_quarter:
        return None  # the run has not reached the tier-assignment quarter yet
    if quarters_to_tier[-1].net_cash_flow_inr >= 0:
        return None

    streak = 0
    for quarter in reversed(quarters_to_tier):
        if quarter.net_cash_flow_inr >= 0:
            break
        streak += 1

    if streak < 2:
        return None
    return (
        f"net cash flow was negative for {streak} consecutive quarters, "
        f"through the tier-assignment quarter Q{tier_assignment_quarter}"
    )


PREDICATES: dict[str, Callable[[list[QuarterResult], int | None], str | None]] = {
    "cash_exhausted": _cash_exhausted,
    "buffer_breached": _buffer_breached,
    "sustained_decline": _sustained_decline,
}


def tier_assignment_quarter(total_quarters: int) -> int:
    """The quarter Tier Assignment is evaluated at: the one before the endgame.

    `docs/17-designer-resolutions.md` states the rule in terms of Q3 for the canonical
    four-quarter scenario; expressed relative to scenario length so a scenario of a different
    length assigns its tier in the right place rather than always at a hardcoded Q3.
    """
    return total_quarters - 1


def evaluate_survival(
    company_history: list[QuarterResult],
    rules: SurvivalConfig,
    tier_quarter: int | None = None,
) -> SurvivalOutcome:
    """Evaluate every configured condition over the run so far.

    `company_history` is every quarter computed to date, oldest first -- not just the current
    one, because `sustained_decline` looks at a streak and `buffer_breached` is "at any point".

    `tier_quarter` is where Tier Assignment is evaluated (see `tier_assignment_quarter`).
    `None` means the caller has no scenario context, and the tier-scoped conditions stay
    dormant rather than guessing a quarter to fire at.
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

        detail = predicate(company_history, tier_quarter)
        if detail is None:
            continue

        status = RunStatus(condition.outcome.lower())
        if _SEVERITY[status] > _SEVERITY[outcome.status]:
            outcome = SurvivalOutcome(status=status, triggered_by=condition.id, detail=detail)

    return outcome


def is_terminal(status: RunStatus) -> bool:
    """Whether the run is over. DISTRESSED is not -- the company keeps playing."""
    return status in (RunStatus.FAILED, RunStatus.COMPLETED)

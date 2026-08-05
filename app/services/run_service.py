"""Phase 12: the DB-facing half of the run/session model.

Loads a `Company` and its `Quarter` rows into `engines/run_state.py`'s pure `RunFacts`, and builds
the richer read (`RunState`) a frontend consults instead of reconstructing game state by combining
`GET /companies/{id}`, `GET /quarters/{id}`, `GET /quarters/{id}/report`, and
`GET /quarters/{id}/endgame` itself. Everything here is either a plain read of already-persisted
data or a call into an already-pure engine function (`engines.report.binding_constraints`,
`engines.endgame.build_endgame_preview` via `endgame_service`) -- this module computes no engine
number of its own.

`require_move` is the one place every write route now consults before doing anything: it loads the
same `RunFacts` `get_run_state` does and raises `IllegalMoveError` if the requested move isn't in
`engines.run_state.legal_moves(facts)`. One function, one error shape, one source of truth for
"can this happen right now" -- see `engines/run_state.py`'s own module docstring for the scattered
checks this replaces.
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.loader import load_scenario
from app.engines.endgame import EndgamePreview
from app.engines.quarter import QuarterResult
from app.engines.report import BindingConstraint, ScoreTrajectoryPoint, binding_constraints
from app.engines.run_state import Move, RunFacts
from app.engines.run_state import check as check_move
from app.engines.run_state import legal_moves as compute_legal_moves
from app.models.company import Company
from app.models.quarter import Quarter, QuarterStatus
from app.models.quarter_performance import QuarterPerformance
from app.services.endgame_service import get_endgame_preview
from app.services.quarter_run_service import _from_jsonable
from app.services.report_service import score_trajectory


class IllegalMoveError(Exception):
    """Raised by `require_move` when the requested move isn't legal right now. Carries enough to
    render the "not allowed, because X, allowed moves are Y" shape without the caller re-deriving
    anything -- `main.py`'s exception handler reads these three fields directly."""

    def __init__(self, move: Move, reason: str, allowed: frozenset[Move]):
        self.move = move
        self.reason = reason
        self.allowed = allowed
        super().__init__(reason)


@dataclass(frozen=True)
class RunState:
    """The single rich state read. `current_quarter_number`/`current_quarter_id`/
    `current_quarter_status` are `None` only before the first quarter is opened."""

    company_id: uuid.UUID
    run_status: str
    total_quarters: int
    crisis_quarter: int | None
    current_quarter_id: uuid.UUID | None
    current_quarter_number: int | None
    current_quarter_status: QuarterStatus | None
    legal_moves: tuple[Move, ...]
    binding_constraint_hint: tuple[BindingConstraint, ...]
    score_trajectory: tuple[ScoreTrajectoryPoint, ...]
    endgame_preview: EndgamePreview | None


async def _latest_quarter(session: AsyncSession, company_id: uuid.UUID) -> Quarter | None:
    return (
        await session.execute(
            select(Quarter).where(Quarter.company_id == company_id).order_by(Quarter.number.desc()).limit(1)
        )
    ).scalar_one_or_none()


async def _latest_locked_result(session: AsyncSession, company_id: uuid.UUID) -> QuarterResult | None:
    row = (
        await session.execute(
            select(QuarterPerformance.engine_result)
            .join(Quarter, Quarter.id == QuarterPerformance.quarter_id)
            .where(QuarterPerformance.company_id == company_id, QuarterPerformance.engine_result.isnot(None))
            .order_by(Quarter.number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return _from_jsonable(QuarterResult, row) if row is not None else None


async def load_run_facts(session: AsyncSession, company: Company) -> RunFacts:
    scenario = load_scenario(company.scenario_id)
    latest = await _latest_quarter(session, company.id)
    return RunFacts(
        run_status=company.run_status,
        total_quarters=scenario.total_quarters,
        crisis_quarter=scenario.crisis_quarter,
        current_quarter_number=latest.number if latest else None,
        current_quarter_status=latest.status if latest else None,
    )


async def require_move(session: AsyncSession, company: Company, move: Move) -> None:
    """Consult the single gatekeeper before doing anything a route's write depends on. Raises
    `IllegalMoveError` rather than returning a bool -- a caller that forgets to check a bool is a
    silent bypass; a caller that forgets to catch an exception is a 500, which is at least loud."""
    facts = await load_run_facts(session, company)
    allowed, reason = check_move(move, facts)
    if not allowed:
        raise IllegalMoveError(move, reason, compute_legal_moves(facts))


async def get_run_state(session: AsyncSession, company: Company) -> RunState:
    """The rich, read-only state view. Never mutates, never recomputes an engine number -- every
    field is either a fact already on `company`/the latest `Quarter` row, the pure gatekeeper's
    output, or a call into an already-pure engine function over already-persisted results."""
    facts = await load_run_facts(session, company)
    latest = await _latest_quarter(session, company.id)

    latest_locked_result = await _latest_locked_result(session, company.id)
    hint = binding_constraints(latest_locked_result) if latest_locked_result is not None else ()

    endgame_preview: EndgamePreview | None = None
    if facts.current_quarter_number == facts.total_quarters and latest is not None:
        endgame_preview = await get_endgame_preview(session, latest.id)

    return RunState(
        company_id=company.id,
        run_status=facts.run_status,
        total_quarters=facts.total_quarters,
        crisis_quarter=facts.crisis_quarter,
        current_quarter_id=latest.id if latest else None,
        current_quarter_number=facts.current_quarter_number,
        current_quarter_status=facts.current_quarter_status,
        # Sorted, not the frozenset's own iteration order -- a stable, alphabetised list is what
        # makes the read genuinely byte-identical on repeat for a client, not just set-equal.
        legal_moves=tuple(sorted(compute_legal_moves(facts), key=lambda m: m.value)),
        binding_constraint_hint=hint,
        score_trajectory=await score_trajectory(session, company.id),
        endgame_preview=endgame_preview,
    )

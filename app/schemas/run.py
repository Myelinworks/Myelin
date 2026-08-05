import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.endgame import EndgamePreviewResponse
from app.schemas.quarter import BindingConstraintSchema, ScoreTrajectoryPointSchema


class RunStateResponse(BaseModel):
    """`GET /companies/{company_id}/run` -- the single rich state read (Phase 12). Everything here
    is either a fact already on `Company`/the latest `Quarter` row, the pure gatekeeper's output,
    or an already-pure engine function's output over already-persisted results; nothing is
    computed by this endpoint itself.
    """

    model_config = ConfigDict(from_attributes=True)

    company_id: uuid.UUID
    run_status: str
    total_quarters: int
    crisis_quarter: int | None = None

    current_quarter_id: uuid.UUID | None = None
    current_quarter_number: int | None = None
    current_quarter_status: str | None = None

    # What the student may legally do next, from engines/run_state.py's single gatekeeper --
    # sorted alphabetically by services/run_service.py so repeated reads are byte-identical.
    legal_moves: list[str]

    # The prior quarter's binding-gate hint, so a frontend opening a new quarter doesn't have to
    # separately fetch that quarter's report to know what constrained it.
    binding_constraint_hint: list[BindingConstraintSchema]

    # The CEO score trajectory so far -- available at any point in the run, not just once terminal.
    score_trajectory: list[ScoreTrajectoryPointSchema]

    # Present only once the current quarter is the scenario's last one.
    endgame_preview: EndgamePreviewResponse | None = None

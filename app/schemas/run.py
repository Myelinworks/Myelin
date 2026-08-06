import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.engines.run_state import Move
from app.engines.survival import RunStatus
from app.models.quarter import QuarterStatus
from app.schemas._examples import example
from app.schemas.endgame import EndgamePreviewResponse
from app.schemas.quarter import BindingConstraintSchema, ScoreTrajectoryPointSchema


class RunStateResponse(BaseModel):
    """The single rich state read a client should poll between every write: where this run stands,
    and exactly what it may legally do next.

    Everything here is either a fact already on `Company`/the latest `Quarter` row, the pure
    gatekeeper's output, or an already-pure engine function's output over already-persisted
    results -- this endpoint computes nothing new. A frontend should never hardcode which moves
    are allowed at which lifecycle point; it reads `legal_moves` from this payload and renders
    accordingly (see `docs/frontend-integration-guide.md`).
    """

    # A single representative capture (mid-quarter -- most fields populated); the guide walks
    # every other lifecycle point (fresh/locked/Q4/completed) with its own captured payload,
    # since OpenAPI's per-schema example slot only cleanly holds one value at a time.
    model_config = ConfigDict(
        from_attributes=True, json_schema_extra={"example": example("run_state_mid_quarter")}
    )

    company_id: uuid.UUID
    run_status: RunStatus = Field(
        description="ACTIVE (playing normally) / DISTRESSED (a warning tier -- the run keeps "
        "playing, but the Q4 term-sheet menu changes) / FAILED (cash hit zero; terminal) / "
        "COMPLETED (played through the scenario's last quarter; terminal). Only FAILED and "
        "COMPLETED are terminal -- see `is_terminal` in the backend's `engines/survival.py`."
    )
    total_quarters: int = Field(description="How many quarters this scenario runs (4 for the shipped scenario).")
    crisis_quarter: int | None = Field(
        default=None,
        description="Which quarter number carries a crisis event (3 for the shipped scenario), "
        "or null for a scenario with no crisis. This tells you WHEN, not WHICH of the four crisis "
        "scenarios (A-D) is live -- see the guide's Q3 section for the current discovery gap.",
    )

    current_quarter_id: uuid.UUID | None = Field(
        default=None, description="Null only before the first POST .../quarters."
    )
    current_quarter_number: int | None = None
    current_quarter_status: QuarterStatus | None = Field(
        default=None,
        description='IN_PROGRESS (allocations may still be submitted) or CLOSED (locked -- read '
        "the quarter's report instead). Null before the first quarter is opened.",
    )

    legal_moves: list[Move] = Field(
        description="What the caller may legally do right next, from the single gatekeeper "
        "(`engines/run_state.py`), sorted alphabetically so repeated reads are byte-identical. "
        "This is the field a frontend renders from -- never hardcode which buttons are enabled."
    )

    binding_constraint_hint: list[BindingConstraintSchema] = Field(
        description="The prior locked quarter's binding-gate hint (0-3 entries; empty means "
        "nothing constrained demand), so a frontend opening a new quarter doesn't have to "
        "separately fetch that quarter's report to know what limited it last time."
    )

    score_trajectory: list[ScoreTrajectoryPointSchema] = Field(
        description="Every locked quarter's CEO score so far, oldest first. Available at any "
        "point in the run, not just once terminal."
    )

    endgame_preview: EndgamePreviewResponse | None = Field(
        default=None, description="Populated only once `current_quarter_number` equals `total_quarters`."
    )

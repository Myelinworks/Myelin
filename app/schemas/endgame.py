import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class _FromAttributes(BaseModel):
    """Constructed directly from `app.engines.endgame`'s pure dataclasses
    (`Model.model_validate(dataclass_instance)`), same convention as `schemas/quarter.py`."""

    model_config = ConfigDict(from_attributes=True)


class TermSheetMenuSchema(_FromAttributes):
    path_a_name: str
    path_b_name: str
    path_c_name: str


class EndgamePreviewResponse(_FromAttributes):
    """`GET .../endgame` -- what this tier is offered, computed straight off Q1-Q3's already-locked
    results. No decision required to see it: the numbers are a consequence of Q1-Q3, not something
    Q4 lets a team negotiate (`docs/16` section 2's design intent).
    """

    tier: str
    tier_detail: str
    momentum_score: Decimal
    term_sheet_menu: TermSheetMenuSchema
    covenant_units: Decimal
    true_continuation_value_inr: Decimal
    acquisition_trap_offer_inr: Decimal | None = None


class EndgameDecisionSubmit(BaseModel):
    path: str = Field(pattern="^[ABC]$")
    term_sheet_name: str
    reasoning: str | None = None


class EndgameDecisionResponse(_FromAttributes):
    id: uuid.UUID
    company_id: uuid.UUID
    quarter_id: uuid.UUID
    path: str
    term_sheet_name: str
    reasoning: str | None = None

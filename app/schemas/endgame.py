import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.engines.endgame import Tier
from app.schemas._examples import example


class _FromAttributes(BaseModel):
    """Constructed directly from `app.engines.endgame`'s pure dataclasses
    (`Model.model_validate(dataclass_instance)`), same convention as `schemas/quarter.py`."""

    model_config = ConfigDict(from_attributes=True)


class TermSheetMenuSchema(_FromAttributes):
    """The three named offers for this run's tier -- names only; Path A/B's actual numbers come
    from `covenant_units`/`true_continuation_value_inr`, which don't vary by term-sheet name."""

    path_a_name: str = Field(description="The Path A (continue independently, hit a covenant) offer's name.")
    path_b_name: str = Field(description="The Path B (accept an acquisition/investment offer) offer's name.")
    path_c_name: str = Field(description="The Path C (stay independent, no covenant) offer's name.")


class EndgamePreviewResponse(_FromAttributes):
    """`GET .../quarters/{quarter_id}/endgame` -- what this tier is offered, computed straight off
    Q1-Q3's already-locked results. No decision required to see it: the numbers are a consequence
    of Q1-Q3 performance, not something Q4 lets a team negotiate. Only exists for the scenario's
    last quarter (404 otherwise) and only once Q3 has locked (409 otherwise).
    """

    model_config = ConfigDict(
        from_attributes=True, json_schema_extra={"example": example("endgame_preview_response")}
    )

    tier: Tier = Field(
        description="THRIVING (Q3 net cash flow positive and valuation grew in both Q2 and Q3) / "
        "STABLE (neither Thriving nor Distressed) / DISTRESSED (the run's own survival tier "
        "carried through -- see RunStateResponse.run_status). Decides which term-sheet menu is offered."
    )
    tier_detail: str = Field(description="Human-readable explanation of why this tier was assigned.")
    momentum_score: Decimal = Field(description="`(Q3 units sold / Q1 units sold)^0.5 - 1`.")
    term_sheet_menu: TermSheetMenuSchema
    covenant_units: Decimal = Field(
        description="Path A's units-sold covenant: `Q3 units sold * (1 + 1.3 * momentum_score)`. "
        "Q4 must sell at least this many units for Path A to be honoured."
    )
    true_continuation_value_inr: Decimal = Field(
        description="Path B's reference value: `Q3 blended valuation * (1 + momentum_score)`."
    )
    acquisition_trap_offer_inr: Decimal | None = Field(
        default=None,
        description="Path B's actual cash offer. Known only for the Thriving tier's Acquisition "
        "Trap term sheet -- null for every other tier/term-sheet combination (no source-stated "
        "formula exists for them; see docs/10-implementation-gaps.md).",
    )


class EndgameDecisionSubmit(BaseModel):
    """`POST .../quarters/{quarter_id}/endgame` -- the Q4 strategic decision. One row per company,
    upserted until Q4 locks. The outcome (covenant hit/missed, offer accepted/declined) is scored
    later, at Q4's own lock, not by this endpoint."""

    model_config = ConfigDict(json_schema_extra={"example": example("endgame_decision_submit_request")})

    path: Literal["A", "B", "C"] = Field(
        description="A = continue independently and try to hit the covenant. B = accept the "
        "acquisition/investment offer. C = stay independent with no covenant attached."
    )
    term_sheet_name: str = Field(
        description="Must match one of `term_sheet_menu`'s three names from the preview for this tier."
    )
    reasoning: str | None = Field(
        default=None,
        description="Free text, read by a future judgment scorer -- never scored by this endpoint itself.",
    )


class EndgameDecisionResponse(_FromAttributes):
    model_config = ConfigDict(
        from_attributes=True, json_schema_extra={"example": example("endgame_decision_submit_response")}
    )

    id: uuid.UUID
    company_id: uuid.UUID
    quarter_id: uuid.UUID
    path: Literal["A", "B", "C"]
    term_sheet_name: str
    reasoning: str | None = None

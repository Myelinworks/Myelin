import uuid
from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config.rules import valid_decision_keys
from app.models.decision import DecisionStatus, Workspace
from app.schemas._examples import example
from app.schemas.base import QuarterScopedBase


class DecisionSubmitBase(BaseModel):
    """Base for the legacy per-decision workspace submissions (`app/routes/_factory.py`) -- a
    separate system from the 22-line allocation endpoints (`/allocations/{department}`), writing
    its own `Decision`/`Evidence` rows that never appear in a quarter report's `evidence` dict
    (that comes from the 22-line flow alone; see `QuarterReportResponse.evidence`). Subclasses set
    `workspace` and decide whether `payload` needs extra structural validation.
    """

    model_config = ConfigDict(json_schema_extra={"example": example("decision_submit_request")})

    workspace: ClassVar[Workspace]

    decision_key: str = Field(description="Looked up against that workspace's rules config; unknown keys 422.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Decision-specific inputs, e.g. a spend amount.")

    @field_validator("decision_key")
    @classmethod
    def _decision_key_must_be_known(cls, v: str) -> str:
        try:
            valid_keys = valid_decision_keys(cls.workspace.value)
        except FileNotFoundError as exc:
            raise ValueError(str(exc)) from exc
        if v not in valid_keys:
            raise ValueError(
                f"'{v}' is not a valid decision_key for workspace '{cls.workspace.value}'. "
                f"Valid keys: {sorted(valid_keys)}"
            )
        return v


class FieldImpactResponse(BaseModel):
    """base_value/actual_value rather than "_pct" -- only Marketing's modifier-chain
    decisions are percentages; Finance/Product/Sales handlers compute plain values
    (ratios, dollar amounts, scores) with no modifier chain applied, so labeling
    every field "_pct" would misrepresent non-percentage results.
    """

    field: str
    base_value: float = Field(description="The value before this decision's impact.")
    actual_value: float = Field(description="The value after this decision's impact.")


class DecisionSubmissionResponse(BaseModel):
    """`POST .../{workspace}/decisions` -- one of the 6 legacy per-workspace routes
    (finance/marketing/product/sales/cx; operations and HR have no decision spec and are not
    routed, per `docs/10-implementation-gaps.md`)."""

    model_config = ConfigDict(json_schema_extra={"example": example("decision_submit_response")})

    decision_id: uuid.UUID
    workspace: Workspace
    decision_key: str
    business_impact: list[FieldImpactResponse]
    evidence_generated: int = Field(
        description="How many Evidence rows this decision produced for the (separate) cognitive-"
        "scoring pipeline. 0 is a legitimate, honest outcome when no evidence rule is registered "
        "for this decision_key yet -- not an error."
    )


_decision_log_examples = example("decision_log_list_response")


class DecisionLogEntry(QuarterScopedBase):
    """`GET .../{workspace}/decisions` -- every decision submitted so far in this workspace/quarter."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={"example": _decision_log_examples[0] if _decision_log_examples else {}},
    )

    workspace: Workspace
    decision_key: str
    title: str
    payload: dict[str, Any]
    status: DecisionStatus
    submitted_at: datetime | None

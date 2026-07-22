import uuid
from datetime import datetime
from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator

from app.config.rules import valid_decision_keys
from app.models.decision import DecisionStatus, Workspace
from app.schemas.base import QuarterScopedBase


class DecisionSubmitBase(BaseModel):
    """Base for per-workspace decision submissions. Subclasses set `workspace` and decide
    whether `payload` needs extra structural validation (see MarketingDecisionSubmit,
    SalesDecisionSubmit for the two payload-shape rules the source spec actually gives).
    """

    workspace: ClassVar[Workspace]

    decision_key: str
    payload: dict[str, Any] = Field(default_factory=dict)

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
    base_value: float
    actual_value: float


class DecisionSubmissionResponse(BaseModel):
    decision_id: uuid.UUID
    workspace: Workspace
    decision_key: str
    business_impact: list[FieldImpactResponse]
    evidence_generated: int


class DecisionLogEntry(QuarterScopedBase):
    workspace: Workspace
    decision_key: str
    title: str
    payload: dict[str, Any]
    status: DecisionStatus
    submitted_at: datetime | None

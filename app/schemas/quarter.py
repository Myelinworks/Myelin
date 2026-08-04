import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class _FromAttributes(BaseModel):
    """Base for every report sub-schema: constructed directly from the pure dataclasses
    `app.engines.report` returns (`Model.model_validate(dataclass_instance)`), never hand-mapped
    field by field -- one more place a field could silently go stale otherwise."""

    model_config = ConfigDict(from_attributes=True)


class MetricSchema(_FromAttributes):
    value: Decimal
    delta: Decimal | None = None


class CompanyOutcomeSchema(_FromAttributes):
    """Section A -- "what happened to the company." Never appears alongside a score value in the
    same object; see `QuarterReportResponse`."""

    units_sold: MetricSchema
    revenue_inr: MetricSchema
    cogs_inr: MetricSchema
    gross_profit_inr: MetricSchema
    net_cash_flow_inr: MetricSchema
    closing_cash_inr: MetricSchema
    cash_runway_quarters: MetricSchema | None = None
    cash_runway_gap_reason: str | None = None
    valuation_inr: MetricSchema | None = None
    valuation_gap_reason: str | None = None


class BindingConstraintSchema(_FromAttributes):
    """Section B -- which hard gate(s) bound this quarter, and how much demand it cost."""

    gate: str
    demand_lost: Decimal
    demand_lost_unit: str
    detail: str


class ModifierLineSchema(_FromAttributes):
    id: str
    points: Decimal
    fired: bool
    applied_points: Decimal
    detail: str


class ScoredCriterionSchema(_FromAttributes):
    id: str
    trait: str
    result: str
    points: Decimal | None = None
    detail: str


class UnscoredCriterionSchema(_FromAttributes):
    """Rendered honestly: a reason, never a zero, never hidden."""

    id: str
    trait: str
    reason: str


class DecisionQualitySchema(_FromAttributes):
    """Section C -- "how good were these decisions." `ceo_score`/`band` are the scoreable-portion,
    normalised score -- labelled as such, not the complete 21-criterion rubric."""

    ceo_score: Decimal
    band: str
    mechanical_points_available: Decimal
    unscored_points: Decimal
    modifiers: list[ModifierLineSchema]
    scored_criteria: list[ScoredCriterionSchema]
    unscored_criteria: list[UnscoredCriterionSchema]


class EvidenceObservationSchema(_FromAttributes):
    """Rendered as an observation, never a grade. `department` is `None` only for the one
    cross-quarter fact (`consistent_objective`) that spans more than one department."""

    department: str | None = None
    evidence_key: str
    value: Any
    detail: str
    weight: Decimal | None = None
    weight_status: str


class ScoreTrajectoryPointSchema(_FromAttributes):
    quarter_number: int
    ceo_score: Decimal
    band: str


class RunSummarySchema(_FromAttributes):
    """Only present on the terminal quarter of a COMPLETED or FAILED run. Just the aggregation of
    quarters that exist -- no Q4 endgame content (Momentum Score, tiers, term sheets; Phase 11)."""

    score_trajectory: list[ScoreTrajectoryPointSchema]
    final_valuation_inr: Decimal | None = None
    terminal_status: str


class QuarterReportResponse(_FromAttributes):
    """The Phase 9 student-facing report. Sections stay structurally separate on purpose: `outcome`
    answers "what happened to the company", `decision_quality` answers "how good were these
    decisions" -- built independently (see `engines/report.py`'s separability guarantee), so a
    student can never read this as "you made money, therefore you scored well".
    """

    company_id: uuid.UUID
    quarter_id: uuid.UUID
    quarter_number: int

    outcome: CompanyOutcomeSchema
    binding_constraints: list[BindingConstraintSchema]
    decision_quality: DecisionQualitySchema
    evidence: dict[str, list[EvidenceObservationSchema]]

    run_status: str
    survival_triggered_by: str | None = None
    survival_detail: str | None = None

    run_summary: RunSummarySchema | None = None


class LeaderboardEntry(BaseModel):
    company_id: uuid.UUID
    quarter_id: uuid.UUID
    quarter_number: int
    overall_score: float | None = None


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]

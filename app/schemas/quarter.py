import uuid
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.survival import RunStatus
from app.schemas._examples import example


class _FromAttributes(BaseModel):
    """Base for every report sub-schema: constructed directly from the pure dataclasses
    `app.engines.report` returns (`Model.model_validate(dataclass_instance)`), never hand-mapped
    field by field -- one more place a field could silently go stale otherwise."""

    model_config = ConfigDict(from_attributes=True)


class MetricSchema(_FromAttributes):
    """One outcome number plus its quarter-over-quarter change."""

    value: Decimal
    delta: Decimal | None = Field(
        default=None, description="Change from the prior quarter, or null when there is no prior quarter yet."
    )


class CompanyOutcomeSchema(_FromAttributes):
    """Section A -- "what happened to the company." Purely financial/operational; never appears
    alongside a score judgement in the same field -- see `QuarterReportResponse`'s docstring for
    why the two sections are kept structurally separate.
    """

    units_sold: MetricSchema
    revenue_inr: MetricSchema
    cogs_inr: MetricSchema = Field(description="Cost of goods sold, in INR.")
    gross_profit_inr: MetricSchema
    net_cash_flow_inr: MetricSchema
    closing_cash_inr: MetricSchema
    cash_runway_quarters: MetricSchema | None = Field(
        default=None, description="Closing cash / |net cash flow|. Null when the quarter didn't burn cash."
    )
    cash_runway_gap_reason: str | None = Field(
        default=None, description="Why `cash_runway_quarters` is null, when it is."
    )
    valuation_inr: MetricSchema | None = Field(
        default=None, description="Blended company valuation. Null when the seed doesn't supply "
        "the asset-based valuation inputs -- see `valuation_gap_reason`."
    )
    valuation_gap_reason: str | None = Field(default=None, description="Why `valuation_inr` is null, when it is.")


class BindingConstraintSchema(_FromAttributes):
    """Section B -- one entry per hard gate that actually bound this quarter (0-3 entries; more
    than one can bind at once). An empty list is a genuinely good outcome: nothing left demand on
    the table.
    """

    gate: str = Field(description='One of "sales_capacity" | "conversion_ceiling" | "available_to_sell".')
    demand_lost: Decimal = Field(description="How much demand this gate cost, in `demand_lost_unit`.")
    demand_lost_unit: str = Field(description='One of "leads" | "conversion_points" | "units".')
    detail: str = Field(description="Human-readable explanation of what bound and by how much.")


class ModifierLineSchema(_FromAttributes):
    """One named scoring modifier (e.g. `crisis_ignored`, `perfect_channel_match`) and whether it
    fired this quarter -- always present, `fired` tells you whether `applied_points` is nonzero."""

    id: str
    points: Decimal = Field(description="The modifier's configured point value if it fires.")
    fired: bool
    applied_points: Decimal = Field(description="`points` if `fired`, else 0.")
    detail: str = Field(description="Human-readable explanation of the numbers that decided whether it fired.")


class ScoredCriterionSchema(_FromAttributes):
    """One of the 6 MECHANICAL (formula-derived) rubric sub-criteria that actually scored this
    quarter."""

    id: str
    trait: str = Field(description="Which of the 7 CEO-score traits this criterion belongs to.")
    result: str = Field(
        description='"clearly_met" (full trait-weight share) / "partially_met" (half share) / '
        '"not_met" (zero) for this quarter\'s numbers.'
    )
    points: Decimal | None = None
    detail: str


class UnscoredCriterionSchema(_FromAttributes):
    """One of the 15 JUDGMENT sub-criteria the mechanical engine cannot evaluate. Rendered
    honestly: a reason, never a zero, never hidden -- a zero would read as a failure the student
    didn't earn."""

    id: str
    trait: str
    reason: str = Field(description="Why this criterion has no mechanical score (it needs human/LLM judgment).")


class DecisionQualitySchema(_FromAttributes):
    """Section C -- "how good were these decisions." Built from the score alone; no field here is
    derived from `outcome` -- a student can never read this report as "you made money, therefore
    you scored well". `ceo_score`/`band` are the scoreable-portion, normalised score -- labelled
    as such, not the complete 21-criterion rubric (only 6 are MECHANICAL today).
    """

    ceo_score: Decimal = Field(description="Normalised 0-100 score over the scoreable (MECHANICAL) portion only.")
    band: str = Field(description='e.g. "Weak" / "Competent" / "Strong" / "Exceptional" -- see docs/10-scoring-methodology.md.')
    mechanical_points_available: Decimal = Field(description="How many of the 100 points come from MECHANICAL criteria.")
    unscored_points: Decimal = Field(description="How many points belong to JUDGMENT criteria not yet scored.")
    modifiers: list[ModifierLineSchema]
    scored_criteria: list[ScoredCriterionSchema]
    unscored_criteria: list[UnscoredCriterionSchema]


class EvidenceObservationSchema(_FromAttributes):
    """One extracted fact for the (separate) cognitive-scoring pipeline. Rendered as an
    observation, never a grade -- evidence is never re-derived from `outcome`/`decision_quality`,
    and vice versa (CLAUDE.md: "Two pipelines stay independent")."""

    department: str | None = Field(
        default=None, description="Null only for the one cross-quarter fact that spans more than one department."
    )
    evidence_key: str
    value: Any = Field(description="The observed value -- type varies by evidence_key.")
    detail: str
    weight: Decimal | None = Field(default=None, description="Null when this evidence key has no stated weight yet.")
    weight_status: str = Field(description="Whether `weight` is a confirmed source value or a documented gap.")


class ScoreTrajectoryPointSchema(_FromAttributes):
    quarter_number: int
    ceo_score: Decimal
    band: str


class RunSummarySchema(_FromAttributes):
    """Only present on the terminal quarter of a COMPLETED or FAILED run. Just the aggregation of
    quarters that exist -- no Q4 endgame content (Momentum Score, tiers, term sheets; that's
    `RunStateResponse.endgame_preview`, populated separately)."""

    score_trajectory: list[ScoreTrajectoryPointSchema]
    final_valuation_inr: Decimal | None = None
    terminal_status: RunStatus = Field(description="Always FAILED or COMPLETED -- the two terminal statuses.")


class QuarterReportResponse(_FromAttributes):
    """`GET .../quarters/{quarter_id}/report` and the response of `POST .../lock` -- the
    student-facing report for one locked quarter. Sections stay structurally separate on purpose:
    `outcome` answers "what happened to the company", `decision_quality` answers "how good were
    these decisions" -- built independently, so a student can never read this as "you made money,
    therefore you scored well". See `docs/frontend-integration-guide.md`'s "Reading the two-part
    report" section for how to render each half.
    """

    model_config = ConfigDict(from_attributes=True, json_schema_extra={"example": example("quarter_report_q1")})

    company_id: uuid.UUID
    quarter_id: uuid.UUID
    quarter_number: int

    outcome: CompanyOutcomeSchema
    binding_constraints: list[BindingConstraintSchema]
    decision_quality: DecisionQualitySchema
    evidence: dict[str, list[EvidenceObservationSchema]] = Field(
        description='Cognitive-dimension category (e.g. "systems_thinking") -> the evidence facts '
        "observed for it this quarter. Populated automatically at lock time from the same 22-line "
        "allocations that produced `outcome` -- no separate submission is needed. The legacy "
        "per-workspace decision routes (see the guide) write their own, separate evidence rows "
        "that never appear here."
    )

    run_status: RunStatus
    survival_triggered_by: str | None = Field(
        default=None, description='Which survival condition fired (e.g. "cash_exhausted"), or null if none did.'
    )
    survival_detail: str | None = Field(default=None, description="The specific numbers that fired it, human-readable.")

    run_summary: RunSummarySchema | None = Field(
        default=None, description="Present only once `run_status` is terminal (FAILED or COMPLETED)."
    )


class LeaderboardEntry(BaseModel):
    """One locked quarter's score. `ceo_score`/`band` are the same two numbers
    `RunStateResponse.score_trajectory` and `DecisionQualitySchema` report -- the scoreable
    (MECHANICAL) portion only, not the full 21-criterion rubric.

    This deliberately does *not* carry `QuarterPerformance.overall_score`: that column belongs to
    the legacy per-decision cognitive pipeline (`services/quarter_engine.py`), which
    `run_quarter()` never invokes, so it is null for every quarter of every run the shipped
    22-line flow produces. Reporting it was reporting a permanent null as if it were a score.
    """

    company_id: uuid.UUID
    quarter_id: uuid.UUID
    quarter_number: int
    ceo_score: Decimal | None = Field(default=None, description="Null until that quarter has been locked.")
    band: str | None = Field(
        default=None, description='e.g. "Weak" / "Competent" / "Strong". Null until that quarter has been locked.'
    )


class LeaderboardResponse(BaseModel):
    """`GET .../leaderboard` -- reads persisted `QuarterPerformance` rollups; never live-aggregates."""

    model_config = ConfigDict(json_schema_extra={"example": example("leaderboard_response")})

    entries: list[LeaderboardEntry]


class QuarterReportPdfResponse(BaseModel):
    """`POST`/`GET .../report/pdf` -- the frontend renders the PDF itself (client-side, from the
    same report data this API already serves) and hands the finished bytes to `POST` for
    storage; this backend never generates the PDF, only stores and re-signs access to it in
    Supabase Storage's private `quarter-reports` bucket."""

    bucket: str
    path: str
    signed_url: str = Field(description="Expires -- re-fetch via GET rather than caching this.")
    expires_in: int


class SimulationReportPdfResponse(BaseModel):
    """`POST`/`GET .../simulation/report/pdf` -- same shape as the quarter variant, stored in
    the `simulation-reports` bucket under a user-scoped path."""

    bucket: str
    path: str
    signed_url: str = Field(description="Expires -- re-fetch via GET rather than caching this.")
    expires_in: int

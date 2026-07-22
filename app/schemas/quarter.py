import uuid
from datetime import datetime

from pydantic import BaseModel


class QuarterReportResponse(BaseModel):
    """Reads back the persisted QuarterPerformance row (+ counts) -- never recomputed on GET.
    quarter_engine.run_quarter is only invoked by the lock endpoint.
    """

    company_id: uuid.UUID
    quarter_id: uuid.UUID
    overall_score: float
    dimension_scores: dict[str, float]
    decisions_submitted: int
    evidence_records_generated: int
    generated_at: datetime


class LeaderboardEntry(BaseModel):
    company_id: uuid.UUID
    quarter_id: uuid.UUID
    quarter_number: int
    overall_score: float


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]

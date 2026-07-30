import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class QuarterReportResponse(BaseModel):
    """Reads back the persisted QuarterPerformance row (+ counts) -- never recomputed on GET.

    Two independent pipelines can each populate part of this row (see
    `models/quarter_performance.py`): `overall_score`/`dimension_scores` come from the legacy
    cognitive-scoring pipeline (`services/quarter_engine.py`), `units_sold` onward from the pure
    22-line engine (`services/quarter_run_service.py::run_quarter`, what `POST /lock` calls).
    Both sets are optional because locking a quarter only ever populates the second.
    """

    company_id: uuid.UUID
    quarter_id: uuid.UUID
    overall_score: float | None = None
    dimension_scores: dict[str, float] | None = None
    decisions_submitted: int
    evidence_records_generated: int
    generated_at: datetime

    # Pure-engine result, from QuarterPerformance.engine_result / result_hash.
    units_sold: Decimal | None = None
    revenue_inr: Decimal | None = None
    net_cash_flow_inr: Decimal | None = None
    closing_cash_inr: Decimal | None = None
    result_hash: str | None = None


class LeaderboardEntry(BaseModel):
    company_id: uuid.UUID
    quarter_id: uuid.UUID
    quarter_number: int
    overall_score: float | None = None


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]

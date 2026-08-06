from decimal import Decimal

from app.models.decision import Workspace
from app.schemas.base import QuarterScopedBase
from app.schemas.decision import DecisionSubmitBase


class CXDecisionSubmit(DecisionSubmitBase):
    """Legacy per-decision submission for the CX workspace -- see `DecisionSubmitBase`."""

    workspace = Workspace.CX


class CXStateResponse(QuarterScopedBase):
    """`GET .../cx/state` -- this workspace's own denormalised snapshot."""

    csat_score: Decimal
    churn_rate: Decimal
    support_tickets_resolved: int

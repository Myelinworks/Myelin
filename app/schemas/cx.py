from decimal import Decimal

from app.models.decision import Workspace
from app.schemas.base import QuarterScopedBase
from app.schemas.decision import DecisionSubmitBase


class CXDecisionSubmit(DecisionSubmitBase):
    workspace = Workspace.CX


class CXStateResponse(QuarterScopedBase):
    csat_score: Decimal
    churn_rate: Decimal
    support_tickets_resolved: int

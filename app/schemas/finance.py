from decimal import Decimal

from app.models.decision import Workspace
from app.schemas.base import QuarterScopedBase
from app.schemas.decision import DecisionSubmitBase


class FinanceDecisionSubmit(DecisionSubmitBase):
    workspace = Workspace.FINANCE


class FinanceStateResponse(QuarterScopedBase):
    cash_balance: Decimal
    revenue: Decimal
    expenses: Decimal
    burn_rate: Decimal
    runway_months: float | None

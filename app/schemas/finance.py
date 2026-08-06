from decimal import Decimal

from app.models.decision import Workspace
from app.schemas.base import QuarterScopedBase
from app.schemas.decision import DecisionSubmitBase


class FinanceDecisionSubmit(DecisionSubmitBase):
    """Legacy per-decision submission for the Finance workspace -- see `DecisionSubmitBase`."""

    workspace = Workspace.FINANCE


class FinanceStateResponse(QuarterScopedBase):
    """`GET .../finance/state` -- this workspace's own denormalised snapshot, distinct from the
    22-line `QuarterAllocationResponse`."""

    cash_balance: Decimal
    revenue: Decimal
    expenses: Decimal
    burn_rate: Decimal
    runway_months: float | None

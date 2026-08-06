from decimal import Decimal
from typing import ClassVar

from pydantic import model_validator

from app.models.decision import Workspace
from app.schemas.base import QuarterScopedBase
from app.schemas.decision import DecisionSubmitBase


class MarketingDecisionSubmit(DecisionSubmitBase):
    """Legacy per-decision submission for the Marketing workspace -- see `DecisionSubmitBase`."""

    workspace = Workspace.MARKETING

    # Rs 0.01: a paisa is the smallest real currency unit here, so this absorbs a rupee split's
    # legitimate rounding remainder (e.g. 33333.33/33333.33/33333.34 against 100000.0) without
    # accepting a genuinely wrong sum. ClassVar, not a model field -- Pydantic would otherwise
    # try to turn a bare leading-underscore attribute into a private instance attribute.
    _BUDGET_SUM_TOLERANCE: ClassVar[Decimal] = Decimal("0.01")

    @model_validator(mode="after")
    def _validate_budget_allocation_payload(self) -> "MarketingDecisionSubmit":
        """Only marketing_budget_allocation has a specified payload shape (spend split
        across channels, per the evidence_engine worked example) -- other marketing
        decision_keys aren't required to match it.
        """
        if self.decision_key != "marketing_budget_allocation":
            return self
        channel_spend = self.payload.get("channel_spend")
        total_budget = self.payload.get("total_budget")
        if not isinstance(channel_spend, dict) or total_budget is None:
            raise ValueError(
                "marketing_budget_allocation payload must include 'channel_spend' (dict) and 'total_budget'"
            )
        # Decimal(str(x)), not Decimal(x): payload numbers arrive as float (dict[str, Any] does
        # not coerce to Decimal), and Decimal(float) preserves the float's binary imprecision
        # instead of the decimal value it was written as.
        spent = sum((Decimal(str(v)) for v in channel_spend.values()), start=Decimal(0))
        total = Decimal(str(total_budget))
        if abs(spent - total) > self._BUDGET_SUM_TOLERANCE:
            raise ValueError(
                f"channel_spend sums to {spent}, which does not match total_budget {total} "
                f"(tolerance {self._BUDGET_SUM_TOLERANCE})"
            )
        return self


class MarketingStateResponse(QuarterScopedBase):
    """`GET .../marketing/state` -- this workspace's own denormalised snapshot."""

    marketing_spend: Decimal
    leads_generated: int
    customer_acquisition_cost: Decimal
    brand_awareness_score: float

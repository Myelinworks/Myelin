from decimal import Decimal

from pydantic import model_validator

from app.models.decision import Workspace
from app.schemas.base import QuarterScopedBase
from app.schemas.decision import DecisionSubmitBase


class MarketingDecisionSubmit(DecisionSubmitBase):
    workspace = Workspace.MARKETING

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
        spent = sum(channel_spend.values())
        if spent != total_budget:
            raise ValueError(f"channel_spend sums to {spent}, which does not match total_budget {total_budget}")
        return self


class MarketingStateResponse(QuarterScopedBase):
    marketing_spend: Decimal
    leads_generated: int
    customer_acquisition_cost: Decimal
    brand_awareness_score: float

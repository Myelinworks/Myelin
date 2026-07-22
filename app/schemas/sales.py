from decimal import Decimal

from pydantic import model_validator

from app.config.rules import load_rules
from app.models.decision import Workspace
from app.schemas.base import QuarterScopedBase
from app.schemas.decision import DecisionSubmitBase


class SalesDecisionSubmit(DecisionSubmitBase):
    workspace = Workspace.SALES

    @model_validator(mode="after")
    def _validate_negotiation_payload(self) -> "SalesDecisionSubmit":
        """Only SAL-011 (Negotiation) has a specified payload shape: keys must be a subset
        of sales_rules.json's negotiation_engine.negotiable_variables.
        """
        if self.decision_key != "SAL-011":
            return self
        negotiable_variables = set(load_rules("sales")["negotiation_engine"]["negotiable_variables"])
        invalid_keys = set(self.payload.keys()) - negotiable_variables
        if invalid_keys:
            raise ValueError(
                f"Negotiation payload keys {sorted(invalid_keys)} are not in sales_rules.json's "
                f"negotiable_variables: {sorted(negotiable_variables)}"
            )
        return self


class SalesStateResponse(QuarterScopedBase):
    pipeline_value: Decimal
    deals_closed: int
    quota_attainment_pct: Decimal

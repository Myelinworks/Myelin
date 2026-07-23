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
        """Only SAL-011 (Negotiation) has a specified payload shape, split into two
        namespaces that are genuinely different concerns:

        - `terms`: the deal terms being negotiated, keys validated against
          sales_rules.json's negotiation_engine.negotiable_variables (e.g. price, quantity).
        - `negotiation_inputs`: the scoring context negotiation_score/acceptance_probability
          need (price_competitiveness, relationship_score, risk, ...) -- not deal terms, and
          not something negotiable_variables covers. Only checked for presence/shape here;
          decision_engine validates its actual required keys.
        """
        if self.decision_key != "SAL-011":
            return self

        terms = self.payload.get("terms")
        if not isinstance(terms, dict):
            raise ValueError("SAL-011 payload must include a 'terms' object")
        negotiable_variables = set(load_rules("sales")["negotiation_engine"]["negotiable_variables"])
        invalid_keys = set(terms.keys()) - negotiable_variables
        if invalid_keys:
            raise ValueError(
                f"SAL-011 'terms' keys {sorted(invalid_keys)} are not in sales_rules.json's "
                f"negotiable_variables: {sorted(negotiable_variables)}"
            )

        if not isinstance(self.payload.get("negotiation_inputs"), dict):
            raise ValueError("SAL-011 payload must include a 'negotiation_inputs' object")

        return self


class SalesStateResponse(QuarterScopedBase):
    pipeline_value: Decimal
    deals_closed: int
    quota_attainment_pct: Decimal

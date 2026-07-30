"""MarketingDecisionSubmit's channel_spend/total_budget validator -- previously compared raw
JSON floats with `!=`, which rejects legitimate rounding remainders in a rupee split.
"""

import pytest
from pydantic import ValidationError

from app.schemas.marketing import MarketingDecisionSubmit


def _submit(channel_spend: dict, total_budget: float) -> MarketingDecisionSubmit:
    return MarketingDecisionSubmit(
        decision_key="marketing_budget_allocation",
        payload={"channel_spend": channel_spend, "total_budget": total_budget},
    )


def test_exact_split_validates():
    _submit({"a": 50000.0, "b": 50000.0}, 100000.0)


def test_rounding_remainder_split_validates():
    """A three-way split of Rs 1,00,000 cannot divide evenly to the paisa -- the classic float
    != failure mode this fix exists for."""
    _submit({"a": 33333.33, "b": 33333.33, "c": 33333.34}, 100000.0)


def test_genuinely_wrong_sum_still_rejects():
    with pytest.raises(ValidationError, match="does not match total_budget"):
        _submit({"a": 40000.0, "b": 40000.0}, 100000.0)


def test_sum_outside_tolerance_by_a_few_paisa_rejects():
    with pytest.raises(ValidationError, match="does not match total_budget"):
        _submit({"a": 50000.0, "b": 49999.90}, 100000.0)

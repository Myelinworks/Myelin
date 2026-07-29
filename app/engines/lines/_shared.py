"""Shared arithmetic for the 22 department spend lines.

Units convention (`docs/00-formula-index.md`): `x` = spend on that line in Rs lakhs. Callers convert
rupees to lakhs once at the input boundary; nothing below converts, with the single documented
exception of Referral, whose cost-per-lead is inherently rupee-denominated.
"""

from decimal import Decimal
from typing import TypeVar

RUPEES_PER_LAKH = Decimal(100_000)

T = TypeVar("T")


def _reject_negative(spend_lakhs: Decimal) -> None:
    if spend_lakhs < 0:
        raise ValueError(f"spend cannot be negative (got {spend_lakhs} lakhs)")


def diminishing(constant: Decimal, spend_lakhs: Decimal, exponent: Decimal) -> Decimal:
    """`constant * x^exponent`.

    The shape of every spend line except Referral (a hard cap, no curve) and Reps capacity
    (linear). Every exponent is below 1.0 because the first rupee reaches the cheapest, most
    responsive audience and each additional rupee reaches a slightly less responsive one.
    """
    _reject_negative(spend_lakhs)
    if spend_lakhs == 0:
        return Decimal(0)
    return constant * (spend_lakhs**exponent)


def linear(constant: Decimal, spend_lakhs: Decimal) -> Decimal:
    """`constant * x`. Only Sales Reps capacity uses this -- twice the budget buys close to
    twice the bandwidth."""
    _reject_negative(spend_lakhs)
    return constant * spend_lakhs


def require(value: T | None, field: str, company: str) -> T:
    """Seed values are `None` when `docs/` never states them for that company.

    Failing loudly here is the point: silently substituting another company's constant is exactly
    the P0 baseline conflict in `docs/10-implementation-gaps.md`.
    """
    if value is None:
        raise NotImplementedError(
            f"'{field}' is not specified in the source documents for company '{company}'; "
            f"it cannot be defaulted or borrowed from another seed"
        )
    return value

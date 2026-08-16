"""Shared arithmetic for the Nadi Wear four-quarter engine.

Units convention, same as the 22-line engine: `x` = spend on that line in Rs lakhs. Callers
convert rupees to lakhs once at the input boundary; nothing below converts, with the single
documented exception of Referral, whose cost-per-lead is inherently rupee-denominated.

Everything is `Decimal`. The reference implementation this is ported from ran on IEEE doubles,
so a handful of values differ in the far decimal places; none of the gates, thresholds or
bands are sensitive at that magnitude, and using Decimal here keeps the money arithmetic
consistent with the rest of `app/engines`.
"""

from decimal import Decimal

RUPEES_PER_LAKH = Decimal(100_000)

ZERO = Decimal(0)
ONE = Decimal(1)
HALF = Decimal("0.5")


def dec(value: object) -> Decimal:
    """Coerce anything to a finite Decimal, defaulting to 0.

    Allocation values arrive from JSON as strings or numbers, and an empty text field is a
    legitimate "nothing committed here" rather than an error.
    """
    if isinstance(value, Decimal):
        return value if value.is_finite() else ZERO
    if value is None or value == "":
        return ZERO
    try:
        out = Decimal(str(value))
    except (ArithmeticError, ValueError, TypeError):
        return ZERO
    return out if out.is_finite() else ZERO


def pw(value: object, exponent: Decimal | str) -> Decimal:
    """`max(0, x) ** exponent` -- the diminishing-returns curve every spend line runs on.

    Every exponent is below 1.0: the first rupee on a line reaches the cheapest, most
    responsive audience and each additional rupee reaches a slightly less responsive one.
    """
    base = dec(value)
    if base <= 0:
        return ZERO
    return base ** Decimal(str(exponent))


def clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return min(high, max(low, value))


def pct_of(part: Decimal, whole: Decimal) -> Decimal:
    """`part / whole`, or 0 when there is no whole -- avoids a guard at every call site."""
    return part / whole if whole else ZERO

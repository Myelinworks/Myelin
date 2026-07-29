"""Formulas the source documents state but do not specify well enough to implement.

Each is flagged ⚠️ in `docs/00-formula-index.md` with the full reasoning in
`docs/10-implementation-gaps.md`. Per `CLAUDE.md`: if a coefficient is not in `docs/`, it does not
exist -- these raise with the specific reason rather than being quietly approximated.

They live here rather than in `app/engines/lines/` so that module keeps a simple invariant:
everything under `lines/` is a spend line that works.
"""

from decimal import Decimal
from typing import Never

NEGOTIATION_REASON = (
    "Negotiation Score has no specified weights or scales; Acceptance Probability has no "
    "normalisation. Six differently-scaled quantities are summed with no weights and the result "
    "multiplied by two further unscaled factors, so it cannot produce a 0-1 probability "
    "(docs/10-implementation-gaps.md, P2)"
)

CX_REASON = (
    "CX engine formulas are not specified in the source documents. All 12 decisions (CX-001 to "
    "CX-012) name an engine -- Retention, Referral, Loyalty, Trust, Reputation, Adoption, "
    "Engagement, Customer Value -- none of which is defined anywhere. The CX ratio definitions "
    "compute a KPI from counts, but nothing specifies how a decision changes those counts "
    "(docs/10-implementation-gaps.md, P1)"
)

MOMENTUM_REASON = (
    "Momentum Score names seven inputs (Brand, Innovation, Quality, Supplier Reliability, Repeat "
    "Purchase Rate, Cash Balance, Net Cash Flow trend) but gives no weights, no normalisation and "
    "no tier cut-offs, so tier assignment and the Q4 endgame cannot be derived "
    "(docs/10-implementation-gaps.md, P1)"
)


def negotiation_score(**_inputs: Decimal) -> Never:
    raise NotImplementedError(NEGOTIATION_REASON)


def acceptance_probability(**_inputs: Decimal) -> Never:
    raise NotImplementedError(NEGOTIATION_REASON)


def cx_decision_impact(decision_key: str, **_inputs: Decimal) -> Never:
    raise NotImplementedError(f"{decision_key}: {CX_REASON}")


def momentum_score(**_inputs: Decimal) -> Never:
    raise NotImplementedError(MOMENTUM_REASON)

"""The Q4 endgame -- Phase 11 (`docs/16-quarter-4-endgame.md` + `docs/17-designer-resolutions.md`).

Pure: no I/O, no DB session, no clock, no RNG -- same discipline as every other `engines/` module.

`docs/16` names a 7-input weighted Momentum Score and marks six items "blocked -- not specified".
`docs/17` resolves five of them with a narrower, 2-input formula; the full 7-input composite stays
genuinely unbuilt (`app/engines/gaps.py`'s `momentum_score()` stub documents that gap -- this
module's `momentum_score` is a *different*, validated function, not a replacement for that stub).

Every formula below is independently confirmed against `docs/17`'s own worked example, which turns
out to chain exactly through Phase 10's already-validated Scenario-C-expert Q3 fixture (1,437
units, Rs 1,28,94,52,430,000... i.e. Rs 12,89,45,243 valuation, chained from Q1's 562 units):

    momentum   = (1437/562)^0.5 - 1                    = 0.5990  (docs/17: "59.9%")
    covenant   = 1437 * (1 + 1.3*0.5990)                = 2556.5  (docs/17: "2,556 units")
    true value = 12894524.3 * 1.5990                    ~= 20618902  (docs/17: "Rs 20,61,89,028")

The one genuine remaining gap: Path B's *offer* has no stated formula except for one term sheet
(Thriving tier's "Acquisition Trap", back-solved to a single ratio from the same worked example --
`Rs 14,82,56,189 / Rs 20,61,89,028 ~= 0.7190`, see `EndgameConfig.acquisition_trap_offer_ratio`).
No ratio exists anywhere for the other two Path-B-eligible term sheets (Fair-Value Acquisition,
Fire-Sale) -- `acquisition_offer_inr` raises rather than invent one.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.config.schema import EndgameConfig, TierTermSheetConfig
from app.engines.quarter import QuarterResult
from app.engines.survival import RunStatus, SurvivalOutcome

HALF = Decimal("0.5")
ONE = Decimal(1)


class Tier(StrEnum):
    """The three Momentum tiers (`docs/17`'s naming -- Thriving/Stable/Distressed, *not* the
    Strong/Flat/Weak naming `docs/16` uses)."""

    THRIVING = "thriving"
    STABLE = "stable"
    DISTRESSED = "distressed"


@dataclass(frozen=True)
class TierOutcome:
    tier: Tier
    detail: str


def momentum_score(q1_units_sold: Decimal, q3_units_sold: Decimal) -> Decimal:
    """docs/17 P1: `(Q3 Units Sold / Q1 Units Sold)^0.5 - 1` -- the validated, narrower 2-input
    formula. Confirmed exactly against the worked example (562 -> 1,437 gives 0.5990, i.e. "59.9%")."""
    return (q3_units_sold / q1_units_sold) ** HALF - ONE


def _valuation_grew(prior: QuarterResult, current: QuarterResult) -> bool:
    if prior.valuation.blended_inr is None or current.valuation.blended_inr is None:
        raise NotImplementedError(
            "Thriving-tier valuation-growth check needs a blended valuation for both quarters -- "
            "at least one is None (this seed doesn't supply the asset-based valuation inputs, so "
            "compute_quarter never produced a blended figure to compare)"
        )
    return current.valuation.blended_inr > prior.valuation.blended_inr


def assign_tier(
    q1_result: QuarterResult,
    q2_result: QuarterResult,
    q3_result: QuarterResult,
    survival_outcome: SurvivalOutcome,
) -> TierOutcome:
    """docs/17 P1's Tier Assignment. Distressed reuses `evaluate_survival`'s own DISTRESSED
    definition unchanged -- computed once, over the whole run, by `engines/survival.py`; never
    reimplemented here (`docs/19-work-split.md`: "Reuse it. Don't reimplement it."). Thriving is
    new: `Q3 NCF > 0 AND valuation grew in both Q2 and Q3`. Everything else is Stable.
    """
    if survival_outcome.status == RunStatus.DISTRESSED:
        return TierOutcome(Tier.DISTRESSED, survival_outcome.detail or "distressed")

    thriving = (
        q3_result.net_cash_flow_inr > 0
        and _valuation_grew(q1_result, q2_result)
        and _valuation_grew(q2_result, q3_result)
    )
    if thriving:
        return TierOutcome(Tier.THRIVING, "Q3 net cash flow positive and valuation grew in both Q2 and Q3")
    return TierOutcome(Tier.STABLE, "did not clear the Thriving bar; not Distressed either")


def term_sheet_menu(tier: Tier, config: EndgameConfig) -> TierTermSheetConfig:
    """The three named term sheets offered for this tier (docs/17 line 63) -- names only, no
    formula; Path A/B's actual numbers come from `covenant_units`/`true_continuation_value_inr`
    below, which don't vary by term-sheet name."""
    return {Tier.THRIVING: config.thriving, Tier.STABLE: config.stable, Tier.DISTRESSED: config.distressed}[tier]


def covenant_units(prior_units_sold: Decimal, momentum: Decimal, config: EndgameConfig) -> Decimal:
    """docs/17: `Covenant = Prior Units * (1 + 1.3*Momentum Score)`. "Prior Units" is Q3's own
    `units_sold` -- confirmed via the worked example (1,437 units -> 2,556-unit covenant at 59.9%
    momentum)."""
    return prior_units_sold * (ONE + config.covenant_momentum_multiplier * momentum)


def true_continuation_value_inr(current_valuation_inr: Decimal, momentum: Decimal) -> Decimal:
    """docs/17: `True Continuation Value = Current Valuation * (1 + Momentum Score)`. "Current
    Valuation" is Q3's own blended valuation -- confirmed via the worked example (Rs 12,89,45,243
    -> ~Rs 20,61,89,028 true continuation value at 59.9% momentum)."""
    return current_valuation_inr * (ONE + momentum)


def acquisition_offer_inr(
    term_sheet_name: str, tier: Tier, true_continuation_value: Decimal, config: EndgameConfig
) -> Decimal:
    """The only Path B offer with a source-stated formula is the Thriving tier's "Acquisition
    Trap" (a single back-solved ratio, see `EndgameConfig.acquisition_trap_offer_ratio`). Raises
    for every other term sheet rather than invent a ratio no source states.
    """
    if tier == Tier.THRIVING and term_sheet_name == config.thriving.path_b_name:
        return true_continuation_value * config.acquisition_trap_offer_ratio
    raise NotImplementedError(
        f"no acquisition-offer formula exists for term sheet {term_sheet_name!r} (tier "
        f"{tier.value!r}) -- only the Thriving tier's {config.thriving.path_b_name!r} has a "
        f"source-stated ratio (docs/17-designer-resolutions.md's own worked example); "
        f"{config.stable.path_b_name!r} and {config.distressed.path_b_name!r} have no ratio "
        f"stated anywhere"
    )

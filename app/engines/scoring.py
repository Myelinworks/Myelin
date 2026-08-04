"""`score_quarter` -- the CEO evaluation matrix (`docs/10-scoring-methodology.md`).

Pure: no I/O, no DB session, no clock, no RNG. Same pattern as `engines/survival.py`: config
declares *which* checks are active, a predicate keyed by `id` decides them, and an `id` with no
registered predicate is a hard error rather than a silently skipped check.

The rubric's two halves are structurally different and stay that way in code:

- `MECHANICAL` sub-criteria and all 8 standard modifiers are decidable from `QuarterResult` /
  `QuarterAllocations` alone, and are checked in full below.
- `JUDGMENT` sub-criteria ask about something no input carries -- a *stated* thesis, whether the
  student raised an issue unprompted, what evidence existed "at the time" of a decision. These
  come back `UNSCORED` and are held out of both the numerator and the denominator of their
  trait's score. Never inferred from spend: a plausible-looking proxy for "did they own the
  trade-off" is exactly the kind of invented number this project refuses to ship (CLAUDE.md).

`score_quarter`'s signature adds one parameter beyond the three data-bearing ones the phase spec
names (`result`, `prior_result`, `allocations`): `prior_allocations`. The compounding-asset-cut
modifier is a quarter-over-quarter comparison of *investment*, and the only fair way to compare
investment is in the same unit spend was made in (Rs lakhs). `QuarterResult` doesn't carry the
allocations that produced it -- only derived quantities (leads, scores) that are non-linear,
diminishing-returns functions of spend, so recovering a comparable spend figure from `prior_result`
alone would mean either reinventing those curves here (this module has no `SimulationProfile` to
do that correctly with) or comparing apples to oranges. `prior_allocations` is `None` in Q1 and
whenever the caller has no prior allocation row to hand it, exactly like `prior_result`.
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Callable

from app.config.schema import ScoringConfig, ScoringCriterion, ScoringModifier
from app.engines.quarter import QuarterResult
from app.engines.state import QuarterAllocations

ZERO = Decimal(0)
THIRD = Decimal(1) / Decimal(3)


class CriterionKind(StrEnum):
    MECHANICAL = "MECHANICAL"
    JUDGMENT = "JUDGMENT"


class CriterionResult(StrEnum):
    CLEARLY_MET = "clearly_met"
    PARTIALLY_MET = "partially_met"
    NOT_MET = "not_met"
    UNSCORED = "unscored"


# 1/3 of trait weight for "clearly met", 1/6 (half of a third) for "partially met", per
# docs/10-scoring-methodology.md's scoring table.
_FRACTION_OF_THIRD: dict[CriterionResult, Decimal] = {
    CriterionResult.CLEARLY_MET: Decimal(1),
    CriterionResult.PARTIALLY_MET: Decimal("0.5"),
    CriterionResult.NOT_MET: Decimal(0),
}


@dataclass(frozen=True)
class CriterionScore:
    """One sub-criterion's outcome. `points` is `None` exactly when `result` is `UNSCORED`."""

    id: str
    trait: str
    kind: CriterionKind
    result: CriterionResult
    detail: str
    points: Decimal | None


@dataclass(frozen=True)
class TraitScore:
    """`points_earned` is out of `weight_scored`, not `weight` -- `weight_scored` is `weight` with
    every UNSCORED sub-criterion's third held out, so a trait with UNSCORED criteria still reports
    a max-achievable ceiling a caller can check `points_earned` against."""

    trait: str
    weight: Decimal
    weight_scored: Decimal
    points_earned: Decimal
    criteria: tuple[CriterionScore, ...]


@dataclass(frozen=True)
class ModifierOutcome:
    """`points` is the configured value regardless of whether it fired; `applied_points` is
    `points` if `fired` else zero -- keeping both means a caller can show every modifier that was
    *checked*, not just the ones that hit."""

    id: str
    points: Decimal
    fired: bool
    applied_points: Decimal
    detail: str


@dataclass(frozen=True)
class QuarterScore:
    traits: tuple[TraitScore, ...]
    modifiers: tuple[ModifierOutcome, ...]

    # Sum of weight_scored / points_earned across all traits -- the trait layer's ceiling and
    # actual total before modifiers, and how far short of 100 that ceiling falls.
    mechanical_points_available: Decimal
    unscored_points: Decimal
    trait_points_earned: Decimal
    modifier_points: Decimal

    # Sum(trait points) + Sum(modifiers), uncapped, against the true 100-point trait scale --
    # held-out weight depresses this even for a perfect quarter.
    raw_score: Decimal
    # Trait points rescaled to the 100 that were actually scoreable, then modifiers added on top.
    # Bands are read off this one so held-out weight (Leadership, today) doesn't silently drag
    # every band down.
    normalised_score: Decimal
    band: str


def _bound_signals(result: QuarterResult) -> tuple[bool, bool, bool]:
    return result.capacity_bound, result.ceiling_bound, result.supply_bound


# ---- MECHANICAL sub-criterion checks -----------------------------------------------------------


def _systems_thinking_2_coordination(
    result: QuarterResult, _prior: QuarterResult | None, _alloc: QuarterAllocations, rubric: ScoringConfig
) -> tuple[CriterionResult, str]:
    band = rubric.thresholds.coordination_ratio

    def _within_band(numerator: Decimal, denominator: Decimal) -> bool | None:
        if denominator == 0:
            return None
        ratio = numerator / denominator
        return (Decimal(1) / band) <= ratio <= band

    leads_ok = _within_band(result.effective_leads, result.effective_sales_capacity)
    supply_ok = _within_band(result.total_units_demanded, result.available_to_sell)
    hits = sum(1 for ok in (leads_ok, supply_ok) if ok)

    detail = (
        f"effective_leads/effective_sales_capacity={result.effective_leads}/{result.effective_sales_capacity}, "
        f"total_units_demanded/available_to_sell={result.total_units_demanded}/{result.available_to_sell}, "
        f"within {band}x band: leads={leads_ok}, supply={supply_ok}"
    )
    if hits == 2:
        return CriterionResult.CLEARLY_MET, detail
    if hits == 1:
        return CriterionResult.PARTIALLY_MET, detail
    return CriterionResult.NOT_MET, detail


def _systems_thinking_3_no_unaddressed_bottleneck(
    result: QuarterResult, _prior: QuarterResult | None, _alloc: QuarterAllocations, _rubric: ScoringConfig
) -> tuple[CriterionResult, str]:
    capacity_bound, ceiling_bound, supply_bound = _bound_signals(result)
    binding = sum((capacity_bound, ceiling_bound, supply_bound))
    detail = f"capacity_bound={capacity_bound}, ceiling_bound={ceiling_bound}, supply_bound={supply_bound}"
    if binding <= 1:
        return CriterionResult.CLEARLY_MET, detail
    if binding == 2:
        return CriterionResult.PARTIALLY_MET, detail
    return CriterionResult.NOT_MET, detail


def _risk_management_1_margin(
    result: QuarterResult, _prior: QuarterResult | None, _alloc: QuarterAllocations, _rubric: ScoringConfig
) -> tuple[CriterionResult, str]:
    margin = result.discretionary_ceiling_inr - result.total_discretionary_inr
    detail = f"margin = discretionary_ceiling_inr - total_discretionary_inr = Rs {margin:,.2f}"
    if margin > 0:
        return CriterionResult.CLEARLY_MET, detail
    if margin == 0:
        return CriterionResult.PARTIALLY_MET, detail
    return CriterionResult.NOT_MET, detail


def _capital_allocation_2_not_overfunded(
    result: QuarterResult, _prior: QuarterResult | None, _alloc: QuarterAllocations, _rubric: ScoringConfig
) -> tuple[CriterionResult, str]:
    referral_overspent = result.referral_wasted_spend_inr > 0
    marketing_overfunded = result.capacity_bound
    hits = sum((referral_overspent, marketing_overfunded))
    detail = f"referral_wasted_spend_inr={result.referral_wasted_spend_inr}, capacity_bound={result.capacity_bound}"
    if hits == 0:
        return CriterionResult.CLEARLY_MET, detail
    if hits == 1:
        return CriterionResult.PARTIALLY_MET, detail
    return CriterionResult.NOT_MET, detail


def _capital_allocation_3_not_underfunded(
    result: QuarterResult, _prior: QuarterResult | None, _alloc: QuarterAllocations, _rubric: ScoringConfig
) -> tuple[CriterionResult, str]:
    capacity_bound, ceiling_bound, supply_bound = _bound_signals(result)
    hits = sum((capacity_bound, ceiling_bound, supply_bound))
    detail = f"capacity_bound={capacity_bound}, ceiling_bound={ceiling_bound}, supply_bound={supply_bound}"
    if hits == 0:
        return CriterionResult.CLEARLY_MET, detail
    if hits == 1:
        return CriterionResult.PARTIALLY_MET, detail
    return CriterionResult.NOT_MET, detail


def _long_term_thinking_1_compounding_investment(
    _result: QuarterResult, _prior: QuarterResult | None, allocations: QuarterAllocations, _rubric: ScoringConfig
) -> tuple[CriterionResult, str]:
    compounding_spend = (
        allocations.meta_ads
        + allocations.social_influencer
        + allocations.events_pr
        + allocations.content_seo
        + allocations.prelaunch_buzz
        + allocations.innovation
    )
    detail = f"compounding-line spend this quarter = {compounding_spend} lakhs"
    return (
        (CriterionResult.CLEARLY_MET, detail)
        if compounding_spend > 0
        else (CriterionResult.NOT_MET, detail)
    )


_CRITERION_PREDICATES: dict[
    str,
    Callable[
        [QuarterResult, QuarterResult | None, QuarterAllocations, ScoringConfig], tuple[CriterionResult, str]
    ],
] = {
    "systems_thinking_2": _systems_thinking_2_coordination,
    "systems_thinking_3": _systems_thinking_3_no_unaddressed_bottleneck,
    "risk_management_1": _risk_management_1_margin,
    "capital_allocation_2": _capital_allocation_2_not_overfunded,
    "capital_allocation_3": _capital_allocation_3_not_underfunded,
    "long_term_thinking_1": _long_term_thinking_1_compounding_investment,
}


# ---- Standard modifiers ---------------------------------------------------------------------


def _profitability_achieved(
    result: QuarterResult, _prior: QuarterResult | None, _alloc, _prior_alloc, _rubric: ScoringConfig
) -> tuple[bool, str]:
    return result.net_cash_flow_inr > 0, f"net_cash_flow_inr = Rs {result.net_cash_flow_inr:,.2f}"


def _perfect_channel_match(
    result: QuarterResult, _prior: QuarterResult | None, _alloc, _prior_alloc, _rubric: ScoringConfig
) -> tuple[bool, str]:
    referral_leads = result.channel_leads.get("referral", ZERO)
    hit_cap = referral_leads == result.referral_lead_cap
    no_overspend = result.referral_wasted_spend_inr == 0
    detail = (
        f"referral leads={referral_leads}, referral_lead_cap={result.referral_lead_cap}, "
        f"referral_wasted_spend_inr={result.referral_wasted_spend_inr}"
    )
    return (hit_cap and no_overspend), detail


def _zero_capacity_waste(
    result: QuarterResult, _prior: QuarterResult | None, _alloc, _prior_alloc, rubric: ScoringConfig
) -> tuple[bool, str]:
    gap = abs(result.effective_leads - result.leads_used)
    detail = f"effective_leads={result.effective_leads}, leads_used={result.leads_used}, gap={gap}"
    return gap <= rubric.thresholds.capacity_waste_leads, detail


def _zero_supply_waste(
    result: QuarterResult, _prior: QuarterResult | None, _alloc, _prior_alloc, rubric: ScoringConfig
) -> tuple[bool, str]:
    gap = result.available_to_sell - result.units_sold
    detail = f"available_to_sell - units_sold = {gap} (threshold {rubric.thresholds.supply_waste_units})"
    return gap <= rubric.thresholds.supply_waste_units, detail


def _compounding_line_totals(allocations: QuarterAllocations) -> dict[str, Decimal]:
    return {
        "brand": allocations.meta_ads + allocations.social_influencer + allocations.events_pr,
        "seo": allocations.content_seo,
        "buzz": allocations.prelaunch_buzz,
        "innovation": allocations.innovation,
    }


def _compounding_asset_cut(
    _result: QuarterResult,
    _prior: QuarterResult | None,
    allocations: QuarterAllocations,
    prior_allocations: QuarterAllocations | None,
    rubric: ScoringConfig,
) -> tuple[bool, str]:
    if prior_allocations is None:
        return False, "no prior_allocations available -- nothing to compare against (e.g. Q1)"

    current = _compounding_line_totals(allocations)
    prior = _compounding_line_totals(prior_allocations)
    cut_lines = []
    for line, prior_spend in prior.items():
        if prior_spend <= 0:
            continue
        ratio = current[line] / prior_spend
        if ratio < rubric.thresholds.compounding_cut_ratio:
            cut_lines.append(f"{line} {current[line]}/{prior_spend}={ratio:.2f}")

    detail = (
        f"lines below {rubric.thresholds.compounding_cut_ratio}x prior spend: {', '.join(cut_lines) or 'none'}"
    )
    return bool(cut_lines), detail


def _ceiling_undershot(
    result: QuarterResult, _prior: QuarterResult | None, _alloc, _prior_alloc, rubric: ScoringConfig
) -> tuple[bool, str]:
    gap = result.raw_conversion_pct - result.conversion_ceiling_pct
    detail = f"raw_conversion_pct - conversion_ceiling_pct = {gap} pts (threshold {rubric.thresholds.ceiling_undershoot_points})"
    return gap > rubric.thresholds.ceiling_undershoot_points, detail


def _cash_buffer_breached(
    result: QuarterResult, _prior: QuarterResult | None, _alloc, _prior_alloc, _rubric: ScoringConfig
) -> tuple[bool, str]:
    return result.spent_into_buffer, f"buffer_overspend_inr = Rs {result.buffer_overspend_inr:,.2f}"


def _debt_without_justification(
    _result: QuarterResult, _prior: QuarterResult | None, _alloc, _prior_alloc, _rubric: ScoringConfig
) -> tuple[bool, str]:
    return False, "no debt/loan mechanic exists in the 22-line chain -- this modifier can never fire today"


_MODIFIER_PREDICATES: dict[
    str,
    Callable[
        [QuarterResult, QuarterResult | None, QuarterAllocations, QuarterAllocations | None, ScoringConfig],
        tuple[bool, str],
    ],
] = {
    "profitability_achieved": _profitability_achieved,
    "perfect_channel_match": _perfect_channel_match,
    "zero_capacity_waste": _zero_capacity_waste,
    "zero_supply_waste": _zero_supply_waste,
    "compounding_asset_cut": _compounding_asset_cut,
    "ceiling_undershot": _ceiling_undershot,
    "cash_buffer_breached": _cash_buffer_breached,
    "debt_without_justification": _debt_without_justification,
}


def _score_criterion(
    criterion: ScoringCriterion,
    result: QuarterResult,
    prior_result: QuarterResult | None,
    allocations: QuarterAllocations,
    rubric: ScoringConfig,
) -> CriterionScore:
    if criterion.kind not in (CriterionKind.MECHANICAL, CriterionKind.JUDGMENT):
        raise NotImplementedError(
            f"scoring criterion '{criterion.id}' has kind '{criterion.kind}', which is neither "
            f"MECHANICAL nor JUDGMENT -- every criterion must be classified before it can be scored"
        )

    if criterion.kind == CriterionKind.JUDGMENT:
        return CriterionScore(
            id=criterion.id,
            trait=criterion.trait,
            kind=CriterionKind.JUDGMENT,
            result=CriterionResult.UNSCORED,
            detail=criterion.reason or "no reason recorded for this JUDGMENT criterion",
            points=None,
        )

    predicate = _CRITERION_PREDICATES.get(criterion.id)
    if predicate is None:
        raise NotImplementedError(
            f"scoring criterion '{criterion.id}' is configured as MECHANICAL but has no predicate "
            f"registered in engines/scoring.py -- a configured check that silently does nothing is "
            f"worse than one that is absent"
        )

    outcome, detail = predicate(result, prior_result, allocations, rubric)
    return CriterionScore(
        id=criterion.id, trait=criterion.trait, kind=CriterionKind.MECHANICAL, result=outcome, detail=detail, points=None
    )


def _trait_score(
    trait: str,
    weight: Decimal,
    criteria: list[ScoringCriterion],
    result: QuarterResult,
    prior_result: QuarterResult | None,
    allocations: QuarterAllocations,
    rubric: ScoringConfig,
) -> TraitScore:
    third = weight * THIRD
    scored: list[CriterionScore] = []
    weight_scored = ZERO
    points_earned = ZERO

    for criterion in criteria:
        scored_criterion = _score_criterion(criterion, result, prior_result, allocations, rubric)
        if scored_criterion.result == CriterionResult.UNSCORED:
            scored.append(scored_criterion)
            continue

        points = third * _FRACTION_OF_THIRD[scored_criterion.result]
        weight_scored += third
        points_earned += points
        scored.append(
            CriterionScore(
                id=scored_criterion.id,
                trait=scored_criterion.trait,
                kind=scored_criterion.kind,
                result=scored_criterion.result,
                detail=scored_criterion.detail,
                points=points,
            )
        )

    return TraitScore(
        trait=trait,
        weight=weight,
        weight_scored=weight_scored,
        points_earned=points_earned,
        criteria=tuple(scored),
    )


def _score_modifier(
    modifier: ScoringModifier,
    result: QuarterResult,
    prior_result: QuarterResult | None,
    allocations: QuarterAllocations,
    prior_allocations: QuarterAllocations | None,
    rubric: ScoringConfig,
) -> ModifierOutcome:
    predicate = _MODIFIER_PREDICATES.get(modifier.id)
    if predicate is None:
        raise NotImplementedError(
            f"scoring modifier '{modifier.id}' is configured but has no predicate registered in "
            f"engines/scoring.py -- a configured modifier that silently does nothing is worse than "
            f"one that is absent"
        )

    fired, detail = predicate(result, prior_result, allocations, prior_allocations, rubric)
    return ModifierOutcome(
        id=modifier.id,
        points=modifier.points,
        fired=fired,
        applied_points=modifier.points if fired else ZERO,
        detail=detail,
    )


def _band(score: Decimal, rubric: ScoringConfig) -> str:
    for candidate in sorted(rubric.bands, key=lambda b: b.minimum, reverse=True):
        if score >= candidate.minimum:
            return candidate.name
    raise NotImplementedError(
        f"score {score} fell below every configured band's minimum -- the lowest band must have a "
        f"minimum low enough to catch every possible score"
    )


def score_quarter(
    result: QuarterResult,
    prior_result: QuarterResult | None,
    allocations: QuarterAllocations,
    rubric: ScoringConfig,
    prior_allocations: QuarterAllocations | None = None,
    modifier_sets: tuple[str, ...] = ("standard",),
) -> QuarterScore:
    """Score one quarter's allocation decisions against `rubric`.

    `modifier_sets` selects which configured modifier groups apply -- only `"standard"` exists
    today; `docs/11-crisis-system.md`'s and `docs/16-quarter-4-endgame.md`'s sets register the
    same way once Phases 10/11 add them to config, with no change needed here.
    """
    traits: list[TraitScore] = []
    for trait_name, weight in rubric.traits.items():
        criteria = [c for c in rubric.criteria if c.trait == trait_name]
        traits.append(
            _trait_score(trait_name, weight, criteria, result, prior_result, allocations, rubric)
        )

    modifiers: list[ModifierOutcome] = []
    for set_name in modifier_sets:
        configured = rubric.modifier_sets.get(set_name)
        if configured is None:
            raise NotImplementedError(
                f"modifier set '{set_name}' was requested but is not configured in this rubric"
            )
        for modifier in configured:
            modifiers.append(
                _score_modifier(modifier, result, prior_result, allocations, prior_allocations, rubric)
            )

    mechanical_points_available = sum((t.weight_scored for t in traits), start=ZERO)
    unscored_points = sum((t.weight for t in traits), start=ZERO) - mechanical_points_available
    trait_points_earned = sum((t.points_earned for t in traits), start=ZERO)
    modifier_points = sum((m.applied_points for m in modifiers), start=ZERO)

    raw_score = trait_points_earned + modifier_points
    normalised_trait_score = (
        (trait_points_earned / mechanical_points_available * 100) if mechanical_points_available > 0 else ZERO
    )
    normalised_score = normalised_trait_score + modifier_points

    return QuarterScore(
        traits=tuple(traits),
        modifiers=tuple(modifiers),
        mechanical_points_available=mechanical_points_available,
        unscored_points=unscored_points,
        trait_points_earned=trait_points_earned,
        modifier_points=modifier_points,
        raw_score=raw_score,
        normalised_score=normalised_score,
        band=_band(normalised_score, rubric),
    )

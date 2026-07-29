"""R&D -- 2 spend lines, plus the Conversion Ceiling and Warranty choice they feed.

The Conversion Ceiling is the single mechanic that stops Marketing from winning the game alone:
no amount of Marketing or Sales spend can convert leads above the rate the product's build
quality allows.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.config.schema import CompanySeed, SimulationProfile
from app.engines.lines._shared import diminishing, require


@dataclass(frozen=True)
class QualityQaResult:
    quality_score: Decimal
    defect_rate_pct: Decimal


@dataclass(frozen=True)
class InnovationResult:
    innovation_score: Decimal
    feature_completeness: Decimal
    launched: bool


def quality_qa(
    spend_lakhs: Decimal, prior_quality_score: Decimal, profile: SimulationProfile
) -> QualityQaResult:
    """`Quality Score += 6 * x^0.5` (cumulative, never resets) ·
    `Defect Rate = max(2%, 8% - 1.2 * x^0.5)`.

    Quality Score is cumulative because it represents accumulated engineering knowledge and
    process maturity -- once learned it doesn't disappear. Defect Rate floors at 2% because even
    world-class manufacturing has an irreducible failure rate.
    """
    line = profile.rnd.quality_qa
    reduction = diminishing(line.defect_rate_constant, spend_lakhs, line.defect_rate_exponent)
    return QualityQaResult(
        quality_score=prior_quality_score
        + diminishing(line.quality_score_constant, spend_lakhs, line.quality_score_exponent),
        defect_rate_pct=max(line.defect_rate_floor_pct, line.defect_rate_base_pct - reduction),
    )


def innovation(
    spend_lakhs: Decimal,
    prior_innovation_score: Decimal,
    prior_feature_completeness: Decimal,
    profile: SimulationProfile,
) -> InnovationResult:
    """`Feature Completeness += 8 * x^0.5` (resets at 100) ·
    `Innovation Score += 5 * x^0.5` (never decays).

    On reaching 100 the feature ships and, per `docs/12-quarter-1-reference.md` §4.2, "the next
    round of feature work starts from zero" -- so completeness resets to 0 rather than carrying
    the overflow. `launched` reports that the reset happened.
    """
    line = profile.rnd.innovation
    completeness = prior_feature_completeness + diminishing(
        line.feature_completeness_constant, spend_lakhs, line.feature_completeness_exponent
    )
    launched = completeness >= line.feature_completeness_reset_at

    return InnovationResult(
        innovation_score=prior_innovation_score
        + diminishing(line.innovation_score_constant, spend_lakhs, line.innovation_score_exponent),
        feature_completeness=Decimal(0) if launched else completeness,
        launched=launched,
    )


def conversion_ceiling(
    quality_score: Decimal, innovation_score: Decimal, profile: SimulationProfile
) -> Decimal:
    """`Ceiling = 15% + (Quality Score + 0.5 * Innovation Score) * 0.3%`.

    Innovation carries half weight because it is a broader, longer-term capability that only
    partially translates into this quarter's conversion; full weighting would double-count R&D.
    """
    line = profile.rnd.conversion_ceiling
    weighted = line.quality_weight * quality_score + line.innovation_weight * innovation_score
    return line.base_pct + weighted * line.pct_per_point


def warranty_conversion_bonus(warranty_years: int, profile: SimulationProfile) -> Decimal:
    """1yr `+1.5` pts · 2yr `+3.0` pts, additive AFTER the ceiling, not subject to it.

    The ceiling is a build-quality limit; a warranty is a trust and risk-transfer signal, a
    different kind of persuasion, so it layers on top. Getting this wrong was Error 1 in
    `docs/12-quarter-1-reference.md` §9.
    """
    line = profile.rnd.warranty
    if warranty_years == 0:
        return Decimal(0)
    if warranty_years == 1:
        return line.one_year_conversion_bonus_pts
    if warranty_years == 2:
        return line.two_year_conversion_bonus_pts
    raise ValueError(f"warranty_years must be 0, 1 or 2 (got {warranty_years})")


def warranty_cost(
    units_sold: Decimal,
    defect_rate_pct: Decimal,
    warranty_years: int,
    seed: CompanySeed,
    profile: SimulationProfile,
) -> Decimal:
    """`Units Sold * Defect Rate * claim cost`, multiplied by 1.8 for a 2-year term.

    A warranty costs nothing to offer; the cost materialises later in proportion to how many
    units fail. Claim cost is company data, so it comes from the seed.
    """
    if warranty_years == 0:
        return Decimal(0)

    claim_cost = require(seed.warranty_claim_cost_inr, "warranty_claim_cost_inr", seed.name)
    cost = units_sold * (defect_rate_pct / 100) * claim_cost
    if warranty_years == 2:
        return cost * profile.rnd.warranty.two_year_cost_multiplier
    if warranty_years == 1:
        return cost
    raise ValueError(f"warranty_years must be 0, 1 or 2 (got {warranty_years})")

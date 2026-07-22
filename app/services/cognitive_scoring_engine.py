"""Cognitive Scoring Engine: reads EvidenceRecord rows for a quarter and computes 0-100
cognitive dimension scores, then rolls them up into a leaderboard-ready quarter summary.

Deliberately workspace-agnostic: every EvidenceRecord carries `categories` (the cognitive
dimensions it counts toward), and this engine only ever aggregates by category -- it never
branches on `record.workspace`. Finance evidence, Marketing evidence, etc. all feed the same
dimension buckets uniformly, so adding a new workspace's evidence extractors never requires
touching this file.

This engine reads evidence only, never business-impact/KPI data -- that's the whole point of
the dual pipeline (see app/services/evidence_engine.py).
"""

import uuid

from app.models.cognitive import CognitiveScore
from app.models.evidence import EvidenceRecord
from app.models.quarter_performance import QuarterPerformance

# Hidden Engine State baseline (Company Load State doc): every dimension starts at 50 except
# the two special-cased ones below.
DEFAULT_BASELINE = 50.0
BASELINE_OVERRIDES: dict[str, float] = {
    "investor_confidence": 60.0,
    "employee_burnout": 10.0,
}

# TODO(source-doc-gap): only these four evidence keys have a confirmed weight from the spec's
# worked example ("Strategic Thinking = Sigma(evidence_weight) e.g. Balanced Budget +3,
# Diversified Marketing +2, Long-term Investment +3, Consistent Objective +2"). Every other
# evidence_key evidence_engine can emit needs a product-owner-provided weight before it moves
# any score -- until registered here it contributes 0, it is never guessed.
EVIDENCE_WEIGHTS: dict[str, dict[str, float]] = {
    "balanced_budget": {"strategic_thinking": 3.0},
    "diversified_investment": {"strategic_thinking": 2.0},
    "long_term_investment": {"strategic_thinking": 3.0},
    "consistent_objective": {"strategic_thinking": 2.0},
}

# Affirmative values that count as "the tracked positive behavior happened" for weight
# purposes. Evidence recorded as "NO", a raw amount, or a Low/Medium/High level doesn't match
# any registered weight today (see TODO above) so it's a no-op, not a penalty.
AFFIRMATIVE_VALUES = {"YES", True}


def get_baseline(dimension: str) -> float:
    return BASELINE_OVERRIDES.get(dimension, DEFAULT_BASELINE)


def score_dimension(dimension: str, evidence_records: list[EvidenceRecord]) -> float:
    score = get_baseline(dimension)
    for record in evidence_records:
        if record.evidence_value not in AFFIRMATIVE_VALUES:
            continue
        score += EVIDENCE_WEIGHTS.get(record.evidence_key, {}).get(dimension, 0.0)
    return max(0.0, min(100.0, score))


def score_quarter(evidence_records: list[EvidenceRecord]) -> dict[str, float]:
    """Score every dimension that either has a baseline override or appears in EVIDENCE_WEIGHTS."""
    dimensions = set(BASELINE_OVERRIDES) | {dim for weights in EVIDENCE_WEIGHTS.values() for dim in weights}
    return {dimension: score_dimension(dimension, evidence_records) for dimension in dimensions}


def build_cognitive_scores(
    company_id: uuid.UUID, quarter_id: uuid.UUID, dimension_scores: dict[str, float]
) -> list[CognitiveScore]:
    """Materialize CognitiveScore rows (not persisted -- caller adds them to the session)."""
    return [
        CognitiveScore(company_id=company_id, quarter_id=quarter_id, dimension=dimension, score=score)
        for dimension, score in dimension_scores.items()
    ]


def build_quarter_performance(
    company_id: uuid.UUID, quarter_id: uuid.UUID, dimension_scores: dict[str, float]
) -> QuarterPerformance:
    """Roll dimension scores up into the leaderboard-ready summary row (not persisted)."""
    overall_score = sum(dimension_scores.values()) / len(dimension_scores) if dimension_scores else 0.0
    return QuarterPerformance(
        company_id=company_id,
        quarter_id=quarter_id,
        overall_score=overall_score,
        dimension_scores=dimension_scores,
    )

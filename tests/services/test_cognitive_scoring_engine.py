import uuid

from app.models.decision import Workspace
from app.models.evidence import EvidenceRecord
from app.services.cognitive_scoring_engine import (
    build_cognitive_scores,
    build_quarter_performance,
    get_baseline,
    score_dimension,
    score_quarter,
)


def _record(evidence_key: str, evidence_value, categories: list[str]) -> EvidenceRecord:
    return EvidenceRecord(
        company_id=uuid.uuid4(),
        quarter_id=uuid.uuid4(),
        decision_id=uuid.uuid4(),
        workspace=Workspace.MARKETING,
        evidence_key=evidence_key,
        evidence_value=evidence_value,
        categories=categories,
    )


def test_baselines():
    assert get_baseline("strategic_thinking") == 50.0
    assert get_baseline("investor_confidence") == 60.0
    assert get_baseline("employee_burnout") == 10.0


def test_score_dimension_no_evidence_returns_baseline():
    assert score_dimension("strategic_thinking", []) == 50.0


def test_score_dimension_applies_weights_from_worked_example():
    records = [
        _record("balanced_budget", "YES", ["strategic_thinking", "capital_allocation"]),
        _record("diversified_investment", "YES", ["strategic_thinking", "capital_allocation"]),
        _record("long_term_investment", "YES", ["long_term_thinking", "strategic_thinking"]),
    ]
    # 50 baseline + 3 (balanced_budget) + 2 (diversified_investment) + 3 (long_term_investment)
    assert score_dimension("strategic_thinking", records) == 58.0


def test_score_dimension_ignores_negative_evidence():
    records = [_record("balanced_budget", "NO", ["strategic_thinking"])]
    assert score_dimension("strategic_thinking", records) == 50.0


def test_score_dimension_ignores_unregistered_evidence_keys():
    records = [_record("some_future_evidence_key", "YES", ["strategic_thinking"])]
    assert score_dimension("strategic_thinking", records) == 50.0


def test_score_dimension_clamps_at_100():
    records = [_record("balanced_budget", "YES", ["strategic_thinking"])] * 30  # 50 + 30*3 = 140, clamped
    assert score_dimension("strategic_thinking", records) == 100.0


def test_score_quarter_covers_baseline_and_weighted_dimensions():
    scores = score_quarter([])
    assert scores["investor_confidence"] == 60.0
    assert scores["employee_burnout"] == 10.0
    assert scores["strategic_thinking"] == 50.0


def test_build_cognitive_scores_and_quarter_performance():
    company_id = uuid.uuid4()
    quarter_id = uuid.uuid4()
    dimension_scores = {"strategic_thinking": 58.0, "investor_confidence": 60.0}

    scores = build_cognitive_scores(company_id, quarter_id, dimension_scores)
    assert len(scores) == 2
    assert all(s.company_id == company_id and s.quarter_id == quarter_id for s in scores)

    performance = build_quarter_performance(company_id, quarter_id, dimension_scores)
    assert performance.overall_score == 59.0
    assert performance.dimension_scores == dimension_scores

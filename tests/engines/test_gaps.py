"""The unimplementable formulas must fail with their specific reason, never a blanket message
and never a guessed number (docs/10-implementation-gaps.md)."""

import pytest

from app.engines import gaps


def test_negotiation_score_names_the_missing_weights():
    with pytest.raises(NotImplementedError, match="no specified weights or scales"):
        gaps.negotiation_score()


def test_acceptance_probability_names_the_missing_normalisation():
    with pytest.raises(NotImplementedError, match="no.*normalisation"):
        gaps.acceptance_probability()


@pytest.mark.parametrize("decision_key", ["CX-001", "CX-007", "CX-012"])
def test_cx_decisions_name_the_key_and_the_reason(decision_key):
    with pytest.raises(NotImplementedError, match=decision_key):
        gaps.cx_decision_impact(decision_key)


def test_cx_reason_explains_that_the_named_engines_are_undefined():
    with pytest.raises(NotImplementedError, match="none of which is defined"):
        gaps.cx_decision_impact("CX-001")


def test_momentum_score_names_the_missing_weights_and_cutoffs():
    with pytest.raises(NotImplementedError, match="no weights, no normalisation and no tier"):
        gaps.momentum_score()


@pytest.mark.parametrize(
    "reason", [gaps.NEGOTIATION_REASON, gaps.CX_REASON, gaps.MOMENTUM_REASON]
)
def test_every_reason_cites_the_gaps_register(reason):
    assert "docs/10-implementation-gaps.md" in reason

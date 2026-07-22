import uuid

import pytest

from app.models.decision import Decision, Workspace
from app.models.evidence import EvidenceRecord
from app.services.evidence_engine import (
    extract_adaptability_evidence,
    extract_marketing_budget_allocation_evidence,
    generate_evidence,
)


def _evidence_dict(evidence_list):
    return {e.evidence_key: e for e in evidence_list}


def test_diversified_low_risk_budget():
    payload = {
        "total_budget": 10000,
        "channel_spend": {
            "increase_google_ads_budget": 3000,
            "increase_seo_budget": 3000,
            "increase_email_marketing": 3000,
        },
    }
    evidence = _evidence_dict(extract_marketing_budget_allocation_evidence(payload))

    assert evidence["diversified_investment"].evidence_value == "YES"
    assert evidence["long_term_investment"].evidence_value == "YES"  # includes SEO
    assert evidence["high_channel_dependency"].evidence_value == "NO"
    assert evidence["balanced_budget"].evidence_value == "YES"
    assert evidence["risk_level"].evidence_value == "Low"
    assert evidence["unused_budget"].evidence_value == 1000


def test_concentrated_high_risk_budget():
    payload = {
        "total_budget": 10000,
        "channel_spend": {
            "increase_google_ads_budget": 9000,
            "increase_email_marketing": 1000,
        },
    }
    evidence = _evidence_dict(extract_marketing_budget_allocation_evidence(payload))

    assert evidence["diversified_investment"].evidence_value == "NO"
    assert evidence["long_term_investment"].evidence_value == "NO"  # no SEO/content/sustainability
    assert evidence["high_channel_dependency"].evidence_value == "YES"
    assert evidence["balanced_budget"].evidence_value == "NO"
    assert evidence["risk_level"].evidence_value == "High"
    assert evidence["unused_budget"].evidence_value == 0


def test_adaptability_pivoted_quickly():
    company_id = uuid.uuid4()
    quarter_id = uuid.uuid4()
    decision_id = uuid.uuid4()
    prior_evidence = [
        EvidenceRecord(
            company_id=company_id,
            quarter_id=quarter_id,
            decision_id=decision_id,
            workspace=Workspace.MARKETING,
            evidence_key="channel_underperformed_increase_seo_budget",
            evidence_value="YES",
            categories=["adaptability"],
        ),
        EvidenceRecord(
            company_id=company_id,
            quarter_id=quarter_id,
            decision_id=decision_id,
            workspace=Workspace.MARKETING,
            evidence_key="channel_spend_increase_seo_budget",
            evidence_value=3000,
            categories=["capital_allocation"],
        ),
    ]
    current_payload = {"channel_spend": {"increase_seo_budget": 1000}}

    evidence = _evidence_dict(extract_adaptability_evidence(current_payload, prior_evidence))

    assert evidence["pivoted_quickly_increase_seo_budget"].evidence_value == "YES"
    assert evidence["ignored_feedback_increase_seo_budget"].evidence_value == "NO"


def test_adaptability_ignored_feedback():
    company_id = uuid.uuid4()
    quarter_id = uuid.uuid4()
    decision_id = uuid.uuid4()
    prior_evidence = [
        EvidenceRecord(
            company_id=company_id,
            quarter_id=quarter_id,
            decision_id=decision_id,
            workspace=Workspace.MARKETING,
            evidence_key="channel_underperformed_increase_seo_budget",
            evidence_value="YES",
            categories=["adaptability"],
        ),
        EvidenceRecord(
            company_id=company_id,
            quarter_id=quarter_id,
            decision_id=decision_id,
            workspace=Workspace.MARKETING,
            evidence_key="channel_spend_increase_seo_budget",
            evidence_value=3000,
            categories=["capital_allocation"],
        ),
    ]
    current_payload = {"channel_spend": {"increase_seo_budget": 5000}}

    evidence = _evidence_dict(extract_adaptability_evidence(current_payload, prior_evidence))

    assert evidence["pivoted_quickly_increase_seo_budget"].evidence_value == "NO"
    assert evidence["ignored_feedback_increase_seo_budget"].evidence_value == "YES"


def test_generate_evidence_end_to_end():
    company_id = uuid.uuid4()
    quarter_id = uuid.uuid4()
    decision = Decision(
        id=uuid.uuid4(),
        quarter_id=quarter_id,
        workspace=Workspace.MARKETING,
        title="Q1 Marketing Budget Allocation",
        decision_key="marketing_budget_allocation",
        payload={
            "total_budget": 10000,
            "channel_spend": {
                "increase_google_ads_budget": 3000,
                "increase_seo_budget": 3000,
                "increase_email_marketing": 3000,
            },
        },
    )

    records = generate_evidence(decision, company_id=company_id)

    assert len(records) == 6
    assert all(isinstance(r, EvidenceRecord) for r in records)
    assert all(r.company_id == company_id and r.quarter_id == quarter_id for r in records)


def test_generate_evidence_unregistered_decision_raises():
    decision = Decision(
        id=uuid.uuid4(),
        quarter_id=uuid.uuid4(),
        workspace=Workspace.FINANCE,
        title="Department Budget Allocation",
        decision_key="FIN-001",
        payload={},
    )

    with pytest.raises(NotImplementedError):
        generate_evidence(decision, company_id=uuid.uuid4())

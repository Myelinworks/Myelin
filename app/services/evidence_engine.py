"""Evidence pipeline: turns a submitted Decision into structured behavioral evidence.

Evidence is a boolean/enum/amount flag about *how* a decision was made (e.g.
"Diversified Investment = YES"), never a score and never a raw KPI -- scoring happens
downstream in cognitive_scoring_engine, which reads only these records and never raw
business-impact data.

Only the two extractors the source spec fully worked through are implemented here:
Marketing Budget Allocation (diversification/risk flags) and the generic cross-quarter
Adaptability check (pivoted vs ignored feedback). Every other decision across the ~60
workspace decisions needs its own evidence-extraction rule from the product owner before
it can emit evidence -- see EVIDENCE_EXTRACTORS below, which raises NotImplementedError
for anything not yet registered rather than guessing what evidence a decision produces.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.models.decision import Decision, Workspace
from app.models.evidence import EvidenceRecord


@dataclass(frozen=True)
class Evidence:
    evidence_key: str
    evidence_value: Any
    categories: list[str]


# Channels considered "long-term" investment per the spec's "SEO/Community/Brand, not just
# performance/paid" wording, mapped onto the actual channel keys in marketing_rules.json.
# TODO(source-doc-gap): exact channel-to-category taxonomy isn't given explicitly; this
# mapping is inferred and should be confirmed with the product owner.
LONG_TERM_MARKETING_CHANNELS = {"increase_seo_budget", "increase_content_marketing", "sustainability_campaign"}

HIGH_CHANNEL_DEPENDENCY_THRESHOLD = 0.7
# TODO(source-doc-gap): only the >70% "High Channel Dependency" threshold is given in the
# spec. This Medium/Low split point is an inferred default, not sourced from the doc.
MEDIUM_RISK_THRESHOLD = 0.4


def extract_marketing_budget_allocation_evidence(payload: dict[str, Any]) -> list[Evidence]:
    """Worked example from the spec: Marketing Budget Allocation decision.

    Expects payload shape: {"total_budget": float, "channel_spend": {channel_key: float, ...}}
    """
    channel_spend: dict[str, float] = payload.get("channel_spend", {})
    total_spent = sum(channel_spend.values())
    total_budget = payload.get("total_budget", total_spent)

    channels_used = [c for c, amount in channel_spend.items() if amount > 0]
    diversified_investment = len(channels_used) > 2

    long_term_spend = sum(amount for c, amount in channel_spend.items() if c in LONG_TERM_MARKETING_CHANNELS)
    long_term_investment = long_term_spend > 0

    max_channel_share = (max(channel_spend.values()) / total_spent) if total_spent else 0.0
    high_channel_dependency = max_channel_share > HIGH_CHANNEL_DEPENDENCY_THRESHOLD

    balanced_budget = diversified_investment and not high_channel_dependency

    if max_channel_share > HIGH_CHANNEL_DEPENDENCY_THRESHOLD:
        risk_level = "High"
    elif max_channel_share > MEDIUM_RISK_THRESHOLD:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    unused_budget = max(total_budget - total_spent, 0)

    return [
        Evidence(
            "diversified_investment",
            "YES" if diversified_investment else "NO",
            ["strategic_thinking", "capital_allocation"],
        ),
        Evidence(
            "long_term_investment",
            "YES" if long_term_investment else "NO",
            ["long_term_thinking", "strategic_thinking"],
        ),
        Evidence("high_channel_dependency", "YES" if high_channel_dependency else "NO", ["risk_management"]),
        Evidence("balanced_budget", "YES" if balanced_budget else "NO", ["strategic_thinking", "capital_allocation"]),
        Evidence("risk_level", risk_level, ["risk_management"]),
        Evidence("unused_budget", unused_budget, ["capital_allocation"]),
    ]


def extract_adaptability_evidence(
    current_payload: dict[str, Any],
    prior_quarter_evidence: list[EvidenceRecord],
) -> list[Evidence]:
    """Cross-quarter pivot check: for each channel flagged as underperforming last quarter
    (a "channel_underperformed_<channel>" = YES evidence record written at the prior
    quarter's close -- see quarter_engine), check whether this quarter's spend on that
    channel dropped (Pivoted Quickly) or held/increased despite the flag (Ignored Feedback).

    Reads `channel_spend_<channel>` records from prior_quarter_evidence as the spend
    baseline to compare against, rather than any raw KPI data.
    """
    current_spend: dict[str, float] = current_payload.get("channel_spend", {})
    prior_spend_by_channel = {
        r.evidence_key.removeprefix("channel_spend_"): r.evidence_value
        for r in prior_quarter_evidence
        if r.evidence_key.startswith("channel_spend_")
    }
    underperformed_channels = {
        r.evidence_key.removeprefix("channel_underperformed_")
        for r in prior_quarter_evidence
        if r.evidence_key.startswith("channel_underperformed_") and r.evidence_value == "YES"
    }

    evidence: list[Evidence] = []
    for channel in underperformed_channels:
        prior_spend = prior_spend_by_channel.get(channel, 0)
        current = current_spend.get(channel, 0)
        pivoted = current < prior_spend
        evidence.append(Evidence(f"pivoted_quickly_{channel}", "YES" if pivoted else "NO", ["adaptability"]))
        evidence.append(Evidence(f"ignored_feedback_{channel}", "NO" if pivoted else "YES", ["adaptability"]))
    return evidence


EVIDENCE_EXTRACTORS: dict[tuple[Workspace, str], Callable[[dict[str, Any]], list[Evidence]]] = {
    (Workspace.MARKETING, "marketing_budget_allocation"): extract_marketing_budget_allocation_evidence,
}


def generate_evidence(
    decision: Decision,
    decision_key: str,
    *,
    company_id: uuid.UUID,
    prior_quarter_evidence: list[EvidenceRecord] | None = None,
) -> list[EvidenceRecord]:
    """Top-level orchestrator: extract evidence for one decision and materialize EvidenceRecord
    rows (not persisted -- caller adds them to the session and commits).

    NOTE: the adaptability check is currently coupled to the "channel_spend" payload shape
    (marketing-specific). Once more workspaces register extractors, this needs a per-workspace
    adaptability hook instead of always assuming channel_spend.
    """
    extractor = EVIDENCE_EXTRACTORS.get((decision.workspace, decision_key))
    if extractor is None:
        raise NotImplementedError(
            f"No evidence-extraction rule registered for {decision.workspace.value}/{decision_key}. "
            "Evidence rules for this decision haven't been specified yet -- register one in "
            "EVIDENCE_EXTRACTORS rather than guessing what evidence it should produce."
        )

    items = list(extractor(decision.payload))
    if prior_quarter_evidence:
        items += extract_adaptability_evidence(decision.payload, prior_quarter_evidence)

    return [
        EvidenceRecord(
            company_id=company_id,
            quarter_id=decision.quarter_id,
            decision_id=decision.id,
            workspace=decision.workspace,
            evidence_key=item.evidence_key,
            evidence_value=item.evidence_value,
            categories=item.categories,
        )
        for item in items
    ]

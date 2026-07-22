"""Orchestrates one quarter's Run Quarter flow: Recurring Cost Engine -> per-decision
Business Impact + Evidence -> Cross-Department Effects -> Cognitive Scores -> Leaderboard.

Deliberately DB-session-agnostic: every function here is a pure transform over plain
Decision/EvidenceRecord objects, returning ORM rows the caller persists. This keeps the
orchestration logic unit-testable without a live database -- persistence (session.add,
commit, loading decisions for a quarter) is the route/service-boundary layer's job, built in
the next pass once the routes exist.
"""

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from app.config.rules import load_rules
from app.models.cognitive import CognitiveScore
from app.models.decision import Decision
from app.models.evidence import EvidenceRecord
from app.models.quarter_performance import QuarterPerformance
from app.services.cognitive_scoring_engine import build_cognitive_scores, build_quarter_performance, score_quarter
from app.services.decision_engine import FieldImpact, compute_decision_impact
from app.services.evidence_engine import generate_evidence

# --- Recurring Cost Engine -------------------------------------------------
# Three categories from the Quarter Flow doc, each its own execution step per the spec,
# implemented generically off finance_rules.json's recurring_cost_categories rather than
# three near-duplicate functions with the item lists hardcoded.


def _sum_cost_category(category: str, cost_breakdown: dict[str, float]) -> float:
    items = load_rules("finance")["recurring_cost_categories"][category]
    return sum(cost_breakdown.get(item, 0.0) for item in items)


def apply_recurring_costs(cost_breakdown: dict[str, float]) -> float:
    """Automatic, always-on costs: salaries, rent, software, insurance, cloud, maintenance."""
    return _sum_cost_category("recurring_automatic", cost_breakdown)


def apply_decision_based_costs(cost_breakdown: dict[str, float]) -> float:
    """Costs triggered by student decisions this quarter: campaigns, hiring, R&D, training, etc."""
    return _sum_cost_category("decision_based", cost_breakdown)


def apply_variable_operating_costs(cost_breakdown: dict[str, float]) -> float:
    """Activity-triggered costs: manufacturing/unit, shipping, gateway fees, warranty, returns."""
    return _sum_cost_category("variable_operating", cost_breakdown)


# --- Cross-Department Effects (generic handoff registry) -------------------
# Only the Marketing Leads -> Sales Capacity example from the spec is implemented. More
# handoffs (Product Readiness -> Sales Launch timing, Operations Inventory -> Sales
# fulfillment, etc.) register into HANDOFFS the same way rather than special-casing them
# in the orchestrator.

HandoffFn = Callable[[dict, dict], dict]


def marketing_leads_to_sales_capacity(marketing_results: dict, sales_results: dict) -> dict:
    """If Marketing generates more Leads than Sales Capacity can absorb, the excess is lost.

    TODO(source-doc-gap): the doc says excess leads "degrade Revenue/Customer
    Satisfaction/Brand Trust for that quarter" but never gives a magnitude per excess lead --
    this reports the excess-leads count only; converting it into concrete KPI deltas needs
    product-owner input.
    """
    leads = marketing_results.get("leads_generated", 0)
    capacity = sales_results.get("sales_capacity", 0)
    excess_leads = max(leads - capacity, 0)
    return {"excess_leads_lost": excess_leads} if excess_leads else {}


HANDOFFS: dict[tuple[str, str], HandoffFn] = {
    ("marketing", "sales"): marketing_leads_to_sales_capacity,
}


def run_handoffs(workspace_results: dict[str, dict]) -> dict[tuple[str, str], dict]:
    effects = {}
    for (source, target), handoff_fn in HANDOFFS.items():
        if source in workspace_results and target in workspace_results:
            result = handoff_fn(workspace_results[source], workspace_results[target])
            if result:
                effects[(source, target)] = result
    return effects


# --- Run Quarter orchestration ----------------------------------------------


@dataclass
class QuarterRunResult:
    evidence_records: list[EvidenceRecord] = field(default_factory=list)
    cognitive_scores: list[CognitiveScore] = field(default_factory=list)
    quarter_performance: QuarterPerformance | None = None
    business_impacts: dict[uuid.UUID, list[FieldImpact]] = field(default_factory=dict)
    cross_department_effects: dict[tuple[str, str], dict] = field(default_factory=dict)
    skipped_evidence: list[str] = field(default_factory=list)
    skipped_business_impact: list[str] = field(default_factory=list)


def run_quarter(
    company_id: uuid.UUID,
    quarter_id: uuid.UUID,
    decisions: list[Decision],
    modifiers: dict[str, float],
    prior_quarter_evidence: list[EvidenceRecord] | None = None,
) -> QuarterRunResult:
    """Run the Business Impact + Evidence pipelines for every decision in a quarter, then
    roll evidence up into cognitive scores and a leaderboard-ready performance summary.

    Decisions without a registered evidence extractor or base-impact table are skipped, not
    fatal -- most of the ~60 workspace decisions don't have their rules specified yet (see
    evidence_engine.EVIDENCE_EXTRACTORS), so failing the whole quarter on the first
    unimplemented decision would make this unusable before every decision is wired up.
    """
    result = QuarterRunResult()
    workspace_results: dict[str, dict] = {}

    for decision in decisions:
        workspace_results.setdefault(decision.workspace.value, {})

        try:
            result.evidence_records += generate_evidence(
                decision, company_id=company_id, prior_quarter_evidence=prior_quarter_evidence
            )
        except NotImplementedError as exc:
            result.skipped_evidence.append(str(exc))

        try:
            result.business_impacts[decision.id] = compute_decision_impact(
                decision.workspace.value, decision.decision_key, modifiers
            )
        except (NotImplementedError, KeyError) as exc:
            result.skipped_business_impact.append(str(exc))

    result.cross_department_effects = run_handoffs(workspace_results)

    dimension_scores = score_quarter(result.evidence_records)
    result.cognitive_scores = build_cognitive_scores(company_id, quarter_id, dimension_scores)
    result.quarter_performance = build_quarter_performance(company_id, quarter_id, dimension_scores)

    return result

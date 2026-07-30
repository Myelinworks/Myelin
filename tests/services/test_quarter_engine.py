import uuid

from app.models.decision import Decision, DecisionStatus, Workspace
from app.services.quarter_engine import (
    apply_decision_based_costs,
    apply_recurring_costs,
    apply_variable_operating_costs,
    marketing_leads_to_sales_capacity,
    run_handoffs,
    run_quarter,
)

WORKED_EXAMPLE_MODIFIERS = {
    "brand_strength": 0.9,
    "market_saturation": 0.6,
    "inventory_availability": 1.0,
    "competitor_activity": 0.8,
}


def test_apply_recurring_costs_sums_only_recurring_items():
    costs = {"salaries": 50000, "rent": 5000, "marketing_campaigns": 9999, "unrelated_key": 1}
    assert apply_recurring_costs(costs) == 55000


def test_apply_decision_based_costs_sums_only_decision_items():
    costs = {"hiring": 2000, "rnd": 3000, "salaries": 9999}
    assert apply_decision_based_costs(costs) == 5000


def test_apply_variable_operating_costs_sums_only_variable_items():
    costs = {"shipping": 400, "warranty_claims": 100, "salaries": 9999}
    assert apply_variable_operating_costs(costs) == 500


def test_apply_cost_functions_missing_items_default_to_zero():
    assert apply_recurring_costs({}) == 0


def test_marketing_leads_to_sales_capacity_no_excess():
    result = marketing_leads_to_sales_capacity({"leads_generated": 100}, {"sales_capacity": 150})
    assert result == {}


def test_marketing_leads_to_sales_capacity_excess_lost():
    result = marketing_leads_to_sales_capacity({"leads_generated": 200}, {"sales_capacity": 150})
    assert result == {"excess_leads_lost": 50}


def test_run_handoffs_only_fires_when_both_sides_present():
    assert run_handoffs({"marketing": {"leads_generated": 200}}) == {}
    effects = run_handoffs({"marketing": {"leads_generated": 200}, "sales": {"sales_capacity": 100}})
    assert effects == {("marketing", "sales"): {"excess_leads_lost": 100}}


def test_run_quarter_end_to_end_mixed_registered_and_unregistered_decisions():
    company_id = uuid.uuid4()
    quarter_id = uuid.uuid4()

    registered_decision = Decision(
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
    unregistered_decision = Decision(
        id=uuid.uuid4(),
        quarter_id=quarter_id,
        workspace=Workspace.FINANCE,
        title="Department Budget Allocation",
        decision_key="FIN-001",
        payload={},
    )

    result = run_quarter(
        company_id,
        quarter_id,
        [registered_decision, unregistered_decision],
        WORKED_EXAMPLE_MODIFIERS,
    )

    # evidence: only the registered marketing decision produces evidence
    assert len(result.evidence_records) == 6
    assert all(r.company_id == company_id for r in result.evidence_records)

    # business impact: marketing_budget_allocation is evidence_only (no base_impact table row),
    # and FIN-001 isn't a base-impact-table workspace at all -- both skipped, for different reasons.
    assert len(result.skipped_business_impact) == 2

    # cognitive scores computed from the one registered decision's evidence: three-way split
    # (33% each) means diversified_investment=YES (+2), long_term_investment=YES (+3, seo
    # included), high_channel_dependency=NO -> balanced_budget=YES (+3) => 50 + 2 + 3 + 3 = 58
    dimension_by_name = {s.dimension: s.score for s in result.cognitive_scores}
    assert dimension_by_name["strategic_thinking"] == 58.0
    assert result.quarter_performance is not None
    assert result.quarter_performance.company_id == company_id

    # every decision run_quarter consumed is marked PROCESSED, registered or not -- it never
    # left DRAFT/SUBMITTED, which would make a locked quarter's decisions look unconsumed.
    assert registered_decision.status == DecisionStatus.PROCESSED
    assert unregistered_decision.status == DecisionStatus.PROCESSED

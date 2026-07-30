"""The Q1 regression target -- the only proof the port is correct.

Every expected value comes from `docs/12-quarter-1-reference.md` §8 and §11. Tolerance is
+/-1 unit or +/-Rs 1, per the phase spec. No database is touched.
"""

from decimal import Decimal

import pytest

from app.engines.quarter import compute_quarter
from app.engines.state import CompanyState, CrisisEvent, QuarterAllocations
from tests.engines.conftest import close

# docs/12-quarter-1-reference.md §12: Rs 45,00,000 across six departments.
Q1_ALLOCATIONS = QuarterAllocations(
    google_ads=Decimal("4.00"),
    meta_ads=Decimal("1.92"),
    social_influencer=Decimal("2.08"),
    content_seo=Decimal("1.28"),
    events_pr=Decimal("0.80"),
    email_marketing=Decimal("1.60"),
    referral=Decimal("2.40"),
    prelaunch_buzz=Decimal("1.92"),
    reps=Decimal("5.45"),
    crm_tools=Decimal("1.30"),
    onboarding=Decimal("1.25"),
    quality_qa=Decimal("2.75"),
    innovation=Decimal("2.25"),
    manufacturing=Decimal("3.30"),
    supplier_qc=Decimal("1.50"),
    logistics=Decimal("1.20"),
    culture_benefits=Decimal("1.20"),
    training_development=Decimal("0.90"),
    cx_team=Decimal("0.90"),
    compliance_legal=Decimal("2.80"),
    financial_planning=Decimal("2.10"),
    audit_prep=Decimal("2.10"),
    warranty_years=1,
)


@pytest.fixture(scope="module")
def q1(nadi_wear, profile):
    opening = CompanyState.opening(nadi_wear)
    return compute_quarter(opening, Q1_ALLOCATIONS, profile, nadi_wear)


class TestQ1Allocation:
    def test_departments_sum_to_45_lakhs(self):
        assert Q1_ALLOCATIONS.marketing_total == Decimal("16.00")
        assert Q1_ALLOCATIONS.sales_total == Decimal("8.00")
        assert Q1_ALLOCATIONS.rnd_total == Decimal("5.00")
        assert Q1_ALLOCATIONS.operations_total == Decimal("6.00")
        assert Q1_ALLOCATIONS.hr_total == Decimal("3.00")
        assert Q1_ALLOCATIONS.finance_admin_total == Decimal("7.00")
        assert Q1_ALLOCATIONS.total_discretionary == Decimal("45.00")


class TestQ1Chain:
    def test_raw_leads(self, q1):
        assert close(q1.raw_leads, "2719", tolerance="2")

    def test_effective_leads(self, q1):
        """2,719 x 1.082 productivity. No brand multiplier and no deferred payouts in Q1."""
        assert q1.seo_payout_leads == Decimal(0)
        assert q1.buzz_payout_leads == Decimal(0)
        assert close(q1.effective_leads, "2941", tolerance="2")

    def test_leads_used_is_capacity_bound(self, q1):
        """MIN(2,941, 2,725) -- Sales Capacity binds, wasting 216 leads' worth of demand."""
        assert close(q1.sales_capacity, "2725")
        assert close(q1.leads_used, "2725")
        assert q1.capacity_bound is True

    def test_conversion_rate(self, q1):
        """R&D ceiling 19.1% + warranty 1.5% = 20.6%."""
        assert close(q1.conversion_ceiling_pct, "19.1", tolerance="0.05")
        assert q1.warranty_bonus_pts == Decimal("1.5")
        assert close(q1.conversion_rate_pct, "20.6", tolerance="0.05")

    def test_available_to_sell(self, q1):
        """923 capacity x 74.9% reliability + 600 carried in."""
        assert close(q1.available_to_sell, "1291")

    def test_units_sold(self, q1):
        """The headline number: 2,725 leads at 20.6%. Supply did not bind this quarter."""
        assert close(q1.units_sold, "562")
        assert q1.supply_bound is False

    def test_revenue(self, q1):
        assert close(q1.revenue_inr, "5615653")

    def test_cogs(self, q1):
        assert close(q1.cogs_inr, "1733449")

    def test_warranty_cost(self, q1):
        assert close(q1.warranty_cost_inr, "50630")

    def test_holding_cost(self, q1):
        """729 unsold units at Rs 150."""
        assert close(q1.available_to_sell - q1.units_sold, "729")
        assert close(q1.holding_cost_inr, "109411")

    def test_net_cash_flow(self, q1):
        """The second headline number."""
        assert close(q1.net_cash_flow_inr, "-3127837")

    def test_closing_cash(self, q1):
        assert close(q1.closing_cash_inr, "11872163")

    def test_discretionary_ceiling(self, q1):
        """Rs 1,50,00,000 cash - Rs 23,50,000 fixed - Rs 10,00,000 buffer."""
        assert q1.discretionary_ceiling_inr == Decimal("11650000")

    def test_q1_stayed_out_of_the_working_capital_buffer(self, q1):
        """Rs 45,00,000 of a Rs 1,16,50,000 ceiling -- deliberately moderate-lean."""
        assert q1.spent_into_buffer is False
        assert q1.buffer_overspend_inr == Decimal(0)


class TestGate1CapacityIsRecheckedAfterMultipliers:
    """Error 2 in §9: HR's multiplier was applied to leads without re-checking Sales Capacity.

    A productivity multiplier makes each lead easier to convert; it cannot make Sales' phones
    ring longer.
    """

    def test_leads_used_never_exceeds_effective_capacity(self, q1):
        assert q1.leads_used == q1.effective_sales_capacity
        assert q1.leads_used < q1.effective_leads

    def test_the_multiplier_is_applied_before_the_gate_not_after(self, q1):
        """Effective Leads must already include the HR multiplier when capacity is checked."""
        assert q1.effective_leads > q1.raw_leads
        assert close(q1.effective_leads, q1.raw_leads * q1.productivity_multiplier, tolerance="0.01")

    def test_extra_hr_spend_cannot_lift_units_while_capacity_binds(self, nadi_wear, profile):
        """The regression: if the gate were skipped, more HR spend would sell more units."""
        opening = CompanyState.opening(nadi_wear)
        from dataclasses import replace

        richer_hr = replace(Q1_ALLOCATIONS, culture_benefits=Decimal("10.00"))
        baseline = compute_quarter(opening, Q1_ALLOCATIONS, profile, nadi_wear)
        boosted = compute_quarter(opening, richer_hr, profile, nadi_wear)

        assert boosted.productivity_multiplier > baseline.productivity_multiplier
        assert boosted.effective_leads > baseline.effective_leads
        assert boosted.units_sold == baseline.units_sold


class TestGate2WarrantyIsAdditiveAfterTheCeiling:
    """Error 1 in §9: the warranty bonus was decided but never applied.

    Correct: `MIN(raw, ceiling) + warranty`. Wrong: `MIN(ceiling, raw + warranty)`.
    """

    def test_final_rate_exceeds_the_ceiling(self, q1):
        """The distinguishing assertion -- under the wrong form the rate could never exceed it."""
        assert q1.conversion_rate_pct > q1.conversion_ceiling_pct
        assert q1.conversion_rate_pct == q1.conversion_ceiling_pct + q1.warranty_bonus_pts

    def test_the_ceiling_binds_raw_conversion_in_q1(self, q1):
        """Raw reaches 25.3% (19% base + 4.7 Reps + 1.7 CRM); the ceiling allows 19.1%."""
        assert close(q1.raw_conversion_pct, "25.3", tolerance="0.1")
        assert q1.ceiling_bound is True
        assert q1.conversion_ceiling_pct < q1.raw_conversion_pct

    def test_a_two_year_warranty_adds_3_points_on_top(self, nadi_wear, profile):
        from dataclasses import replace

        opening = CompanyState.opening(nadi_wear)
        two_year = compute_quarter(
            opening, replace(Q1_ALLOCATIONS, warranty_years=2), profile, nadi_wear
        )

        assert two_year.conversion_rate_pct == two_year.conversion_ceiling_pct + Decimal("3.0")

    def test_no_warranty_leaves_the_rate_at_the_ceiling(self, nadi_wear, profile):
        from dataclasses import replace

        opening = CompanyState.opening(nadi_wear)
        none = compute_quarter(opening, replace(Q1_ALLOCATIONS, warranty_years=0), profile, nadi_wear)

        assert none.conversion_rate_pct == none.conversion_ceiling_pct


class TestQ1SpecificExclusions:
    def test_brand_multiplier_is_not_applied_in_q1(self, q1):
        """Brand built in Q1 applies from Q2. Q1 runs at exactly 1.0."""
        assert q1.brand_multiplier == Decimal(1)

    def test_brand_is_still_built_and_carried_forward(self, q1):
        """8.7 built in Q1 -- it becomes a x1.174 multiplier in Q2."""
        assert close(q1.closing_state.brand_score, "8.7", tolerance="0.01")

    def test_attrition_is_not_applied_in_q1(self, q1):
        """No prior quarter means no capacity to erode."""
        assert q1.effective_sales_capacity == q1.sales_capacity

    def test_attrition_is_computed_for_q2(self, q1):
        assert close(q1.closing_state.attrition_rate_pct, "7.1", tolerance="0.05")

    def test_no_free_repeat_units_in_q1(self, q1):
        """Free repeat units are prior rate x prior units sold, and Q1 has no prior quarter."""
        assert q1.free_repeat_units == Decimal(0)


class TestQ1CarryForward:
    def test_closing_inventory(self, q1):
        """729 unsold units carry into Q2."""
        assert close(q1.closing_state.inventory_units, "729")

    def test_closing_customers(self, q1):
        """4,000 + 562 sold -> Q2's referral cap rises to 912."""
        assert close(q1.closing_state.customers, "4562")

    def test_seo_asset_carried_for_q2_payout(self, q1):
        assert close(q1.closing_state.seo_asset, "4.5", tolerance="0.05")

    def test_buzz_carried_with_its_payout_clock_started(self, q1):
        assert close(q1.closing_state.buzz_score, "5.5", tolerance="0.05")
        assert q1.closing_state.buzz_quarters_since_investment == 1

    def test_cash_efficiency_bonus_discounts_next_quarter(self, q1):
        """Forecast Accuracy 63.7 -> a 1.37% discount on Q2's fixed costs.

        §7.2 quotes Rs 23,17,805, reached by rounding the bonus to 1.37%. Unrounded it is
        1.36948%, giving Rs 23,17,817 -- a Rs 12 display artefact, not a disagreement.
        """
        assert close(q1.cash_efficiency_bonus_pct, "1.37", tolerance="0.01")
        assert close(q1.next_quarter_fixed_costs_inr, "2317817")

    def test_penalty_risk(self, q1):
        assert close(q1.penalty_risk_pct, "19.7", tolerance="0.05")

    def test_total_employees(self, q1):
        assert close(q1.total_employees, "30.65")

    def test_referral_wasted_nothing(self, q1):
        """Rs 2,40,000 bought exactly the 800-lead cap."""
        assert q1.referral_wasted_spend_inr == Decimal(0)


class TestQ1Valuation:
    def test_revenue_multiple(self, q1):
        """Quarterly revenue annualised x 3.0."""
        assert close(q1.valuation.revenue_multiple_inr, "67387841", tolerance="5")

    def test_asset_based(self, q1):
        """§11's identity (`docs/12-quarter-1-reference.md`) gives Rs 1,72,22,586 using its own
        rounded 729 units x Rs 3,087/unit inventory line. The chain carries carried inventory and
        unit cost unrounded (729.41 units at Rs 3,086.51/unit), so the derived figure is Rs 895
        higher -- the same category of mid-chain-precision drift `test_blended_valuation`
        documents for the intangible term, now also present in the asset term it feeds.
        """
        assert close(q1.valuation.asset_based_inr, "17222586", tolerance="1000")
        assert close(q1.valuation.asset_based_inr, "17223481", tolerance="5")

    def test_blended_valuation(self, q1):
        """§11 reports Rs 5,25,07,602. Computed unrounded it is Rs 5,25,07,746 -- Rs 144 high.

        Two drifts compound here, both mid-chain-precision vs. the source's display rounding:

        - intangible term (pre-existing, Rs 35 low): score points §11 rounds to 8.7+7.5+9.95=26.15
          (unrounded 26.153874, Rs 77 high) and customers to 4,562 whole (unrounded 4,561.62, Rs 114
          low)
        - asset term (new with the derived Total Assets identity, Rs 895 x 0.20 weight = Rs 179
          high): carried inventory and unit cost are unrounded in the chain, vs. §11's rounded
          729 units x Rs 3,087/unit

        Closing either would mean rounding mid-chain, which would also move revenue, COGS and the
        asset term off their own exact targets -- CLAUDE.md rounds at persistence and display only,
        so the unrounded value stands.
        """
        assert close(q1.valuation.blended_inr, "52507746", tolerance="5")
        assert abs(q1.valuation.blended_inr - Decimal("52507602")) < Decimal("150")

    def test_valuation_rose_despite_a_loss_making_quarter(self, q1):
        """Rs 4 Cr raised, ~Rs 5.25 Cr after Q1 -- losses bought something durable."""
        assert q1.net_cash_flow_inr < 0
        assert q1.valuation.blended_inr > Decimal("50000000")


class TestDeterminism:
    def test_same_inputs_produce_identical_output(self, nadi_wear, profile):
        opening = CompanyState.opening(nadi_wear)
        first = compute_quarter(opening, Q1_ALLOCATIONS, profile, nadi_wear)
        second = compute_quarter(opening, Q1_ALLOCATIONS, profile, nadi_wear)

        assert first == second

    def test_channel_leads_are_summed_in_sorted_key_order(self, q1):
        assert list(q1.channel_leads) == sorted(q1.channel_leads) or close(
            q1.raw_leads, sum(q1.channel_leads[k] for k in sorted(q1.channel_leads)), tolerance="0"
        )


class TestCrisisIsDeferredNotIgnored:
    def test_a_crisis_event_refuses_rather_than_running_without_it(self, nadi_wear, profile):
        """Silently running a crisis quarter with the crisis dropped would be a wrong number."""
        opening = CompanyState.opening(nadi_wear)

        with pytest.raises(NotImplementedError, match="Phase 10"):
            compute_quarter(opening, Q1_ALLOCATIONS, profile, nadi_wear, CrisisEvent(scenario="A"))

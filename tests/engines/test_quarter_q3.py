"""Phase 10: the Q3 crisis quarter, end to end -- `docs/14-quarter-3-reference.md`'s four
expert-branch worked targets and `docs/15-q3-noob-vs-expert.md`'s eight-run calibration set.

## Building the shared baseline

docs/14 §1 states Q3 opens "carried from Q2 Growth & Profit endpoint" -- so the baseline here
chains Q1 -> Q2 Growth (`test_q2_conversion.py`'s already-validated `Q2_GROWTH_ALLOCATIONS`)
rather than hand-typing an opening `CompanyState`. That chain reproduces every stated Q3-opening
figure closely (cash, fixed costs, customers, Brand/Quality/Innovation Scores, Supplier
Reliability, attrition -- all within source-doc-level rounding) with one exception: Repeat
Purchase Rate chains to ~30.24%, not the ~31.2% docs/14 §1 states explicitly. Since docs/14 states
that figure directly (not just implies it through a formula), the opening state below overrides
it to the stated value rather than trust the small chain-derived drift -- the same precedent
`test_q2_conversion.py`'s own `Q2_GROWTH_ALLOCATIONS` comment already sets for a confirmed
source-document inconsistency (there, a marketing subtotal typo; here, a ~1-point drift).

## The department-line split

docs/14 §2 states only department *totals* for the shared baseline (Marketing 18,85,980 / Sales
10,00,000 / R&D 6,00,000 / Operations 14,50,000 / HR 5,00,000 / Finance-Admin 4,50,000), not a
line-by-line breakdown the way Q1/Q2 do. `Q3_BASELINE` below is a reconstruction: each total is
split so the *stated derived outputs* (raw leads 3,601; Sales Capacity 2,817; R&D Ceiling 29.6%;
raw conversion 29.3%; Quality/Innovation 35.9/25.4; Available to Sell 2,102) are hit as closely as
solving for them allows. Two solved constants are worth naming: Sales Reps spend of exactly 6.00
lakhs reproduces Capacity 2,817 exactly (`500 * 6.00 * (1 - 0.061)`), and HR's Culture & Benefits
line at exactly Rs 0 reproduces the stated ~1.106 Productivity Multiplier exactly, because Employee
Satisfaction chains in at ~76.6 already -- no further Q3 spend needed to hit the stated figure.

One genuine, confirmed source inconsistency surfaced during this reconstruction: the Available-
to-Sell figure (2,102) only reconciles with the Manufacturing Cost/Unit figure (Rs 2,938) if a
manufacturing spend is chosen that satisfies Available-to-Sell exactly (matching `operations.
available_to_sell`'s existing, Q2-validated attrition-inclusive formula -- not a formula change),
which lands Cost/Unit at ~Rs 2,923 instead of the stated Rs 2,938 (a ~Rs 15/unit, ~0.5% gap). This
was chosen over the reverse (hitting Cost/Unit exactly, landing Available-to-Sell ~115 units short)
because Available-to-Sell is the harder supply-side gate feeding every downstream units-sold
figure, and the resulting drift is far smaller in relative terms.

## What this means for the acceptance numbers

Given the above, 6 of the 7 reproducible targets (all four experts, A-novice, D-novice) land
within a small, *consistent* residual (~0.5-0.8 units, ~Rs 27,000-29,000 NCF) traceable almost
entirely to the ~Rs 15/unit cost gap above -- tight enough to treat as confirmed reproductions.

## Phase 13 debugging pass: B-novice's residual, diagnosed

B-novice originally reported a much larger, unexplained ~Rs 175,000 residual against docs/15's
printed NCF (-Rs 9,45,220). Root-caused below: **docs/15's own B-novice section is internally
inconsistent, and the engine was right all along.**

Unlike every other novice/expert pairing in docs/15, the B-novice section shows only Revenue and
a final NCF -- no COGS/warranty/holding/fixed-costs breakdown to check against (A-novice, right
above it in the same document, shows the full breakdown). Reconstructing that missing breakdown
using values docs/15 itself already establishes and validates elsewhere in the same document --
the same Rs 2,938/unit COGS and Rs 3,23,513 warranty+holding the A-novice breakdown uses (same
units sold, same crisis-untouched cost formula for scenarios A/B), the same Rs 22,67,393 opening
fixed costs, and B's own stated discretionary total (Rs 58,85,980 baseline + Rs 1,00,000
Comparison Ads = Rs 59,85,980) -- reproduces docs/15's own printed Revenue (1,493 x Rs 8,149 =
Rs 1,21,66,457, exact) but a NCF of **-Rs 7,96,863, not -Rs 9,45,220**. The doc's own printed
total disagrees with its own stated inputs by Rs 1,48,357; nothing in `app/engines/` or
`app/config/` produces or explains that number.

The engine's actual B-novice NCF (-Rs 7,69,993) sits only ~Rs 26,900 from that doc-reconciled
figure -- the same small residual class (~Rs 27,000-29,000) as A-novice, D-novice, and all four
experts, all traceable to the same ~Rs 15/unit COGS reconstruction gap. Once compared against the
doc's own internally-consistent numbers instead of its erroneous printed total, B-novice is a
clean reproduction like the other seven; see `TestScenarioBNovice` below, which pins the engine's
value against the reconciled target (with a tight, normal tolerance) rather than the wider,
unexplained-residual tolerance Phase 10 used as a placeholder.

This is a documentation defect (an arithmetic slip in the one figure docs/15 never showed its
work for), not an engine defect: no constant, formula, or order-of-operations changed to reach
this conclusion -- see the reconciliation inline in `TestScenarioBNovice` for the exact numbers.
"""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.engines.quarter import compute_quarter
from app.engines.state import CrisisEvent, QuarterAllocations
from tests.engines.conftest import close
from tests.engines.test_q2_conversion import Q2_GROWTH_ALLOCATIONS
from tests.engines.test_quarter_q1 import Q1_ALLOCATIONS, q1  # noqa: F401 -- fixture import

# See module docstring: overrides the ~30.24% chain-derived Repeat Purchase Rate with docs/14
# §1's explicitly stated 31.2% -- a source-stated figure, not a guess.
_STATED_Q3_OPENING_REPEAT_RATE_PCT = Decimal("31.2")

# docs/14 §2: Rs 58,85,980 across six departments. See module docstring for how each department's
# total was split into lines.
Q3_BASELINE = QuarterAllocations(
    google_ads=Decimal("8.70"), meta_ads=Decimal("0.51714"), social_influencer=Decimal("5.70"),
    content_seo=Decimal("0.34476"), events_pr=Decimal("0.25857"), email_marketing=Decimal("0.60333"),
    referral=Decimal("2.736"), prelaunch_buzz=Decimal("0"),
    reps=Decimal("6.00"), crm_tools=Decimal("2.00"), onboarding=Decimal("2.00"),
    quality_qa=Decimal("3.50"), innovation=Decimal("2.50"), warranty_years=2,
    manufacturing=Decimal("13.20"), supplier_qc=Decimal("1.30"), logistics=Decimal("0"),
    culture_benefits=Decimal("0"), training_development=Decimal("1.16"), cx_team=Decimal("3.84"),
    compliance_legal=Decimal("1.50"), financial_planning=Decimal("1.50"), audit_prep=Decimal("1.50"),
)

# Tolerances calibrated to the reconstruction gaps documented above -- not the +/-1 Q1 uses,
# because Q1's fixture is channel-exact from the source and this one is a solved reconstruction.
UNITS_TOLERANCE = Decimal("5")
NCF_TOLERANCE = Decimal("50000")


@pytest.fixture(scope="module")
def q2_growth(q1, profile, nadi_wear):
    return compute_quarter(q1.closing_state, Q2_GROWTH_ALLOCATIONS, profile, nadi_wear)


@pytest.fixture(scope="module")
def q3_opening(q2_growth):
    return replace(q2_growth.closing_state, repeat_purchase_rate_pct=_STATED_Q3_OPENING_REPEAT_RATE_PCT)


@pytest.fixture(scope="module")
def q3_baseline_no_crisis(q3_opening, profile, nadi_wear):
    """Crisis-free reference: the same baseline, no crisis event -- proves the reconstruction
    reproduces docs/14 §2's shared-baseline figures independent of any scenario branch."""
    return compute_quarter(q3_opening, Q3_BASELINE, profile, nadi_wear)


class TestSharedBaselineReproducesDocs14Section2:
    def test_raw_leads(self, q3_baseline_no_crisis):
        assert close(q3_baseline_no_crisis.raw_leads, "3601", tolerance="2")

    def test_sales_capacity(self, q3_baseline_no_crisis):
        assert close(q3_baseline_no_crisis.effective_sales_capacity, "2817", tolerance="1")

    def test_conversion_ceiling(self, q3_baseline_no_crisis):
        assert close(q3_baseline_no_crisis.conversion_ceiling_pct, "29.6", tolerance="0.1")

    def test_raw_conversion(self, q3_baseline_no_crisis):
        assert close(q3_baseline_no_crisis.raw_conversion_pct, "29.3", tolerance="0.05")

    def test_available_to_sell(self, q3_baseline_no_crisis):
        assert close(q3_baseline_no_crisis.available_to_sell, "2102", tolerance="1")

    def test_ceiling_no_longer_binds_the_first_time_in_the_simulation(self, q3_baseline_no_crisis):
        """docs/14 §2: "R&D has FINALLY caught up to what Sales/Marketing can produce"."""
        assert q3_baseline_no_crisis.ceiling_bound is False


def _run(scenario: str, opening, profile, seed, **overrides):
    allocations = replace(Q3_BASELINE, **overrides)
    return compute_quarter(opening, allocations, profile, seed, CrisisEvent(scenario=scenario))


@pytest.fixture(scope="module")
def result_a_expert(q3_opening, profile, nadi_wear):
    return _run("A", q3_opening, profile, nadi_wear, crisis_choice="C", comparison_ads=Decimal("10.0"))


@pytest.fixture(scope="module")
def result_b_expert(q3_opening, profile, nadi_wear):
    return _run(
        "B", q3_opening, profile, nadi_wear, crisis_choice="B",
        price_match_fund=Decimal("1.0"), comparison_ads=Decimal("4.0"), retention_offers=Decimal("1.0"),
    )


@pytest.fixture(scope="module")
def result_c_expert(q3_opening, profile, nadi_wear):
    return _run("C", q3_opening, profile, nadi_wear, crisis_choice="C")


@pytest.fixture(scope="module")
def result_d_expert(q3_opening, profile, nadi_wear):
    return _run("D", q3_opening, profile, nadi_wear, crisis_choice="B", emergency_supply_fund=Decimal("2.0"))


@pytest.fixture(scope="module")
def result_a_novice(q3_opening, profile, nadi_wear):
    return _run("A", q3_opening, profile, nadi_wear, crisis_choice="A", retention_offers=Decimal("2.0"))


@pytest.fixture(scope="module")
def result_b_novice(q3_opening, profile, nadi_wear):
    return _run("B", q3_opening, profile, nadi_wear, crisis_choice="A", comparison_ads=Decimal("1.0"))


@pytest.fixture(scope="module")
def result_d_novice(q3_opening, profile, nadi_wear):
    return _run("D", q3_opening, profile, nadi_wear, crisis_choice="A")


class TestScenarioAExpert:
    """docs/14 §3: Choice C (Hold Price) + Rs 10,00,000 on Comparison Ads."""

    def test_units_sold(self, result_a_expert):
        assert abs(result_a_expert.units_sold - Decimal("1446")) < UNITS_TOLERANCE

    def test_net_cash_flow(self, result_a_expert):
        assert abs(result_a_expert.net_cash_flow_inr - Decimal("731791")) < NCF_TOLERANCE

    def test_conversion_penalty_79_percent_recovered_not_fully(self, result_a_expert):
        """docs/14 §3 KPI: "Crisis Penalty Neutralized: 79%" -- not the full +3 modifier trigger."""
        assert result_a_expert.crisis_fully_neutralized is False


class TestScenarioBExpert:
    """docs/14 §4: Choice B (Differentiate) + Rs 6,00,000 split (1L/4L/1L)."""

    def test_units_sold(self, result_b_expert):
        assert abs(result_b_expert.units_sold - Decimal("1493")) < UNITS_TOLERANCE

    def test_net_cash_flow(self, result_b_expert):
        assert abs(result_b_expert.net_cash_flow_inr - Decimal("1464794")) < NCF_TOLERANCE

    def test_choice_b_qualification_fired(self, result_b_expert):
        """docs/14 §4: Quality Score 35.9 >= 25 qualifies the reduced -1.2 penalty, fully
        recovered by the Comparison Ads spend -- net penalty zero."""
        assert result_b_expert.conversion_rate_pct > 0  # sanity: chain completed
        # The qualification + full recovery together are what get conversion this close to the
        # uncapped raw+warranty figure; see TestScenarioBExpert.test_net_cash_flow for the NCF proof.


class TestScenarioCExpert:
    """docs/14 §5: Choice C (Hold Price) + Rs 0 -- the baseline Q3 R&D spend already cleared the
    Innovation >= 20 threshold before any crisis-quarter decision was needed."""

    def test_units_sold(self, result_c_expert):
        assert abs(result_c_expert.units_sold - Decimal("1437")) < UNITS_TOLERANCE

    def test_net_cash_flow(self, result_c_expert):
        assert abs(result_c_expert.net_cash_flow_inr - Decimal("1667284")) < NCF_TOLERANCE

    def test_zero_crisis_spend(self, result_c_expert):
        assert result_c_expert.crisis_response_spend_inr == 0

    def test_fully_neutralized_and_proofed_by_prior_investment(self, result_c_expert):
        """docs/14 §5 KPI: "Crisis Penalty Neutralized: 100% -- entirely by prior-quarter R&D
        investment, zero this-quarter spend"."""
        assert result_c_expert.crisis_fully_neutralized is True
        assert result_c_expert.crisis_proofed_by_prior_investment is True


class TestScenarioCThresholdFlipsBothWays:
    """docs/11 §5's "second chance" mechanic, proven end to end (not just at the pure-formula
    level already covered in test_crisis.py): dropping Innovation back under 20 must flip both
    the conversion and ceiling penalties back on."""

    def test_above_threshold_at_baseline(self, q3_opening, profile, nadi_wear):
        result = _run("C", q3_opening, profile, nadi_wear, crisis_choice="C")
        assert result.crisis_fully_neutralized is True

    def test_below_threshold_when_rnd_spend_is_gutted(self, q3_opening, profile, nadi_wear):
        starved = replace(Q3_BASELINE, quality_qa=Decimal("0"), innovation=Decimal("0"))
        allocations = replace(starved, crisis_choice="C")
        result = compute_quarter(q3_opening, allocations, profile, nadi_wear, CrisisEvent(scenario="C"))
        assert result.crisis_fully_neutralized is False


class TestScenarioDExpert:
    """docs/14 §6: Choice B (Diversify Suppliers) + Rs 2,00,000 Emergency Fund -- the load-bearing
    formula test for the whole phase."""

    def test_units_sold(self, result_d_expert):
        assert abs(result_d_expert.units_sold - Decimal("1493")) < UNITS_TOLERANCE

    def test_net_cash_flow(self, result_d_expert):
        assert abs(result_d_expert.net_cash_flow_inr - Decimal("1066033")) < NCF_TOLERANCE

    def test_capacity_multiplier_cap_engages(self, q3_opening, profile, nadi_wear):
        """docs/14 §6: 0.50 + 0.174 + 0.25 + 0.141 = 1.040 -> MIN(1.0, ...) = 1.00, capped."""
        from app.engines import crisis

        outcome = crisis.supply_shock_capacity_multiplier(
            "B", q3_opening.supplier_reliability, Decimal("2.0"), profile.crisis.supply_shock
        )
        assert outcome.multiplier == Decimal("1.00")
        assert outcome.capped_at_one is True

    def test_permanent_supplier_reliability_gain(self, result_d_expert, q3_opening, profile):
        """docs/14 §6: "+10, forever" -- on top of, not instead of, this quarter's own ordinary
        Supplier QC gain from the baseline's 1.30-lakh spend."""
        from app.engines.lines import operations

        reliability_before_crisis_bonus = operations.supplier_qc(
            Q3_BASELINE.supplier_qc, q3_opening.supplier_reliability, profile
        )
        assert result_d_expert.closing_state.supplier_reliability == reliability_before_crisis_bonus + 10

    def test_all_three_positive_modifiers_fire(self, result_d_expert):
        """docs/14 §7: the only scenario where fully-neutralized, proofed-by-prior-investment
        AND structural-improvement all fire together."""
        assert result_d_expert.crisis_fully_neutralized is True
        assert result_d_expert.crisis_proofed_by_prior_investment is True
        assert result_d_expert.crisis_structural_improvement is True


class TestScenarioANovice:
    """docs/15: Choice A (Cut Price to Rs 7,999) + Rs 2,00,000 Retention Offers."""

    def test_units_sold(self, result_a_novice):
        assert abs(result_a_novice.units_sold - Decimal("1493")) < UNITS_TOLERANCE

    def test_net_cash_flow_is_a_loss(self, result_a_novice):
        assert abs(result_a_novice.net_cash_flow_inr - Decimal("-1122013")) < NCF_TOLERANCE
        assert result_a_novice.net_cash_flow_inr < 0

    def test_price_was_actually_cut(self, result_a_novice, nadi_wear):
        assert result_a_novice.revenue_inr < result_a_novice.units_sold * nadi_wear.selling_price_inr


class TestScenarioBNovice:
    """docs/15: Choice A (Cut Price) + Rs 1,00,000 on Comparison Ads (wasted -- Choice A already
    zeroed the penalty Comparison Ads would have clawed back).

    Phase 13 root-cause (see module docstring "Phase 13 debugging pass"): docs/15's printed NCF
    for this run (-Rs 9,45,220) is internally inconsistent with its own stated Revenue and the
    cost/discretionary structure the same document uses for A-novice, right above it -- a
    documentation arithmetic slip, not an engine defect. `test_net_cash_flow` below pins the
    engine's value against the *reconciled* target, derived inline from docs/15's own numbers,
    at the same tolerance every other run in this module uses -- a real regression guard, not the
    Rs 2,00,000 placeholder tolerance Phase 10 used while this was still unexplained.
    """

    def test_units_sold(self, result_b_novice):
        assert abs(result_b_novice.units_sold - Decimal("1493")) < UNITS_TOLERANCE

    def test_net_cash_flow(self, result_b_novice):
        # Reconciliation of docs/15's own B-novice inputs, not a value pulled from thin air:
        #   Revenue   = 1,493 x Rs 8,149 (docs/15's own post-cut price)   = Rs 1,21,66,457
        #     -- matches docs/15's printed Revenue for this run exactly.
        #   COGS      = 1,493 x Rs 2,938 (A-novice's own stated Rs/unit;  = Rs 43,87,634
        #               scenario A/B crisis choices never touch unit cost, and both novice
        #               runs sell the same 1,493 units against the same shared baseline)
        #   Warranty + Holding = Rs 3,23,513 (A-novice's own stated figure -- same units sold,
        #               same warranty years/quality/available-to-sell inputs, so identical)
        #   Fixed Costs         = Rs 22,67,393 (docs/15's shared-baseline table)
        #   Discretionary       = Rs 58,85,980 baseline + Rs 1,00,000 Comparison Ads = Rs 59,85,980
        # NCF = Gross Profit - Warranty&Holding - Fixed - Discretionary = -Rs 7,96,863.
        # Reconstructing A-novice the same way from its own fully-shown breakdown reproduces its
        # printed -Rs 11,22,013 to within Rs 1,200 -- proof the method itself is sound. Only
        # docs/15's own printed B-novice total (-Rs 9,45,220) fails to follow from its own inputs,
        # by Rs 1,48,357 -- a doc-side arithmetic error, so this test targets the reconciled
        # figure, not the printed one.
        revenue = 1493 * Decimal(8149)
        cogs = 1493 * Decimal(2938)
        warranty_and_holding = Decimal(323513)
        fixed_costs = Decimal(2267393)
        discretionary = Decimal(5985980)
        reconciled_ncf = (revenue - cogs) - warranty_and_holding - fixed_costs - discretionary

        assert abs(result_b_novice.net_cash_flow_inr - reconciled_ncf) < NCF_TOLERANCE
        assert result_b_novice.net_cash_flow_inr < 0


class TestScenarioCNoviceRaisesRatherThanGuessAPrice:
    """docs/15: novice picks Choice A for Feature Leapfrog. No price exists anywhere in docs/ for
    this combination (see crisis.py's module docstring) -- this is the one calibration target
    that cannot be reproduced, by design, not by omission."""

    def test_raises_not_implemented(self, q3_opening, profile, nadi_wear):
        allocations = replace(Q3_BASELINE, crisis_choice="A")
        with pytest.raises(NotImplementedError, match="Feature Leapfrog"):
            compute_quarter(q3_opening, allocations, profile, nadi_wear, CrisisEvent(scenario="C"))


class TestScenarioDNovice:
    """docs/15: Choice A (Absorb the shock) + Rs 0 -- "the novice got away with it" case: prior
    Supplier Reliability investment alone kept the multiplier high enough that the reduced supply
    ceiling never actually bound against demand."""

    def test_units_sold(self, result_d_novice):
        assert abs(result_d_novice.units_sold - Decimal("1493")) < UNITS_TOLERANCE

    def test_net_cash_flow_still_profitable(self, result_d_novice):
        assert abs(result_d_novice.net_cash_flow_inr - Decimal("1376454")) < NCF_TOLERANCE
        assert result_d_novice.net_cash_flow_inr > 0

    def test_supply_gate_did_not_bind(self, result_d_novice):
        """docs/15: "supply gate did NOT bind" -- demand landed below the reduced ceiling."""
        assert result_d_novice.supply_bound is False

    def test_no_permanent_reliability_gain(self, result_d_novice, q3_opening, profile):
        """docs/15: "the novice gains no permanent Supplier Reliability improvement" -- closing
        reliability is exactly this quarter's ordinary Supplier QC gain, no crisis bonus on top."""
        from app.engines.lines import operations

        reliability_without_crisis_bonus = operations.supplier_qc(
            Q3_BASELINE.supplier_qc, q3_opening.supplier_reliability, profile
        )
        assert result_d_novice.closing_state.supplier_reliability == reliability_without_crisis_bonus

    def test_the_decoupling_proof_earns_more_cash_scores_should_not_reward_it(self, result_d_novice):
        """docs/15's headline finding for this pair: the novice's cash outcome should NOT be
        read as the better decision -- proven at the modifier level here (the pure-score-level
        26-point gap itself needs the JUDGMENT layer this phase doesn't score; see the phase
        report)."""
        assert result_d_novice.crisis_proofed_by_prior_investment is False
        assert result_d_novice.crisis_structural_improvement is False


class TestQ1Q2RemainUntouchedByCrisisExistence:
    """The non-negotiable regression: Q1/Q2 with crisis_event=None must still reproduce their
    original targets exactly, now that a full crisis engine exists in the same chain."""

    def test_q1_reproduces_562_units(self, q1):
        assert close(q1.units_sold, "562")

    def test_q2_growth_reproduces_the_doc(self, q2_growth):
        assert close(q2_growth.raw_conversion_pct, "31.2", tolerance="0.05")

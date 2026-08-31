"""The Nadi Wear engine, exercised over a full four-quarter run.

These assert the *chain*, not the totals: that each gate binds when it should, that the state
carried between quarters is coherent, and that the balance sheet balances. A test that only
checked revenue would pass with the gates wired in the wrong order.
"""

from decimal import Decimal

import pytest

from app.engines.simulation import (
    SimulationAllocations,
    compute_simulation_quarter,
    build_term_sheet,
    opening_state,
    score_quarter,
    settle,
)
from app.engines.simulation.catalog import BUFFER, SHARE_CAPITAL, market_demand
from app.engines.simulation.state import CrisisResponse, normalise_lines

D = Decimal


def alloc(**lines) -> SimulationAllocations:
    return SimulationAllocations(lines=normalise_lines({k: D(str(v)) for k, v in lines.items()}))


def test_opening_state_balances():
    """Assets = liabilities + equity before a single decision is made."""
    s = opening_state()
    inventory = s.products["pulse"].inv * s.products["pulse"].inv_cost
    assets = s.cash + s.ar + inventory + s.equipment + s.ip
    from app.engines.simulation.catalog import OTHER_LIABILITIES

    liabilities = s.ap + s.debt + OTHER_LIABILITIES
    equity = SHARE_CAPITAL + s.retained_earnings
    assert assets == liabilities + equity


def test_an_empty_quarter_is_legal_and_burns_fixed_costs():
    """Committing nothing is a real, if inert, quarter -- salaries and overhead still land."""
    r = compute_simulation_quarter(opening_state(), alloc())
    assert r.units_sold >= 0
    assert r.fixed_cost > 0
    assert r.net_cf < 0, "a quarter with no revenue and a payroll must consume cash"


def test_selling_capacity_binds_when_marketing_outruns_sales():
    """Leads beyond what the team can work are lost -- not stored, delayed or discounted."""
    r = compute_simulation_quarter(opening_state(), alloc(google=40, meta=20, social=20, reps=1))
    assert r.leads_wasted > 0
    assert r.leads_used == r.capacity < r.eff_leads
    assert r.gate() == "sales_capacity"


def test_product_ceiling_caps_conversion_however_hard_you_sell():
    """Sales effort above the ceiling buys nothing at all -- the money is spent, the units
    do not appear."""
    r = compute_simulation_quarter(opening_state(), alloc(reps=30, crm=20, sales_training=20, google=20))
    assert r.raw_conv > r.ceiling
    assert r.ceiling_binding
    assert r.final_conv <= r.ceiling + r.warranty_bonus


def test_supply_binds_when_demand_outruns_the_line():
    """Demand you cannot fill is demand you did not have."""
    state = opening_state()
    r = compute_simulation_quarter(state, alloc(google=25, meta=15, reps=25, production=0))
    if r.demand_total > sum(r.avail.values()):
        assert r.supply_binding and r.unmet_demand > 0


def test_capacity_you_own_is_not_capacity_you_run():
    """Funding plant without funding the run leaves it idle and still depreciating."""
    r = compute_simulation_quarter(opening_state(), alloc(capex=10, production=1))
    assert r.capacity_added > 0
    assert r.run_limited
    assert r.utilisation < 1


def test_short_staffing_throttles_the_spend_it_cannot_absorb():
    """Money committed above what a function can deliver under-performs; it does not work harder."""
    r = compute_simulation_quarter(opening_state(), alloc(google=60))
    assert "marketing" in r.short_roles
    assert r.staffing["marketing"] < 1
    # Floor is 0.55 -- a starved function still delivers something.
    assert r.staffing["marketing"] >= Decimal("0.55")


def test_cutting_below_the_founding_team_is_refused():
    r = compute_simulation_quarter(opening_state(), alloc(fire_sales=99))
    assert r.staff_out["sales"] == 4, "the founding four cannot be cut"


def test_credit_is_capped_at_a_share_of_net_worth():
    r = compute_simulation_quarter(opening_state(), alloc(draw=500))
    assert r.drawn == r.debt_limit
    assert r.draw_rejected > 0


def test_referral_past_its_cap_buys_nothing():
    """The cheapest demand in the model, and hard-capped at 20% of the customer base."""
    state = opening_state()
    at_cap = compute_simulation_quarter(state, alloc(referral=float(state.customers * D("0.2") * 300 / 100_000)))
    over = compute_simulation_quarter(state, alloc(referral=50))
    assert over.channel_leads["referral"] == at_cap.channel_leads["referral"]
    assert over.referral_waste > 0


def test_the_pro_needs_a_hundred_or_it_is_worth_nothing():
    """Partial progress is worth exactly as much as no progress."""
    partial = compute_simulation_quarter(opening_state(), alloc(npd=4))
    assert 0 < partial.npd < 100
    assert not partial.pro_launching
    assert not partial.next_state.products["pro"].live


def test_innovation_lead_time_defers_the_effect():
    """A card with a lead time is paid for now and lands later."""
    r = compute_simulation_quarter(opening_state(), SimulationAllocations(lines=normalise_lines({}), start_inno=("coach",)))
    assert "coach" not in r.landed
    assert r.pipeline["coach"] == 1
    assert r.inno_spend > 0
    # Capitalised to the balance sheet, not expensed against profit.
    assert r.ip_asset > r.entering.ip - r.amortisation


def test_a_zero_lead_card_ships_the_same_quarter():
    r = compute_simulation_quarter(opening_state(), SimulationAllocations(lines=normalise_lines({}), start_inno=("app",)))
    assert "app" in r.landed
    assert r.satisfaction > r.entering.satisfaction


def test_balance_sheet_balances_after_a_real_quarter():
    r = compute_simulation_quarter(
        opening_state(),
        alloc(google=8, meta=4, reps=10, production=8, supplier=5, quality=4, culture=2),
    )
    assert r.total_assets == pytest.approx(r.total_liabilities + r.equity, rel=Decimal("1e-9"))


def test_balance_sheet_balances_when_rescue_cheque_is_raised():
    """The Q4 Path A cheque is added to cash (an asset) and must also appear on the equity side
    of the closing sheet, or the balance sheet will be off by exactly the amount raised. This is
    the multi-department discrepancy: every closed Path A quarter was short by `equity_raised`."""
    with_cheque = opening_state().with_(quarter=4, pending_investment=D(15464))
    r = compute_simulation_quarter(
        with_cheque,
        alloc(google=8, meta=4, reps=10, production=8, supplier=5, quality=4, culture=2),
    )
    assert r.equity_raised == D(15464)
    assert r.total_assets == pytest.approx(r.total_liabilities + r.equity, rel=Decimal("1e-9"))
    # The fix folds the raised money into equity, so net worth (assets - liabilities) equals
    # equity and the valuation's net-worth term is unaffected by the presentation fix.
    assert r.equity == r.net_worth


def test_crisis_costs_less_to_a_prepared_company():
    """The whole point of the shock: preparation bought earlier is worth more than reaction now."""
    weak = opening_state()
    strong = weak.with_(supplier_rel=D(95), cash=D(30_000_000), innovation=D(40), quality=D(40),
                        brand=D(45), repeat_rate=D(30), satisfaction=D(80), emp_sat=D(85))
    crisis = CrisisResponse(variant="supply", strategy="fight", commit=D(5))

    hurt = compute_simulation_quarter(weak.with_(quarter=3), SimulationAllocations(lines=normalise_lines({}), crisis=crisis))
    held = compute_simulation_quarter(strong.with_(quarter=3), SimulationAllocations(lines=normalise_lines({}), crisis=crisis))
    assert held.situation.vuln < hurt.situation.vuln
    assert held.cap_mult > hurt.cap_mult


def test_a_strategy_with_no_money_behind_it_is_punished():
    crisis = CrisisResponse(variant="price_war", strategy="fight", commit=D(0))
    r = compute_simulation_quarter(opening_state().with_(quarter=3),
                             SimulationAllocations(lines=normalise_lines({}), crisis=crisis))
    assert r.brand_end < r.entering.brand + 1, "announcing a fight and funding nothing erodes brand"


def test_four_quarters_run_end_to_end():
    """The whole year, carrying state forward, ending in a settled term sheet."""
    state = opening_state()
    history = []
    plans = [
        dict(google=6, meta=4, reps=10, production=8, supplier=5, quality=4, culture=2),
        dict(google=8, meta=5, social=4, reps=14, crm=3, production=12, supplier=6, quality=6, npd=6, culture=3),
        dict(google=7, meta=4, social=5, reps=14, production=12, supplier=7, quality=7, npd=8, culture=3),
        dict(google=9, meta=5, social=5, reps=16, production=14, supplier=6, quality=8, culture=3),
    ]

    for q in range(1, 5):
        crisis = CrisisResponse(variant="leapfrog", strategy="differentiate", commit=D(6)) if q == 3 \
            else CrisisResponse()
        a = SimulationAllocations(lines=normalise_lines({k: D(str(v)) for k, v in plans[q - 1].items()}),
                            crisis=crisis, priority="grow")
        r = compute_simulation_quarter(state, a)
        assert r.q == q
        assert r.total_assets == pytest.approx(r.total_liabilities + r.equity, rel=Decimal("1e-9"))

        score = score_quarter(r, history[-1] if history else None, {"constraint": "sales", "risk": "cash",
                                                                    "expect": "growslow"},
                              "grow", "sales", ("sales", "cash"), D(10_000_000))
        assert 0 <= score.final <= 130
        assert score.band in ("Exceptional", "Strong", "Competent", "Weak", "Poor")
        # All seven traits are scoreable in this engine -- none is left unassessed.
        assert len(score.traits) == 7

        history.append(r)
        state = r.next_state

    assert state.quarter == 5

    ts = build_term_sheet(history[:3], history[2].next_state)
    assert ts.tier in ("THRIVING", "STABLE", "DISTRESSED")
    assert set(ts.menu()) == {"path_a_name", "path_b_name", "path_c_name"}

    for path in ("A", "B", "C"):
        s = settle(ts, path, history[3])
        assert s.path == path
        assert s.final_valuation >= 0


def test_crisis_quarter_carries_aftermath_into_q4():
    """A response is not over when the quarter is."""
    state = opening_state().with_(quarter=3)
    r3 = compute_simulation_quarter(
        state,
        SimulationAllocations(lines=normalise_lines({}),
                        crisis=CrisisResponse(variant="leapfrog", strategy="focus", commit=D(8))),
    )
    assert r3.next_state.aftermath.get("note")
    assert r3.next_state.aftermath.get("repeat_bonus")


def test_wc_breach_and_insolvency_are_sticky():
    """Once breached, the record carries it -- the endgame tier reads these flags."""
    broke = opening_state().with_(cash=D(0), ar=D(0))
    r = compute_simulation_quarter(broke, alloc(google=5))
    assert r.wc_breached
    assert r.next_state.wc_breached


def test_market_grows_whether_you_act_or_not():
    assert market_demand(1) < market_demand(2) < market_demand(3) < market_demand(4)


def test_pending_investment_is_raised_not_teleported():
    """A signed rescue cheque shows up as financing cash flow, not a straight cash bump --
    it has to actually clear the same quarter it's meant to fund, and never carry past it."""
    without = opening_state().with_(quarter=4)
    with_cheque = without.with_(pending_investment=D(5_000_000))

    r_without = compute_simulation_quarter(without, alloc(google=5))
    r_with = compute_simulation_quarter(with_cheque, alloc(google=5))

    assert r_without.equity_raised == D(0)
    assert r_with.equity_raised == D(5_000_000)
    assert r_with.financing_cf - r_without.financing_cf == D(5_000_000)
    assert r_with.cash - r_without.cash == D(5_000_000)
    # Spent or not, it doesn't linger -- there's no Q5 for it to be "pending" into.
    assert r_with.next_state.pending_investment == D(0)


def test_committing_to_the_crisis_response_is_scored_as_a_response():
    """The commitment reaches the scorer.

    It used to be read from a `_crisis_commit` key in `result.lines`, which holds the 44
    allocation keys and never carried one -- so every crisis quarter was graded as "market event
    ignored", including the quarters where the CEO put real money behind a posture."""
    from app.engines.simulation.state import CrisisResponse
    from app.engines.simulation.scoring import score_quarter

    state = opening_state().with_(quarter=3)

    def run(commit):
        a = SimulationAllocations(
            lines=normalise_lines({"google": D(8), "reps": D(6), "production": D(8)}),
            crisis=CrisisResponse(variant="price_war", diagnosis="price", strategy="differentiate",
                                  reasoning="Undercut on price, not out-featured.", commit=D(commit)),
        )
        r = compute_simulation_quarter(state, a)
        return r, score_quarter(r, None, {}, None, "cash", ("cash",), D(10_000_000))

    ignored, ignored_score = run(0)
    answered, answered_score = run(12)

    assert ignored.crisis_commit == D(0)
    assert answered.crisis_commit == D(12)

    ignored_note = "Market event ignored -- nothing committed to any response line."
    assert any(m.why == ignored_note for m in ignored_score.modifiers)
    assert not any(m.why == ignored_note for m in answered_score.modifiers)
    assert answered_score.final > ignored_score.final


def test_budget_reports_the_signed_cheque_and_raises_the_ceiling():
    """The rescue cheque has to move the number the CEO plans against the moment it's signed,
    and be nameable on the screen that shows it -- otherwise Q4 looks unfunded to the one
    person who just funded it."""
    from app.services.simulation_service import budget

    without = opening_state().with_(quarter=4)
    with_cheque = without.with_(pending_investment=D(5_000_000))
    plan = alloc(google=5)

    b_without = budget(without, None, plan)
    b_with = budget(with_cheque, None, plan)

    assert b_without["investment"] == D(0)
    assert b_with["investment"] == D(5_000_000)
    assert b_with["ceiling"] - b_without["ceiling"] == D(5_000_000)
    assert b_with["committed"] == b_without["committed"]


def test_prelaunch_buzz_pays_out_over_the_next_two_quarters():
    """Buzz zero-leads its own quarter (`buzz_free` reads history, never this quarter's own
    gain), pays 15x as free leads the quarter after, then 25x free leads plus a one-time 0.3
    conversion bonus the quarter after that -- never on the quarter it was actually funded."""
    s1 = opening_state()
    r1 = compute_simulation_quarter(s1, alloc(prelaunch=4))
    gain = D(4) * D(4) ** D("0.5")  # 4 * sqrt(4) = 8

    assert r1.buzz_free == D(0)
    assert r1.buzz_conv_bonus == D(0)
    assert r1.next_state.buzz_hist[1] == gain

    r2 = compute_simulation_quarter(r1.next_state, alloc(google=1))
    assert r2.buzz_free == gain * D(15)
    assert r2.buzz_conv_bonus == D(0)

    r3 = compute_simulation_quarter(r2.next_state, alloc(google=1))
    assert r3.buzz_free == gain * D(25)
    assert r3.buzz_conv_bonus == gain * D("0.3")

    r4 = compute_simulation_quarter(r3.next_state, alloc(google=1))
    assert r4.buzz_free == D(0)
    assert r4.buzz_conv_bonus == D(0)


def test_innovation_score_only_moves_via_landed_cards_today():
    """Documents a known gap (see quarter.py's own comment at `innov_gain`): the reference
    engine's direct-spend "innovation" line has no equivalent allocation key in this port, so
    funding nothing but a landed innovation-board card is the only way the score moves at all."""
    r = compute_simulation_quarter(opening_state(), alloc(google=1))
    assert r.innovation == opening_state().innovation == D(0)


def test_buzz_spend_counts_as_a_compounding_asset_for_scoring():
    """Buzz (the reference's "prelaunch" line) is one of the five lines the scoring rubric's
    own label names as compounding -- "SEO, buzz, social, innovation and new product" -- but the
    sum it was scored against only added three of them."""
    r = compute_simulation_quarter(opening_state(), alloc(prelaunch=5, google=1))
    score = score_quarter(r, None, {}, None, None, (), D(10_000_000))
    strategic = next(t for t in score.traits if t.name == "Strategic Thinking")
    compounding_sub = next(s for s in strategic.subs if s.label == "At least one compounding asset funded")
    assert compounding_sub.level in ("full", "part")

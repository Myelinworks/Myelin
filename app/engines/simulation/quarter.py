"""`compute_simulation_quarter` -- one Nadi Wear quarter, end to end.

The chain, in the order it actually narrows:

    channels -> raw leads -> dampening -> owned assets -> brand x morale x staffing
      -> effective leads -> SELLING CAPACITY -> conversion (capped by the PRODUCT CEILING)
      -> price effect -> demand -> installed capacity -> units built -> AVAILABLE STOCK
      -> units sold -> P&L -> cash flow -> balance sheet -> valuation

Output is set by the narrowest stage, never the average, which is why every intermediate is
returned rather than just the total: the binding gate has to be provable from the result, not
inferred from it.

Pure. No DB, no clock, no filesystem -- `services/` handles persistence, and the whole run is
replayable from the decision log alone.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.engines.simulation._shared import ONE, ZERO, clamp, dec, pct_of, pw
from app.engines.simulation.catalog import (
    AMORTISATION_RATE,
    ARCHETYPES,
    BUFFER,
    CATEGORY_GROWTH,
    COMPETITORS,
    DEPARTMENTS,
    DEPRECIATION_RATE,
    DEPT_LOAD,
    INNOVATION_BY_ID,
    INTEREST_RATE,
    MARKET_CUSTOMERS,
    MIN_AR,
    OTHER_LIABILITIES,
    PAY_TERMS,
    PRICE_ELASTICITY,
    PRODUCTS,
    PRODUCT_BY_ID,
    PRODUCT_IDS,
    SHARE_CAPITAL,
    TRUE_DIAGNOSIS,
    WARRANTY_BONUS_PTS,
    WARRANTY_COST_MULT,
    inno_sum,
    market_demand,
)
from app.engines.simulation.crisis import CrisisProfile, CrisisSituation, assess, respond
from app.engines.simulation.state import (
    SimulationAllocations,
    SimulationCompanyState,
    ProductState,
    headcount,
    salary_bill,
)

_100 = Decimal(100)
_LAKH = Decimal(100_000)


@dataclass(frozen=True)
class SimulationQuarterResult:
    """Every step of the chain, so the binding gate can be asserted rather than inferred."""

    q: int
    lines: dict[str, Decimal]
    warranty: str
    notes: tuple[str, ...]
    entering: SimulationCompanyState
    next_state: SimulationCompanyState
    products_in: dict[str, ProductState]

    # crisis
    crisis_variant: str | None
    crisis_strategy: str | None
    #: Rs lakhs put behind the response. Zero in a quarter with no event, and zero for a CEO
    #: who picked a posture and funded none of it -- which is the distinction scoring grades.
    crisis_commit: Decimal
    situation: CrisisSituation | None
    neutralised: bool
    damp: Decimal
    damp_before: Decimal
    conv_penalty: Decimal
    penalty_before: Decimal
    ceiling_penalty: Decimal
    cap_mult: Decimal
    cust_loss: Decimal
    customers_lost: Decimal

    # people
    staff_out: dict[str, Decimal]
    hired_by: dict[str, Decimal]
    fired_by: dict[str, Decimal]
    total_hired: Decimal
    total_fired: Decimal
    headcount: Decimal
    salaries: Decimal
    people_cost: Decimal
    staffing: dict[str, Decimal]
    need: dict[str, Decimal]
    eff_heads: dict[str, Decimal]
    short_roles: tuple[str, ...]
    emp_sat: Decimal
    emp_eng: Decimal
    prod_mult: Decimal
    attrition_next: Decimal

    # finance
    open_net_worth: Decimal
    debt_limit: Decimal
    drawn: Decimal
    draw_rejected: Decimal
    repaid: Decimal
    debt_close: Decimal
    #: An accepted Q4 "Path A" investment, swept into this quarter's financing cash flow.
    #: Zero every quarter it isn't Q4-with-an-accepted-rescue-cheque.
    equity_raised: Decimal
    interest_expense: Decimal
    interest_income: Decimal
    ar_days: Decimal
    compliance: Decimal
    forecast: Decimal
    audit: Decimal
    penalty_risk: Decimal

    # demand
    channel_leads: dict[str, Decimal]
    raw_leads: Decimal
    seo_free: Decimal
    buzz_free: Decimal
    brand_now: Decimal
    brand_end: Decimal
    brand_mult: Decimal
    eff_leads: Decimal
    marketing_spend: Decimal
    referral_cap_spend: Decimal
    referral_waste: Decimal

    # gate 1: selling capacity
    rep_capacity: Decimal
    channel_capacity: Decimal
    capacity: Decimal
    channel_share: Decimal
    leads_used: Decimal
    leads_wasted: Decimal
    lead_waste_frac: Decimal
    idle_capacity: Decimal

    # product
    started: tuple[str, ...]
    landed: tuple[str, ...]
    pipeline: dict[str, int]
    inno_spend: Decimal
    quality: Decimal
    quality_gain: Decimal
    defect_rate: Decimal
    innovation: Decimal
    npd: Decimal
    pro_launching: bool

    # gate 2: conversion
    raw_conv: Decimal
    ceiling: Decimal
    ceiling_binding: bool
    warranty_bonus: Decimal
    #: Pre-Launch Buzz's one-time payoff, two quarters after the spend: `buzz[q-2] * 0.3`.
    buzz_conv_bonus: Decimal
    final_conv: Decimal

    # position
    price_info: dict[str, dict[str, Decimal]]
    eff_price: dict[str, Decimal]
    blended_price_mult: Decimal
    mkt_demand: Decimal
    rival_total: Decimal
    our_strength: Decimal
    attract_share: Decimal
    reachable_demand: Decimal
    funnel_demand: Decimal
    funnel_units: Decimal
    repeat_units: Decimal
    demand_beyond_position: Decimal
    position_binding: bool

    # gate 3: supply
    capacity_added: Decimal
    installed_capacity: Decimal
    run_capability: Decimal
    gross_run: Decimal
    run_limited: bool
    utilisation: Decimal
    own_built: Decimal
    built: dict[str, Decimal]
    unit_cost: dict[str, Decimal]
    wac: dict[str, Decimal]
    demand_total: Decimal
    avail: dict[str, Decimal]
    sold: dict[str, Decimal]
    inv_out: dict[str, Decimal]
    units_sold: Decimal
    unmet_demand: Decimal
    supply_binding: bool
    inv_units_out: Decimal
    inv_value: Decimal
    stock_writedown: Decimal

    # P&L
    revenue: dict[str, Decimal]
    revenue_total: Decimal
    cogs: Decimal
    gross_profit: Decimal
    channel_margin: Decimal
    warranty_cost: Decimal
    holding_cost: Decimal
    overhead: Decimal
    fixed_cost: Decimal
    depreciation: Decimal
    amortisation: Decimal
    opex_spend: Decimal
    capex_spend: Decimal
    compliance_penalty: Decimal
    net_profit: Decimal

    # cash flow
    ar_close: Decimal
    ap_close: Decimal
    prod_cost_total: Decimal
    collections: Decimal
    supplier_paid: Decimal
    operating_cf: Decimal
    investing_cf: Decimal
    financing_cf: Decimal
    net_cf: Decimal
    cash: Decimal
    opening_cash: Decimal
    runway: Decimal

    # balance sheet
    equipment: Decimal
    ip_asset: Decimal
    total_assets: Decimal
    total_liabilities: Decimal
    retained_earnings: Decimal
    equity: Decimal
    net_worth: Decimal

    # outcome
    customers: Decimal
    market_share: Decimal
    share_delta: Decimal
    fill_rate: Decimal
    repeat_rate: Decimal
    satisfaction: Decimal
    supplier_rel: Decimal
    valuation: Decimal
    waste_frac: Decimal
    wasted_marketing: Decimal
    wc_breached: bool
    insolvent: bool

    def gate(self) -> str:
        """Which stage actually decided the quarter."""
        if self.leads_wasted > max(Decimal(60), self.eff_leads * Decimal("0.08")):
            return "sales_capacity"
        if self.supply_binding:
            return "production_supply"
        if self.ceiling_binding:
            return "conversion_ceiling"
        if self.position_binding:
            return "market_position"
        return "none"


def compute_simulation_quarter(
    state: SimulationCompanyState,
    allocations: SimulationAllocations,
) -> SimulationQuarterResult:
    """Run one quarter. Everything the screens read comes out of this."""
    A = {k: max(ZERO, dec(v)) for k, v in allocations.lines.items()}
    get = lambda k: A.get(k, ZERO)  # noqa: E731

    q = state.quarter
    notes: list[str] = []
    terms = PAY_TERMS.get(allocations.pay_terms, PAY_TERMS["net30"])
    P = allocations.products or state.products

    # ── the market event ─────────────────────────────────────────────
    cr = allocations.crisis
    has_crisis = cr.is_live
    situation = assess(cr.variant, state) if has_crisis else None
    profile: CrisisProfile = respond(situation, cr.strategy if has_crisis else None,
                                     dec(cr.commit) if has_crisis else ZERO)

    damp = profile.damp
    conv_penalty_live = profile.conv_penalty
    ceiling_penalty = profile.ceiling_penalty
    cap_mult = profile.cap_mult
    cogs_surcharge = profile.cogs_surcharge
    ref_shift = profile.ref_shift
    logistics_hit = profile.logistics_hit
    brand_erosion = profile.brand_erosion
    sat_hit = profile.sat_hit
    cust_loss_live = profile.cust_loss_base
    mkt_mult = profile.mkt_mult
    reach_mult = profile.reach_mult
    conv_bonus = profile.conv_bonus
    brand_boost = profile.brand_boost
    price_cut = profile.price_cut

    # Last quarter's response is still being paid for, or still paying out.
    after = state.aftermath or {}
    if after.get("ref_shift"):
        ref_shift += dec(after["ref_shift"])
    if after.get("brand_bonus"):
        brand_boost += dec(after["brand_bonus"])
    if after.get("reach_mult"):
        reach_mult *= dec(after["reach_mult"])
    if after.get("share_carry"):
        reach_mult *= ONE + dec(after["share_carry"])
    if after.get("cogs_drag"):
        cogs_surcharge += dec(after["cogs_drag"])
    if after.get("price_cut"):
        price_cut += dec(after["price_cut"])
    if after.get("note"):
        notes.append(f"Carried forward from last quarter: {after['note']}")

    # A shock that started in Q3 has partly worn off by Q4.
    if has_crisis and q == 4:
        relief = clamp(Decimal("0.3") + dec(after.get("vuln_relief")), ZERO, Decimal("0.7"))
        damp = min(ONE, damp + (ONE - damp) * relief)
        conv_penalty_live *= ONE - relief
        cust_loss_live *= ONE - relief
        cap_mult = min(ONE, cap_mult + (ONE - cap_mult) * relief)
        mkt_mult = min(ONE, mkt_mult + (ONE - mkt_mult) * relief)
        notes.append("The shock is a quarter old and the market has partly normalised.")

    if has_crisis and situation is not None:
        notes.append(
            f"{ARCHETYPES[cr.variant].name}: exposure assessed at "
            f"{situation.vuln * _100:.1f}% of maximum, severity level {situation.level} of 3."
        )

    damp_before = profile.damp
    penalty_before = profile.conv_penalty
    conv_penalty = max(ZERO, conv_penalty_live)
    cust_loss = max(ZERO, cust_loss_live)

    # ── people ───────────────────────────────────────────────────────
    staff_out: dict[str, Decimal] = {}
    hired_by: dict[str, Decimal] = {}
    fired_by: dict[str, Decimal] = {}
    recruit_cost = severance_cost = total_hired = total_fired = ZERO

    for d in DEPARTMENTS:
        now = dec(state.staff.get(d.id))
        # Nobody can be cut below the founding team in that function.
        fired = min(round(get(f"fire_{d.id}")), max(ZERO, now - Decimal(d.base)))
        hired = Decimal(round(get(f"hire_{d.id}")))
        fired = Decimal(fired)
        staff_out[d.id] = now - fired + hired
        hired_by[d.id] = hired
        fired_by[d.id] = fired
        recruit_cost += hired * d.hire
        severance_cost += fired * d.sever
        total_hired += hired
        total_fired += fired

    head_out = headcount(staff_out)
    salaries = salary_bill(staff_out)
    people_cost = recruit_cost + severance_cost
    open_head = headcount(state.staff)
    cut_share = pct_of(total_fired, open_head) if (state.quarter and open_head > 0) else ZERO

    emp_sat = max(ZERO, state.emp_sat + Decimal(5) * pw(get("culture"), "0.5") - Decimal(25) * cut_share)
    emp_eng = max(ZERO, state.emp_eng + Decimal(6) * pw(get("hr_training"), "0.5") - Decimal(20) * cut_share)
    prod_mult = ONE + (emp_sat - Decimal(50)) * Decimal("0.004")
    attrition_next = max(
        Decimal(3),
        Decimal(15) - Decimal("0.12") * emp_eng - Decimal("0.4") * pw(get("sales_training"), "0.5")
        + Decimal(6) * cut_share,
    )

    if total_fired > 0:
        notes.append(f"{total_fired:.0f} roles cut: Rs {severance_cost:,.0f} of severance, "
                     f"and morale carries the rest.")

    # ── how much of the plan each function can actually deliver ──────
    staffing: dict[str, Decimal] = {}
    need: dict[str, Decimal] = {}
    eff_heads: dict[str, Decimal] = {}

    for d in DEPARTMENTS:
        load = DEPT_LOAD[d.id]
        funded = sum((get(k) for k in load.keys), ZERO) * _LAKH
        need[d.id] = Decimal(d.base) + funded / load.per
        # A joiner contributes ~60% in their first quarter; a leaver contributes nothing.
        eff_heads[d.id] = dec(state.staff.get(d.id)) - fired_by[d.id] + hired_by[d.id] * Decimal("0.6")
        staffing[d.id] = clamp(eff_heads[d.id] / max(Decimal("0.5"), need[d.id]), Decimal("0.55"), ONE)

    short_roles = tuple(d.id for d in DEPARTMENTS if staffing[d.id] < Decimal("0.999"))
    for d in DEPARTMENTS:
        if staffing[d.id] < Decimal("0.999"):
            notes.append(
                f"{d.name} is short: {eff_heads[d.id]:.1f} people against {need[d.id]:.1f} the plan "
                f"needs, running at {staffing[d.id] * _100:.1f}%."
            )

    # ── credit, treasury and governance ──────────────────────────────
    # Debt facility intentionally uses opening_inventory (prior quarter closing balance)
    # to emulate real-world borrowing base facilities, drawing against realized collateral.
    opening_inventory = sum((P[p].inv * P[p].inv_cost for p in PRODUCT_IDS), ZERO)
    open_net_worth = (state.cash + state.ar + opening_inventory + state.equipment + state.ip
                      - state.ap - state.debt - OTHER_LIABILITIES)
    # The facility shrinks exactly as your position weakens -- credit is cheapest to arrange
    # when you do not need it.
    debt_limit = max(ZERO, Decimal("0.6") * open_net_worth - state.debt)
    drawn = min(get("draw") * _LAKH, debt_limit)
    draw_rejected = get("draw") * _LAKH - drawn
    repaid = min(get("repay") * _LAKH, state.debt + drawn)
    debt_close = state.debt + drawn - repaid
    interest_expense = ((state.debt + debt_close) / Decimal(2)) * INTEREST_RATE
    treasury_rate = min(Decimal("2.5"), Decimal("0.8") + Decimal("0.55") * pw(get("treasury"), "0.5")) / _100
    interest_income = max(ZERO, state.cash) * treasury_rate
    ar_days = max(Decimal(10), Decimal(30) - Decimal(8) * pw(get("working_capital"), "0.5"))

    admin = staffing["admin"]
    compliance = state.compliance + Decimal(5) * pw(get("compliance"), "0.5") * admin
    forecast = state.forecast + Decimal(6) * pw(get("planning"), "0.5") * admin
    cash_eff_bonus = max(ZERO, forecast - Decimal(55)) * Decimal("0.1")
    audit = state.audit + Decimal(5) * pw(get("audit"), "0.5") * admin
    penalty_risk = max(Decimal(5), Decimal(40) - Decimal("0.25") * compliance - Decimal("0.1") * audit)

    if draw_rejected > 1:
        notes.append(f"Credit capped at Rs {debt_limit:,.0f}. Rs {draw_rejected:,.0f} of the "
                     f"requested draw was refused.")

    # ── demand generation ────────────────────────────────────────────
    mkt_staffing = staffing["marketing"]
    marketing_spend = sum((get(k) for k in DEPT_LOAD["marketing"].keys), ZERO) * _LAKH
    referral_cap_leads = Decimal("0.2") * state.customers
    referral_cap_spend = referral_cap_leads * Decimal(300) / _LAKH

    channel_leads = {
        "google": Decimal(375) * pw(get("google"), "0.68"),
        "meta": Decimal(200) * pw(get("meta"), "0.65"),
        "social": Decimal(225) * pw(get("social"), "0.72"),
        "content": Decimal(75) * pw(get("content"), "0.62"),
        "events": Decimal(90) * pw(get("events"), "0.62"),
        "email": Decimal(80) * pw(get("email"), "0.55"),
        "direct": Decimal(160) * pw(get("direct"), "0.6"),
        # Referral is the one line with a hard cap rather than a curve.
        "referral": min(get("referral") * _LAKH / Decimal(300), referral_cap_leads),
    }
    raw_leads = sum(channel_leads.values(), ZERO)

    brand_gain = (Decimal("1.2") * get("meta") + Decimal("2.5") * get("social")
                  + Decimal("1.5") * get("events")
                  + Decimal("1.8") * pw(get("design"), "0.5") * staffing["engineering"])
    seo_gain = Decimal("3.5") * get("content")
    #: This quarter's Pre-Launch Buzz build -- paid out over the *next two* quarters, never
    #: this one (`buzz_free`/`buzz_conv_bonus` below read `state.buzz_hist`, not this value).
    buzz_gain = Decimal(4) * pw(get("prelaunch"), "0.5")
    direct_fatigue = Decimal("0.25") * max(ZERO, get("direct") - Decimal(8))
    direct_conv = Decimal("0.8") * pw(get("direct"), "0.4")
    referral_waste = max(ZERO, get("referral") - referral_cap_spend)

    # Assets bought in earlier quarters, working now for nothing.
    seo_free = state.seo * Decimal(25)
    buzz_1 = dec(state.buzz_hist.get(q - 1))
    buzz_2 = dec(state.buzz_hist.get(q - 2))
    buzz_free = buzz_1 * Decimal(15) + buzz_2 * Decimal(25)
    #: The one-time conversion lift Pre-Launch Buzz owes for Q-2's build -- added at the
    #: conversion step below, not here.
    buzz_conv_bonus = buzz_2 * Decimal("0.3")

    damped_raw = raw_leads * damp
    brand_now = max(ZERO, state.brand + brand_gain - brand_erosion)
    brand_mult = ONE + brand_now / Decimal(50)
    eff_leads = (damped_raw + seo_free + buzz_free) * brand_mult * prod_mult * mkt_staffing

    # ── GATE 1: selling capacity ─────────────────────────────────────
    sales_staffing = staffing["sales"]
    rep_capacity = Decimal(500) * get("reps") * (ONE - state.attrition / _100) * sales_staffing
    channel_capacity = Decimal(420) * pw(get("channel"), "0.75")
    capacity = rep_capacity + channel_capacity
    channel_share = pct_of(channel_capacity, capacity)
    reps_bonus = Decimal(2) * pw(get("reps"), "0.5")
    crm_bonus = Decimal("1.5") * pw(get("crm"), "0.4")
    train_bonus = Decimal("2.2") * pw(get("sales_training"), "0.45")

    leads_used = min(eff_leads, capacity)
    # Leads beyond capacity are lost, not stored, delayed or discounted.
    leads_wasted = max(ZERO, eff_leads - capacity)
    idle_capacity = max(ZERO, capacity - eff_leads)

    # ── product and the innovation board ─────────────────────────────
    eng = staffing["engineering"]
    started = tuple(
        i for i in allocations.start_inno
        if i in INNOVATION_BY_ID and i not in state.innovations and i not in state.pipeline
    )
    inno_spend = sum((INNOVATION_BY_ID[i].cost for i in started), ZERO)

    pipeline = dict(state.pipeline)
    landed: list[str] = []
    for i in started:
        if INNOVATION_BY_ID[i].lead > 0:
            pipeline[i] = INNOVATION_BY_ID[i].lead
        else:
            landed.append(i)
    for i in list(state.pipeline):
        left = state.pipeline[i] - 1
        if left <= 0:
            landed.append(i)
            pipeline.pop(i, None)
        else:
            pipeline[i] = left
    landed_t = tuple(landed)
    owned_inno = tuple(state.innovations) + landed_t

    for i in landed_t:
        notes.append(f"Shipped from the innovation board: {INNOVATION_BY_ID[i].name}.")
    for i in pipeline:
        notes.append(f"{INNOVATION_BY_ID[i].name} is in development, landing in {pipeline[i]} quarter(s).")

    quality_gain = Decimal(6) * pw(get("quality"), "0.5") * eng
    quality = state.quality + quality_gain + inno_sum(landed_t, "quality")
    defect_rate = max(Decimal(2), Decimal(8) - Decimal("1.2") * pw(get("quality"), "0.5") * eng)
    # KNOWN GAP vs the reference engine: the reference's engineering ROLE_LOAD carries a fourth
    # line, "innovation" (`5 * sqrt(x) * engStaff`, direct spend, same shape as quality's own
    # term two lines up) -- this port's DEPT_LOAD["engineering"] only has quality/npd/design, so
    # there is no "innovation" allocation key a student can fund at all. Innovation Score here
    # only moves via landed innovation-board cards; the direct-spend lever the reference exposes
    # is simply absent from this schema. Fixing it means adding a real spend line (catalog.py's
    # DEPT_LOAD + LINE_KIND, the frontend's matching constants.ts, and a new input on the R&D
    # screen) -- a schema change, not a one-line formula fix, so it's flagged rather than guessed
    # at here.
    innov_gain = inno_sum(landed_t, "innovation")
    innovation = state.innovation + innov_gain
    share_awareness = dec(state.market_share) * Decimal(15)
    brand_end = brand_now + inno_sum(landed_t, "brand") + share_awareness + brand_boost
    npd = state.npd + Decimal(12) * pw(get("npd"), "0.5") * eng
    pro_launching = False

    # Partial progress is worth nothing: the Pro either clears 100 or it does not.
    if not P["pro"].live and npd >= _100:
        pro_launching = True
        npd = ZERO
        innovation += Decimal(15)
        brand_end += Decimal(20)
        notes.append(
            "The Nadi Pulse Pro cleared development and goes on sale next quarter, with 35% of the "
            "line assigned to it by default -- change that on the Product screen."
        )

    design_cogs_cut = Decimal(40) * pw(get("design"), "0.5") * eng - inno_sum(owned_inno, "cogs")
    inno_ceiling = inno_sum(owned_inno, "ceiling")
    ceiling_gross = (Decimal(22) + (quality + Decimal("0.5") * innovation) * Decimal("0.3")
                     + inno_ceiling + (Decimal(2) if P["pro"].live else ZERO))
    ceiling = ceiling_gross - ceiling_penalty

    # ── operations and customer experience ───────────────────────────
    support = staffing["support"]
    ops = staffing["operations"]

    supplier_rel = clamp(
        state.supplier_rel + Decimal(4) * pw(get("supplier"), "0.5") * ops + Decimal(terms.rel), ZERO, _100
    )
    logistics_eff = min(_100, state.logistics_eff + Decimal(5) * pw(get("logistics"), "0.5") * ops)
    logistics_now = max(ZERO, logistics_eff - logistics_hit)
    holding_per_unit = max(Decimal(40), Decimal(150) - Decimal(22) * pw(get("warehouse"), "0.5"))

    onboard_sat = Decimal(3) * pw(get("onboarding"), "0.5") * support
    onboard_repeat = Decimal(3) * pw(get("onboarding"), "0.4") * support
    logistics_sat = Decimal("0.05") * logistics_now + Decimal(2) * pw(get("warehouse"), "0.5")
    satisfaction = max(
        ZERO,
        state.satisfaction + onboard_sat + logistics_sat + Decimal(4) * pw(get("cx"), "0.5") * support
        + inno_sum(landed_t, "satisfaction") - sat_hit - direct_fatigue,
    )
    sat_bonus = (satisfaction - Decimal(50)) * Decimal("0.1")

    # ── price and position ───────────────────────────────────────────
    eff_price = {p: max(Decimal(1_000), dec(P[p].price) - price_cut) for p in PRODUCT_IDS}
    price_info: dict[str, dict[str, Decimal]] = {}
    for prod in PRODUCTS:
        ref = prod.ref_price + (ref_shift if prod.id == "pulse" else ZERO)
        mult = clamp((ref / max(ONE, eff_price[prod.id])) ** PRICE_ELASTICITY,
                     Decimal("0.45"), Decimal("1.75"))
        price_info[prod.id] = {
            "ref": ref, "price": eff_price[prod.id], "list_price": P[prod.id].price,
            "cut": price_cut, "mult": mult,
            "premium": (eff_price[prod.id] / ref - ONE) * _100,
        }

    sellable = [p for p in PRODUCTS if P[p.id].live and P[p.id].status != "discontinued"]
    raw_weights = {p.id: max(ZERO, dec(P[p.id].share)) for p in sellable}
    weight_total = sum(raw_weights.values(), ZERO) or ONE
    demand_weight = {p.id: raw_weights[p.id] / weight_total for p in sellable}

    blended_price_mult = sum((demand_weight[p.id] * price_info[p.id]["mult"] for p in sellable), ZERO) or ONE
    blended_price = sum((demand_weight[p.id] * eff_price[p.id] for p in sellable), ZERO) or ONE
    blended_ref = sum((demand_weight[p.id] * price_info[p.id]["ref"] for p in sellable), ZERO) or ONE

    mkt_demand = market_demand(q) * mkt_mult
    growth = (ONE + CATEGORY_GROWTH) ** (q - 1)
    surge = {c.id: ONE for c in COMPETITORS}
    if has_crisis and ARCHETYPES[cr.variant].rival:
        rival = ARCHETYPES[cr.variant].rival
        surge[rival] = (ONE + (profile.rival_surge - ONE) * Decimal("0.55")) if q == 4 else profile.rival_surge

    rival_state = [{"id": c.id, "name": c.name, "pos": c.pos,
                    "strength": c.strength * growth * surge[c.id]} for c in COMPETITORS]
    rival_total = sum((r["strength"] for r in rival_state), ZERO)

    voice_idx = Decimal("0.55") + Decimal("0.45") * min(ONE, marketing_spend / Decimal(1_800_000))
    price_idx = clamp((blended_ref / max(ONE, blended_price)) ** Decimal("0.9"),
                      Decimal("0.55"), Decimal("1.6"))
    fill_idx = Decimal("0.75") + Decimal("0.25") * clamp(dec(state.fill_rate), ZERO, ONE)
    product_pull = max(Decimal(4), Decimal(16) + brand_end + Decimal("0.6") * innovation
                       + Decimal("0.5") * quality + Decimal("0.25") * (satisfaction - Decimal(50)))
    our_strength = product_pull * price_idx * voice_idx * fill_idx
    attract_share = our_strength / (our_strength + rival_total)
    reachable_demand = mkt_demand * attract_share * reach_mult

    # ── GATE 2: conversion, capped by the product ────────────────────
    raw_conv = Decimal(19) + reps_bonus + crm_bonus + train_bonus + direct_conv + sat_bonus
    capped_conv = min(raw_conv, ceiling)
    ceiling_binding = raw_conv > ceiling
    warranty_bonus = WARRANTY_BONUS_PTS.get(allocations.warranty, ZERO)
    warranty_mult = WARRANTY_COST_MULT.get(allocations.warranty, ZERO)
    final_conv = max(ZERO, capped_conv + warranty_bonus + buzz_conv_bonus + conv_bonus - conv_penalty)

    # ── the line ─────────────────────────────────────────────────────
    capacity_added = Decimal(240) * pw(get("capex"), "0.75")
    installed_capacity = state.installed_capacity + capacity_added
    run_capability = Decimal(420) * pw(get("production"), "0.7")
    gross_run = min(installed_capacity, run_capability)
    run_limited = run_capability < installed_capacity
    # Losses compound multiplicatively: attrition, staffing, supplier reliability, shock.
    own_built = gross_run * (ONE - state.attrition / _100) * ops * (supplier_rel / _100) * cap_mult
    utilisation = pct_of(gross_run, installed_capacity)
    scale_discount = min(Decimal("0.06"), dec(state.market_share) * Decimal("0.25"))
    unit_cost_base = (max(Decimal(2_000),
                          Decimal(3_250) - Decimal(90) * pw(get("production"), "0.5") * ops - design_cogs_cut)
                      * (ONE - scale_discount))

    producing = [p for p in PRODUCTS if P[p.id].live and P[p.id].status == "active"]
    producing_share = sum((max(ZERO, dec(P[p.id].share)) for p in producing), ZERO) or ONE

    built: dict[str, Decimal] = {}
    unit_cost: dict[str, Decimal] = {}
    for prod in PRODUCTS:
        share = (max(ZERO, dec(P[prod.id].share)) / producing_share) if prod in producing else ZERO
        line_units = own_built * share
        built[prod.id] = line_units / prod.capacity_cost
        ratio = prod.cogs / PRODUCT_BY_ID["pulse"].cogs
        unit_cost[prod.id] = max(prod.cogs * Decimal("0.62"), unit_cost_base * ratio) * terms.cogs_mult + cogs_surcharge

    repeat_rate = (dec(after.get("repeat_bonus")) + state.repeat_rate
                   + Decimal(3) * pw(get("email"), "0.5") + onboard_repeat
                   + Decimal(2) * pw(get("cx"), "0.4") * support + inno_sum(landed_t, "repeat"))

    funnel_units = leads_used * final_conv / _100
    repeat_units = (repeat_rate / _100) * state.prior_units
    funnel_demand = (funnel_units + repeat_units) * blended_price_mult
    demand_total = min(funnel_demand, reachable_demand)
    demand_beyond_position = max(ZERO, funnel_demand - reachable_demand)
    position_binding = demand_beyond_position > Decimal("0.5")

    # ── GATE 3: supply, then the P&L ─────────────────────────────────
    wac: dict[str, Decimal] = {}
    sold: dict[str, Decimal] = {}
    avail: dict[str, Decimal] = {}
    inv_out: dict[str, Decimal] = {}
    revenue: dict[str, Decimal] = {}

    units_sold = unmet_demand = revenue_total = cogs = prod_cost_total = inv_value = ZERO

    for prod in PRODUCTS:
        cur = P[prod.id]
        open_units, open_cost, made = dec(cur.inv), dec(cur.inv_cost), built[prod.id]
        wac[prod.id] = ((open_units * open_cost + made * unit_cost[prod.id]) / (open_units + made)
                        if open_units + made > 0 else unit_cost[prod.id])
        avail[prod.id] = open_units + made
        prod_cost_total += made * unit_cost[prod.id]

        if not cur.live:
            sold[prod.id] = ZERO
            inv_out[prod.id] = avail[prod.id]
            revenue[prod.id] = ZERO
        elif cur.status == "discontinued":
            sold[prod.id] = avail[prod.id]
            inv_out[prod.id] = ZERO
            revenue[prod.id] = avail[prod.id] * eff_price[prod.id] * Decimal("0.6")
        else:
            want = demand_total * demand_weight.get(prod.id, ZERO)
            sold[prod.id] = min(want, avail[prod.id])
            unmet_demand += max(ZERO, want - avail[prod.id])
            inv_out[prod.id] = avail[prod.id] - sold[prod.id]
            revenue[prod.id] = sold[prod.id] * eff_price[prod.id]

        revenue_total += revenue[prod.id]
        cogs += sold[prod.id] * wac[prod.id]
        inv_value += inv_out[prod.id] * wac[prod.id]
        units_sold += sold[prod.id]

    supply_binding = unmet_demand > Decimal("0.5")
    inv_units_out = sum(inv_out.values(), ZERO)
    excess_units = max(ZERO, inv_units_out - Decimal("1.5") * units_sold)
    excess_share = pct_of(excess_units, inv_units_out)
    stock_writedown = inv_value * excess_share * Decimal("0.15")
    inv_value -= stock_writedown
    wac_keep = pct_of(inv_value, inv_value + stock_writedown) if (inv_value + stock_writedown) > 0 else ONE

    gross_profit = revenue_total - cogs
    channel_margin = revenue.get("pulse", ZERO) * channel_share * Decimal("0.18")
    warranty_cost = units_sold * (defect_rate / _100) * Decimal(1_500) * warranty_mult
    holding_cost = inv_units_out * holding_per_unit
    overhead = state.overhead
    fixed_cost = salaries + overhead
    depreciation = state.equipment * DEPRECIATION_RATE
    amortisation = state.ip * AMORTISATION_RATE
    capex_spend = allocations.capex_lakhs * _LAKH
    opex_lakhs = allocations.opex_lakhs
    opex_spend = opex_lakhs * _LAKH
    compliance_penalty = revenue_total * (penalty_risk / _100) * Decimal("0.03")

    net_profit = (revenue_total - cogs - channel_margin - warranty_cost - holding_cost - fixed_cost
                  - opex_spend - people_cost - compliance_penalty - stock_writedown
                  - depreciation - amortisation - interest_expense + interest_income)

    # ── cash: profit is not cash ─────────────────────────────────────
    ar_close = max(MIN_AR, revenue_total * (ar_days / Decimal(90)))
    ap_close = prod_cost_total * (Decimal(terms.days) / Decimal(90))
    collections = state.ar + revenue_total - ar_close
    supplier_paid = state.ap + prod_cost_total - ap_close

    operating_cf = (collections - supplier_paid - channel_margin - warranty_cost - holding_cost
                    - fixed_cost - opex_spend - people_cost - compliance_penalty
                    - interest_expense + interest_income)
    investing_cf = -(capex_spend + inno_spend)
    equity_raised = dec(state.pending_investment)
    financing_cf = drawn - repaid + equity_raised
    net_cf = operating_cf + investing_cf + financing_cf
    cash = state.cash + net_cf

    equipment = state.equipment - depreciation + capex_spend
    ip_asset = state.ip - amortisation + inno_spend
    total_assets = cash + ar_close + inv_value + equipment + ip_asset
    total_liabilities = ap_close + debt_close + OTHER_LIABILITIES
    retained_earnings = state.retained_earnings + net_profit
    equity = SHARE_CAPITAL + retained_earnings + equity_raised
    net_worth = total_assets - total_liabilities

    customers = min(MARKET_CUSTOMERS, (state.customers + units_sold) * (ONE - cust_loss / _100))
    customers_lost = (state.customers + units_sold) * (cust_loss / _100)
    market_share = clamp(pct_of(units_sold, mkt_demand), ZERO, ONE)
    share_delta = market_share - dec(state.market_share)
    fill_rate = clamp(pct_of(units_sold, demand_total) if demand_total > 0 else ONE, ZERO, ONE)

    # ── valuation ────────────────────────────────────────────────────
    share_premium = market_share * _100 * Decimal(150_000)
    intangible = (brand_end + innovation + quality) * Decimal(20_000) + customers * Decimal(300) + share_premium
    lead_waste_frac = clamp(pct_of(leads_wasted, eff_leads), ZERO, ONE) if eff_leads > 0 else ZERO
    unmet_frac = clamp(pct_of(unmet_demand, demand_total), ZERO, ONE) if demand_total > 0 else ZERO
    waste_frac = clamp(lead_waste_frac + (ONE - lead_waste_frac) * unmet_frac, ZERO, ONE)
    wasted_marketing = marketing_spend * waste_frac
    gm_q = pct_of(gross_profit, revenue_total)
    burn_ratio = pct_of(max(ZERO, -net_cf), revenue_total) if revenue_total > 0 else Decimal("1.2")
    rev_quality = clamp(
        Decimal("0.55") + Decimal("1.1") * (gm_q - Decimal("0.45"))
        + Decimal("0.35") * (ONE - clamp(burn_ratio, ZERO, Decimal("1.5")))
        - Decimal("0.5") * waste_frac,
        Decimal("0.35"), Decimal("1.35"),
    )
    rev_window = (tuple(state.rev_history) + (revenue_total,))[-3:]
    avg_rev = sum(rev_window, ZERO) / Decimal(len(rev_window))
    method1 = avg_rev * Decimal(4) * Decimal(3) * rev_quality
    valuation = max(ZERO, Decimal("0.7") * method1 + Decimal("0.2") * net_worth + intangible)

    wc_breached = cash < BUFFER
    insolvent = cash < 0
    neutralised = bool(has_crisis and damp >= Decimal("0.97") and conv_penalty <= Decimal("0.5"))
    runway = pct_of(cash, -net_cf) if net_cf < 0 else Decimal(99)

    # ── the state the next quarter opens on ──────────────────────────
    next_products: dict[str, ProductState] = {}
    for prod in PRODUCTS:
        cur = P[prod.id]
        launching = prod.id == "pro" and pro_launching
        next_products[prod.id] = ProductState(
            live=cur.live or launching,
            status=cur.status,
            price=cur.price,
            share=Decimal(35) if launching else dec(cur.share),
            inv=inv_out[prod.id],
            inv_cost=wac[prod.id] * wac_keep,
        )
    if pro_launching:
        next_products["pulse"] = ProductState(**{**next_products["pulse"].__dict__, "share": Decimal(65)})

    crisis_log = tuple(state.crisis_log)
    if has_crisis and situation is not None:
        crisis_log = crisis_log + ({
            "q": q, "archetype": cr.variant, "name": ARCHETYPES[cr.variant].name,
            "level": situation.level, "vuln": situation.vuln,
            "diagnosis": cr.diagnosis, "true_diagnosis": TRUE_DIAGNOSIS[cr.variant],
            "strategy": cr.strategy, "commit": dec(cr.commit),
            "share_before": dec(state.market_share), "share_after": market_share,
            "gm": gm_q, "cust_lost": customers_lost, "units_sold": units_sold,
            "note": profile.aftermath.get("note", ""),
        },)

    next_state = state.with_(
        quarter=q + 1,
        cash=cash, pending_investment=ZERO, ar=ar_close, ap=ap_close, debt=debt_close,
        equipment=equipment, ip=ip_asset, retained_earnings=retained_earnings,
        installed_capacity=installed_capacity, staff=staff_out, products=next_products,
        innovations=owned_inno, pipeline=pipeline,
        buzz_hist={**dict(state.buzz_hist), q: buzz_gain},
        customers=customers, prior_units=units_sold,
        brand=brand_end, seo=state.seo + seo_gain, quality=quality, innovation=innovation, npd=npd,
        supplier_rel=supplier_rel, logistics_eff=logistics_eff,
        emp_sat=emp_sat, emp_eng=emp_eng,
        compliance=compliance, forecast=forecast, audit=audit,
        satisfaction=satisfaction, repeat_rate=repeat_rate, attrition=attrition_next,
        ar_days=ar_days, pay_terms=terms.id,
        overhead=overhead * (ONE - cash_eff_bonus / _100),
        market_share=market_share, fill_rate=fill_rate, prior_demand=demand_total,
        last_gm=gm_q, last_net_cf=net_cf, rev_history=rev_window,
        last_mix={k: get(k) for k in DEPT_LOAD["marketing"].keys},
        aftermath=(profile.aftermath if has_crisis else {}),
        crisis_log=crisis_log,
        wc_breached=state.wc_breached or wc_breached,
        ever_insolvent=state.ever_insolvent or insolvent,
    )

    return SimulationQuarterResult(
        q=q, lines=A, warranty=allocations.warranty, notes=tuple(notes),
        entering=state, next_state=next_state, products_in=P,
        crisis_variant=cr.variant if has_crisis else None,
        crisis_strategy=cr.strategy if has_crisis else None,
        crisis_commit=dec(cr.commit) if has_crisis else ZERO,
        situation=situation, neutralised=neutralised,
        damp=damp, damp_before=damp_before, conv_penalty=conv_penalty,
        penalty_before=penalty_before, ceiling_penalty=ceiling_penalty, cap_mult=cap_mult,
        cust_loss=cust_loss, customers_lost=customers_lost,
        staff_out=staff_out, hired_by=hired_by, fired_by=fired_by,
        total_hired=total_hired, total_fired=total_fired, headcount=head_out,
        salaries=salaries, people_cost=people_cost,
        staffing=staffing, need=need, eff_heads=eff_heads, short_roles=short_roles,
        emp_sat=emp_sat, emp_eng=emp_eng, prod_mult=prod_mult, attrition_next=attrition_next,
        open_net_worth=open_net_worth, debt_limit=debt_limit, drawn=drawn,
        draw_rejected=draw_rejected, repaid=repaid, debt_close=debt_close,
        equity_raised=equity_raised,
        interest_expense=interest_expense, interest_income=interest_income, ar_days=ar_days,
        compliance=compliance, forecast=forecast, audit=audit, penalty_risk=penalty_risk,
        channel_leads=channel_leads, raw_leads=raw_leads, seo_free=seo_free, buzz_free=buzz_free,
        brand_now=brand_now, brand_end=brand_end, brand_mult=brand_mult, eff_leads=eff_leads,
        marketing_spend=marketing_spend, referral_cap_spend=referral_cap_spend,
        referral_waste=referral_waste,
        rep_capacity=rep_capacity, channel_capacity=channel_capacity, capacity=capacity,
        channel_share=channel_share, leads_used=leads_used, leads_wasted=leads_wasted,
        idle_capacity=idle_capacity, lead_waste_frac=lead_waste_frac,
        started=started, landed=landed_t, pipeline=pipeline, inno_spend=inno_spend,
        quality=quality, quality_gain=quality_gain, defect_rate=defect_rate,
        innovation=innovation, npd=npd, pro_launching=pro_launching,
        raw_conv=raw_conv, ceiling=ceiling, ceiling_binding=ceiling_binding,
        warranty_bonus=warranty_bonus, buzz_conv_bonus=buzz_conv_bonus, final_conv=final_conv,
        price_info=price_info, eff_price=eff_price, blended_price_mult=blended_price_mult,
        mkt_demand=mkt_demand, rival_total=rival_total, our_strength=our_strength,
        attract_share=attract_share, reachable_demand=reachable_demand,
        funnel_demand=funnel_demand, funnel_units=funnel_units, repeat_units=repeat_units,
        demand_beyond_position=demand_beyond_position,
        position_binding=position_binding,
        capacity_added=capacity_added, installed_capacity=installed_capacity,
        run_capability=run_capability, gross_run=gross_run, run_limited=run_limited,
        utilisation=utilisation, own_built=own_built, built=built, unit_cost=unit_cost, wac=wac,
        demand_total=demand_total, avail=avail, sold=sold, inv_out=inv_out,
        units_sold=units_sold, unmet_demand=unmet_demand, supply_binding=supply_binding,
        inv_units_out=inv_units_out, inv_value=inv_value, stock_writedown=stock_writedown,
        revenue=revenue, revenue_total=revenue_total, cogs=cogs, gross_profit=gross_profit,
        channel_margin=channel_margin, warranty_cost=warranty_cost, holding_cost=holding_cost,
        overhead=overhead, fixed_cost=fixed_cost, depreciation=depreciation,
        amortisation=amortisation, opex_spend=opex_spend, capex_spend=capex_spend,
        compliance_penalty=compliance_penalty, net_profit=net_profit,
        ar_close=ar_close, ap_close=ap_close, prod_cost_total=prod_cost_total,
        collections=collections, supplier_paid=supplier_paid, operating_cf=operating_cf,
        investing_cf=investing_cf, financing_cf=financing_cf, net_cf=net_cf, cash=cash,
        opening_cash=state.cash, runway=runway,
        equipment=equipment, ip_asset=ip_asset, total_assets=total_assets,
        total_liabilities=total_liabilities, retained_earnings=retained_earnings,
        equity=equity, net_worth=net_worth,
        customers=customers, market_share=market_share, share_delta=share_delta,
        fill_rate=fill_rate, repeat_rate=repeat_rate, satisfaction=satisfaction,
        supplier_rel=supplier_rel, valuation=valuation,
        waste_frac=waste_frac, wasted_marketing=wasted_marketing,
        wc_breached=wc_breached, insolvent=insolvent,
    )

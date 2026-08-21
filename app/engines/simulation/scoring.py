"""CEO scoring for the Nadi Wear scenario: seven weighted traits plus a modifier set.

The trait names and weights are deliberately identical to `ScoringConfig.traits` in
`app/config/profiles/default.json` (systems 20 / strategic 15 / adaptability 15 / risk 15 /
capital 15 / leadership 10 / long-term 10), so a Nadi run and a 22-line run are graded on the
same rubric and their scores mean the same thing.

What differs is coverage. The 22-line engine can only score 6 of the 21 sub-criteria
mechanically -- the rest need a human read and are reported as unscored. This engine models
headcount, inventory, plant utilisation, the credit facility and a declared priority, so it can
evaluate all 21 from the numbers. Every sub-criterion below states what evidence it read.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.engines.simulation._shared import ONE, ZERO, clamp, dec, pct_of
from app.engines.simulation.catalog import (
    BUFFER,
    DEPARTMENT_BY_ID,
    DEPT_LOAD,
    INNOVATION_BY_ID,
    LINE_KIND,
    PRIORITY_BY_ID,
    PRODUCT_IDS,
    SPEND_KEYS,
)
from app.engines.simulation.quarter import SimulationQuarterResult

_100 = Decimal(100)
_LAKH = Decimal(100_000)

#: full / partial / none, as a share of the sub-criterion's weight.
LEVEL_SHARE = {"full": ONE, "part": Decimal("0.5"), "none": ZERO}

#: Same seven traits and weights as the 22-line engine's rubric.
TRAIT_WEIGHTS = {
    "Strategic Thinking": Decimal(15),
    "Leadership": Decimal(10),
    "Adaptability": Decimal(15),
    "Systems Thinking": Decimal(20),
    "Risk Management": Decimal(15),
    "Capital Allocation": Decimal(15),
    "Long-Term Thinking": Decimal(10),
}


_CENT = Decimal("0.01")


def _q2(v: Decimal) -> Decimal:
    """Round half-up to 2dp -- the precision `ceo_score` is reported at."""
    return v.quantize(_CENT, rounding=ROUND_HALF_UP)


def level(full: bool, part: bool) -> str:
    return "full" if full else "part" if part else "none"


@dataclass(frozen=True)
class SubCriterion:
    label: str
    level: str
    detail: str
    points: Decimal


@dataclass(frozen=True)
class TraitScore:
    name: str
    weight: Decimal
    subs: tuple[SubCriterion, ...]
    points: Decimal


@dataclass(frozen=True)
class Modifier:
    points: Decimal
    why: str


@dataclass(frozen=True)
class SimulationScore:
    traits: tuple[TraitScore, ...]
    trait_total: Decimal
    modifiers: tuple[Modifier, ...]
    modifier_total: Decimal
    final: Decimal
    band: str


def band_for(score: Decimal) -> str:
    if score >= 90:
        return "Exceptional"
    if score >= 75:
        return "Strong"
    if score >= 60:
        return "Competent"
    if score >= 40:
        return "Weak"
    return "Poor"


def priority_match(priority: str | None, lines: dict[str, Decimal]) -> dict | None:
    """Did the money follow the declared priority?

    "Protect cash" is the one priority measured by restraint rather than by share of spend --
    the only way to follow through on it is to commit less.
    """
    p = PRIORITY_BY_ID.get(priority or "")
    committed = sum((dec(lines.get(k)) for k in SPEND_KEYS), ZERO)
    if p is None or committed <= Decimal("0.01"):
        return None
    if p.id == "cash":
        return {"share": None, "ok": committed * _LAKH < Decimal(4_000_000),
                "note": f"Rs {committed * _LAKH:,.0f} committed in total"}
    on_priority = sum((dec(lines.get(k)) for k in p.keys), ZERO)
    share = on_priority / committed
    return {"share": share, "ok": share >= Decimal("0.35"),
            "note": f"{share * _100:.1f}% of committed spend went to it"}


def _mix_shares(lines: dict[str, Decimal]) -> list[Decimal]:
    total = sum((dec(lines.get(k)) for k in SPEND_KEYS if LINE_KIND[k] == "opex"), ZERO) or ONE
    return [dec(lines.get(k)) / total if LINE_KIND[k] == "opex" else ZERO for k in SPEND_KEYS]


def score_quarter(
    r: SimulationQuarterResult,
    prior: SimulationQuarterResult | None,
    reflection: dict | None,
    priority: str | None,
    constraint_id: str | None,
    all_constraint_ids: tuple[str, ...],
    budget_ceiling: Decimal,
    extra_modifiers: tuple[Modifier, ...] = (),
) -> SimulationScore:
    """Grade one quarter.

    `constraint_id` is what the evidence says was actually binding; `reflection` is what the
    student said they were solving. Comparing the two is the whole point of Adaptability --
    a company that fixes the wrong stage has still learned nothing.
    """
    A = r.lines
    opex = r.opex_spend / _LAKH
    funded = opex > Decimal("0.001")
    refl = reflection or {}
    named_sacrifice = bool(refl.get("sacrifice"))
    read_right = bool(constraint_id and refl.get("constraint") == constraint_id)
    read_plausible = bool(refl.get("constraint") in all_constraint_ids)
    named_risk = bool(refl.get("risk"))
    match = priority_match(priority, A)

    # Did the quarter land where they said they expected it to?
    expectation_met = False
    if refl.get("expect"):
        grew = r.units_sold > (prior.units_sold if prior else ZERO)
        cash_positive = r.net_cf >= 0
        e = refl["expect"]
        if e == "growfast":
            expectation_met = grew and r.units_sold > (prior.units_sold * Decimal("1.2") if prior else ZERO)
        elif e == "growslow":
            expectation_met = grew
        elif e in ("hold", "shrink"):
            expectation_met = (not grew) or cash_positive

    slack = pct_of(max(r.leads_wasted, r.idle_capacity), max(ONE, r.eff_leads))
    # KNOWN GAP: the reference's compounding set also includes direct "innovation" spend --
    # see quarter.py's own note at `innov_gain`. That line has no equivalent allocation key in
    # this port, so it can't be added here either.
    compounding = dec(A.get("content")) + dec(A.get("prelaunch")) + dec(A.get("social")) + dec(A.get("npd"))
    durable = compounding + dec(A.get("quality")) + dec(A.get("design")) + dec(A.get("capex"))
    largest = max((dec(A.get(k)) for k in SPEND_KEYS if LINE_KIND[k] == "opex"), default=ZERO)
    worst_staffing = min(r.staffing.values()) if r.staffing else ONE
    available = sum((r.avail[p] for p in PRODUCT_IDS), ZERO)
    demand = r.demand_total
    # The result carries the commitment; `r.lines` holds the 44 allocation keys and never has
    # held a `_crisis_commit` among them, so reading it from there scored every response as
    # nothing committed -- including the ones that were.
    commit = r.crisis_commit

    # How far the mix moved from last quarter -- half the total absolute change, so a full
    # reallocation reads as 1.0 rather than 2.0.
    mix_move: Decimal | None = None
    if prior is not None:
        now, before = _mix_shares(A), _mix_shares(prior.lines)
        mix_move = sum((abs(a - b) for a, b in zip(now, before)), ZERO) / Decimal(2)

    # What last quarter's binding constraint was, and whether they moved money at it.
    responded, constraint_label = "none", "n/a"
    if prior is not None:
        pa = prior.lines
        if prior.leads_wasted > prior.eff_leads * Decimal("0.05"):
            constraint_label = "selling capacity"
            nowv = dec(A.get("reps")) + dec(A.get("channel"))
            was = dec(pa.get("reps")) + dec(pa.get("channel"))
            responded = "full" if nowv > was * Decimal("1.15") else "part" if nowv > was else "none"
        elif prior.unmet_demand > 1:
            constraint_label = "production supply"
            nowv = dec(A.get("production")) + dec(A.get("capex"))
            was = dec(pa.get("production")) + dec(pa.get("capex"))
            responded = "full" if nowv > was * Decimal("1.15") else "part" if nowv > was else "none"
        elif prior.ceiling_binding:
            constraint_label = "the product conversion ceiling"
            nowv = dec(A.get("quality")) + dec(A.get("npd"))
            was = dec(pa.get("quality")) + dec(pa.get("npd"))
            responded = ("full" if nowv > was * Decimal("1.15") or r.landed
                         else "part" if nowv > was else "none")
        elif prior.short_roles:
            names = " and ".join(DEPARTMENT_BY_ID[i].name for i in prior.short_roles)
            constraint_label = f"{names} staffing"
            was = min(prior.staffing[i] for i in prior.short_roles)
            nowv = min(r.staffing[i] for i in prior.short_roles)
            responded = "full" if nowv > was + Decimal("0.05") else "part" if nowv > was else "none"
        else:
            constraint_label, responded = "no single binding constraint", "full"

    crisis_answer, crisis_detail = "none", "No market event in play."
    if r.crisis_variant:
        crisis_answer = "full" if r.neutralised else "part" if commit > 0 else "none"
        crisis_detail = (
            "Event fully neutralised." if r.neutralised
            else f"Rs {commit:.1f}L committed to the response, partially closing it out." if commit > 0
            else "No rupees committed to any response line."
        )

    spec: list[tuple[str, list[tuple[str, str, str]]]] = [
        ("Strategic Thinking", [
            ("Funnel stages sized against each other",
             level(slack < Decimal("0.15"), slack < Decimal("0.35")) if funded else "none",
             (f"{r.leads_wasted:.0f} leads past capacity, {r.idle_capacity:.0f} capacity idle "
              f"-- slack {slack * _100:.1f}%") if funded else "Nothing funded, so nothing was sized."),
            ("At least one compounding asset funded",
             level(compounding >= opex * Decimal("0.1") and funded, compounding > 0),
             f"Rs {compounding:.1f}L into SEO, buzz, social, innovation and new product"
             + (f" -- {pct_of(compounding, opex) * _100:.1f}% of spend" if funded else "")),
            ("Bets concentrated rather than sprinkled",
             level(largest >= opex * Decimal("0.16"), largest >= opex * Decimal("0.1")) if funded else "none",
             (f"largest line is {pct_of(largest, opex) * _100:.1f}% of operating spend"
              if funded else "No operating spend committed.")),
            ("Money followed the stated priority",
             level(bool(match and match["ok"]),
                   bool(match and match["share"] is not None and match["share"] >= Decimal("0.2")))
             if match else "none",
             (f"Declared {PRIORITY_BY_ID[priority].name.lower()}; "
              f"{match['note'] if match else 'nothing committed'}.") if priority else "No priority declared."),
        ]),
        ("Leadership", [
            ("Every function staffed for the plan",
             level(worst_staffing >= Decimal("0.999"), worst_staffing >= Decimal("0.85")),
             (", ".join(f"{DEPARTMENT_BY_ID[i].name} {r.staffing[i] * _100:.1f}%" for i in r.short_roles)
              if r.short_roles else "All six functions carrying their load.")),
            ("Morale held through the quarter",
             level(r.emp_sat >= 75, r.emp_sat >= 65),
             f"employee satisfaction {r.emp_sat:.1f}"
             + (f" after {r.total_fired:.0f} exits" if r.total_fired > 0 else "")
             + f", productivity {r.prod_mult:.2f}x"),
            ("Attrition kept off next quarter",
             level(r.attrition_next <= 6, r.attrition_next <= 9),
             f"attrition entering next quarter {r.attrition_next:.1f}%"),
        ]),
        ("Adaptability", [
            ("Allocation mix moved with the evidence",
             (level(mix_move >= Decimal("0.15"), mix_move >= Decimal("0.06")) if mix_move is not None else "part"),
             (f"{mix_move * _100:.1f}% of the mix reallocated" if mix_move is not None
              else "Opening quarter, scored as partial by default.")),
            ("Market event answered on its own terms" if r.crisis_variant
             else "Last quarter's binding constraint addressed",
             crisis_answer if r.crisis_variant else responded,
             crisis_detail if r.crisis_variant
             else (f"the binding constraint was {constraint_label}" if prior else "No prior quarter to respond to.")),
            ("Read the company's actual constraint correctly",
             level(read_right, read_plausible),
             ("Named the constraint the evidence says was binding." if read_right
              else "Named a real pressure, but not the one that was actually binding." if read_plausible
              else "No reading recorded." if not refl.get("constraint")
              else "The reading did not match what was binding.")),
        ]),
        ("Systems Thinking", [
            ("Supply matched to demand",
             level(abs(available - demand) <= Decimal("0.1") * max(ONE, demand),
                   abs(available - demand) <= Decimal("0.25") * max(ONE, demand)),
             f"{demand:.0f} units of demand against {available:.0f} available"
             + (f", {r.unmet_demand:.0f} unmet" if r.unmet_demand > 1 else "")),
            ("Product ceiling kept ahead of the funnel",
             level(r.ceiling >= r.raw_conv, r.raw_conv - r.ceiling <= 3),
             f"raw conversion {r.raw_conv:.1f}% against a {r.ceiling:.1f}% ceiling"),
            ("Plant you own is plant you run",
             level(r.utilisation >= Decimal("0.85"), r.utilisation >= Decimal("0.65"))
             if r.installed_capacity > 0 else "none",
             f"{r.utilisation * _100:.1f}% utilisation on {r.installed_capacity:.0f} units of "
             f"installed capacity"),
        ]),
        ("Risk Management", [
            ("Working capital kept clear of the floor",
             level(r.cash >= BUFFER * Decimal("2.5"), r.cash >= BUFFER),
             f"closing cash Rs {r.cash:,.0f} against a Rs {BUFFER:,.0f} buffer"),
            ("Compliance exposure contained",
             level(r.penalty_risk <= 12, r.penalty_risk <= 20),
             f"penalty risk {r.penalty_risk:.1f}% (compliance {r.compliance:.0f}, audit {r.audit:.0f})"),
            ("Single points of failure funded down",
             level(r.supplier_rel >= 85, r.supplier_rel >= 78),
             f"supplier reliability {r.supplier_rel:.0f}"),
        ]),
        ("Capital Allocation", [
            ("Cash flow controlled",
             level(r.net_cf >= 0, r.net_cf >= -Decimal("0.15") * max(ONE, r.opening_cash)),
             f"net cash movement Rs {r.net_cf:,.0f} on an opening balance of Rs {r.opening_cash:,.0f}"),
            ("Commitments held inside the ceiling",
             level(r.opex_spend + r.capex_spend + r.inno_spend + r.people_cost <= budget_ceiling,
                   r.opex_spend + r.capex_spend + r.inno_spend + r.people_cost <= budget_ceiling * Decimal("1.1")),
             f"Rs {r.opex_spend + r.capex_spend + r.inno_spend + r.people_cost:,.0f} committed against "
             f"a ceiling of Rs {budget_ceiling:,.0f}"),
            ("Debt carried for a reason",
             (level(r.net_profit > 0 or named_risk, named_risk) if r.debt_close > 0 else "full"),
             (f"Rs {r.debt_close:,.0f} outstanding, Rs {r.interest_expense:,.0f} of interest this quarter"
              if r.debt_close > 0 else "No borrowings outstanding.")),
        ]),
        ("Long-Term Thinking", [
            ("Assets built that outlive the quarter",
             level(durable >= opex * Decimal("0.15"), durable >= opex * Decimal("0.08")) if funded else "none",
             f"Rs {durable:.1f}L into product, brand assets and plant"
             + (f", plus Rs {r.inno_spend:,.0f} of innovation cards" if r.started else "")),
            ("Product moved forward",
             level((r.quality_gain > 0 and r.defect_rate <= 4) or r.pro_launching or bool(r.landed),
                   r.quality_gain > 0 or bool(r.started)),
             f"quality +{r.quality_gain:.1f}"
             + (", the Pro cleared development" if r.pro_launching else "")
             + (f", shipped {' and '.join(INNOVATION_BY_ID[i].name for i in r.landed)}" if r.landed else "")),
            ("Enterprise value trending up",
             (level(r.valuation > prior.valuation, r.valuation >= prior.valuation * Decimal("0.95"))
              if prior else level(r.revenue_total > 0, r.units_sold > 0)),
             (f"Rs {prior.valuation / Decimal(10_000_000):.2f} Cr -> "
              f"Rs {r.valuation / Decimal(10_000_000):.2f} Cr" if prior
              else f"opening valuation Rs {r.valuation / Decimal(10_000_000):.2f} Cr")),
        ]),
    ]

    traits: list[TraitScore] = []
    for name, raw_subs in spec:
        weight = TRAIT_WEIGHTS[name]
        per = weight / Decimal(len(raw_subs))
        subs = tuple(SubCriterion(lbl, lvl, det, _q2(per * LEVEL_SHARE[lvl])) for lbl, lvl, det in raw_subs)
        traits.append(TraitScore(name, weight, subs, sum((s.points for s in subs), ZERO)))

    trait_total = sum((t.points for t in traits), ZERO)
    mods = list(_modifiers(r, prior, named_sacrifice, named_risk, expectation_met, worst_staffing,
                           available, demand, commit))
    mods.extend(extra_modifiers)

    mod_total = sum((m.points for m in mods), ZERO)
    # Quantise to 2dp, as the 22-line engine reports `ceo_score`. Trait weights divide by three
    # sub-criteria, so the raw sum carries a long repeating tail (40.999...) that is noise, not
    # precision -- and a band boundary decided by the 28th decimal place would be indefensible.
    final = _q2(trait_total + mod_total)
    return SimulationScore(tuple(traits), _q2(trait_total), tuple(mods), mod_total, final, band_for(final))


def _modifiers(
    r: SimulationQuarterResult,
    prior: SimulationQuarterResult | None,
    named_sacrifice: bool,
    named_risk: bool,
    expectation_met: bool,
    worst_staffing: Decimal,
    available: Decimal,
    demand: Decimal,
    commit: Decimal,
):
    """Named point adjustments. Each fires on a specific, checkable fact about the quarter."""
    A = r.lines
    out: list[Modifier] = []

    if dec(A.get("referral")) > 0 and abs(dec(A.get("referral")) - r.referral_cap_spend) <= max(
        Decimal("0.05"), r.referral_cap_spend * Decimal("0.02")
    ):
        out.append(Modifier(Decimal(2), f"Referral funded to exactly its hard cap of "
                                        f"Rs {r.referral_cap_spend:.1f}L -- no rupee spent past the ceiling."))
    if r.capacity > 0 and r.leads_wasted < 1 and r.eff_leads > 1:
        out.append(Modifier(Decimal(2), "Zero leads lost to selling capacity -- every effective lead was worked."))
    if available > 0 and 0 <= available - demand <= max(Decimal(50), Decimal("0.05") * available):
        out.append(Modifier(Decimal(2), "Units built landed inside a deliberate buffer of units sold "
                                        "-- no stockpile, no shortfall."))
    if r.installed_capacity > 0 and r.utilisation < Decimal("0.6") and r.capex_spend > 0:
        out.append(Modifier(Decimal(-2), f"Capital spent on plant while only {r.utilisation * _100:.1f}% of "
                                         f"the plant you already own was running."))
    if prior is not None:
        cut = [label for key, label in (("content", "SEO"), ("prelaunch", "pre-launch marketing"),
                                        ("social", "brand and social"), ("npd", "new product development"))
               if dec(prior.lines.get(key)) > 0 and dec(A.get(key)) == 0]
        if cut and not named_sacrifice:
            out.append(Modifier(Decimal(-2), f"Compounding asset cut to zero ({', '.join(cut)}) without "
                                             f"naming it as a deliberate sacrifice."))
    if r.raw_conv - r.ceiling > 3:
        out.append(Modifier(Decimal(-2), f"Raw conversion overshot the product ceiling by "
                                         f"{r.raw_conv - r.ceiling:.1f} points -- selling paid for demand "
                                         f"the product could not close."))
    if r.wc_breached:
        out.append(Modifier(Decimal(-3), f"Working capital buffer breached -- closing cash below Rs {BUFFER:,.0f}."))
    if r.insolvent:
        out.append(Modifier(Decimal(-5), "Cash closed negative. The company traded while insolvent."))
    if r.drawn > 0 and not named_risk:
        out.append(Modifier(Decimal(-2), f"Rs {r.drawn:,.0f} of debt drawn without naming the risk being accepted."))
    if worst_staffing < Decimal("0.85"):
        names = " and ".join(DEPARTMENT_BY_ID[i].name for i in r.short_roles)
        out.append(Modifier(Decimal(-2), f"{names} ran at {worst_staffing * _100:.1f}% -- the spend plan was "
                                         f"funded well beyond the people available to deliver it."))
    if r.wasted_marketing > r.marketing_spend * Decimal("0.2") and r.marketing_spend > Decimal(100_000):
        out.append(Modifier(Decimal(-3), f"Rs {r.wasted_marketing:,.0f} of demand generation -- "
                                         f"{r.waste_frac * _100:.1f}% of the marketing budget -- had nowhere to "
                                         f"land, with neither the selling capacity nor the stock behind it."))
    if expectation_met:
        out.append(Modifier(Decimal(1), "The quarter landed roughly where you said you expected it to."))
    if r.position_binding and r.marketing_spend > Decimal(800_000):
        out.append(Modifier(Decimal(-2), f"Heavy demand generation against a market position that could not "
                                         f"absorb it -- {r.demand_beyond_position:.0f} units of interest went "
                                         f"to competitors."))
    if r.market_share > Decimal("0.1") and pct_of(r.gross_profit, max(ONE, r.revenue_total)) < Decimal("0.35"):
        out.append(Modifier(Decimal(-3), f"Share of {r.market_share * _100:.1f}% bought at a gross margin of "
                                         f"{pct_of(r.gross_profit, max(ONE, r.revenue_total)) * _100:.1f}% "
                                         f"-- volume without economics."))
    if r.marketing_spend > Decimal(100_000) and r.waste_frac < Decimal("0.02") and r.units_sold > 0:
        out.append(Modifier(Decimal(2), "Every rupee of demand generation converted -- selling capacity and "
                                        "production both sized to the marketing behind them."))

    below_cost = [p for p in PRODUCT_IDS
                  if r.products_in[p].live and r.products_in[p].status == "active"
                  and r.sold[p] > 0 and r.wac[p] >= r.products_in[p].price]
    if below_cost:
        from app.engines.simulation.catalog import PRODUCT_BY_ID
        names = " and ".join(PRODUCT_BY_ID[p].name for p in below_cost)
        out.append(Modifier(Decimal(-4), f"{names} sold below unit cost -- every sale destroyed value."))

    if r.crisis_variant:
        if r.neutralised:
            out.append(Modifier(Decimal(3), "Market event fully neutralised -- dampening and conversion "
                                            "penalty both closed out."))
        if r.crisis_variant == "leapfrog" and r.entering.innovation >= 20:
            out.append(Modifier(Decimal(3), f"Crisis-proofed in advance -- innovation of "
                                            f"{r.entering.innovation:.0f} at onset absorbed the leapfrog."))
        if r.crisis_variant == "supply" and r.entering.supplier_rel >= 85:
            out.append(Modifier(Decimal(3), f"Crisis-proofed in advance -- supplier reliability of "
                                            f"{r.entering.supplier_rel:.0f} carried the capacity multiplier."))
        if commit <= 0:
            out.append(Modifier(Decimal(-4), "Market event ignored -- nothing committed to any response line."))

    return out

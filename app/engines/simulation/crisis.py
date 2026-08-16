"""The Nadi Wear market-event model: six archetypes, five response strategies.

The central idea, same as the 22-line engine's crisis system: what a shock costs depends on the
company you spent the earlier quarters building, not on how hard you react to it. Eleven health
factors -- every one of them bought quarters earlier for no visible reason at the time -- decide
exposure. The response budget helps at the margin, and its effect saturates.

Wider than `app/engines/crisis.py`: that models four lettered scenarios with A/B/C/D choices,
this models six archetypes against five postures. The four overlapping archetypes map onto the
same letters via `catalog.ARCHETYPE_FOR_SCENARIO_LETTER`, so a company can be assigned a crisis
by either system and land on the same event.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.engines.simulation._shared import ONE, ZERO, clamp, dec, pct_of
from app.engines.simulation.catalog import (
    ARCHETYPES,
    BUFFER,
    DEPT_LOAD,
    Archetype,
)
from app.engines.simulation.state import SimulationCompanyState

_SIX = Decimal(6)


def health_factors(s: SimulationCompanyState) -> dict[str, Decimal]:
    """Eleven readings of the company, each normalised to 0-1, that decide shock exposure.

    `channels` is the odd one out: it rewards a *spread* of marketing rather than a level, via
    the Herfindahl concentration of last quarter's mix. A company that bought all its demand
    from one channel is the one a competitor can outbid.
    """
    runway = pct_of(s.cash, -dec(s.last_net_cf)) if dec(s.last_net_cf) < 0 else _SIX

    mix = [dec((s.last_mix or {}).get(k)) for k in DEPT_LOAD["marketing"].keys]
    mix_total = sum(mix, ZERO) or ONE
    concentration = sum(((m / mix_total) ** 2 for m in mix), ZERO)

    return {
        "brand": clamp(s.brand / Decimal(50), ZERO, ONE),
        "retention": clamp((s.repeat_rate - Decimal(8)) / Decimal(25), ZERO, ONE),
        "satisfaction": clamp((s.satisfaction - Decimal(45)) / Decimal(35), ZERO, ONE),
        "margin": clamp((dec(s.last_gm) - Decimal("0.45")) / Decimal("0.3"), ZERO, ONE),
        "innovation": clamp(s.innovation / Decimal(45), ZERO, ONE),
        "quality": clamp(s.quality / Decimal(45), ZERO, ONE),
        "supplier": clamp((s.supplier_rel - Decimal(65)) / Decimal(30), ZERO, ONE),
        "cash": clamp(runway / Decimal(4), ZERO, ONE),
        "channels": clamp((ONE - concentration) / Decimal("0.65"), ZERO, ONE),
        "people": clamp((s.emp_sat - Decimal(50)) / Decimal(35), ZERO, ONE),
        "capacity": clamp(
            s.installed_capacity / max(Decimal(1_200), dec(s.prior_demand) * Decimal("1.4")), ZERO, ONE
        ),
    }


@dataclass(frozen=True)
class CrisisSituation:
    """How badly this particular archetype hurts this particular company."""

    arch: Archetype
    factors: dict[str, Decimal]
    #: 0.12-1.0. What share of the event's maximum damage actually lands.
    vuln: Decimal
    #: 1-3, as reported to the student. Never the underlying number.
    level: int
    shield: Decimal
    protected_by: tuple[str, ...]
    exposed_by: tuple[str, ...]


def assess(archetype_id: str, s: SimulationCompanyState) -> CrisisSituation:
    arch = ARCHETYPES[archetype_id]
    factors = health_factors(s)
    weights = arch.weights

    shielded = sum((weights[k] * factors[k] for k in weights), ZERO)
    weight_total = sum(weights.values(), ZERO)
    vuln = clamp(ONE - shielded / weight_total, Decimal("0.12"), ONE)

    runway = pct_of(s.cash, -dec(s.last_net_cf)) if dec(s.last_net_cf) < 0 else _SIX
    level = 1 if vuln < Decimal("0.38") else 2 if vuln < Decimal("0.68") else 3
    # Thin runway makes any shock worse, and a breached buffer makes every shock severe.
    if runway < Decimal("1.5") and level < 3:
        level += 1
    if s.cash < BUFFER:
        level = 3

    ranked = sorted(weights, key=lambda k: weights[k] * factors[k], reverse=True)

    return CrisisSituation(
        arch=arch,
        factors=factors,
        vuln=vuln,
        level=level,
        shield=shielded / weight_total,
        protected_by=tuple(k for k in ranked if factors[k] > Decimal("0.5"))[:3],
        exposed_by=tuple(k for k in reversed(ranked) if factors[k] < Decimal("0.4"))[:3],
    )


@dataclass(frozen=True)
class CrisisProfile:
    """The penalties a live event applies, after the chosen strategy claws some of them back."""

    damp: Decimal = ONE
    conv_penalty: Decimal = ZERO
    ceiling_penalty: Decimal = ZERO
    cap_mult: Decimal = ONE
    cogs_surcharge: Decimal = ZERO
    ref_shift: Decimal = ZERO
    logistics_hit: Decimal = ZERO
    brand_erosion: Decimal = ZERO
    sat_hit: Decimal = ZERO
    cust_loss_base: Decimal = ZERO
    price_cut: Decimal = ZERO
    mkt_mult: Decimal = ONE
    reach_mult: Decimal = ONE
    conv_bonus: Decimal = ZERO
    brand_boost: Decimal = ZERO
    rival_surge: Decimal = Decimal("1.45")
    #: What this response leaves behind for the following quarter.
    aftermath: dict[str, Decimal | str] = field(default_factory=dict)
    commit_effect: Decimal = ZERO
    strategy: str | None = None


#: Commitment saturates on this scale: the first lakhs move the needle far more than the last,
#: so there is no amount of money that fully buys out a shock you were unprepared for.
_COMMIT_SCALE = Decimal(11)


def _saturating(commit: Decimal) -> Decimal:
    """`1 - e^(-commit/11)`, in Decimal."""
    if commit <= 0:
        return ZERO
    return ONE - (-(max(ZERO, commit) / _COMMIT_SCALE)).exp()


def respond(situation: CrisisSituation | None, strategy: str | None, commit: Decimal) -> CrisisProfile:
    """Apply the event, then the posture and the money behind it."""
    if situation is None:
        return CrisisProfile()

    v = situation.vuln
    arch_id = situation.arch.id
    p: dict = {"aftermath": {}}

    if arch_id == "price_war":
        p.update(damp=ONE - Decimal("0.3") * v, conv_penalty=Decimal(11) * v,
                 cust_loss_base=Decimal(9) * v, ref_shift=Decimal(-1_500))
    elif arch_id == "blitz":
        p.update(damp=ONE - Decimal("0.46") * v, conv_penalty=Decimal(4) * v, cust_loss_base=_SIX * v)
    elif arch_id == "leapfrog":
        p.update(damp=ONE - Decimal("0.18") * v, conv_penalty=Decimal(9) * v,
                 ceiling_penalty=Decimal("3.5") * v, cust_loss_base=Decimal(7) * v)
    elif arch_id == "supply":
        p.update(cap_mult=ONE - Decimal("0.62") * v, cogs_surcharge=Decimal(800) * v,
                 logistics_hit=Decimal(18) * v, cust_loss_base=Decimal(4) * v)
    elif arch_id == "demand_shift":
        p.update(mkt_mult=ONE - Decimal("0.3") * v, damp=ONE - Decimal("0.16") * v,
                 conv_penalty=Decimal(3) * v)
    elif arch_id == "trust":
        p.update(sat_hit=Decimal(13) * v, cust_loss_base=Decimal(12) * v,
                 conv_penalty=_SIX * v, brand_erosion=Decimal(9) * v)

    base = CrisisProfile(**p)
    e = _saturating(commit)
    after: dict[str, Decimal | str] = {}
    out = {
        "damp": base.damp, "conv_penalty": base.conv_penalty, "ceiling_penalty": base.ceiling_penalty,
        "cap_mult": base.cap_mult, "cogs_surcharge": base.cogs_surcharge, "ref_shift": base.ref_shift,
        "logistics_hit": base.logistics_hit, "brand_erosion": base.brand_erosion, "sat_hit": base.sat_hit,
        "cust_loss_base": base.cust_loss_base, "price_cut": base.price_cut, "mkt_mult": base.mkt_mult,
        "reach_mult": base.reach_mult, "conv_bonus": base.conv_bonus, "brand_boost": base.brand_boost,
        "rival_surge": base.rival_surge,
    }

    if strategy == "fight":
        out["conv_penalty"] *= ONE - Decimal("0.8") * e
        out["damp"] += (ONE - out["damp"]) * Decimal("0.75") * e
        out["cust_loss_base"] *= ONE - Decimal("0.6") * e
        out["cap_mult"] += (ONE - out["cap_mult"]) * Decimal("0.7") * e
        if arch_id == "price_war":
            out["price_cut"] = Decimal(1_500) * e
            after["price_cut"] = Decimal(1_100) * e
        after["cogs_drag"] = Decimal(180) * e
        after["note"] = ("Fighting held the line, and the price and margin pressure it created does "
                         "not stop when the quarter does.")
    elif strategy == "differentiate":
        out["ceiling_penalty"] *= ONE - Decimal("0.75") * e
        out["conv_penalty"] *= ONE - Decimal("0.35") * e
        out["brand_boost"] = Decimal(7) * e
        out["reach_mult"] = ONE - Decimal("0.16") * (ONE - e)
        after["brand_bonus"] = _SIX * e
        after["note"] = ("Refusing the comparison cost volume now and left the brand stronger going "
                         "into the last quarter.")
    elif strategy == "focus":
        out["reach_mult"] = Decimal("0.72")
        out["conv_bonus"] = Decimal(4) * e
        out["cust_loss_base"] *= ONE - Decimal("0.85") * e
        out["conv_penalty"] *= ONE - Decimal("0.45") * e
        after["repeat_bonus"] = Decimal(4) * e
        after["reach_mult"] = Decimal("0.88")
        after["note"] = "Narrowing the base improved who you sell to and shrank how many of them there are."
    elif strategy == "learn":
        out["cust_loss_base"] *= Decimal("1.15")
        out["conv_penalty"] *= Decimal("1.05")
        after["vuln_relief"] = Decimal("0.18") + Decimal("0.1") * e
        after["note"] = ("Holding back preserved cash and bought a clearer read of the situation for "
                         "the final quarter.")
    elif strategy == "exploit":
        out["reach_mult"] = ONE + Decimal("0.28") * e
        out["conv_bonus"] = Decimal(2) * e
        out["rival_surge"] = Decimal("1.45") - Decimal("0.35") * e
        out["cust_loss_base"] *= ONE - Decimal("0.4") * e
        out["cogs_surcharge"] += Decimal(220) * e
        after["share_carry"] = Decimal("0.1") * e
        after["note"] = "Share taken while the market was distracted tends to stay taken."

    # A posture nobody funded is worse than no posture at all: the market notices the announcement
    # and nothing behind it.
    if commit <= Decimal("0.01") and strategy != "learn":
        out["brand_erosion"] += _SIX
        after["note"] = "A strategy was chosen and nothing was committed behind it."

    return CrisisProfile(**out, aftermath=after, commit_effect=e, strategy=strategy)


def commit_reading(strategy: str | None, commit: Decimal, s: SimulationCompanyState) -> dict[str, str]:
    """How finance describes the commitment, without ever quoting a coefficient."""
    from app.engines.simulation.catalog import STRATEGY_BY_ID

    e = _saturating(commit)
    strain = pct_of(commit * Decimal(100_000), max(ONE, s.cash))
    band = ("token" if e < Decimal("0.15") else "modest" if e < Decimal("0.4")
            else "material" if e < Decimal("0.7") else "decisive")
    pressure = ("barely noticeable" if strain < Decimal("0.05") else "noticeable" if strain < Decimal("0.15")
                else "significant" if strain < Decimal("0.3") else "severe")
    strat = STRATEGY_BY_ID.get(strategy or "")
    return {
        "band": band,
        "strain": pressure,
        "line": ("Nothing committed. Whatever the strategy says, the company will do none of it."
                 if commit <= 0 else
                 f"Finance reads this as a {band} commitment, putting {pressure} pressure on cash."),
        "trade": strat.risk if strat else "",
    }


def available_strategies(archetype_id: str, s: SimulationCompanyState, factors: dict[str, Decimal]) -> tuple[str, ...]:
    """Which postures are on the table.

    "Press the advantage" only appears when the company has spare capacity and cash to press
    *with* -- offering it to a company that cannot act on it would be a trap, not a choice.
    """
    ids = ["fight", "differentiate", "focus", "learn"]
    if (
        factors["capacity"] > Decimal("0.55")
        and factors["cash"] > Decimal("0.45")
        and (archetype_id in ("supply", "trust", "demand_shift") or factors["brand"] > Decimal("0.5"))
    ):
        ids.append("exploit")
    return tuple(ids)


@dataclass(frozen=True)
class EvidenceLine:
    """One function's readout while the event runs."""

    fn: str
    line: str
    detail: str
    #: "bad" / "watch" / "flat" -- how alarming it looks, not how relevant it is.
    tone: str


def evidence(archetype_id: str, s: SimulationCompanyState, last, prior) -> tuple[EvidenceLine, ...]:
    """What each part of the business is seeing.

    Deliberately mixed: some of it is the event, some of it is normal noise, and none of it
    names the cause. Diagnosing which is which is the exercise -- so this returns symptoms and
    never the exposure number behind them.
    """
    out: list[EvidenceLine] = []
    add = lambda fn, line, detail, tone: out.append(EvidenceLine(fn, line, detail, tone))  # noqa: E731

    conv = dec(getattr(last, "final_conv", ZERO)) if last else ZERO
    prior_conv = dec(getattr(prior, "final_conv", ZERO)) if prior else conv
    cpl = (dec(last.marketing_spend) / dec(last.raw_leads)) if last and dec(last.raw_leads) > 0 else ZERO
    prior_cpl = (dec(prior.marketing_spend) / dec(prior.raw_leads)) if prior and dec(prior.raw_leads) > 0 else cpl
    runway = pct_of(s.cash, -dec(s.last_net_cf)) if dec(s.last_net_cf) < 0 else Decimal(99)

    def move(a: Decimal, b: Decimal) -> Decimal:
        return (a / b - ONE) * Decimal(100) if b > 0 else ZERO

    if archetype_id == "price_war":
        add("Sales", f"Conversion down {abs(move(conv, prior_conv)) + _SIX:.1f}%",
            "Deals are dying later in the cycle. The objection is arriving after the demo, not before it.", "bad")
        add("Product", "Customer rating unchanged",
            f"Satisfaction sits at {s.satisfaction:.0f} and returns have not moved. Nothing about the "
            f"product got worse.", "flat")
        add("Marketing", f"Cost per lead up {max(Decimal(4), move(cpl, prior_cpl) + Decimal(5)):.1f}%",
            "Volume is holding. The leads are simply more expensive to get.", "watch")
        add("Market intelligence", "A competitor is discounting",
            "Kalpa Labs is visibly cheaper in the channel. Nobody will tell you by exactly how much, or "
            "for how long.", "bad")
    elif archetype_id == "blitz":
        add("Marketing", f"Cost per lead up {max(Decimal(18), move(cpl, prior_cpl) + Decimal(22)):.1f}%",
            "Auction prices doubled in a fortnight across every paid channel at once.", "bad")
        add("Sales", "Lead quality down",
            "Volume is close to plan. The leads convert worse than the same leads did last quarter.", "watch")
        add("Product", "Nothing has changed", "Ratings, returns and satisfaction are all flat.", "flat")
        add("Market intelligence", "Somebody is buying the category",
            "Vega Health is unavoidable in every feed your buyer uses. Their spend is not public.", "bad")
    elif archetype_id == "leapfrog":
        add("Sales", "Win rate against one competitor collapsed",
            "Against everyone else it is unchanged. The losses are concentrated.", "bad")
        add("Product", "Your ratings have not moved",
            f"Satisfaction {s.satisfaction:.0f}, quality score {s.quality:.0f}. Nothing you shipped got worse.", "flat")
        add("Marketing", "Comparison searches rising",
            "Buyers are researching you alongside a specific rival more than they were.", "watch")
        add("Market intelligence", "A rival shipped something",
            "Zenith has a capability you do not. Whether buyers will keep caring is not yet clear.", "bad")
    elif archetype_id == "supply":
        add("Operations", "Two vendors missed confirmations",
            f"Both source from the same fab. Supplier reliability stands at {s.supplier_rel:.0f}.", "bad")
        add("Operations", "Lead times extending",
            "Your contract manufacturer needs a commitment by Friday to hold the slot.", "bad")
        add("Sales", "Pipeline unaffected so far",
            "Demand has not moved. This is not yet a customer-facing problem.", "flat")
        add("Finance", "Runway " + ("self-funding" if runway > 90 else f"{runway:.1f} quarters"),
            "Whatever you commit to secure supply comes out of this.", "bad" if runway < 2 else "flat")
    elif archetype_id == "demand_shift":
        add("Sales", "Pipeline below forecast, second month",
            "Fewer buyers are entering the process at all. The ones who do still convert normally.", "bad")
        add("Market intelligence", "Competitors look soft too",
            "This does not appear to be share moving between players.", "watch")
        add("Product", f"Satisfaction stable at {s.satisfaction:.0f}",
            "Existing customers are unchanged in their behaviour.", "flat")
        add("Finance", "Collections slowing slightly", f"Receivables sit at {s.ar_days:.0f} days.", "watch")
    elif archetype_id == "trust":
        add("Operations", "Return rate spiked",
            f"A batch appears to be failing in the field. QA did not catch it. Quality score is "
            f"{s.quality:.0f}.", "bad")
        add("Customer success", "Satisfaction falling",
            f"Currently {s.satisfaction:.0f} and moving down through the quarter.", "bad")
        add("Marketing", "Negative reviews rising",
            "It is being discussed publicly. Branded search sentiment has turned.", "bad")
        add("Sales", "New business slowing, renewals worse",
            f"Repeat purchase is {s.repeat_rate:.1f}% and existing customers are the ones hesitating.", "watch")

    return tuple(out)

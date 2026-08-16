"""The Q4 term sheet and its settlement.

After Q3 closes, the first three quarters decide a tier, the tier decides a three-path menu,
and the path decides how Q4 is graded. The interesting number is never the headline cheque --
it is the covenant attached to it, and the continuation value the acquisition offer is being
measured against.

Mirrors `app/engines/endgame.py`'s three-tier / three-path shape so both scenarios speak the
same vocabulary to the API (`tier`, `path_a_name`/`b`/`c`, `covenant_units`,
`true_continuation_value_inr`).
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.engines.simulation._shared import ONE, ZERO, clamp
from app.engines.simulation.quarter import SimulationQuarterResult
from app.engines.simulation.scoring import Modifier

_CR = Decimal(10_000_000)


def _cr(v: Decimal) -> str:
    return f"Rs {v / _CR:.2f} Cr"


def _rs(v: Decimal) -> str:
    return f"Rs {v:,.0f}"


def _pct(v: Decimal) -> str:
    return f"{v:.1f}%"


@dataclass(frozen=True)
class Offer:
    id: str
    kind: str
    title: str
    who: str
    pitch: str
    terms: tuple[tuple[str, str], ...]
    price: Decimal | None = None
    investment: Decimal | None = None
    equity: Decimal | None = None
    covenant: Decimal | None = None
    hit_mult: Decimal | None = None
    miss_haircut: Decimal | None = None
    ratchet: Decimal | None = None


@dataclass(frozen=True)
class TermSheet:
    tier: str
    #: Q3 valuation, the reference every number here is struck against.
    v: Decimal
    #: Momentum: unit growth Q1 -> Q3, on a square-root curve, clamped to [-0.5, 1.5].
    momentum: Decimal
    true_continuation: Decimal
    offers: tuple[Offer, ...]

    def menu(self) -> dict[str, str]:
        by_id = {o.id: o.title for o in self.offers}
        return {"path_a_name": by_id["A"], "path_b_name": by_id["B"], "path_c_name": by_id["C"]}

    def offer(self, path: str) -> Offer | None:
        return next((o for o in self.offers if o.id == path), None)


def assign_tier(history: list[SimulationQuarterResult], state) -> str:
    """THRIVING / STABLE / DISTRESSED from the first three quarters.

    Thriving needs cash-positive Q3 *and* a valuation that rose in both Q2 and Q3 -- one good
    quarter is not a trend. Distressed is the survival gate: a breached buffer, an insolvency
    at any point, or three consecutive quarters of falling cash against negative flow.
    """
    q1, q2, q3 = history[0], history[1], history[2]
    thriving = q3.net_cf > 0 and q2.valuation > q1.valuation and q3.valuation > q2.valuation
    distressed = (
        state.wc_breached
        or state.ever_insolvent
        or (q3.net_cf < 0 and q3.cash < q2.cash and q2.cash < q1.cash)
    )
    return "THRIVING" if thriving else "DISTRESSED" if distressed else "STABLE"


def build_term_sheet(history: list[SimulationQuarterResult], state) -> TermSheet:
    if len(history) < 3:
        raise ValueError("the term sheet is only defined once three quarters have locked")

    tier = assign_tier(history, state)
    q1, q3 = history[0], history[2]

    v = max(ONE, q3.valuation)
    base_units = max(q1.units_sold, Decimal(250))
    momentum = clamp((q3.units_sold / base_units) ** Decimal("0.5") - ONE, Decimal("-0.5"), Decimal("1.5"))
    true_continuation = v * (ONE + momentum)

    def invest(ratio: str, covenant_slope: str, hit: str, haircut: str, ratchet: str) -> dict:
        investment = Decimal(ratio) * v
        return {
            "investment": investment,
            "equity": investment / (v + investment),
            "covenant": q3.units_sold * (ONE + Decimal(covenant_slope) * momentum),
            "hit_mult": Decimal(hit),
            "miss_haircut": Decimal(haircut),
            "ratchet": Decimal(ratchet),
        }

    if tier == "THRIVING":
        a = invest("0.25", "1.3", "1.6", "0.6", "1.6")
        price = v * (ONE + Decimal("0.15") * min(ONE, momentum / Decimal("0.6")))
        offers = (
            Offer("A", "invest", "Growth Investor", "Sattva Capital, Series A",
                  "They like the trajectory and want you to spend into it. The money is real; so is the "
                  "covenant attached to it.",
                  (("Investment", f"{_rs(a['investment'])} (25% of your Q3 valuation)"),
                   ("Equity given up", _pct(a["equity"] * Decimal(100))),
                   ("Q4 covenant", f"{a['covenant']:.0f} units sold"),
                   ("If you hit it", "Q4 valuation marked up 1.60x"),
                   ("If you miss", f"capped at 60% of Q3, stake ratchets to "
                                   f"{_pct(a['equity'] * a['ratchet'] * Decimal(100))}")),
                  **a),
            Offer("B", "acquire", "Acquisition Trap", "Meridian Consumer Devices",
                  "Cash today, no covenant, no Q4 risk. The number on the page is the whole story -- or "
                  "the part of it they want you to read.",
                  (("Offer price", _rs(price)),
                   ("Premium over Q3", _pct(Decimal(15) * min(ONE, momentum / Decimal("0.6")))),
                   ("Structure", "All cash, closes on signature"),
                   ("Your Q4", "Does not happen. The simulation ends here.")),
                  price=price),
            Offer("C", "solo", "Independent", "No counterparty",
                  "No cash in, no covenant, no dilution. Q4 runs on your own balance sheet and you are "
                  "graded on consistency.",
                  (("Investment", "None"), ("Dilution", "None"), ("Q4", "Runs normally"),
                   ("Grading", "Consistency of execution"))),
        )
    elif tier == "STABLE":
        a = invest("0.15", "1.1", "1.35", "0.75", "1.3")
        offers = (
            Offer("A", "invest", "Growth Investor - measured terms", "Sattva Capital, bridge round",
                  "A smaller cheque against a gentler covenant. They are buying optionality, not conviction.",
                  (("Investment", f"{_rs(a['investment'])} (15% of your Q3 valuation)"),
                   ("Equity given up", _pct(a["equity"] * Decimal(100))),
                   ("Q4 covenant", f"{a['covenant']:.0f} units sold"),
                   ("If you hit it", "Q4 valuation marked up 1.35x"),
                   ("If you miss", f"25% haircut, stake ratchets to "
                                   f"{_pct(a['equity'] * a['ratchet'] * Decimal(100))}")),
                  **a),
            Offer("B", "acquire", "Fair-Value Acquisition", "Meridian Consumer Devices",
                  "A fair price, honestly struck. Whether fair is enough depends on what you believe the "
                  "next four quarters hold.",
                  (("Offer price", _rs(v)), ("Premium over Q3", "None -- struck at value"),
                   ("Structure", "All cash, closes on signature"),
                   ("Your Q4", "Does not happen. The simulation ends here.")),
                  price=v),
            Offer("C", "solo", "Stay Independent, Prove Stability", "No counterparty",
                  "Nobody is forcing your hand. Run a clean quarter and let the numbers make the argument.",
                  (("Investment", "None"), ("Dilution", "None"), ("Q4", "Runs normally"),
                   ("Grading", "Consistency of execution"))),
        )
    else:
        a = invest("0.4", "0", "1", "0", "1")
        a["covenant"] = ZERO  # survival, not a unit target
        offers = (
            Offer("A", "invest", "Rescue Financing", "Sattva Capital, structured rescue",
                  "The cheque is large because the situation is bad and they know it. No markup on the "
                  "other side -- only survival.",
                  (("Investment", f"{_rs(a['investment'])} (40% of your Q3 valuation)"),
                   ("Equity given up", _pct(a["equity"] * Decimal(100))),
                   ("Q4 covenant", "Close the quarter solvent. No unit target."),
                   ("If you survive", "Valuation stands, no markup"),
                   ("If you do not", "Game over -- the company is wound up")),
                  **a),
            Offer("B", "acquire", "Fire-Sale", "Meridian Consumer Devices",
                  "A genuine discount on a genuinely distressed asset. It ends the risk and it ends the upside.",
                  (("Offer price", _rs(v * Decimal("0.68"))),
                   ("Discount to Q3 valuation", "32%"),
                   ("Structure", "All cash, closes on signature"),
                   ("Your Q4", "Does not happen. The simulation ends here.")),
                  price=v * Decimal("0.68")),
            Offer("C", "solo", "High-Risk Independent", "No counterparty",
                  "No cheque, no floor. If the cash runs out before the quarter closes, it runs out.",
                  (("Investment", "None"), ("Dilution", "None"),
                   ("Q4", "Runs, with a real chance of insolvency"),
                   ("Grading", "Survival and execution"))),
        )

    return TermSheet(tier=tier, v=v, momentum=momentum, true_continuation=true_continuation, offers=offers)


@dataclass(frozen=True)
class Settlement:
    path: str
    modifiers: tuple[Modifier, ...]
    final_valuation: Decimal
    ended_early: bool = False
    price: Decimal | None = None
    gap: Decimal | None = None
    covenant_hit: bool | None = None
    covenant: Decimal | None = None
    equity: Decimal | None = None
    game_over: bool = False


def settle(ts: TermSheet, path: str, q4: SimulationQuarterResult) -> Settlement:
    """Grade the path against the quarter that actually happened."""
    acquisition = ts.offer("B")
    offer = ts.offer(path)
    gap = ts.true_continuation - acquisition.price
    mods: list[Modifier] = []

    if path == "B":
        # Was the offer worth taking, measured against what the business would have been worth?
        if gap <= acquisition.price * Decimal("0.02"):
            mods.append(Modifier(Decimal(4), f"Acquisition accepted correctly -- momentum was weak and the "
                                             f"price sat at or above a continuation value of "
                                             f"{_cr(ts.true_continuation)}."))
        elif gap > acquisition.price * Decimal("0.15"):
            mods.append(Modifier(Decimal(-3), f"Acquisition accepted leaving {_cr(gap)} of continuation value "
                                              f"unexamined -- momentum implied the business was worth more."))
        else:
            mods.append(Modifier(Decimal(1), f"Acquisition accepted at a defensible price -- {_cr(gap)} left "
                                             f"on the table, within a reasonable margin for risk."))
        return Settlement("B", tuple(mods), acquisition.price, ended_early=True,
                          price=acquisition.price, gap=gap)

    if gap > acquisition.price * Decimal("0.15"):
        mods.append(Modifier(Decimal(4), f"Acquisition rejected correctly -- momentum implied a continuation "
                                         f"value of {_cr(ts.true_continuation)} against an offer of "
                                         f"{_cr(acquisition.price)}."))

    if path == "A":
        hit = (q4.cash > 0) if ts.tier == "DISTRESSED" else (q4.units_sold >= offer.covenant)
        equity = offer.equity if hit else offer.equity * offer.ratchet
        if ts.tier == "DISTRESSED":
            mods.append(Modifier(Decimal(5), "Rescue covenant met -- the company closed Q4 solvent.") if hit
                        else Modifier(Decimal(-8), "Rescue covenant missed -- the company did not close the "
                                                   "quarter solvent."))
            return Settlement("A", tuple(mods), q4.valuation if hit else ZERO,
                              covenant_hit=hit, covenant=offer.covenant, equity=equity, game_over=not hit)
        final = (q4.valuation * offer.hit_mult) if hit else min(q4.valuation, ts.v * offer.miss_haircut)
        mods.append(
            Modifier(Decimal(5), f"Covenant hit -- {q4.units_sold:.0f} units against a target of "
                                 f"{offer.covenant:.0f}.") if hit
            else Modifier(Decimal(-8), f"Covenant missed -- {q4.units_sold:.0f} units against a target of "
                                       f"{offer.covenant:.0f}. Valuation haircut and the stake ratcheted.")
        )
        return Settlement("A", tuple(mods), final, covenant_hit=hit, covenant=offer.covenant, equity=equity)

    game_over = ts.tier == "DISTRESSED" and q4.cash <= 0
    if game_over:
        mods.append(Modifier(Decimal(-8), "Continued unfunded from a distressed position and ran out of cash."))
    return Settlement("C", tuple(mods), q4.valuation, game_over=game_over)

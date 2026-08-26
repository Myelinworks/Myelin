"""Every fixed table the Nadi Wear four-quarter simulation runs on.

Departments and their salary/ramp costs, the two products, the innovation board, supplier
terms, the competitor set, the six market-event archetypes and the five response strategies.

These are simulation *content*, not tunable coefficients, which is why they live here as
module constants rather than in `app/config/profiles/*.json`: the 22-line engine's profile
describes one company's calibration, while this describes the shape of a different scenario
entirely. Nothing here is read by the 22-line engine.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from app.engines.simulation._shared import ZERO, dec

# ── scale constants ──────────────────────────────────────────────────

#: Working-capital buffer the board set. Closing below it is a breach.
BUFFER = Decimal(1_000_000)
#: Total addressable customers in the category.
MARKET_CUSTOMERS = Decimal(250_000)
OTHER_LIABILITIES = Decimal(1_200_000)
#: Share capital -- the seed round.
SHARE_CAPITAL = Decimal(40_000_000)
OPENING_OVERHEAD = Decimal(250_000)
OPENING_CASH = Decimal(15_000_000)

DEPRECIATION_RATE = Decimal("0.05")
AMORTISATION_RATE = Decimal("0.08")
# 3.5% quarterly evaluates to 14% annually - a deliberately punishing unsecured distress rate
INTEREST_RATE = Decimal("0.035")
MIN_AR = Decimal(800_000)
#: Price elasticity exponent -- demand moves against the market reference price to this power.
PRICE_ELASTICITY = Decimal("1.2")
#: Category growth per quarter, compounding against every rival's strength.
CATEGORY_GROWTH = Decimal("0.05")

_SHARE_BY_QUARTER = [Decimal("0.048"), Decimal("0.054"), Decimal("0.061"), Decimal("0.068")]

TOTAL_QUARTERS = 4
CRISIS_QUARTER = 3


def market_demand(quarter: int) -> Decimal:
    """Units the whole category buys in `quarter`. Grows every quarter whether you act or not."""
    index = min(4, max(1, quarter)) - 1
    return MARKET_CUSTOMERS * _SHARE_BY_QUARTER[index]


# ── departments ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class Department:
    id: str
    name: str
    salary: Decimal
    hire: Decimal
    sever: Decimal
    #: The founding team in this function. Nobody can be cut below it.
    base: int
    drives: str
    if_short: str
    if_cut: str


DEPARTMENTS: tuple[Department, ...] = (
    Department(
        "marketing", "Marketing", Decimal(130_000), Decimal(200_000), Decimal(240_000), 2,
        "Campaign execution",
        "Campaigns run late and untuned. Every lead you paid for is discounted by the shortfall.",
        "Leads fall immediately, in the same quarter, across every channel you funded.",
    ),
    Department(
        "sales", "Sales & field", Decimal(120_000), Decimal(180_000), Decimal(220_000), 4,
        "Selling capacity",
        "Leads arrive and sit unworked. Capacity is throttled to the staffing you actually have.",
        "Selling capacity drops the same quarter and leads spill unconverted.",
    ),
    Department(
        "engineering", "Engineering & product", Decimal(175_000), Decimal(300_000), Decimal(320_000), 3,
        "R&D output and the conversion ceiling",
        "Quality, innovation and new product work all deliver less than you paid for.",
        "The product stops improving. The conversion ceiling stalls while sales keeps pushing against it.",
    ),
    Department(
        "operations", "Operations & production", Decimal(115_000), Decimal(160_000), Decimal(200_000), 3,
        "Production throughput",
        "The line runs below the capacity you own. You build fewer units than the plant allows.",
        "Production falls even though the plant is unchanged. Unmet demand appears immediately.",
    ),
    Department(
        "support", "Support & success", Decimal(95_000), Decimal(130_000), Decimal(165_000), 1,
        "Satisfaction and repeat purchase",
        "Satisfaction and onboarding spend under-deliver, and repeat buying slows.",
        "Customer satisfaction falls, taking conversion and repeat purchases with it.",
    ),
    Department(
        "admin", "Finance & admin", Decimal(140_000), Decimal(200_000), Decimal(250_000), 1,
        "Compliance, audit and financial control",
        "Governance spend under-delivers and penalty risk stays high.",
        "Compliance and audit readiness stop improving. Penalty exposure rises.",
    ),
)

DEPARTMENT_BY_ID = {d.id: d for d in DEPARTMENTS}
DEPT_IDS = tuple(d.id for d in DEPARTMENTS)
BASE_STAFF = {d.id: Decimal(d.base) for d in DEPARTMENTS}


@dataclass(frozen=True)
class DeptLoad:
    """How much spend a function can absorb per head.

    `keys` are the lines that draw on it; `per` is the rupees of spend one person can carry in
    a quarter. Funding a line beyond what its function can absorb is money that under-performs,
    not money that works harder.
    """

    keys: tuple[str, ...]
    per: Decimal


DEPT_LOAD: dict[str, DeptLoad] = {
    "marketing": DeptLoad(
        ("google", "meta", "social", "content", "events", "email", "direct", "referral", "prelaunch"),
        Decimal(1_100_000),
    ),
    "sales": DeptLoad(("reps", "crm", "onboarding", "sales_training", "channel"), Decimal(950_000)),
    "engineering": DeptLoad(("quality", "npd", "design"), Decimal(1_100_000)),
    "operations": DeptLoad(("production", "capex", "supplier", "logistics", "warehouse"), Decimal(1_300_000)),
    "support": DeptLoad(("cx", "onboarding"), Decimal(800_000)),
    "admin": DeptLoad(("compliance", "planning", "audit", "working_capital", "treasury"), Decimal(900_000)),
}


# ── products ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    ref_price: Decimal
    cogs: Decimal
    #: Units of production line consumed per unit built. The Pro eats 1.4.
    capacity_cost: Decimal
    blurb: str


PRODUCTS: tuple[Product, ...] = (
    Product(
        "pulse", "Nadi Pulse", Decimal(9_999), Decimal(3_250), Decimal(1),
        "The original. Volume product, thin margin, carries the brand.",
    ),
    Product(
        "pro", "Nadi Pulse Pro", Decimal(14_999), Decimal(5_200), Decimal("1.4"),
        "Higher price, higher margin, and it eats 1.4 units of line capacity for every one built.",
    ),
)

PRODUCT_BY_ID = {p.id: p for p in PRODUCTS}
PRODUCT_IDS = tuple(p.id for p in PRODUCTS)


# ── the innovation board ─────────────────────────────────────────────


@dataclass(frozen=True)
class Innovation:
    id: str
    cat: str
    name: str
    cost: Decimal
    #: Quarters before it ships. A card started in Q4 never lands.
    lead: int
    effect: dict[str, Decimal] = field(default_factory=dict)
    blurb: str = ""


def _eff(**kwargs: int) -> dict[str, Decimal]:
    return {k: Decimal(v) for k, v in kwargs.items()}


INNOVATIONS: tuple[Innovation, ...] = (
    Innovation("app", "Software", "Redesigned companion app", Decimal(900_000), 0,
               _eff(innovation=6, satisfaction=5, repeat=2),
               "The complaint in every review. Cheap to fix, and it moves satisfaction and repeat buying."),
    Innovation("sleep", "Software", "Sleep and recovery scoring", Decimal(1_100_000), 0,
               _eff(ceiling=3, innovation=7, repeat=2),
               "The feature buyers compare on. Pure software, no bill of materials."),
    Innovation("coach", "Software", "On-device AI health coach", Decimal(2_600_000), 1,
               _eff(ceiling=5, innovation=10, repeat=3, brand=4),
               "A quarter to ship. The one feature reviewers would lead with."),
    Innovation("ecg", "Sensors", "ECG & SpO2 sensor suite", Decimal(1_800_000), 1,
               _eff(ceiling=4, innovation=8, quality=3, cogs=220),
               "Medical-grade credibility. Adds Rs 220 to every unit you build, forever."),
    Innovation("gnss", "Sensors", "Multi-band GNSS positioning", Decimal(1_500_000), 0,
               _eff(ceiling=3, innovation=5, cogs=300),
               "Opens the running and cycling segment. The most expensive component on this board."),
    Innovation("temp", "Sensors", "Skin temperature sensing", Decimal(800_000), 0,
               _eff(ceiling=2, innovation=4, cogs=120),
               "Small, cheap, and it fills a line on the comparison table."),
    Innovation("amoled", "Hardware", "AMOLED always-on display", Decimal(1_200_000), 0,
               _eff(ceiling=2, brand=5, satisfaction=3, cogs=250),
               "The first thing anyone notices in a shop. Costs Rs 250 a unit to keep."),
    Innovation("battery", "Hardware", "14-day battery platform", Decimal(2_000_000), 1,
               _eff(ceiling=4, quality=5, satisfaction=4),
               "A platform change, not a part swap. A quarter of engineering, no unit cost."),
    Innovation("titanium", "Hardware", "Titanium & sapphire build", Decimal(1_600_000), 0,
               _eff(brand=8, quality=6, cogs=450),
               "Buys permission to charge more. Adds Rs 450 a unit whether you raise price or not."),
    Innovation("dfm", "Manufacturing", "Design for manufacture programme", Decimal(1_400_000), 1,
               _eff(cogs=-400, quality=4),
               "Takes Rs 400 off every unit you ever build again. Nothing a customer will ever see."),
    Innovation("modular", "Manufacturing", "Modular strap and case platform", Decimal(1_000_000), 0,
               _eff(cogs=-150, brand=3, repeat=2),
               "Shared parts across both products, and an accessory habit that brings people back."),
)

INNOVATION_BY_ID = {c.id: c for c in INNOVATIONS}
INNOVATION_CATEGORIES = ("Software", "Sensors", "Hardware", "Manufacturing")


def inno_sum(ids: tuple[str, ...] | list[str], key: str) -> Decimal:
    """Total of one effect across a set of shipped cards."""
    return sum((INNOVATION_BY_ID[i].effect.get(key, ZERO) for i in ids if i in INNOVATION_BY_ID), ZERO)


# ── supplier payment terms ───────────────────────────────────────────


@dataclass(frozen=True)
class PayTerms:
    id: str
    name: str
    #: Days of production financed by the supplier, as a share of 90.
    days: int
    cogs_mult: Decimal
    #: Supplier-reliability points, applied for as long as the terms hold.
    rel: int
    note: str


PAY_TERMS: dict[str, PayTerms] = {
    "advance": PayTerms("advance", "Pay on despatch", 0, Decimal("0.97"), 3,
                        "3% off every unit and +3 supplier reliability. Your cash leaves first."),
    "net30": PayTerms("net30", "Net 30", 30, Decimal(1), 0,
                      "Standard terms. A third of production financed by your supplier."),
    "net60": PayTerms("net60", "Net 60", 60, Decimal("1.02"), -2,
                      "2% more a unit and -2 reliability, but two thirds of production sits in payables."),
}

WARRANTY_TERMS = ("6mo", "1yr", "2yr")
#: Conversion points and warranty-provision multiplier per term. Matches the 22-line engine's
#: `product.warranty` block, which is the same designer source.
WARRANTY_BONUS_PTS = {"6mo": ZERO, "1yr": Decimal("1.5"), "2yr": Decimal(3)}
WARRANTY_COST_MULT = {"6mo": ZERO, "1yr": Decimal(1), "2yr": Decimal("1.8")}


# ── competitors ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class Competitor:
    id: str
    name: str
    pos: str
    strength: Decimal
    note: str


COMPETITORS: tuple[Competitor, ...] = (
    Competitor("kalpa", "Kalpa Labs", "Value", Decimal(52), "Shenzhen-backed, undercuts everyone on price."),
    Competitor("vega", "Vega Health", "Mass market", Decimal(46), "Outspends the category on media and celebrity."),
    Competitor("zenith", "Zenith", "Premium", Decimal(58), "Ships the feature everyone else copies next year."),
    Competitor("tail", "The long tail", "Unbranded", Decimal(84), "Dozens of white-label brands on the marketplaces."),
)


# ── the spend line catalog ───────────────────────────────────────────

#: Which cash statement each line lands on. `count` lines are headcount, not rupees.
LINE_KIND: dict[str, str] = {
    "google": "opex", "meta": "opex", "social": "opex", "content": "opex", "events": "opex",
    "email": "opex", "direct": "opex", "referral": "opex", "prelaunch": "opex",
    "reps": "opex", "crm": "opex", "onboarding": "opex", "sales_training": "opex", "channel": "opex",
    "quality": "opex", "npd": "opex", "design": "opex",
    "capex": "capex", "production": "opex", "supplier": "opex", "logistics": "opex", "warehouse": "opex",
    "culture": "opex", "hr_training": "opex", "cx": "opex",
    "compliance": "opex", "planning": "opex", "audit": "opex",
    "working_capital": "opex", "treasury": "opex",
    "draw": "fin_in", "repay": "fin_out",
}

for _d in DEPT_IDS:
    LINE_KIND[f"hire_{_d}"] = "count"
    LINE_KIND[f"fire_{_d}"] = "count"

#: Every spend line, in a deterministic order.
LINE_KEYS: tuple[str, ...] = tuple(LINE_KIND)
#: Rupee spend lines only -- excludes headcount counts and the financing lines.
SPEND_KEYS: tuple[str, ...] = tuple(k for k, v in LINE_KIND.items() if v in ("opex", "capex"))


# ── market events ────────────────────────────────────────────────────


@dataclass(frozen=True)
class Archetype:
    id: str
    name: str
    #: Which competitor surges while this event runs, if any.
    rival: str | None
    #: Which of the eleven health factors shield against it, and how much each matters.
    weights: dict[str, Decimal]
    signal: str
    body: str
    diagnoses: tuple[str, ...]


def _w(**kwargs: str) -> dict[str, Decimal]:
    return {k: Decimal(v) for k, v in kwargs.items()}


ARCHETYPES: dict[str, Archetype] = {
    "price_war": Archetype(
        "price_war", "Price War", "kalpa",
        _w(brand="0.22", retention="0.20", margin="0.20", innovation="0.16", satisfaction="0.12", cash="0.10"),
        "Sales conversion has fallen for three consecutive weeks.",
        "Nothing in the product has changed and satisfaction is stable, but deals are dying later in "
        "the cycle than they used to. Your head of sales says the objection has changed shape -- people "
        "are not saying no, they are saying not at this price.",
        ("price", "differentiation", "demand", "retention"),
    ),
    "blitz": Archetype(
        "blitz", "Marketing Blitz", "vega",
        _w(brand="0.26", channels="0.22", retention="0.16", cash="0.16", satisfaction="0.10", margin="0.10"),
        "Acquisition cost has risen sharply across every paid channel at once.",
        "Lead volume is holding but the leads are colder and each one costs materially more than last "
        "quarter. Nothing you changed explains it. Someone else is buying the same attention you are.",
        ("demand", "price", "segment", "differentiation"),
    ),
    "leapfrog": Archetype(
        "leapfrog", "Feature Leapfrog", "zenith",
        _w(innovation="0.30", quality="0.22", brand="0.18", retention="0.16", satisfaction="0.14"),
        "Win rates against one competitor have collapsed while everything else holds.",
        "Reviews have started opening with a comparison rather than a description. Your own ratings "
        "have not moved. The frame of reference has.",
        ("differentiation", "price", "retention", "segment"),
    ),
    "supply": Archetype(
        "supply", "Supply Shock", None,
        _w(supplier="0.34", capacity="0.22", cash="0.18", margin="0.14", people="0.12"),
        "Two component vendors have missed confirmations in the same week.",
        "Your contract manufacturer wants a commitment for the quarter and cannot promise the slot "
        "beyond Friday. Nobody will yet say how long this lasts.",
        ("supply", "capacity", "cash", "demand"),
    ),
    "demand_shift": Archetype(
        "demand_shift", "Demand Shift", "tail",
        _w(retention="0.24", brand="0.20", satisfaction="0.18", channels="0.16", cash="0.12", margin="0.10"),
        "Category demand has come in below forecast for the second month running.",
        "This is not a share problem -- your competitors' numbers look soft too. Buyers appear to be "
        "deferring rather than choosing somebody else.",
        ("demand", "segment", "price", "retention"),
    ),
    "trust": Archetype(
        "trust", "Trust Event", None,
        _w(quality="0.28", satisfaction="0.24", retention="0.20", brand="0.16", people="0.12"),
        "Return rates and negative reviews have both spiked in the same fortnight.",
        "A batch appears to be failing in the field in a way QA did not catch. It is being discussed "
        "publicly. You do not yet know how many units are affected.",
        ("quality", "retention", "supply", "differentiation"),
    ),
}

ARCHETYPE_IDS = tuple(ARCHETYPES)

#: What each archetype actually is, for grading the student's reading of it.
TRUE_DIAGNOSIS = {
    "price_war": "price", "blitz": "demand", "leapfrog": "differentiation",
    "supply": "supply", "demand_shift": "demand", "trust": "quality",
}

DIAGNOSIS_LABELS = {
    "price": "Competitive pricing pressure",
    "differentiation": "Product differentiation problem",
    "demand": "Demand generation problem",
    "capacity": "Capacity constraint",
    "supply": "Supply disruption",
    "retention": "Customer retention problem",
    "cash": "Cash flow problem",
    "segment": "Market segment mismatch",
    "quality": "Product quality problem",
}

#: The four archetypes the 22-line engine's crisis system also models, by its own letter.
#: `demand_shift` and `trust` are Nadi-only and have no letter.
ARCHETYPE_FOR_SCENARIO_LETTER = {"A": "price_war", "B": "blitz", "C": "leapfrog", "D": "supply"}
SCENARIO_LETTER_FOR_ARCHETYPE = {v: k for k, v in ARCHETYPE_FOR_SCENARIO_LETTER.items()}


@dataclass(frozen=True)
class Strategy:
    id: str
    name: str
    thesis: str
    gain: str
    risk: str


STRATEGIES: tuple[Strategy, ...] = (
    Strategy("fight", "Fight", "Meet it head on and defend volume and share.",
             "Protects share and conversion while the pressure lasts.",
             "Margin, cash burn, and the possibility that the other side escalates."),
    Strategy("differentiate", "Differentiate", "Refuse the comparison. Compete on what you are better at.",
             "Protects price and margin, and compounds into brand and product position.",
             "You will lose volume in the meantime, and it is slow."),
    Strategy("focus", "Focus", "Retreat to the customers you serve best and defend them properly.",
             "Better conversion and retention on a narrower base, at lower cost.",
             "A deliberately smaller market. Share falls even if the business improves."),
    Strategy("learn", "Hold and learn", "Commit little, watch closely, keep the options open.",
             "Preserves cash and buys information for the following quarter.",
             "The situation may be worse by the time you understand it."),
    Strategy("exploit", "Press the advantage", "Treat this as an opening rather than a threat.",
             "Share taken while competitors are distracted, and it does not come back easily.",
             "Needs capacity and cash you may not have. Exposed if the read is wrong."),
)

STRATEGY_BY_ID = {s.id: s for s in STRATEGIES}
STRATEGY_IDS = tuple(s.id for s in STRATEGIES)


# ── declared priorities ──────────────────────────────────────────────


@dataclass(frozen=True)
class Priority:
    id: str
    name: str
    desc: str
    #: The lines that count as following through on this priority.
    keys: tuple[str, ...]


PRIORITIES: tuple[Priority, ...] = (
    Priority("grow", "Grow faster", "Take share now and worry about economics later.",
             ("google", "meta", "social", "direct", "events", "reps", "channel")),
    Priority("cash", "Protect cash", "Extend runway. Accept a slower quarter to stay alive.", ()),
    Priority("product", "Improve the product", "Raise what the product can convert and keep.",
             ("quality", "npd", "design")),
    Priority("ops", "Fix operations", "Build and deliver what has already been sold.",
             ("production", "capex", "supplier", "logistics", "warehouse")),
    Priority("retain", "Keep the customers we have", "Satisfaction and repeat buying over new acquisition.",
             ("cx", "onboarding", "email", "referral")),
    Priority("risk", "Prepare for risk", "Buy cover before you need it.",
             ("supplier", "compliance", "audit", "planning", "working_capital")),
    Priority("longterm", "Build long-term value", "Assets that pay out after this year is over.",
             ("content", "prelaunch", "npd", "capex", "design")),
)

PRIORITY_BY_ID = {p.id: p for p in PRIORITIES}
PRIORITY_IDS = tuple(p.id for p in PRIORITIES)


QUARTER_BRIEFS = (
    (1, "Prove the machine",
     "You have a product, four thousand customers and twelve months of cash. Nobody knows yet whether "
     "this business works. Find out what actually sells before you scale anything."),
    (2, "Scale",
     "You know a little more than you did. Now the question is whether the machine holds together when "
     "you push on it -- and which part gives way first."),
    (3, "Survive competition",
     "The category has noticed you. Somebody with more money is about to make this quarter difficult, "
     "and what you built in the first half decides how much it costs you."),
    (4, "Create value",
     "One quarter left. Whatever the company is going to be worth, it will be worth it because of what "
     "happens now and what you already put in place."),
)

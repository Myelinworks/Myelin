"""Inputs to `compute_simulation_quarter` -- the company between quarters, and one quarter's decisions.

All plain frozen dataclasses. Nothing here touches a DB, a clock or the filesystem, which is
what lets the whole four-quarter run be replayed deterministically from the decision log.
"""

from dataclasses import dataclass, field, replace
from decimal import Decimal

from app.engines.simulation._shared import ZERO, dec
from app.engines.simulation.catalog import (
    BASE_STAFF,
    LINE_KEYS,
    LINE_KIND,
    OPENING_CASH,
    OPENING_OVERHEAD,
    OTHER_LIABILITIES,
    SHARE_CAPITAL,
    DEPARTMENTS,
    PRODUCT_IDS,
)


@dataclass(frozen=True)
class ProductState:
    """One product as it stands entering a quarter."""

    live: bool
    #: "active" builds and sells; "paused" sells existing stock only; "discontinued" clears at 40% off.
    status: str
    price: Decimal
    #: Requested share of the production line, 0-100.
    share: Decimal
    #: Units in stock.
    inv: Decimal
    #: Weighted-average cost of that stock.
    inv_cost: Decimal


@dataclass(frozen=True)
class SimulationCompanyState:
    """Everything the next quarter opens on.

    Far wider than the 22-line engine's `CompanyState` because this scenario models headcount by
    function, a two-product portfolio, an innovation board with lead times, a credit facility and
    a real balance sheet -- none of which the 22-line model carries.
    """

    quarter: int = 1

    # balance sheet
    cash: Decimal = OPENING_CASH
    #: An accepted Q4 "Path A" term sheet's investment, not yet swept into cash. Set on Q4's
    #: opening state once the deal is signed, cleared to zero on `next_state` -- the same
    #: two-step (raised, then closed) `drawn`/`repaid` already model for debt, so a rescue
    #: cheque shows up as `equity_raised` in financing cash flow rather than teleporting
    #: straight into the balance the moment it's accepted.
    pending_investment: Decimal = ZERO
    ar: Decimal = Decimal(800_000)
    ap: Decimal = ZERO
    debt: Decimal = ZERO
    equipment: Decimal = Decimal(2_500_000)
    ip: Decimal = Decimal(1_000_000)
    retained_earnings: Decimal = (
        OPENING_CASH + Decimal(800_000) + Decimal(600) * Decimal(3_250) + Decimal(2_500_000) + Decimal(1_000_000)
        - OTHER_LIABILITIES - SHARE_CAPITAL
    )

    # operations
    installed_capacity: Decimal = Decimal(2_500)
    staff: dict[str, Decimal] = field(default_factory=lambda: dict(BASE_STAFF))
    products: dict[str, ProductState] = field(
        default_factory=lambda: {
            "pulse": ProductState(True, "active", Decimal(9_999), Decimal(100), Decimal(600), Decimal(3_250)),
            "pro": ProductState(False, "active", Decimal(14_999), ZERO, ZERO, Decimal(5_200)),
        }
    )

    # product pipeline
    innovations: tuple[str, ...] = ()
    #: card id -> quarters remaining before it ships.
    pipeline: dict[str, int] = field(default_factory=dict)
    launch_hype: Decimal = ZERO
    launch_boost_left: Decimal = ZERO

    # cumulative scores
    customers: Decimal = Decimal(4_000)
    prior_units: Decimal = ZERO
    brand: Decimal = ZERO
    seo: Decimal = ZERO
    quality: Decimal = ZERO
    innovation: Decimal = ZERO
    npd: Decimal = ZERO
    supplier_rel: Decimal = Decimal(70)
    logistics_eff: Decimal = Decimal(60)
    emp_sat: Decimal = Decimal(65)
    emp_eng: Decimal = Decimal(60)
    compliance: Decimal = Decimal(50)
    forecast: Decimal = Decimal(55)
    audit: Decimal = Decimal(50)
    satisfaction: Decimal = Decimal(50)
    repeat_rate: Decimal = Decimal(10)
    attrition: Decimal = ZERO

    # working capital / terms
    ar_days: Decimal = Decimal(30)
    pay_terms: str = "net30"
    overhead: Decimal = OPENING_OVERHEAD

    # carried performance
    market_share: Decimal = ZERO
    fill_rate: Decimal = Decimal(1)
    prior_demand: Decimal = ZERO
    last_gm: Decimal = Decimal("0.66")
    last_net_cf: Decimal = ZERO
    rev_history: tuple[Decimal, ...] = ()
    last_mix: dict[str, Decimal] = field(default_factory=dict)

    #: What last quarter's crisis response is still doing to this one.
    aftermath: dict[str, Decimal | str] = field(default_factory=dict)
    crisis_log: tuple[dict, ...] = ()

    # survival flags, sticky once set
    wc_breached: bool = False
    ever_insolvent: bool = False

    def with_(self, **kwargs) -> "SimulationCompanyState":
        return replace(self, **kwargs)


def opening_state() -> SimulationCompanyState:
    """The company as it stands the morning of Q1."""
    return SimulationCompanyState()


@dataclass(frozen=True)
class CrisisResponse:
    """The student's answer to a live market event."""

    #: Which archetype fired. `None` outside the crisis quarter.
    variant: str | None = None
    #: What they believe is happening. Graded against `TRUE_DIAGNOSIS`, never confirmed to them.
    diagnosis: str | None = None
    reasoning: str = ""
    #: One of `STRATEGY_IDS`.
    strategy: str | None = None
    #: Rs lakhs put behind the strategy. Effect saturates.
    commit: Decimal = ZERO

    @property
    def is_live(self) -> bool:
        return bool(self.variant)


@dataclass(frozen=True)
class SimulationAllocations:
    """One quarter's decisions in full.

    `lines` holds every rupee spend line plus the hire/fire counts, keyed by `LINE_KEYS`, all in
    Rs lakhs except the `hire_*`/`fire_*` counts which are headcount. The structural decisions
    that are not spend -- warranty term, supplier terms, which innovation cards to start, and
    the product portfolio -- are their own fields, because none of them is a budget.
    """

    lines: dict[str, Decimal] = field(default_factory=dict)
    warranty: str = "6mo"
    pay_terms: str = "net30"
    #: Innovation-board cards started this quarter. Capitalised, not expensed.
    start_inno: tuple[str, ...] = ()
    #: Price / line-share / status per product. `None` keeps the opening state unchanged.
    products: dict[str, ProductState] | None = None
    crisis: CrisisResponse = field(default_factory=CrisisResponse)

    #: Declared before the levers are seen, and compared against actual spend at the close.
    priority: str | None = None
    #: The five reflection answers, recorded before the outcome is known.
    reflection: dict[str, object] = field(default_factory=dict)

    def get(self, key: str) -> Decimal:
        return dec(self.lines.get(key))

    def _sum_kind(self, kind: str) -> Decimal:
        return sum((self.get(k) for k in LINE_KEYS if LINE_KIND[k] == kind), ZERO)

    @property
    def opex_lakhs(self) -> Decimal:
        return self._sum_kind("opex")

    @property
    def capex_lakhs(self) -> Decimal:
        return self._sum_kind("capex")

    @property
    def committed_lakhs(self) -> Decimal:
        """Every discretionary rupee, before people costs and the innovation board."""
        return self.opex_lakhs + self.capex_lakhs


def normalise_lines(raw: dict[str, object] | None) -> dict[str, Decimal]:
    """Coerce a submitted allocation to numbers, flooring at zero and dropping unknown keys.

    Floors rather than rejects: a negative spend line is meaningless, and silently treating it
    as zero is what the reference implementation does at every input boundary.
    """
    raw = raw or {}
    return {k: max(ZERO, dec(raw.get(k))) for k in LINE_KEYS}


def headcount(staff: dict[str, Decimal]) -> Decimal:
    return sum((dec(staff.get(d.id)) for d in DEPARTMENTS), ZERO)


def salary_bill(staff: dict[str, Decimal]) -> Decimal:
    return sum((dec(staff.get(d.id)) * d.salary for d in DEPARTMENTS), ZERO)


def inventory_value(products: dict[str, ProductState]) -> Decimal:
    return sum((products[p].inv * products[p].inv_cost for p in PRODUCT_IDS), ZERO)

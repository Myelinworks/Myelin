"""Three CEOs, told apart by how they read the company rather than by how much they spend.

Each persona is a pure function of what the API has already told it: the run state, and the
preview of its own draft plan. None of them reads engine internals -- everything they decide
from is on the wire, which is what makes the comparison a fair test of the product and not of
the test's own arithmetic.

    NOVICE        Buys leads. Every quarter, with whatever cash is in the bank. Declares no
                  priority, answers no reflection, ignores the market event, and keeps the
                  company because nobody told them the offer was worth reading.

    INTERMEDIATE  Spreads the budget across every function, which is not the same as funding
                  the one that is binding. Declares a priority, half-fills the reflection,
                  answers the crisis with the safe posture, and takes the cheque on offer.

    EXPERT        Reads the gate the preview reports, moves money at it, keeps the plan inside
                  the ceiling, names the constraint it is actually solving, diagnoses the event
                  from its own evidence, and reads the term sheet against continuation value.

`TRUE_DIAGNOSIS` is imported for the expert alone, and that is the point: the expert persona is
defined as the CEO who reads the market correctly. The other two are given no such help.
"""

from __future__ import annotations

from app.engines.simulation.catalog import TRUE_DIAGNOSIS

LAKH = 100_000

#: Which posture each archetype actually rewards, for the persona that reads it right.
BEST_STRATEGY = {
    "price_war": "differentiate",
    "blitz": "focus",
    "leapfrog": "differentiate",
    "supply": "fight",
    "demand_shift": "exploit",
    "trust": "fight",
}

#: The balanced quarter both the intermediate and the expert start from, in Rs lakhs. Sharing
#: it is the point of the comparison: the two CEOs commit a similar budget, and what separates
#: them is where it goes and what they do with what the preview tells them.
BALANCED = {
    "google": 9, "meta": 6, "content": 5, "social": 4, "email": 2,
    "reps": 7, "crm": 3, "onboarding": 3,
    "quality": 5, "npd": 4, "design": 3,
    "production": 9, "supplier": 3, "logistics": 3, "warehouse": 2,
    "culture": 2, "hr_training": 2, "cx": 3,
    "compliance": 2, "planning": 2, "audit": 1,
}

#: What the preview's gate says is binding -> where an expert puts the next rupee.
GATE_RESPONSE = {
    "sales_capacity": {"reps": 6, "onboarding": 3, "crm": 2, "sales_training": 2},
    "production_supply": {"production": 8, "capex": 6, "supplier": 3, "logistics": 2},
    "conversion_ceiling": {"design": 5, "quality": 5, "npd": 4},
    "market_position": {"content": 5, "social": 4, "prelaunch": 4},
    "none": {"google": 3, "content": 3, "npd": 2},
}

#: The gate id the API reports -> the constraint id the scorer grades the reflection against.
GATE_TO_CONSTRAINT = {
    "sales_capacity": "sales",
    "production_supply": "production",
    "conversion_ceiling": "ceiling",
    "market_position": "position",
}


def _plan(lines: dict[str, float], **rest) -> dict:
    """A submitted quarter, in the shape `POST .../simulation/preview` and `/lock` accept."""
    return {
        "lines": {k: float(v) for k, v in lines.items()},
        "warranty": rest.get("warranty", "6mo"),
        "pay_terms": rest.get("pay_terms", "net30"),
        "start_inno": rest.get("start_inno", []),
        "products": None,
        "priority": rest.get("priority"),
        "reflection": rest.get("reflection", {}),
        "crisis": rest.get(
            "crisis", {"diagnosis": None, "reasoning": "", "strategy": None, "commit": 0}
        ),
    }


def _scale(lines: dict[str, float], factor: float) -> dict[str, float]:
    """Shrink every rupee line by the same factor, leaving headcount counts alone."""
    return {
        k: (v if k.startswith(("hire_", "fire_")) or k in ("draw", "repay") else round(v * factor, 2))
        for k, v in lines.items()
    }


class Persona:
    """One play style. `name` is what the report table calls it; `label` says what it does."""

    name: str = "persona"
    label: str = ""

    # ── the quarter ──────────────────────────────────────────────────
    def draft(self, quarter: int, run: dict) -> dict:  # pragma: no cover - overridden
        raise NotImplementedError

    def revise(self, plan: dict, preview: dict) -> dict:
        """A second pass once the preview has come back. Only the expert uses it."""
        return plan

    # ── the Q4 term sheet ────────────────────────────────────────────
    def choose_path(self, term_sheet: dict, run: dict) -> str:  # pragma: no cover - overridden
        raise NotImplementedError


class Novice(Persona):
    """Everything into paid acquisition, because leads look like progress."""

    name = "novice"
    label = "Novice · buys leads"

    def draft(self, quarter: int, run: dict) -> dict:
        spend = {1: 55.0, 2: 65.0, 3: 75.0, 4: 85.0}[quarter]
        # No priority, no reflection, no answer to the market event: the three things this
        # persona never thinks to do, and three of the seven traits it therefore cannot score.
        return _plan({"google": spend * 0.6, "meta": spend * 0.4})

    def choose_path(self, term_sheet: dict, run: dict) -> str:
        # Never opens the term sheet. Keeps the company because that is the default.
        return "C"


class Intermediate(Persona):
    """A little of everything, a declared priority, and the safe answer to the event."""

    name = "intermediate"
    label = "Intermediate · spreads it evenly"

    def draft(self, quarter: int, run: dict) -> dict:
        # The same plan every quarter, whatever the last one reported. That is the persona:
        # a reasonable budget, never revisited.
        lines = dict(BALANCED)
        if quarter == 2:
            lines["hire_sales"] = 1
        crisis = {"diagnosis": None, "reasoning": "", "strategy": None, "commit": 0}
        if run.get("crisis"):
            # Answers the event, but with the first diagnosis on the list and the posture that
            # never looks wrong in a board meeting.
            crisis = {
                "diagnosis": run["crisis"]["diagnoses"][0]["id"],
                "reasoning": "The numbers moved and this is the closest label on the list.",
                "strategy": "learn",
                "commit": 6,
            }
        return _plan(
            lines,
            priority="grow",
            # Half the reflection: says what it is solving, never what it gave up.
            reflection={"constraint": "demand", "expect": "growslow"},
            crisis=crisis,
        )

    def choose_path(self, term_sheet: dict, run: dict) -> str:
        # Takes the money. Does not check the covenant against its own unit history.
        return "A"


class Expert(Persona):
    """Funds the binding stage, stays inside the ceiling, and prices the term sheet."""

    name = "expert"
    label = "Expert · funds the constraint"

    def draft(self, quarter: int, run: dict) -> dict:
        lines = dict(BALANCED)

        # React to the quarter that just closed: its gate is the stage that decided it.
        history = run.get("history") or []
        gate = history[-1].get("gate", "none") if history else "none"
        for key, add in GATE_RESPONSE.get(gate, {}).items():
            lines[key] = lines.get(key, 0) + add
        if gate == "sales_capacity" and quarter <= 3:
            lines["hire_sales"] = 1

        crisis = {"diagnosis": None, "reasoning": "", "strategy": None, "commit": 0}
        if run.get("crisis"):
            archetype = run["crisis"]["archetype"]
            crisis = {
                "diagnosis": TRUE_DIAGNOSIS[archetype],
                "reasoning": (
                    "The directors' evidence all points the same way, and the symptom set "
                    "matches this cause rather than the one it is easiest to blame."
                ),
                "strategy": BEST_STRATEGY[archetype],
                "commit": 10,
            }

        return _plan(
            lines,
            start_inno=["app"] if quarter == 1 else ["battery"] if quarter == 2 else [],
            priority={1: "product", 2: "grow", 3: "ops", 4: "longterm"}[quarter],
            reflection={
                # Filled in properly by `revise`, once the preview says what is binding.
                "constraint": "demand",
                "sacrifice": ["events", "channel"],
                "risk": "Spending into a stage that is not the one holding the quarter back.",
                "expect": "growslow",
            },
            crisis=crisis,
        )

    def revise(self, plan: dict, preview: dict) -> dict:
        """Read the preview and act on it: name the real constraint, and respect the ceiling."""
        gate = preview["projection"].get("gate", "none")
        plan["reflection"]["constraint"] = GATE_TO_CONSTRAINT.get(gate, "demand")

        budget = preview["budget"]
        ceiling = float(budget["ceiling"])
        # People and innovation cards are committed by decisions already taken this quarter and
        # do not scale with the spend lines, so the discretionary budget is what is left of the
        # ceiling after them -- scaling against total committed would overshoot every time.
        fixed = float(budget["people"]) + float(budget["inno"])
        discretionary = float(budget["opex"]) + float(budget["capex"]) + float(budget["repay"])
        if discretionary <= 0 or ceiling <= 0:
            return plan

        # Size the quarter to what the balance sheet actually supports -- in both directions.
        # Overcommitting is how a run goes insolvent; sitting on idle cash is a capital
        # allocation the rubric marks down just as hard. A tenth of the ceiling stays unspent:
        # that margin is the difference between a tight quarter and an insolvent one.
        room = max(0.0, ceiling * 0.9 - fixed)

        # If the plan does not fit, draw on the facility before cutting the plan. A quarter
        # funded by credit still sells; a quarter cut to fit a thin cash balance sells less,
        # earns less and leaves next quarter thinner still. The facility is capped by the
        # engine, so ask for the shortfall and take whatever the limit allows.
        if discretionary > room:
            headroom = float(preview["projection"]["debt_limit"]) - float(
                preview["opening_state"]["debt"]
            )
            draw = min((discretionary - room) * 1.1, max(0.0, headroom) / LAKH)
            if draw > 1:
                plan["lines"]["draw"] = round(draw, 2)
                room += draw * 0.9

        # Never more than double the plan in one step -- a quarter is not long enough to spend
        # into that well, and the mix would stop being one the CEO reasoned about.
        plan["lines"] = _scale(plan["lines"], min(room / discretionary, 2.0))
        return plan

    def choose_path(self, term_sheet: dict, run: dict) -> str:
        """Price the acquisition against continuation value; take the cheque only if the
        covenant is reachable from the units already being sold."""
        offers = {o["id"]: o for o in term_sheet["offers"]}
        price = float(offers["B"]["price"] or 0)
        continuation = float(term_sheet["true_continuation_value_inr"])
        if price > continuation * 1.05:
            return "B"  # they are paying more than the business is worth run on.

        covenant = float(offers["A"]["covenant"] or 0)
        q3_units = float((run["history"][2] or {}).get("units_sold", 0))
        if covenant <= 0 or covenant <= q3_units * 1.25:
            return "A"
        return "C"


NOVICE = Novice()
INTERMEDIATE = Intermediate()
EXPERT = Expert()

ALL_PERSONAS = (NOVICE, INTERMEDIATE, EXPERT)

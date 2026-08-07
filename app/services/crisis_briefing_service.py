"""What a student is allowed to know about their crisis *before* they respond to it.

`docs/11-crisis-system.md` section 2 draws the line this module implements:

    Students are told the narrative and the choices, but **never** the underlying formula
    constants or thresholds -- they must diagnose their specific situation from their own
    quarter's results.

Before this, neither half of that was reachable: `RunStateResponse.crisis_quarter` told a client
*when* a crisis fires, and nothing told it *what* the crisis is. A frontend could only render a
generic five-field spend form, which meant a Feature Leapfrog run could pour its whole response
budget into the Price-Match Fund -- a line that does literally nothing in that scenario
(`engines/crisis.RESPONSE_LINES_BY_SCENARIO`).

Everything here is either config copy or an already-pure engine mapping. No coefficient,
threshold, penalty magnitude or multiplier is ever included -- that is the half students are
meant to diagnose, and leaking it would defeat the exercise the crisis exists to run.
"""

from dataclasses import dataclass

from app.config.loader import load_profile, load_scenario
from app.engines.crisis import RESPONSE_LINES_BY_SCENARIO
from app.models.company import Company
from app.models.quarter import Quarter
from app.services.company_service import assign_crisis_scenario

# `CrisisConfig`'s per-scenario attribute for each letter docs/11 assigns.
_SCENARIO_ATTR = {
    "A": "price_warrior",
    "B": "marketing_blitz",
    "C": "feature_leapfrog",
    "D": "supply_shock",
}

# Student-facing names for the `QuarterAllocation` crisis columns. The mapping of which lines
# matter is *not* here -- that is `RESPONSE_LINES_BY_SCENARIO`, so this dict only ever supplies
# display text for a line the engine already said was relevant.
_RESPONSE_LINE_LABELS = {
    "price_match_fund": "Price Match Fund",
    "comparison_ads": "Comparison Ads",
    "retention_offers": "Retention Offers",
    "emergency_supply_fund": "Emergency Supply Fund",
    "crisis_choice_d_spend": "Choice D spend",
}


class NotCrisisQuarterError(Exception):
    """This quarter isn't the one the scenario fires its crisis in, so there is no briefing to
    read -- distinct from "the run has no crisis at all", which raises the same type with its
    own reason rather than returning an empty briefing that reads like a crisis with no content.
    """


@dataclass(frozen=True)
class CrisisChoiceBriefing:
    code: str
    label: str
    effect: str


@dataclass(frozen=True)
class CrisisResponseLine:
    field: str
    label: str


@dataclass(frozen=True)
class CrisisBriefing:
    scenario_code: str
    title: str
    category: str
    narrative: str
    choices: list[CrisisChoiceBriefing]
    response_lines: list[CrisisResponseLine]
    ignoring_is_legal: bool


def crisis_scenario_letter(company: Company) -> str:
    """Which of the four events (docs/11) this company draws. Deterministic from the company id
    -- the same assignment `quarter_run_service` scores against, so the briefing can never name
    a different crisis than the one that actually fires."""
    scenario = load_scenario(company.scenario_id)
    return scenario.crisis_scenario or assign_crisis_scenario(company.id)


def build_crisis_briefing(company: Company, quarter: Quarter) -> CrisisBriefing:
    """Assemble the pre-response briefing for `quarter`, or raise `NotCrisisQuarterError` if this
    isn't the quarter that carries the crisis."""
    scenario = load_scenario(company.scenario_id)
    if scenario.crisis_quarter is None:
        raise NotCrisisQuarterError(f"scenario {scenario.scenario_id} has no crisis quarter")
    if quarter.number != scenario.crisis_quarter:
        raise NotCrisisQuarterError(
            f"quarter {quarter.number} is not this scenario's crisis quarter "
            f"(Q{scenario.crisis_quarter})"
        )

    letter = crisis_scenario_letter(company)
    # `company.profile_name`, not the scenario's -- that is the profile `run_quarter` actually
    # evaluates this company against, so the briefing describes the crisis that will really fire.
    config = getattr(load_profile(company.profile_name).crisis, _SCENARIO_ATTR[letter])
    briefing = config.briefing

    return CrisisBriefing(
        scenario_code=letter,
        title=briefing.title,
        category=briefing.category,
        narrative=briefing.narrative,
        choices=[
            CrisisChoiceBriefing(code=c.code, label=c.label, effect=c.effect) for c in briefing.choices
        ],
        response_lines=[
            CrisisResponseLine(field=field, label=_RESPONSE_LINE_LABELS[field])
            for field in RESPONSE_LINES_BY_SCENARIO[letter]
        ],
        # docs/11 section 7: spending Rs 0 is a real, accepted response -- penalised by the
        # `crisis_ignored` modifier (-4), never refused. Stated explicitly so a client doesn't
        # invent a required-field rule the API doesn't have.
        ignoring_is_legal=True,
    )

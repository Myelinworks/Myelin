"""`build_crisis_briefing` -- the boundary between what a student is told about their crisis and
what they must diagnose themselves (`docs/11-crisis-system.md` section 2).

The response-line assertions are the ones that matter most: they lock the briefing to
`engines/crisis.RESPONSE_LINES_BY_SCENARIO`, the same mapping `response_spend_total` scores
against, so the advice a student acts on can never drift from what the engine actually reads.
"""

import uuid

import pytest

from app.engines.crisis import RESPONSE_LINES_BY_SCENARIO
from app.models.company import Company
from app.models.quarter import Quarter, QuarterStatus
from app.services.crisis_briefing_service import (
    NotCrisisQuarterError,
    build_crisis_briefing,
    crisis_scenario_letter,
)

SCENARIO_ID = "nadi_wear_standard"
CRISIS_QUARTER = 3


def _company(company_id: uuid.UUID | None = None) -> Company:
    return Company(
        id=company_id or uuid.uuid4(),
        name="Nadi Wear",
        scenario_id=SCENARIO_ID,
        seed_name="nadi_wear",
        profile_name="default",
    )


def _quarter(company: Company, number: int) -> Quarter:
    return Quarter(
        id=uuid.uuid4(),
        company_id=company.id,
        number=number,
        status=QuarterStatus.IN_PROGRESS,
        cash_balance=0,
        revenue=0,
    )


def _company_drawing(letter: str) -> Company:
    """Crisis assignment is a deterministic hash of the company id, so a company that draws a
    specific letter is found by trying ids rather than by injecting one -- the assignment is the
    thing under test everywhere else, and stubbing it here would hide a real mismatch."""
    for _ in range(500):
        company = _company()
        if crisis_scenario_letter(company) == letter:
            return company
    raise AssertionError(f"no company id drew crisis scenario {letter} in 500 tries")


class TestGating:
    def test_non_crisis_quarter_has_no_briefing(self):
        company = _company()
        with pytest.raises(NotCrisisQuarterError, match="not this scenario's crisis quarter"):
            build_crisis_briefing(company, _quarter(company, 1))

    def test_crisis_quarter_returns_a_briefing(self):
        company = _company()
        briefing = build_crisis_briefing(company, _quarter(company, CRISIS_QUARTER))
        assert briefing.scenario_code in ("A", "B", "C", "D")
        assert briefing.narrative


class TestContent:
    @pytest.mark.parametrize("letter", ["A", "B", "C", "D"])
    def test_response_lines_match_what_the_engine_scores(self, letter):
        company = _company_drawing(letter)
        briefing = build_crisis_briefing(company, _quarter(company, CRISIS_QUARTER))

        assert briefing.scenario_code == letter
        assert tuple(line.field for line in briefing.response_lines) == RESPONSE_LINES_BY_SCENARIO[letter]

    @pytest.mark.parametrize("letter", ["A", "B", "C", "D"])
    def test_every_scenario_has_narrative_choices_and_labels(self, letter):
        company = _company_drawing(letter)
        briefing = build_crisis_briefing(company, _quarter(company, CRISIS_QUARTER))

        assert briefing.title and briefing.narrative
        assert briefing.category in ("competitive", "operational")
        assert briefing.choices, "every scenario exposes at least one Strategic Choice"
        assert all(c.code in ("A", "B", "C", "D") and c.label and c.effect for c in briefing.choices)
        assert all(line.label for line in briefing.response_lines)

    def test_feature_leapfrog_offers_only_its_choice_d_line(self):
        """The whole point of the endpoint: Scenario C has no documented recovery for its
        dampening or conversion penalty, so funding any other line is inert. A student shown the
        full five-field form would have no way to know that."""
        company = _company_drawing("C")
        briefing = build_crisis_briefing(company, _quarter(company, CRISIS_QUARTER))

        assert [line.field for line in briefing.response_lines] == ["crisis_choice_d_spend"]

    def test_supply_shock_is_the_operational_scenario(self):
        company = _company_drawing("D")
        briefing = build_crisis_briefing(company, _quarter(company, CRISIS_QUARTER))

        assert briefing.category == "operational"
        assert "emergency_supply_fund" in [line.field for line in briefing.response_lines]

    def test_ignoring_the_crisis_is_reported_as_legal(self):
        company = _company()
        briefing = build_crisis_briefing(company, _quarter(company, CRISIS_QUARTER))
        assert briefing.ignoring_is_legal is True


class TestNoConstantsLeak:
    """docs/11 section 2: students are told the narrative and the choices, *never* the underlying
    constants. A briefing that quoted "25% cut" or "-8 points" would hand over the diagnosis the
    crisis exists to make them work out."""

    @pytest.mark.parametrize("letter", ["A", "B", "C", "D"])
    def test_no_field_carries_a_numeric_constant(self, letter):
        company = _company_drawing(letter)
        briefing = build_crisis_briefing(company, _quarter(company, CRISIS_QUARTER))

        prose = " ".join(
            [briefing.title, briefing.narrative, briefing.category]
            + [c.label for c in briefing.choices]
            + [c.effect for c in briefing.choices]
            + [line.label for line in briefing.response_lines]
        )
        # Rupee prices in a narrative are the competitor's shelf price -- public, stated to
        # students by design (docs/11's own narratives quote them). What must never appear is a
        # coefficient/threshold/penalty: percentages, point deltas, and multipliers.
        for banned in ("%", " pts", "point", "multiplier", "coefficient", "threshold ", "0.75", "0.60", "0.80", "0.50"):
            assert banned not in prose.lower(), f"scenario {letter} briefing leaks {banned!r}"

"""The pre-response crisis briefing -- what `docs/11-crisis-system.md` section 2 says students
are entitled to know before they act, and nothing beyond it.

No field here carries a coefficient, threshold, penalty magnitude or multiplier. That half is
what the crisis exists to make students diagnose from their own quarter's results; the report
they read *after* locking is where the numbers show up.
"""

from pydantic import BaseModel, ConfigDict, Field


class _FromAttributes(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CrisisChoiceSchema(_FromAttributes):
    """One Strategic Choice, described qualitatively. Only the choices this scenario gives a
    distinct outcome are listed -- a letter the engine treats identically to submitting nothing
    is not presented as if it were a real option."""

    code: str = Field(description='"A" / "B" / "C" / "D" -- the value to send as `crisis_choice`.')
    label: str
    effect: str = Field(description="What this posture does, in plain language. Never a formula.")


class CrisisResponseLineSchema(_FromAttributes):
    """A crisis spend line that actually feeds this scenario's recovery formulas."""

    field: str = Field(
        description="The request field on `POST .../allocations/crisis` this line corresponds to."
    )
    label: str


class CrisisBriefingResponse(_FromAttributes):
    """`GET .../quarters/{quarter_id}/crisis` -- readable only in the scenario's crisis quarter
    (404 otherwise), and readable before, during and after the response is submitted: the
    briefing is a description of the event, not of the student's answer to it.

    `response_lines` is the field that makes this endpoint worth calling. The crisis allocation
    request accepts five spend lines, but each scenario's recovery formulas read only a subset --
    Feature Leapfrog, for example, has no documented recovery for its dampening or conversion
    penalty at all, so every rupee outside its Choice-D line is inert. Rendering the full
    five-field form to every student invites exactly that mistake.
    """

    scenario_code: str = Field(
        description='Which of the four events fired ("A" Price Warrior / "B" Marketing Blitz / '
        '"C" Feature Leapfrog / "D" Global Supply Shock). This is a different letter axis than '
        "`crisis_choice`: Scenario B's Choice A is not Scenario A's Choice A."
    )
    title: str
    category: str = Field(
        description='"competitive" (a rival\'s launch -- can be answered commercially) or '
        '"operational" (an external shock -- must be absorbed, not marketed around).'
    )
    narrative: str = Field(description="What has happened to the company, as the student is told it.")
    choices: list[CrisisChoiceSchema]
    response_lines: list[CrisisResponseLineSchema]
    ignoring_is_legal: bool = Field(
        description="Always true. Submitting nothing is an accepted response, not a refused one "
        "-- it is simply penalised (the `crisis_ignored` modifier). Stated so a client does not "
        "invent a required-field rule this API does not have."
    )

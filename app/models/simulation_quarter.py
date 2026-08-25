import uuid

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPkMixin


class SimulationQuarter(Base, UUIDPkMixin, TimestampMixin):
    """One locked quarter of a Nadi Wear run -- the decisions, and what they produced.

    Two JSON documents rather than a column per figure, and the reason is the engine's own
    shape: `decisions` is the ~40-line allocation plus the structural choices (warranty,
    supplier terms, innovation cards, the product portfolio, the crisis response), and
    `result` is the ~150-field `SimulationQuarterResult`. Spreading either across typed columns
    would mean a migration every time the scenario gains a lever, for no query we ever run --
    nothing filters or aggregates on an individual spend line, and the report is always read
    whole, by company and quarter.

    `decisions` is the authoritative record. Because the engine is pure, the entire run can be
    replayed from these rows alone: `result` and `opening_state` are a cache of that replay,
    kept so reading a report never costs a re-simulation.
    """

    __tablename__ = "simulation_quarters"
    __table_args__ = (
        UniqueConstraint("company_id", "number", name="uq_simulation_quarter_company_number"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: 1-4. The scenario is fixed at four quarters.
    number: Mapped[int] = mapped_column(Integer, nullable=False)

    #: Everything the CEO chose: spend lines, headcount moves, warranty, terms, cards,
    #: portfolio, the declared priority, the reflection and the crisis response.
    decisions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    #: The company as this quarter opened -- so a single quarter can be re-run in isolation.
    opening_state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    #: The full computed result, as the report and every closed-quarter screen render it.
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    #: The seven traits, the modifiers that fired, the final score and the band.
    score: Mapped[dict] = mapped_column(JSONB, nullable=False)

    ceo_score: Mapped[str] = mapped_column(String(16), nullable=False)
    band: Mapped[str] = mapped_column(String(16), nullable=False)


class SimulationRun(Base, UUIDPkMixin, TimestampMixin):
    """Run-level state for a Nadi Wear company: the assigned market event and the Q4 decision.

    The archetype is assigned once, deterministically, and stored rather than re-derived, so a
    student cannot reroll their crisis by reloading -- the same reason
    `company_service.assign_crisis_scenario` is deterministic in the 22-line flow.
    """

    __tablename__ = "simulation_runs"
    __table_args__ = (UniqueConstraint("company_id", name="uq_simulation_run_company"),)

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    #: One of `catalog.ARCHETYPE_IDS`. Fixed at company creation.
    archetype: Mapped[str] = mapped_column(String(32), nullable=False)

    #: "A" / "B" / "C", once the Q4 term sheet is signed.
    endgame_path: Mapped[str | None] = mapped_column(String(1), nullable=True)
    endgame_term_sheet: Mapped[str | None] = mapped_column(String(100), nullable=True)
    endgame_reasoning: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    #: How many of the 2 allowed rewinds the player has used. Backend is source of truth.
    rewinds_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

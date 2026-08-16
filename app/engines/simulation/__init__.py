"""The Nadi Wear four-quarter engine.

A second, self-contained scenario engine sitting alongside the 22-line one in
`app/engines/`. Same discipline -- pure functions, frozen dataclasses, Decimal money, no I/O --
but a wider model: headcount by function, a two-product portfolio, an innovation board with
lead times, a credit facility, supplier terms, six market-event archetypes and a real balance
sheet.

Nothing here is imported by the 22-line pipeline, and nothing here imports it. The two share
only the rubric's seven trait names and weights, deliberately, so their CEO scores mean the
same thing.

    state.opening_state()          -- the company the morning of Q1
    quarter.compute_simulation_quarter() -- one quarter, end to end
    scoring.score_quarter()        -- the seven traits plus modifiers
    endgame.build_term_sheet()     -- the Q4 menu, once three quarters have locked
    endgame.settle()               -- how the chosen path resolves
"""

from app.engines.simulation.crisis import assess, available_strategies, commit_reading, health_factors, respond
from app.engines.simulation.endgame import Settlement, TermSheet, build_term_sheet, settle
from app.engines.simulation.quarter import SimulationQuarterResult, compute_simulation_quarter
from app.engines.simulation.scoring import SimulationScore, band_for, priority_match, score_quarter
from app.engines.simulation.state import (
    CrisisResponse,
    SimulationAllocations,
    SimulationCompanyState,
    ProductState,
    normalise_lines,
    opening_state,
)

__all__ = [
    "assess",
    "available_strategies",
    "band_for",
    "build_term_sheet",
    "commit_reading",
    "compute_simulation_quarter",
    "CrisisResponse",
    "health_factors",
    "SimulationAllocations",
    "SimulationCompanyState",
    "SimulationQuarterResult",
    "SimulationScore",
    "normalise_lines",
    "opening_state",
    "priority_match",
    "ProductState",
    "respond",
    "score_quarter",
    "settle",
    "Settlement",
    "TermSheet",
]

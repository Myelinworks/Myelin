"""rename the four-quarter simulation tables

`c7d4a1e9b820` created these as `nadi_runs`/`nadi_quarters`, after the scenario that ships in
them. The engine is scenario-agnostic -- a second scenario would run through exactly the same
tables -- so they are renamed to describe what they are rather than which scenario happened to
be first. "Nadi Wear" remains the company the shipped scenario is about, and
`companies.scenario_id` still carries `nadi_wear_standard`; nothing about that changes.

A rename rather than a drop-and-recreate: the rows already in these tables are real runs, and
`decisions` is the authoritative record the whole run replays from. Indexes and constraints are
renamed alongside so nothing is left carrying the old name.

Revision ID: d3f81a5c9e42
Revises: c7d4a1e9b820
Create Date: 2026-08-16 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3f81a5c9e42"
down_revision: Union[str, Sequence[str], None] = "c7d4a1e9b820"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.rename_table("nadi_runs", "simulation_runs")
    op.rename_table("nadi_quarters", "simulation_quarters")

    # Postgres keeps the old names on indexes and constraints through a table rename.
    op.execute("ALTER INDEX ix_nadi_runs_company_id RENAME TO ix_simulation_runs_company_id")
    op.execute("ALTER INDEX ix_nadi_quarters_company_id RENAME TO ix_simulation_quarters_company_id")
    op.execute("ALTER TABLE simulation_runs RENAME CONSTRAINT uq_nadi_run_company TO uq_simulation_run_company")
    op.execute(
        "ALTER TABLE simulation_quarters "
        "RENAME CONSTRAINT uq_nadi_quarter_company_number TO uq_simulation_quarter_company_number"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "ALTER TABLE simulation_quarters "
        "RENAME CONSTRAINT uq_simulation_quarter_company_number TO uq_nadi_quarter_company_number"
    )
    op.execute("ALTER TABLE simulation_runs RENAME CONSTRAINT uq_simulation_run_company TO uq_nadi_run_company")
    op.execute("ALTER INDEX ix_simulation_quarters_company_id RENAME TO ix_nadi_quarters_company_id")
    op.execute("ALTER INDEX ix_simulation_runs_company_id RENAME TO ix_nadi_runs_company_id")

    op.rename_table("simulation_quarters", "nadi_quarters")
    op.rename_table("simulation_runs", "nadi_runs")

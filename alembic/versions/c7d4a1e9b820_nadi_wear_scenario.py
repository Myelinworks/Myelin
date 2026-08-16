"""nadi wear scenario -- nadi_runs and nadi_quarters

Two new tables for the Nadi Wear four-quarter scenario (`app/engines/nadi/`). Purely additive:
no existing table, column or constraint is touched, so a company driven by the 22-line pipeline
is completely unaffected and the two flows can coexist on the same database.

`nadi_quarters.decisions` is the authoritative record -- the engine is pure, so the whole run
replays from those rows. `opening_state`, `result` and `score` are a cache of that replay, kept
so reading a report never costs a re-simulation. They are JSONB rather than typed columns
because nothing queries an individual spend line: the report is always read whole, by company
and quarter, and a column per figure would mean a migration every time the scenario gains a
lever.

Revision ID: c7d4a1e9b820
Revises: f9663562516e
Create Date: 2026-08-16 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c7d4a1e9b820"
down_revision: Union[str, Sequence[str], None] = "f9663562516e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "nadi_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        # Assigned once from the company id and stored, so reloading cannot reroll the crisis.
        sa.Column("archetype", sa.String(length=32), nullable=False),
        sa.Column("endgame_path", sa.String(length=1), nullable=True),
        sa.Column("endgame_term_sheet", sa.String(length=100), nullable=True),
        sa.Column("endgame_reasoning", sa.String(length=2000), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id", name="uq_nadi_run_company"),
    )
    op.create_index(op.f("ix_nadi_runs_company_id"), "nadi_runs", ["company_id"], unique=False)

    op.create_table(
        "nadi_quarters",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("decisions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("opening_state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("score", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ceo_score", sa.String(length=16), nullable=False),
        sa.Column("band", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # One row per quarter per company: locking Q2 twice is a bug, not an upsert.
        sa.UniqueConstraint("company_id", "number", name="uq_nadi_quarter_company_number"),
    )
    op.create_index(op.f("ix_nadi_quarters_company_id"), "nadi_quarters", ["company_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_nadi_quarters_company_id"), table_name="nadi_quarters")
    op.drop_table("nadi_quarters")
    op.drop_index(op.f("ix_nadi_runs_company_id"), table_name="nadi_runs")
    op.drop_table("nadi_runs")

"""Persist the Q4 endgame settlement on simulation_runs.

At Quarter 4 lock the term sheet is settled against the quarter that happened. That outcome
(valuation, covenant hit/miss, equity, game over) is what the CEO performance report shows,
and a reopened completed run must show the exact same numbers -- so it is stored here rather
than reconstructed at read time.

Revision ID: a2b3c4d5e6f7
Revises: d1e2f3a4b5c6
Create Date: 2026-08-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = 'a2b3c4d5e6f7'
down_revision: Union[str, Sequence[str], None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'simulation_runs',
        sa.Column('settlement', JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('simulation_runs', 'settlement')

"""Add simulation_runs.rewinds_used -- server-side rewind counter.

Backend is source of truth for how many of the 2 allowed rewinds a player has consumed.
Default 0 means existing runs start with both rewinds available.

Revision ID: d1e2f3a4b5c6
Revises: c1a7e2d40b93
Create Date: 2026-08-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c1a7e2d40b93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'simulation_runs',
        sa.Column('rewinds_used', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('simulation_runs', 'rewinds_used')

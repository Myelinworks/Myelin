"""phase 11 -- endgame_decisions table

New table for the Q4 strategic decision (`docs/16-quarter-4-endgame.md` section 3): one row per
company, submitted before Q4 locks. `path` is "A"/"B"/"C"; `term_sheet_name` records which named
offer from the assigned tier's menu was picked; `reasoning` is free text, read by a future
judgment scorer exactly like Phase 8's evidence, never scored by this migration.

Revision ID: a3f6d1c9e4b7
Revises: 1d6e3caeaf78
Create Date: 2026-08-05 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a3f6d1c9e4b7'
down_revision: Union[str, Sequence[str], None] = '1d6e3caeaf78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'endgame_decisions',
        sa.Column('company_id', sa.UUID(), nullable=False),
        sa.Column('quarter_id', sa.UUID(), nullable=False),
        sa.Column('path', sa.String(length=1), nullable=False),
        sa.Column('term_sheet_name', sa.String(length=100), nullable=False),
        sa.Column('reasoning', sa.Text(), nullable=True),
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
        sa.ForeignKeyConstraint(['quarter_id'], ['quarters.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('company_id', name='uq_endgame_decision_company'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('endgame_decisions')

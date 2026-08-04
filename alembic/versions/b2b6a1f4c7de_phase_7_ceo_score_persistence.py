"""phase 7 -- CEO score persistence

Revision ID: b2b6a1f4c7de
Revises: 955a8f228746
Create Date: 2026-08-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2b6a1f4c7de'
down_revision: Union[str, Sequence[str], None] = '955a8f228746'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('quarter_performances', sa.Column('ceo_score', sa.Numeric(precision=6, scale=2), nullable=True))
    op.add_column('quarter_performances', sa.Column('score_band', sa.String(length=20), nullable=True))
    op.add_column('quarter_performances', sa.Column('trait_points', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('quarter_performances', sa.Column('modifiers_applied', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('quarter_performances', sa.Column('unscored_criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('quarter_performances', 'unscored_criteria')
    op.drop_column('quarter_performances', 'modifiers_applied')
    op.drop_column('quarter_performances', 'trait_points')
    op.drop_column('quarter_performances', 'score_band')
    op.drop_column('quarter_performances', 'ceo_score')

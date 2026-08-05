"""phase 10 -- crisis allocation columns

Additive only: 6 new nullable/zero-defaulted columns on `quarter_allocations` for the crisis
response lines (`docs/11-crisis-system.md`) -- `crisis_choice` plus 5 spend amounts. Meaningless
outside the quarter a crisis actually fires; every existing row gets the same defaults the ORM
model already declares (`crisis_choice` null, spend columns 0), so no backfill is needed.

Revision ID: 1d6e3caeaf78
Revises: bc314ea96d16
Create Date: 2026-08-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '1d6e3caeaf78'
down_revision: Union[str, Sequence[str], None] = 'bc314ea96d16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LAKHS = sa.Numeric(10, 4)


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('quarter_allocations', sa.Column('crisis_choice', sa.String(length=1), nullable=True))
    op.add_column('quarter_allocations', sa.Column('price_match_fund', _LAKHS, nullable=False, server_default='0'))
    op.add_column('quarter_allocations', sa.Column('comparison_ads', _LAKHS, nullable=False, server_default='0'))
    op.add_column('quarter_allocations', sa.Column('retention_offers', _LAKHS, nullable=False, server_default='0'))
    op.add_column('quarter_allocations', sa.Column('emergency_supply_fund', _LAKHS, nullable=False, server_default='0'))
    op.add_column('quarter_allocations', sa.Column('crisis_choice_d_spend', _LAKHS, nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('quarter_allocations', 'crisis_choice_d_spend')
    op.drop_column('quarter_allocations', 'emergency_supply_fund')
    op.drop_column('quarter_allocations', 'retention_offers')
    op.drop_column('quarter_allocations', 'comparison_ads')
    op.drop_column('quarter_allocations', 'price_match_fund')
    op.drop_column('quarter_allocations', 'crisis_choice')

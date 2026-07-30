"""phase 5 -- company scenario link

Revision ID: e4ea0702d359
Revises: e99f2f6300f9
Create Date: 2026-07-30 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e4ea0702d359'
down_revision: Union[str, Sequence[str], None] = 'e99f2f6300f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default backfills existing rows, then is dropped: new rows get their scenario from
    # company_service.create_company, which either takes the caller's scenario_id or assigns one
    # deterministically -- a lingering column default would quietly bypass that.
    op.add_column(
        'companies',
        sa.Column('scenario_id', sa.String(length=100), nullable=False, server_default='nadi_wear_standard'),
    )
    op.alter_column('companies', 'scenario_id', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('companies', 'scenario_id')

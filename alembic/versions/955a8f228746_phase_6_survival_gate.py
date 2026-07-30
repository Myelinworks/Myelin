"""phase 6 -- survival gate and run termination

Revision ID: 955a8f228746
Revises: e4ea0702d359
Create Date: 2026-07-30 17:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '955a8f228746'
down_revision: Union[str, Sequence[str], None] = 'e4ea0702d359'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RUN_STATUS = sa.Enum('ACTIVE', 'DISTRESSED', 'FAILED', 'COMPLETED', name='run_status')


def upgrade() -> None:
    """Upgrade schema."""
    RUN_STATUS.create(op.get_bind(), checkfirst=True)

    # Existing companies backfill to ACTIVE, then the server_default is dropped: run status is
    # recomputed from the full quarter history on every lock, so a column default would be a
    # second, silently-diverging source for it.
    op.add_column(
        'companies',
        sa.Column('run_status', RUN_STATUS, nullable=False, server_default='ACTIVE'),
    )
    op.alter_column('companies', 'run_status', server_default=None)

    op.add_column('companies', sa.Column('survival_condition', sa.String(length=100), nullable=True))
    op.add_column('companies', sa.Column('survival_detail', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('companies', 'survival_detail')
    op.drop_column('companies', 'survival_condition')
    op.drop_column('companies', 'run_status')
    RUN_STATUS.drop(op.get_bind(), checkfirst=True)

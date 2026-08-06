"""phase 13 -- companies.owner_id

Gives every Company an owner: the authorization key everything downstream (routes/deps.py,
services/authorization_service.py) checks before deferring to the gatekeeper. Nullable at the
schema level since there is no real user data to backfill (pre-launch) -- see the column's
docstring in app/models/company.py for why that is not a permanent bypass.

Revision ID: f9663562516e
Revises: 034c39b2cc60
Create Date: 2026-08-06 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f9663562516e'
down_revision: Union[str, Sequence[str], None] = '034c39b2cc60'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('companies', sa.Column('owner_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_companies_owner_id'), 'companies', ['owner_id'], unique=False)
    op.create_foreign_key(
        'fk_companies_owner_id_app_users', 'companies', 'app_users', ['owner_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_companies_owner_id_app_users', 'companies', type_='foreignkey')
    op.drop_index(op.f('ix_companies_owner_id'), table_name='companies')
    op.drop_column('companies', 'owner_id')

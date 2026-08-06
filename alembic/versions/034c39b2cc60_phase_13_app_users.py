"""phase 13 -- app_users table

The local mirror of a Supabase Auth identity: one row per `sub` claim, provisioned
get-or-create on first authenticated request. `role` defaults to "student"; instructor/admin
elevation is a manual DB/seed operation, not a self-service route (see
`app/services/auth_service.py`, `app/services/authorization_service.py`).

Revision ID: 034c39b2cc60
Revises: a3f6d1c9e4b7
Create Date: 2026-08-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '034c39b2cc60'
down_revision: Union[str, Sequence[str], None] = 'a3f6d1c9e4b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'app_users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='student'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('app_users')

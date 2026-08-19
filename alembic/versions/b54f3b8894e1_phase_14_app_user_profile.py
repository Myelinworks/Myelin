"""phase 14 -- app_user profile fields

The onboarding-screen answers (`components/auth/OnboardingProfile.tsx` on the frontend) --
first name, institution, degree, current year, up to three goals. All optional, filled in
by `PATCH /profile` rather than at signup, and stored flat on `app_users` rather than as a
JSON blob to match that table's existing plain-column style. See `app/models/app_user.py`.

Revision ID: b54f3b8894e1
Revises: d3f81a5c9e42
Create Date: 2026-08-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b54f3b8894e1'
down_revision: Union[str, Sequence[str], None] = 'd3f81a5c9e42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('app_users', sa.Column('first_name', sa.String(length=120), nullable=True))
    op.add_column('app_users', sa.Column('institution_id', sa.String(length=120), nullable=True))
    op.add_column('app_users', sa.Column('institution_name', sa.String(length=255), nullable=True))
    op.add_column(
        'app_users',
        sa.Column('institution_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column('app_users', sa.Column('degree', sa.String(length=80), nullable=True))
    op.add_column('app_users', sa.Column('current_year', sa.String(length=40), nullable=True))
    op.add_column(
        'app_users',
        sa.Column('goals', sa.ARRAY(sa.String()), nullable=False, server_default='{}'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('app_users', 'goals')
    op.drop_column('app_users', 'current_year')
    op.drop_column('app_users', 'degree')
    op.drop_column('app_users', 'institution_verified')
    op.drop_column('app_users', 'institution_name')
    op.drop_column('app_users', 'institution_id')
    op.drop_column('app_users', 'first_name')

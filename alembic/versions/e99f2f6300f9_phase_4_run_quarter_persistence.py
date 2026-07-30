"""phase 4 -- run_quarter persistence

Revision ID: e99f2f6300f9
Revises: 357474ec114c
Create Date: 2026-07-30 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e99f2f6300f9'
down_revision: Union[str, Sequence[str], None] = '357474ec114c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('companies', sa.Column('seed_name', sa.String(length=100), nullable=False, server_default='nadi_wear'))
    op.add_column('companies', sa.Column('profile_name', sa.String(length=100), nullable=False, server_default='default'))
    op.alter_column('companies', 'seed_name', server_default=None)
    op.alter_column('companies', 'profile_name', server_default=None)

    op.create_table('quarter_allocations',
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('quarter_id', sa.UUID(), nullable=False),
    sa.Column('google_ads', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('meta_ads', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('social_influencer', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('content_seo', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('events_pr', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('email_marketing', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('referral', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('prelaunch_buzz', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('reps', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('crm_tools', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('onboarding', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('quality_qa', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('innovation', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('warranty_years', sa.Integer(), nullable=False),
    sa.Column('manufacturing', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('supplier_qc', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('logistics', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('culture_benefits', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('training_development', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('cx_team', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('compliance_legal', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('financial_planning', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('audit_prep', sa.Numeric(precision=10, scale=4), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.ForeignKeyConstraint(['quarter_id'], ['quarters.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('quarter_id', name='uq_quarter_allocation_quarter')
    )

    op.create_table('company_state_snapshots',
    sa.Column('company_id', sa.UUID(), nullable=False),
    sa.Column('quarter_id', sa.UUID(), nullable=False),
    sa.Column('state', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ),
    sa.ForeignKeyConstraint(['quarter_id'], ['quarters.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('quarter_id', name='uq_company_state_snapshot_quarter')
    )

    op.add_column('quarter_performances', sa.Column('result_hash', sa.String(length=64), nullable=True))
    op.add_column('quarter_performances', sa.Column('engine_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.alter_column('quarter_performances', 'overall_score', existing_type=sa.Float(), nullable=True)
    op.alter_column('quarter_performances', 'dimension_scores', existing_type=postgresql.JSONB(astext_type=sa.Text()), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('quarter_performances', 'dimension_scores', existing_type=postgresql.JSONB(astext_type=sa.Text()), nullable=False)
    op.alter_column('quarter_performances', 'overall_score', existing_type=sa.Float(), nullable=False)
    op.drop_column('quarter_performances', 'engine_result')
    op.drop_column('quarter_performances', 'result_hash')

    op.drop_table('company_state_snapshots')
    op.drop_table('quarter_allocations')

    op.drop_column('companies', 'profile_name')
    op.drop_column('companies', 'seed_name')

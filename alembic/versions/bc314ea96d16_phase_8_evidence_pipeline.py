"""phase 8 -- evidence pipeline on the 22 lines

Additive only: `decision_id`/`workspace` become nullable so the new 22-line producer
(`app/engines/evidence.py`) can write rows with no `Decision` behind them, alongside four new
nullable columns it owns (`department`, `weight`, `weight_status`, `detail`). The legacy
per-decision pipeline (`app/services/evidence_engine.py`) is untouched -- its rows keep populating
`decision_id`/`workspace` exactly as before.

A partial unique index scopes idempotent re-lock upserts to the new producer's rows only
(`decision_id IS NULL`); legacy rows, which can legitimately repeat an `evidence_key` across
several Decisions in one quarter, stay unconstrained.

Revision ID: bc314ea96d16
Revises: b2b6a1f4c7de
Create Date: 2026-08-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'bc314ea96d16'
down_revision: Union[str, Sequence[str], None] = 'b2b6a1f4c7de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('evidence_records', 'decision_id', existing_type=sa.UUID(), nullable=True)
    op.alter_column(
        'evidence_records',
        'workspace',
        existing_type=sa.Enum('FINANCE', 'MARKETING', 'PRODUCT', 'SALES', 'OPERATIONS', 'CX', name='workspace'),
        nullable=True,
    )
    op.add_column('evidence_records', sa.Column('department', sa.String(length=20), nullable=True))
    op.add_column('evidence_records', sa.Column('weight', sa.Numeric(precision=6, scale=2), nullable=True))
    op.add_column('evidence_records', sa.Column('weight_status', sa.String(length=20), nullable=True))
    op.add_column('evidence_records', sa.Column('detail', sa.Text(), nullable=True))
    op.create_index(
        'uq_evidence_records_quarter_key_new_pipeline',
        'evidence_records',
        ['quarter_id', 'evidence_key'],
        unique=True,
        postgresql_where=sa.text('decision_id IS NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_evidence_records_quarter_key_new_pipeline', table_name='evidence_records')
    op.drop_column('evidence_records', 'detail')
    op.drop_column('evidence_records', 'weight_status')
    op.drop_column('evidence_records', 'weight')
    op.drop_column('evidence_records', 'department')
    op.alter_column(
        'evidence_records',
        'workspace',
        existing_type=sa.Enum('FINANCE', 'MARKETING', 'PRODUCT', 'SALES', 'OPERATIONS', 'CX', name='workspace'),
        nullable=False,
    )
    op.alter_column('evidence_records', 'decision_id', existing_type=sa.UUID(), nullable=False)

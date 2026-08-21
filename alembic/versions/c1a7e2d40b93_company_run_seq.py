"""companies.seq -- the per-owner run number a `/run/<n>` URL is built from

Backfills every existing row in creation order per owner, so a run that already exists gets the
number a student would expect ("my first run" == 1) rather than a fresh arbitrary one. The
uuid primary key is untouched and remains the only key the API and every foreign key use --
this column is a label, not an identifier.

Revision ID: c1a7e2d40b93
Revises: b54f3b8894e1
Create Date: 2026-08-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c1a7e2d40b93'
down_revision: Union[str, Sequence[str], None] = 'b54f3b8894e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('companies', sa.Column('seq', sa.Integer(), nullable=True))

    # Same ordering `GET /companies` sorts by (created_at, then id to break the tie two runs
    # started inside one transaction would otherwise leave undefined), read forwards so the
    # oldest run becomes 1.
    op.execute(
        """
        UPDATE companies AS c
        SET seq = numbered.rn
        FROM (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY owner_id ORDER BY created_at, id
                   ) AS rn
            FROM companies
        ) AS numbered
        WHERE c.id = numbered.id
        """
    )

    op.alter_column('companies', 'seq', nullable=False)
    op.create_unique_constraint('uq_companies_owner_id_seq', 'companies', ['owner_id', 'seq'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_companies_owner_id_seq', 'companies', type_='unique')
    op.drop_column('companies', 'seq')

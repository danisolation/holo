"""add sector_analyses table

Revision ID: 6ae2a74c3387
Revises: 6ae2a74c3386
Create Date: 2026-05-14 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = '6ae2a74c3387'
down_revision: Union[str, Sequence[str], None] = '6ae2a74c3386'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sector_analyses table for AI sector intelligence."""
    op.create_table(
        'sector_analyses',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('analysis_date', sa.Date(), nullable=False),
        sa.Column('analysis_json', JSONB(), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('analysis_date'),
    )
    op.create_index('ix_sector_analyses_date', 'sector_analyses', ['analysis_date'])


def downgrade() -> None:
    """Drop sector_analyses table."""
    op.drop_index('ix_sector_analyses_date', table_name='sector_analyses')
    op.drop_table('sector_analyses')

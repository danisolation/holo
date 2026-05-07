"""add unified analysis columns to ai_analyses

Revision ID: 6ae2a74c3386
Revises: 6ae2a74c3385
Create Date: 2026-05-07 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6ae2a74c3386'
down_revision: Union[str, Sequence[str], None] = '6ae2a74c3385'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add entry_price, stop_loss, take_profit_1, take_profit_2, key_levels columns."""
    op.add_column('ai_analyses', sa.Column('entry_price', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('ai_analyses', sa.Column('stop_loss', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('ai_analyses', sa.Column('take_profit_1', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('ai_analyses', sa.Column('take_profit_2', sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column('ai_analyses', sa.Column('key_levels', sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove unified analysis columns."""
    op.drop_column('ai_analyses', 'key_levels')
    op.drop_column('ai_analyses', 'take_profit_2')
    op.drop_column('ai_analyses', 'take_profit_1')
    op.drop_column('ai_analyses', 'stop_loss')
    op.drop_column('ai_analyses', 'entry_price')

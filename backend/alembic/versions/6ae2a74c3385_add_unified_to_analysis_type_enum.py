"""add unified to analysis_type enum

Revision ID: 6ae2a74c3385
Revises: 031
Create Date: 2026-05-07 16:55:32.925267

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6ae2a74c3385'
down_revision: Union[str, Sequence[str], None] = '031'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'unified' value to analysis_type PostgreSQL ENUM."""
    op.execute("ALTER TYPE analysis_type ADD VALUE IF NOT EXISTS 'unified'")


def downgrade() -> None:
    """PostgreSQL does not support removing enum values. No-op."""
    pass

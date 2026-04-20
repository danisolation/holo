"""Add pivot point S/R and Fibonacci retracement columns to technical_indicators.

Revision ID: 011
Revises: 010
Create Date: 2026-04-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Phase 18: Classic Pivot Points
    op.add_column("technical_indicators", sa.Column("pivot_point", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("support_1", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("support_2", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("resistance_1", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("resistance_2", sa.Numeric(12, 4), nullable=True))
    # Phase 18: Fibonacci Retracement Levels
    op.add_column("technical_indicators", sa.Column("fib_236", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("fib_382", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("fib_500", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("fib_618", sa.Numeric(12, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("technical_indicators", "fib_618")
    op.drop_column("technical_indicators", "fib_500")
    op.drop_column("technical_indicators", "fib_382")
    op.drop_column("technical_indicators", "fib_236")
    op.drop_column("technical_indicators", "resistance_2")
    op.drop_column("technical_indicators", "resistance_1")
    op.drop_column("technical_indicators", "support_2")
    op.drop_column("technical_indicators", "support_1")
    op.drop_column("technical_indicators", "pivot_point")

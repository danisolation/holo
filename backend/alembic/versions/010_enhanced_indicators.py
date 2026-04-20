"""Add ATR, ADX, +DI, -DI, Stochastic columns to technical_indicators.

Revision ID: 010
Revises: 009
Create Date: 2026-04-20
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("technical_indicators", sa.Column("atr_14", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("adx_14", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("plus_di_14", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("minus_di_14", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("stoch_k_14", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("stoch_d_14", sa.Numeric(12, 4), nullable=True))


def downgrade() -> None:
    op.drop_column("technical_indicators", "stoch_d_14")
    op.drop_column("technical_indicators", "stoch_k_14")
    op.drop_column("technical_indicators", "minus_di_14")
    op.drop_column("technical_indicators", "plus_di_14")
    op.drop_column("technical_indicators", "adx_14")
    op.drop_column("technical_indicators", "atr_14")

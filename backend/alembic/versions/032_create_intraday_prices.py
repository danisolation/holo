"""Create intraday_prices table for poll snapshots.

Revision ID: 032
Revises: 031
Create Date: 2025-07-27
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "032"
down_revision: Union[str, None] = "6ae2a74c3386"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "intraday_prices",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("ticker_id", sa.Integer(), sa.ForeignKey("tickers.id"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("volume", sa.BigInteger(), nullable=False),
        sa.Column("day_high", sa.Numeric(12, 2), nullable=False),
        sa.Column("day_low", sa.Numeric(12, 2), nullable=False),
        sa.Column("change", sa.Numeric(12, 2), nullable=True, server_default="0"),
        sa.Column("change_pct", sa.Numeric(8, 4), nullable=True, server_default="0"),
        sa.Column(
            "recorded_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_intraday_symbol_recorded",
        "intraday_prices",
        ["symbol", "recorded_at"],
    )
    op.create_index(
        "ix_intraday_ticker_recorded",
        "intraday_prices",
        ["ticker_id", "recorded_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_intraday_ticker_recorded", table_name="intraday_prices")
    op.drop_index("ix_intraday_symbol_recorded", table_name="intraday_prices")
    op.drop_table("intraday_prices")

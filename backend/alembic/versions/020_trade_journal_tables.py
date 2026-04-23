"""Create trades, lots, and lot_matches tables for trade journal.

Trade journal foundation — stores real buy/sell trades with FIFO lot
matching for P&L calculation. Supports VN market fees (broker + sell tax).

Revision ID: 020
Revises: 019
Create Date: 2026-04-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "trades",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("ticker_id", sa.Integer, sa.ForeignKey("tickers.id"), nullable=False),
        sa.Column("daily_pick_id", sa.BigInteger, sa.ForeignKey("daily_picks.id"), nullable=True),
        sa.Column("side", sa.String(4), nullable=False),  # "BUY" or "SELL"
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("broker_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("sell_tax", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("gross_pnl", sa.Numeric(14, 2), nullable=True),  # NULL for BUY
        sa.Column("net_pnl", sa.Numeric(14, 2), nullable=True),    # NULL for BUY
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("user_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trades_ticker_date", "trades", ["ticker_id", "trade_date"])
    op.create_index("ix_trades_trade_date", "trades", ["trade_date"])

    op.create_table(
        "lots",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("trade_id", sa.BigInteger, sa.ForeignKey("trades.id"), nullable=False),
        sa.Column("ticker_id", sa.Integer, sa.ForeignKey("tickers.id"), nullable=False),
        sa.Column("buy_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("remaining_quantity", sa.Integer, nullable=False),
        sa.Column("buy_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    # Partial index for fast FIFO lookup — only lots with remaining shares
    op.create_index(
        "ix_lots_fifo_lookup",
        "lots",
        ["ticker_id", "buy_date", "id"],
        postgresql_where=sa.text("remaining_quantity > 0"),
    )

    # Junction table for SELL → lot matches (enables delete reversal)
    op.create_table(
        "lot_matches",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("sell_trade_id", sa.BigInteger, sa.ForeignKey("trades.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lot_id", sa.BigInteger, sa.ForeignKey("lots.id"), nullable=False),
        sa.Column("matched_quantity", sa.Integer, nullable=False),
    )
    op.create_index("ix_lot_matches_sell_trade", "lot_matches", ["sell_trade_id"])


def downgrade() -> None:
    op.drop_table("lot_matches")
    op.drop_table("lots")
    op.drop_table("trades")

"""Add trades and lots tables for portfolio tracking.

Revision ID: 007
Revises: 006
Create Date: 2026-04-18
"""
from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE trades (
            id BIGSERIAL PRIMARY KEY,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            side VARCHAR(4) NOT NULL CHECK (side IN ('BUY', 'SELL')),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            price NUMERIC(12,2) NOT NULL CHECK (price > 0),
            fees NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (fees >= 0),
            trade_date DATE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_trades_ticker_id ON trades (ticker_id)")
    op.execute("CREATE INDEX idx_trades_trade_date ON trades (trade_date DESC)")

    op.execute("""
        CREATE TABLE lots (
            id BIGSERIAL PRIMARY KEY,
            trade_id BIGINT NOT NULL REFERENCES trades(id),
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            buy_price NUMERIC(12,2) NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            remaining_quantity INTEGER NOT NULL CHECK (remaining_quantity >= 0),
            buy_date DATE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_lots_ticker_id ON lots (ticker_id)")
    op.execute(
        "CREATE INDEX idx_lots_remaining ON lots (ticker_id, remaining_quantity) "
        "WHERE remaining_quantity > 0"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS lots")
    op.execute("DROP TABLE IF EXISTS trades")

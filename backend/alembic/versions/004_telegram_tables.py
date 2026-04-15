"""telegram_tables

Revision ID: 004
Revises: 003
Create Date: 2025-07-18
"""
from typing import Sequence, Union
from alembic import op

revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user_watchlist table
    op.execute("""
        CREATE TABLE user_watchlist (
            id BIGSERIAL PRIMARY KEY,
            chat_id VARCHAR(50) NOT NULL,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_user_watchlist_chat_ticker UNIQUE (chat_id, ticker_id)
        );
        CREATE INDEX idx_user_watchlist_chat_id ON user_watchlist (chat_id);
    """)

    # Create price_alerts table
    op.execute("""
        CREATE TABLE price_alerts (
            id BIGSERIAL PRIMARY KEY,
            chat_id VARCHAR(50) NOT NULL,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            target_price NUMERIC(12, 2) NOT NULL,
            direction VARCHAR(10) NOT NULL,
            is_triggered BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            triggered_at TIMESTAMPTZ,
            CONSTRAINT chk_price_alerts_direction CHECK (direction IN ('up', 'down'))
        );
        CREATE INDEX idx_price_alerts_active ON price_alerts (chat_id, is_triggered)
            WHERE is_triggered = FALSE;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS price_alerts CASCADE;")
    op.execute("DROP TABLE IF EXISTS user_watchlist CASCADE;")

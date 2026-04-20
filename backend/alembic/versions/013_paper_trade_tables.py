"""Add paper_trades and simulation_config tables.

Revision ID: 013
Revises: 012
Create Date: 2025-07-18
"""
from typing import Sequence, Union

from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TYPE trade_status AS ENUM (
            'pending', 'active', 'partial_tp',
            'closed_tp2', 'closed_sl', 'closed_timeout', 'closed_manual'
        )
    """)
    op.execute("""
        CREATE TYPE trade_direction AS ENUM ('long', 'bearish')
    """)

    op.execute("""
        CREATE TABLE paper_trades (
            id BIGSERIAL PRIMARY KEY,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            ai_analysis_id BIGINT REFERENCES ai_analyses(id),
            direction trade_direction NOT NULL,
            status trade_status NOT NULL DEFAULT 'pending',
            entry_price NUMERIC(12,2) NOT NULL,
            stop_loss NUMERIC(12,2) NOT NULL,
            take_profit_1 NUMERIC(12,2) NOT NULL,
            take_profit_2 NUMERIC(12,2) NOT NULL,
            adjusted_stop_loss NUMERIC(12,2),
            quantity INTEGER NOT NULL CHECK (quantity > 0),
            closed_quantity INTEGER NOT NULL DEFAULT 0 CHECK (closed_quantity >= 0),
            realized_pnl NUMERIC(14,2),
            realized_pnl_pct DOUBLE PRECISION,
            exit_price NUMERIC(12,2),
            partial_exit_price NUMERIC(12,2),
            signal_date DATE NOT NULL,
            entry_date DATE,
            closed_date DATE,
            confidence INTEGER NOT NULL CHECK (confidence BETWEEN 1 AND 10),
            timeframe VARCHAR(20) NOT NULL CHECK (timeframe IN ('swing', 'position')),
            position_size_pct INTEGER NOT NULL CHECK (position_size_pct BETWEEN 1 AND 100),
            risk_reward_ratio DOUBLE PRECISION NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("CREATE INDEX idx_paper_trades_status ON paper_trades (status)")
    op.execute("CREATE INDEX idx_paper_trades_ticker ON paper_trades (ticker_id)")
    op.execute("CREATE INDEX idx_paper_trades_signal_date ON paper_trades (signal_date DESC)")

    op.execute("""
        CREATE TABLE simulation_config (
            id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            initial_capital NUMERIC(16,2) NOT NULL DEFAULT 100000000,
            auto_track_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            min_confidence_threshold INTEGER NOT NULL DEFAULT 5
                CHECK (min_confidence_threshold BETWEEN 1 AND 10),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    op.execute("""
        INSERT INTO simulation_config (id) VALUES (1)
        ON CONFLICT (id) DO NOTHING
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS simulation_config")
    op.execute("DROP TABLE IF EXISTS paper_trades")
    op.execute("DROP TYPE IF EXISTS trade_status")
    op.execute("DROP TYPE IF EXISTS trade_direction")

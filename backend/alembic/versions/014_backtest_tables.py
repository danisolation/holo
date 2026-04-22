"""Add backtest tables (backtest_runs, backtest_analyses, backtest_trades, backtest_equity).

Revision ID: 014
Revises: 013
Create Date: 2025-07-21
"""
from typing import Sequence, Union

from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Type ---
    op.execute("""
        CREATE TYPE backtest_status AS ENUM (
            'running', 'completed', 'cancelled', 'failed'
        )
    """)

    # --- backtest_runs ---
    op.execute("""
        CREATE TABLE backtest_runs (
            id BIGSERIAL PRIMARY KEY,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            initial_capital NUMERIC(16,2) NOT NULL DEFAULT 100000000,
            slippage_pct NUMERIC(5,4) NOT NULL DEFAULT 0.5,
            status backtest_status NOT NULL DEFAULT 'running',
            last_completed_date DATE,
            total_sessions INTEGER NOT NULL DEFAULT 0,
            completed_sessions INTEGER NOT NULL DEFAULT 0,
            is_cancelled BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW(),
            CHECK (end_date > start_date),
            CHECK (initial_capital > 0),
            CHECK (slippage_pct >= 0 AND slippage_pct <= 5)
        )
    """)

    # --- backtest_analyses ---
    op.execute("""
        CREATE TABLE backtest_analyses (
            id BIGSERIAL PRIMARY KEY,
            run_id BIGINT NOT NULL REFERENCES backtest_runs(id),
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            analysis_type VARCHAR(20) NOT NULL,
            analysis_date DATE NOT NULL,
            signal VARCHAR(20) NOT NULL,
            score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 10),
            reasoning TEXT NOT NULL,
            model_version VARCHAR(50) NOT NULL,
            raw_response JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_backtest_analyses_run_ticker_type_date
                UNIQUE (run_id, ticker_id, analysis_type, analysis_date)
        )
    """)

    # --- backtest_trades (reuses existing trade_status and trade_direction enums) ---
    op.execute("""
        CREATE TABLE backtest_trades (
            id BIGSERIAL PRIMARY KEY,
            run_id BIGINT NOT NULL REFERENCES backtest_runs(id),
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            backtest_analysis_id BIGINT REFERENCES backtest_analyses(id),
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
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)

    # --- backtest_equity ---
    op.execute("""
        CREATE TABLE backtest_equity (
            id BIGSERIAL PRIMARY KEY,
            run_id BIGINT NOT NULL REFERENCES backtest_runs(id),
            date DATE NOT NULL,
            cash NUMERIC(16,2) NOT NULL,
            positions_value NUMERIC(16,2) NOT NULL,
            total_equity NUMERIC(16,2) NOT NULL,
            daily_return_pct DOUBLE PRECISION,
            cumulative_return_pct DOUBLE PRECISION,
            CONSTRAINT uq_backtest_equity_run_date UNIQUE (run_id, date)
        )
    """)

    # --- Indexes ---
    op.execute("CREATE INDEX idx_backtest_trades_run_id ON backtest_trades (run_id)")
    op.execute("CREATE INDEX idx_backtest_trades_status ON backtest_trades (status)")
    op.execute("CREATE INDEX idx_backtest_trades_run_signal ON backtest_trades (run_id, signal_date)")
    op.execute("CREATE INDEX idx_backtest_analyses_run_date ON backtest_analyses (run_id, analysis_date)")
    op.execute("CREATE INDEX idx_backtest_equity_run_date ON backtest_equity (run_id, date)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS backtest_equity")
    op.execute("DROP TABLE IF EXISTS backtest_trades")
    op.execute("DROP TABLE IF EXISTS backtest_analyses")
    op.execute("DROP TABLE IF EXISTS backtest_runs")
    op.execute("DROP TYPE IF EXISTS backtest_status")

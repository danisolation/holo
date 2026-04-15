"""initial_schema

Revision ID: 001
Revises:
Create Date: 2025-07-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Tickers table (standard, not partitioned) ---
    op.execute("""
        CREATE TABLE tickers (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) UNIQUE NOT NULL,
            name VARCHAR(200) NOT NULL,
            sector VARCHAR(100),
            industry VARCHAR(100),
            exchange VARCHAR(10) NOT NULL DEFAULT 'HOSE',
            market_cap NUMERIC(18,2),
            is_active BOOLEAN NOT NULL DEFAULT true,
            last_updated TIMESTAMPTZ DEFAULT NOW(),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        CREATE INDEX ix_tickers_symbol ON tickers (symbol);
    """)

    # --- Daily prices table (partitioned by year) ---
    # 400 tickers × 250 trading days = ~100K rows/year
    op.execute("""
        CREATE TABLE daily_prices (
            id BIGSERIAL,
            ticker_id INTEGER NOT NULL,
            date DATE NOT NULL,
            open NUMERIC(12,2) NOT NULL,
            high NUMERIC(12,2) NOT NULL,
            low NUMERIC(12,2) NOT NULL,
            close NUMERIC(12,2) NOT NULL,
            volume BIGINT NOT NULL,
            adjusted_close NUMERIC(12,2),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (date, id),
            CONSTRAINT uq_daily_prices_ticker_date UNIQUE (ticker_id, date),
            CONSTRAINT fk_daily_prices_ticker FOREIGN KEY (ticker_id) REFERENCES tickers(id)
        ) PARTITION BY RANGE (date);
    """)

    # Create yearly partitions: 2023 (backfill start) through 2026 (next year)
    for year in [2023, 2024, 2025, 2026]:
        op.execute(f"""
            CREATE TABLE daily_prices_{year} PARTITION OF daily_prices
                FOR VALUES FROM ('{year}-01-01') TO ('{year + 1}-01-01');
        """)

    op.execute("""
        CREATE INDEX idx_daily_prices_ticker_date ON daily_prices (ticker_id, date DESC);
    """)

    # --- Financials table (standard, not partitioned) ---
    op.execute("""
        CREATE TABLE financials (
            id SERIAL PRIMARY KEY,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            period VARCHAR(10) NOT NULL,
            year INTEGER NOT NULL,
            quarter INTEGER,
            pe NUMERIC(10,2),
            pb NUMERIC(10,2),
            eps NUMERIC(14,2),
            roe NUMERIC(8,4),
            roa NUMERIC(8,4),
            revenue NUMERIC(18,2),
            net_profit NUMERIC(18,2),
            revenue_growth NUMERIC(8,4),
            profit_growth NUMERIC(8,4),
            current_ratio NUMERIC(8,4),
            debt_to_equity NUMERIC(8,4),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_financials_ticker_period UNIQUE (ticker_id, period)
        );
        CREATE INDEX idx_financials_ticker ON financials (ticker_id);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS financials CASCADE;")
    op.execute("DROP TABLE IF EXISTS daily_prices CASCADE;")
    op.execute("DROP TABLE IF EXISTS tickers CASCADE;")

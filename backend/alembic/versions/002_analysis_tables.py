"""analysis_tables

Revision ID: 002
Revises: 001
Create Date: 2025-07-17
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM type for analysis categories (supports Phase 3 sentiment)
    op.execute("""
        CREATE TYPE analysis_type AS ENUM ('technical', 'fundamental', 'sentiment');
    """)

    # Technical indicators — one row per ticker per date
    # All indicator columns nullable (NaN warm-up periods → NULL)
    op.execute("""
        CREATE TABLE technical_indicators (
            id BIGSERIAL PRIMARY KEY,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            date DATE NOT NULL,
            rsi_14 NUMERIC(8,4),
            macd_line NUMERIC(12,6),
            macd_signal NUMERIC(12,6),
            macd_histogram NUMERIC(12,6),
            sma_20 NUMERIC(12,4),
            sma_50 NUMERIC(12,4),
            sma_200 NUMERIC(12,4),
            ema_12 NUMERIC(12,4),
            ema_26 NUMERIC(12,4),
            bb_upper NUMERIC(12,4),
            bb_middle NUMERIC(12,4),
            bb_lower NUMERIC(12,4),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_technical_indicators_ticker_date UNIQUE (ticker_id, date)
        );
        CREATE INDEX idx_technical_indicators_ticker_date
            ON technical_indicators (ticker_id, date DESC);
    """)

    # AI analyses — one row per ticker per analysis_type per date
    # Stores Gemini output: signal, score, reasoning, raw JSONB
    op.execute("""
        CREATE TABLE ai_analyses (
            id BIGSERIAL PRIMARY KEY,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            analysis_type analysis_type NOT NULL,
            analysis_date DATE NOT NULL,
            signal VARCHAR(20) NOT NULL,
            score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 10),
            reasoning TEXT NOT NULL,
            model_version VARCHAR(50) NOT NULL,
            raw_response JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_ai_analyses_ticker_type_date
                UNIQUE (ticker_id, analysis_type, analysis_date)
        );
        CREATE INDEX idx_ai_analyses_ticker_type
            ON ai_analyses (ticker_id, analysis_type, analysis_date DESC);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_analyses CASCADE;")
    op.execute("DROP TABLE IF EXISTS technical_indicators CASCADE;")
    op.execute("DROP TYPE IF EXISTS analysis_type;")

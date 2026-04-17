"""Add corporate_events table for tracking dividends, stock dividends, and bonus shares.

Revision ID: 006
Revises: 005
Create Date: 2026-04-18
"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE corporate_events (
            id BIGSERIAL PRIMARY KEY,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            event_source_id VARCHAR(50) NOT NULL,
            event_type VARCHAR(20) NOT NULL,
            ex_date DATE NOT NULL,
            record_date DATE,
            announcement_date DATE,
            dividend_amount NUMERIC(12,2),
            ratio NUMERIC(10,4),
            adjustment_factor NUMERIC(10,8),
            note VARCHAR(500),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_corporate_events_source_id UNIQUE (event_source_id),
            CONSTRAINT uq_corporate_events_ticker_type_date UNIQUE (ticker_id, event_type, ex_date)
        )
    """)
    op.execute(
        "CREATE INDEX idx_corporate_events_ticker_id ON corporate_events (ticker_id)"
    )
    op.execute(
        "CREATE INDEX idx_corporate_events_ex_date ON corporate_events (ex_date DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS corporate_events")

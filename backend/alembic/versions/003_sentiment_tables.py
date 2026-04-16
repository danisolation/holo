"""sentiment_tables

Revision ID: 003
Revises: 002
Create Date: 2025-07-18
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'combined' to existing analysis_type PostgreSQL ENUM
    # IF NOT EXISTS prevents error if re-run; works in PG 12+ transactions
    op.execute("ALTER TYPE analysis_type ADD VALUE IF NOT EXISTS 'combined';")

    # Create news_articles table
    op.execute("""
        CREATE TABLE news_articles (
            id BIGSERIAL PRIMARY KEY,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            title TEXT NOT NULL,
            url VARCHAR(500) NOT NULL,
            published_at TIMESTAMPTZ NOT NULL,
            source VARCHAR(20) NOT NULL DEFAULT 'cafef',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_news_articles_ticker_url UNIQUE (ticker_id, url)
        )
    """)
    op.execute("""
        CREATE INDEX idx_news_articles_ticker_published
            ON news_articles (ticker_id, published_at DESC)
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS news_articles CASCADE;")
    # NOTE: PostgreSQL does not support removing a value from an ENUM type.
    # To remove 'combined', the type would need to be recreated.

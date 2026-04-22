"""Remove price_alerts table and news_articles.source column.

Dead features: price_alert system never had UI/Telegram commands wired,
news_article.source was always "cafef" — no multi-source support.

Revision ID: 015
Revises: 014
Create Date: 2025-07-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("price_alerts")
    op.drop_column("news_articles", "source")


def downgrade() -> None:
    op.create_table(
        "price_alerts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("chat_id", sa.String(50), nullable=False),
        sa.Column("ticker_id", sa.Integer(), sa.ForeignKey("tickers.id"), nullable=False),
        sa.Column("target_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("is_triggered", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("triggered_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "news_articles",
        sa.Column("source", sa.String(20), nullable=False, server_default="cafef"),
    )

"""Migrate user_watchlist from Telegram-era (chat_id + ticker_id) to web single-user (symbol).

Drop old table and recreate with simplified schema for web dashboard watchlist.
Single-user — no chat_id needed, stores ticker symbol directly.

Revision ID: 025
Revises: 024
Create Date: 2026-04-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("user_watchlist")
    op.create_table(
        "user_watchlist",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("symbol", sa.String(10), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("symbol", name="uq_user_watchlist_symbol"),
    )


def downgrade() -> None:
    op.drop_table("user_watchlist")
    op.create_table(
        "user_watchlist",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.String(50), nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"]),
        sa.UniqueConstraint("chat_id", "ticker_id", name="uq_user_watchlist_chat_ticker"),
    )

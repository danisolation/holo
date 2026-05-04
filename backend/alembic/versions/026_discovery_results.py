"""Create discovery_results table and add sector_group to user_watchlist.

Revision ID: 026
Revises: 025
Create Date: 2025-07-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create discovery_results table
    op.create_table(
        "discovery_results",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("score_date", sa.Date(), nullable=False),
        sa.Column("rsi_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("macd_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("adx_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("volume_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("pe_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("roe_score", sa.Numeric(4, 2), nullable=True),
        sa.Column("total_score", sa.Numeric(5, 2), nullable=False),
        sa.Column("dimensions_scored", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"]),
        sa.UniqueConstraint("ticker_id", "score_date", name="uq_discovery_results_ticker_date"),
    )

    # 2. Add sector_group column to user_watchlist (nullable — Phase 54 preparation)
    op.add_column("user_watchlist", sa.Column("sector_group", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("user_watchlist", "sector_group")
    op.drop_table("discovery_results")

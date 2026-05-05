"""Create ai_accuracy table for tracking AI prediction accuracy.

Revision ID: 030
Revises: 029
Create Date: 2025-07-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "030"
down_revision: Union[str, None] = "029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_accuracy",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("analysis_date", sa.Date(), nullable=False),
        sa.Column("direction_predicted", sa.String(10), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("price_at_signal", sa.Float(), nullable=True),
        sa.Column("price_at_1d", sa.Float(), nullable=True),
        sa.Column("price_at_3d", sa.Float(), nullable=True),
        sa.Column("price_at_7d", sa.Float(), nullable=True),
        sa.Column("pct_change_1d", sa.Float(), nullable=True),
        sa.Column("pct_change_3d", sa.Float(), nullable=True),
        sa.Column("pct_change_7d", sa.Float(), nullable=True),
        sa.Column("verdict_1d", sa.String(20), nullable=True),
        sa.Column("verdict_3d", sa.String(20), nullable=True),
        sa.Column("verdict_7d", sa.String(20), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"]),
        sa.UniqueConstraint("ticker_id", "analysis_date", name="uq_ai_accuracy_ticker_date"),
    )
    op.create_index(
        "ix_ai_accuracy_ticker_date",
        "ai_accuracy",
        ["ticker_id", sa.text("analysis_date DESC")],
        unique=False,
    )
    op.create_index(
        "ix_ai_accuracy_verdict",
        "ai_accuracy",
        ["verdict_7d"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ai_accuracy_verdict", table_name="ai_accuracy")
    op.drop_index("ix_ai_accuracy_ticker_date", table_name="ai_accuracy")
    op.drop_table("ai_accuracy")

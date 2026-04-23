"""Create trading_goals, weekly_prompts, weekly_reviews tables.

Three tables for Phase 47 Goals & Weekly Reviews:
- trading_goals: monthly profit target tracking
- weekly_prompts: weekly risk tolerance prompts
- weekly_reviews: AI-generated weekly performance reviews

Revision ID: 023
Revises: 022
Create Date: 2026-04-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── trading_goals ────────────────────────────────────────────────────
    op.create_table(
        "trading_goals",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("target_pnl", sa.Numeric(18, 2), nullable=False),
        sa.Column("month", sa.Date, nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="active"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trading_goals_month", "trading_goals", ["month"])

    # ── weekly_prompts ───────────────────────────────────────────────────
    op.create_table(
        "weekly_prompts",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("week_start", sa.Date, nullable=False),
        sa.Column("prompt_type", sa.String(20), nullable=False, server_default="risk_tolerance"),
        sa.Column("response", sa.String(20), nullable=True),
        sa.Column("risk_level_before", sa.Integer, nullable=True),
        sa.Column("risk_level_after", sa.Integer, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_weekly_prompts_week_start", "weekly_prompts", ["week_start"])

    # ── weekly_reviews ───────────────────────────────────────────────────
    op.create_table(
        "weekly_reviews",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("week_start", sa.Date, nullable=False),
        sa.Column("week_end", sa.Date, nullable=False),
        sa.Column("summary_text", sa.Text, nullable=False),
        sa.Column("highlights", JSONB, nullable=False),
        sa.Column("suggestions", JSONB, nullable=False),
        sa.Column("trades_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("win_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_pnl", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_weekly_reviews_week_start", "weekly_reviews", ["week_start"])


def downgrade() -> None:
    op.drop_table("weekly_reviews")
    op.drop_table("weekly_prompts")
    op.drop_table("trading_goals")

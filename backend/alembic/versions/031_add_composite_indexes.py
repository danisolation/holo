"""Add composite indexes on hot tables for query performance.

Revision ID: 031
Revises: 030
Create Date: 2025-07-26
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "031"
down_revision: Union[str, None] = "030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_technical_indicators_ticker_date",
        "technical_indicators",
        ["ticker_id", sa.text("date DESC")],
        unique=False,
    )
    op.create_index(
        "ix_ai_analyses_ticker_type_date",
        "ai_analyses",
        ["ticker_id", "analysis_type", sa.text("analysis_date DESC")],
        unique=False,
    )
    op.create_index(
        "ix_daily_picks_date_ticker",
        "daily_picks",
        [sa.text("pick_date DESC"), "ticker_id"],
        unique=False,
    )
    op.create_index(
        "ix_weekly_reviews_week_start",
        "weekly_reviews",
        [sa.text("week_start DESC")],
        unique=False,
    )
    op.create_index(
        "ix_job_executions_job_started",
        "job_executions",
        ["job_id", sa.text("started_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_job_executions_job_started", table_name="job_executions")
    op.drop_index("ix_weekly_reviews_week_start", table_name="weekly_reviews")
    op.drop_index("ix_daily_picks_date_ticker", table_name="daily_picks")
    op.drop_index("ix_ai_analyses_ticker_type_date", table_name="ai_analyses")
    op.drop_index("ix_technical_indicators_ticker_date", table_name="technical_indicators")

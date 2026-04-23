"""Create behavior_events, habit_detections, risk_suggestions, sector_preferences tables.

Four tables for Phase 46 behavior tracking and adaptive strategy:
- behavior_events: logs user viewing/interaction events
- habit_detections: stores detected trading habit patterns
- risk_suggestions: risk level adjustment suggestions
- sector_preferences: learned sector performance from trades

Revision ID: 022
Revises: 021
Create Date: 2026-04-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── behavior_events ──────────────────────────────────────────────────
    op.create_table(
        "behavior_events",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("ticker_id", sa.Integer, sa.ForeignKey("tickers.id"), nullable=True),
        sa.Column("event_metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_behavior_events_type_ticker", "behavior_events", ["event_type", "ticker_id"])

    # ── habit_detections ─────────────────────────────────────────────────
    op.create_table(
        "habit_detections",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("habit_type", sa.String(20), nullable=False),
        sa.Column("ticker_id", sa.Integer, sa.ForeignKey("tickers.id"), nullable=False),
        sa.Column("trade_id", sa.BigInteger, sa.ForeignKey("trades.id"), nullable=False),
        sa.Column("evidence", JSONB, nullable=False),
        sa.Column("detected_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_habit_detections_type", "habit_detections", ["habit_type"])

    # ── risk_suggestions ─────────────────────────────────────────────────
    op.create_table(
        "risk_suggestions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("current_level", sa.Integer, nullable=False),
        sa.Column("suggested_level", sa.Integer, nullable=False),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("responded_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_risk_suggestions_status", "risk_suggestions", ["status"])

    # ── sector_preferences ───────────────────────────────────────────────
    op.create_table(
        "sector_preferences",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("sector", sa.String(100), nullable=False, unique=True),
        sa.Column("total_trades", sa.Integer, nullable=False, server_default="0"),
        sa.Column("win_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("loss_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("net_pnl", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("preference_score", sa.Numeric(5, 3), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("sector_preferences")
    op.drop_table("risk_suggestions")
    op.drop_table("habit_detections")
    op.drop_table("behavior_events")

"""Create daily_picks and user_risk_profile tables.

Daily Picks Engine foundation — stores AI-selected daily picks with
entry/SL/TP targets and user risk preferences.

Revision ID: 019
Revises: 018
Create Date: 2026-04-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_picks",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("pick_date", sa.Date, nullable=False),
        sa.Column("ticker_id", sa.Integer, sa.ForeignKey("tickers.id"), nullable=False),
        sa.Column("rank", sa.Integer, nullable=True),
        sa.Column("composite_score", sa.Numeric(6, 2), nullable=False),
        sa.Column("entry_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("stop_loss", sa.Numeric(12, 2), nullable=True),
        sa.Column("take_profit_1", sa.Numeric(12, 2), nullable=True),
        sa.Column("take_profit_2", sa.Numeric(12, 2), nullable=True),
        sa.Column("risk_reward", sa.Numeric(6, 2), nullable=True),
        sa.Column("position_size_shares", sa.Integer, nullable=True),
        sa.Column("position_size_vnd", sa.BigInteger, nullable=True),
        sa.Column("position_size_pct", sa.Numeric(5, 1), nullable=True),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("rejection_reason", sa.String(200), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("pick_date", "ticker_id", name="uq_daily_picks_date_ticker"),
    )

    op.create_table(
        "user_risk_profile",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("capital", sa.Numeric(18, 2), nullable=False, server_default="50000000"),
        sa.Column("risk_level", sa.Integer, nullable=False, server_default="3"),
        sa.Column("broker_fee_pct", sa.Numeric(5, 3), nullable=False, server_default="0.150"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # Insert default risk profile row
    op.execute(
        "INSERT INTO user_risk_profile (capital, risk_level, broker_fee_pct) "
        "VALUES (50000000, 3, 0.150)"
    )


def downgrade() -> None:
    op.drop_table("daily_picks")
    op.drop_table("user_risk_profile")

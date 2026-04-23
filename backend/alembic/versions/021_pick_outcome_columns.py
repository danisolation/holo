"""Add outcome tracking columns to daily_picks table.

Adds pick_outcome, days_held, hit_stop_loss, hit_take_profit_1,
hit_take_profit_2, actual_return_pct columns plus a partial index
on pending picks for efficient scheduler queries.

Revision ID: 021
Revises: 020
Create Date: 2026-04-23
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("daily_picks", sa.Column("pick_outcome", sa.String(10), nullable=False, server_default="pending"))
    op.add_column("daily_picks", sa.Column("days_held", sa.Integer, nullable=True))
    op.add_column("daily_picks", sa.Column("hit_stop_loss", sa.Boolean, nullable=True))
    op.add_column("daily_picks", sa.Column("hit_take_profit_1", sa.Boolean, nullable=True))
    op.add_column("daily_picks", sa.Column("hit_take_profit_2", sa.Boolean, nullable=True))
    op.add_column("daily_picks", sa.Column("actual_return_pct", sa.Numeric(8, 2), nullable=True))
    # Partial index for outcome check: only pending picks need processing
    op.create_index(
        "ix_daily_picks_outcome_pending",
        "daily_picks",
        ["pick_outcome"],
        postgresql_where=sa.text("pick_outcome = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index("ix_daily_picks_outcome_pending", table_name="daily_picks")
    op.drop_column("daily_picks", "actual_return_pct")
    op.drop_column("daily_picks", "hit_take_profit_2")
    op.drop_column("daily_picks", "hit_take_profit_1")
    op.drop_column("daily_picks", "hit_stop_loss")
    op.drop_column("daily_picks", "days_held")
    op.drop_column("daily_picks", "pick_outcome")

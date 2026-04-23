"""Drop backtest tables (backtest_equity, backtest_trades, backtest_analyses, backtest_runs) and backtest_status enum.

Backtest feature removed in v7.0 consolidation. Paper-trading feature is retained.
DO NOT delete migration 014_backtest_tables.py — it is part of the migration chain.

Revision ID: 017
Revises: 016
Create Date: 2025-07-23
"""
from typing import Sequence, Union

from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop tables in FK-dependency order (children first, parent last)
    op.drop_table("backtest_equity")
    op.drop_table("backtest_trades")
    op.drop_table("backtest_analyses")
    op.drop_table("backtest_runs")

    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS backtest_status")


def downgrade() -> None:
    # Downgrade is intentionally not implemented — restoring backtest
    # requires re-running migration 014 logic which is complex.
    raise NotImplementedError(
        "Downgrade not supported. Restore from migration 014 if needed."
    )

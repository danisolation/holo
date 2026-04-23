"""Drop portfolio and paper trading tables.

Portfolio (trades, lots) and Paper Trading (paper_trades, simulation_config)
features removed in v7.0 consolidation.
DO NOT delete migration 007 or 013 — they are part of the migration chain.

Revision ID: 018
Revises: 017
Create Date: 2025-07-23
"""
from typing import Sequence, Union
from alembic import op

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop tables (order: children first due to FK constraints)
    op.drop_table("lots")           # FK → trades
    op.drop_table("trades")         # FK → tickers
    op.drop_table("paper_trades")   # FK → tickers, ai_analyses
    op.drop_table("simulation_config")

    # Drop enums (only used by paper_trades — safe to drop)
    op.execute("DROP TYPE IF EXISTS trade_status")
    op.execute("DROP TYPE IF EXISTS trade_direction")


def downgrade() -> None:
    # Not implementing downgrade — these features are permanently removed
    raise NotImplementedError("Cannot downgrade: portfolio and paper trading features permanently removed")

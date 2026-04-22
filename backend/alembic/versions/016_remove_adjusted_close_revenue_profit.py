"""Remove adjusted_close from daily_prices, revenue and net_profit from financials.

adjusted_close was never populated by vnstock (only by corporate_action_service
which is being deleted). revenue/net_profit stored but never consumed by AI or API.

Revision ID: 016
Revises: 015
Create Date: 2025-07-22
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("daily_prices", "adjusted_close")
    op.drop_column("financials", "revenue")
    op.drop_column("financials", "net_profit")


def downgrade() -> None:
    op.add_column(
        "daily_prices",
        sa.Column("adjusted_close", sa.Numeric(12, 2), nullable=True),
    )
    op.add_column(
        "financials",
        sa.Column("revenue", sa.Numeric(18, 2), nullable=True),
    )
    op.add_column(
        "financials",
        sa.Column("net_profit", sa.Numeric(18, 2), nullable=True),
    )

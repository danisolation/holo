"""Add composite index on daily_prices(ticker_id, date DESC).

Revision ID: 027
Revises: 026
Create Date: 2025-07-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_daily_prices_ticker_date",
        "daily_prices",
        ["ticker_id", sa.text("date DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_daily_prices_ticker_date", table_name="daily_prices")

"""Drop corporate_events table.

Corporate events feature removed in Phase 48. Table and all constraints dropped.

Revision ID: 024
Revises: 023
Create Date: 2026-04-24
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("corporate_events")
    # Deactivate HNX/UPCOM tickers — HOSE-only going forward
    op.execute("UPDATE tickers SET is_active = false WHERE exchange IN ('HNX', 'UPCOM')")


def downgrade() -> None:
    op.execute("UPDATE tickers SET is_active = true WHERE exchange IN ('HNX', 'UPCOM')")
    op.create_table(
        "corporate_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ticker_id", sa.Integer(), nullable=False),
        sa.Column("event_source_id", sa.String(50), nullable=False),
        sa.Column("event_type", sa.String(20), nullable=False),
        sa.Column("ex_date", sa.Date(), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=True),
        sa.Column("announcement_date", sa.Date(), nullable=True),
        sa.Column("dividend_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("ratio", sa.Numeric(10, 4), nullable=True),
        sa.Column("adjustment_factor", sa.Numeric(10, 8), nullable=True),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("alert_sent", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["ticker_id"], ["tickers.id"]),
        sa.UniqueConstraint("event_source_id", name="uq_corporate_events_source_id"),
        sa.UniqueConstraint("ticker_id", "event_type", "ex_date", name="uq_corporate_events_ticker_type_date"),
    )

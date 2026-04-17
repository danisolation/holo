"""Add alert_sent column to corporate_events.

Revision ID: 008
Revises: 007
Create Date: 2026-04-17
"""
from typing import Sequence, Union

from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE corporate_events
        ADD COLUMN alert_sent BOOLEAN NOT NULL DEFAULT FALSE
    """)
    # Partial index for efficient "unsent alerts" queries
    op.execute("""
        CREATE INDEX idx_corporate_events_alert_sent
        ON corporate_events (alert_sent)
        WHERE alert_sent = FALSE
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_corporate_events_alert_sent")
    op.execute("ALTER TABLE corporate_events DROP COLUMN IF EXISTS alert_sent")

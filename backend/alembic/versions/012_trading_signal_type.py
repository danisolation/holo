"""trading_signal_type

Revision ID: 012
Revises: 011
Create Date: 2026-04-20
"""
from typing import Sequence, Union
from alembic import op

revision: str = '012'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add 'trading_signal' to existing analysis_type PostgreSQL ENUM
    op.execute("ALTER TYPE analysis_type ADD VALUE IF NOT EXISTS 'trading_signal';")

    # CRITICAL: Allow score=0 for invalid trading signals (Pitfall 1 from RESEARCH.md)
    # Current constraint: CHECK (score BETWEEN 1 AND 10) defined in migration 002
    # Use generic approach: query pg_constraint for actual constraint name
    op.execute("""
        DO $$
        DECLARE
            constraint_name TEXT;
        BEGIN
            SELECT conname INTO constraint_name
            FROM pg_constraint
            WHERE conrelid = 'ai_analyses'::regclass
              AND contype = 'c'
              AND pg_get_constraintdef(oid) LIKE '%score%';
            IF constraint_name IS NOT NULL THEN
                EXECUTE format('ALTER TABLE ai_analyses DROP CONSTRAINT %I', constraint_name);
            END IF;
        END $$;
    """)
    op.execute("ALTER TABLE ai_analyses ADD CONSTRAINT ai_analyses_score_check CHECK (score BETWEEN 0 AND 10);")


def downgrade() -> None:
    # Cannot remove ENUM value in PostgreSQL — this is a known limitation
    # Restore original score constraint
    op.execute("ALTER TABLE ai_analyses DROP CONSTRAINT IF EXISTS ai_analyses_score_check;")
    op.execute("ALTER TABLE ai_analyses ADD CONSTRAINT ai_analyses_score_check CHECK (score BETWEEN 1 AND 10);")

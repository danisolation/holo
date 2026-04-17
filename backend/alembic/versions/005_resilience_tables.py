"""Add job_executions and failed_jobs tables for resilience tracking.

Revision ID: 005
Revises: 004
Create Date: 2026-04-17
"""
from typing import Sequence, Union
from alembic import op

revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE job_executions (
            id BIGSERIAL PRIMARY KEY,
            job_id VARCHAR(100) NOT NULL,
            started_at TIMESTAMPTZ NOT NULL,
            completed_at TIMESTAMPTZ,
            status VARCHAR(20) NOT NULL,
            result_summary JSONB,
            error_message TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_job_executions_job_id ON job_executions (job_id)")
    op.execute("CREATE INDEX idx_job_executions_started_at ON job_executions (started_at DESC)")

    op.execute("""
        CREATE TABLE failed_jobs (
            id BIGSERIAL PRIMARY KEY,
            job_type VARCHAR(100) NOT NULL,
            ticker_symbol VARCHAR(10),
            error_message TEXT NOT NULL,
            retry_count INTEGER NOT NULL DEFAULT 1,
            failed_at TIMESTAMPTZ NOT NULL,
            resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_failed_jobs_job_type ON failed_jobs (job_type)")
    op.execute("CREATE INDEX idx_failed_jobs_unresolved ON failed_jobs (resolved_at) WHERE resolved_at IS NULL")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS failed_jobs")
    op.execute("DROP TABLE IF EXISTS job_executions")

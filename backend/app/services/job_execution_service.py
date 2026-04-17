"""Service for tracking job executions in the database.

Per D-13: One row per job run with job_id, started_at, completed_at,
status (success/partial/failed), and result_summary (JSONB).
Per D-14: One row per job run — NOT per-ticker.
"""
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_execution import JobExecution


class JobExecutionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def start(self, job_id: str) -> JobExecution:
        """Create a new execution record with status='running'."""
        execution = JobExecution(
            job_id=job_id,
            started_at=datetime.now(timezone.utc),
            status="running",
        )
        self.session.add(execution)
        await self.session.flush()
        logger.debug(f"Job execution started: {job_id} (id={execution.id})")
        return execution

    async def complete(
        self, execution: JobExecution, status: str, result_summary: dict | None = None
    ) -> None:
        """Mark execution as complete with status and optional result summary.
        status must be one of: 'success', 'partial', 'failed'."""
        execution.completed_at = datetime.now(timezone.utc)
        execution.status = status
        execution.result_summary = result_summary
        await self.session.flush()
        logger.debug(f"Job execution completed: {execution.job_id} status={status}")

    async def fail(self, execution: JobExecution, error: str) -> None:
        """Mark execution as failed with error message.
        Truncate error to 500 chars per T-06-01 threat mitigation."""
        execution.completed_at = datetime.now(timezone.utc)
        execution.status = "failed"
        execution.error_message = error[:500] if error else "Unknown error"
        await self.session.flush()
        logger.debug(f"Job execution failed: {execution.job_id} error={error[:100]}")

    async def get_latest(self, job_id: str) -> JobExecution | None:
        """Get the most recent execution for a given job_id."""
        result = await self.session.execute(
            select(JobExecution)
            .where(JobExecution.job_id == job_id)
            .order_by(JobExecution.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

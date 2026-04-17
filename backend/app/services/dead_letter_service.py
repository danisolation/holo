"""Dead-letter queue service for permanently failed items.

Per D-08: Store job_type, ticker_symbol, error_message, retry_count, failed_at, resolved_at.
Per D-09: After auto-retry fails, item goes to DLQ. No further automatic retries.
Per T-06-01: Truncate error_message to 500 chars to prevent API key leakage.
"""
from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.failed_job import FailedJob


class DeadLetterService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(
        self, job_type: str, ticker_symbol: str | None, error_message: str,
        retry_count: int = 1,
    ) -> FailedJob:
        """Add a permanently failed item to the dead-letter queue.
        Truncates error_message to 500 chars per T-06-01."""
        item = FailedJob(
            job_type=job_type,
            ticker_symbol=ticker_symbol,
            error_message=error_message[:500] if error_message else "Unknown error",
            retry_count=retry_count,
            failed_at=datetime.now(timezone.utc),
        )
        self.session.add(item)
        await self.session.flush()
        logger.info(f"DLQ: {job_type} / {ticker_symbol} added (retry_count={retry_count})")
        return item

    async def get_unresolved(self, job_type: str | None = None) -> list[FailedJob]:
        """Get all unresolved DLQ items. Optionally filter by job_type."""
        query = select(FailedJob).where(FailedJob.resolved_at.is_(None))
        if job_type:
            query = query.where(FailedJob.job_type == job_type)
        query = query.order_by(FailedJob.failed_at.desc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def resolve(self, item_id: int) -> bool:
        """Mark a DLQ item as resolved. Returns True if found and updated."""
        result = await self.session.execute(
            select(FailedJob).where(FailedJob.id == item_id)
        )
        item = result.scalar_one_or_none()
        if item is None:
            return False
        item.resolved_at = datetime.now(timezone.utc)
        await self.session.flush()
        logger.info(f"DLQ: item {item_id} resolved ({item.job_type} / {item.ticker_symbol})")
        return True

    async def count_unresolved(self) -> int:
        """Count total unresolved DLQ items."""
        result = await self.session.execute(
            select(func.count(FailedJob.id)).where(FailedJob.resolved_at.is_(None))
        )
        return result.scalar_one()

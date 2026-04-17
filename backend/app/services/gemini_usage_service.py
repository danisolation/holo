"""Gemini API usage tracking service.

Records per-call token usage and provides aggregation for the health
dashboard (D-15-01, D-15-09).
"""
from datetime import date, datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import func, select, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gemini_usage import GeminiUsage


class GeminiUsageService:
    """Track and aggregate Gemini API token usage."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_usage(
        self,
        analysis_type: str,
        batch_size: int,
        usage_metadata,
        model_name: str,
    ) -> None:
        """Insert a usage row after a Gemini API call.

        Args:
            analysis_type: e.g. 'technical', 'fundamental', 'sentiment', 'combined'
            batch_size: number of tickers in the batch
            usage_metadata: Gemini response.usage_metadata (may be None)
            model_name: e.g. 'gemini-2.0-flash'
        """
        prompt_tokens = 0
        completion_tokens = 0
        total_tokens = 0

        if usage_metadata is not None:
            prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0) or 0
            completion_tokens = getattr(usage_metadata, "candidates_token_count", 0) or 0
            total_tokens = getattr(usage_metadata, "total_token_count", 0) or 0

        usage = GeminiUsage(
            analysis_type=analysis_type,
            batch_size=batch_size,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            model_name=model_name,
        )
        self.session.add(usage)
        await self.session.flush()
        logger.debug(
            f"Recorded Gemini usage: {analysis_type} batch={batch_size} "
            f"tokens={total_tokens} ({prompt_tokens}+{completion_tokens})"
        )

    async def get_daily_usage(self, days: int = 7) -> list[dict]:
        """Get daily token usage aggregates.

        Returns list of dicts: [{date, tokens, requests}, ...]
        ordered by date descending.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(
                cast(GeminiUsage.created_at, Date).label("date"),
                func.sum(GeminiUsage.total_tokens).label("total_tokens"),
                func.count().label("total_requests"),
            )
            .where(GeminiUsage.created_at >= since)
            .group_by(cast(GeminiUsage.created_at, Date))
            .order_by(cast(GeminiUsage.created_at, Date).desc())
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {
                "date": str(row.date),
                "tokens": row.total_tokens,
                "requests": row.total_requests,
            }
            for row in rows
        ]

    async def get_today_usage(self) -> dict:
        """Get today's usage totals with per-analysis-type breakdown.

        Returns:
            {requests, tokens, breakdown: [{analysis_type, requests, tokens}, ...]}
        """
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = (
            select(
                GeminiUsage.analysis_type,
                func.sum(GeminiUsage.total_tokens).label("total_tokens"),
                func.count().label("total_requests"),
            )
            .where(GeminiUsage.created_at >= today_start)
            .group_by(GeminiUsage.analysis_type)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        breakdown = [
            {
                "analysis_type": row.analysis_type,
                "requests": row.total_requests,
                "tokens": row.total_tokens,
            }
            for row in rows
        ]
        total_requests = sum(item["requests"] for item in breakdown)
        total_tokens = sum(item["tokens"] for item in breakdown)

        return {
            "requests": total_requests,
            "tokens": total_tokens,
            "breakdown": breakdown,
        }

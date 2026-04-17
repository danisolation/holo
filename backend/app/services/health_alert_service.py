"""Health alert service — proactive Telegram alerts for sustained errors/stale data.

Per D-15-05/D-15-06/D-15-07:
- Checks every 30 min via scheduler
- 4h cooldown per alert type to prevent spam
- Vietnamese HTML messages via MessageFormatter
"""
from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import engine
from app.services.health_service import HealthService
from app.telegram.formatter import MessageFormatter

# Module-level cooldown tracking (per D-15-06)
# Keys: "job_failures", "stale_data", "pool_exhaustion"
# Values: datetime of last alert sent
_last_alert_times: dict[str, datetime] = {}

COOLDOWN_HOURS = 4


def _cooldown_active(alert_type: str) -> bool:
    """Check if alert type is still within cooldown window."""
    last = _last_alert_times.get(alert_type)
    if last is None:
        return False
    elapsed = datetime.now(timezone.utc) - last
    return elapsed < timedelta(hours=COOLDOWN_HOURS)


class HealthAlertService:
    """Checks health conditions and sends Telegram alerts when thresholds exceeded."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_and_alert(self) -> None:
        """Run all health checks and send alerts for triggered conditions.

        Checks:
        1. Consecutive job failures (≥3 same job_id with status="failed" in 24h)
        2. Stale data (any source > 2× threshold from _FRESHNESS_SOURCES)
        3. DB pool exhaustion (checked_out / size > 0.8)
        """
        from app.telegram.bot import telegram_bot

        # 1. Check consecutive job failures
        if not _cooldown_active("job_failures"):
            failed_jobs = await self._check_job_failures()
            if failed_jobs:
                details = [
                    f"{job_id} ({count} lần thất bại)"
                    for job_id, count in failed_jobs
                ]
                message = MessageFormatter.health_alert("job_failures", details)
                _last_alert_times["job_failures"] = datetime.now(timezone.utc)
                logger.warning(f"Health alert: job_failures — {details}")
                if telegram_bot.is_configured:
                    await telegram_bot.send_message(message)

        # 2. Check stale data
        if not _cooldown_active("stale_data"):
            stale_sources = await self._check_stale_data()
            if stale_sources:
                message = MessageFormatter.health_alert("stale_data", stale_sources)
                _last_alert_times["stale_data"] = datetime.now(timezone.utc)
                logger.warning(f"Health alert: stale_data — {stale_sources}")
                if telegram_bot.is_configured:
                    await telegram_bot.send_message(message)

        # 3. Check DB pool exhaustion
        if not _cooldown_active("pool_exhaustion"):
            pool_details = self._check_pool_exhaustion()
            if pool_details:
                message = MessageFormatter.health_alert("pool_exhaustion", pool_details)
                _last_alert_times["pool_exhaustion"] = datetime.now(timezone.utc)
                logger.warning(f"Health alert: pool_exhaustion — {pool_details}")
                if telegram_bot.is_configured:
                    await telegram_bot.send_message(message)

    async def _check_job_failures(self) -> list[tuple[str, int]]:
        """Find jobs with ≥3 failures in the last 24 hours."""
        since = datetime.now(timezone.utc) - timedelta(hours=24)
        result = await self.session.execute(
            text(
                "SELECT job_id, COUNT(*) as fail_count "
                "FROM job_executions "
                "WHERE status = 'failed' AND started_at >= :since "
                "GROUP BY job_id "
                "HAVING COUNT(*) >= 3"
            ),
            {"since": since},
        )
        rows = result.fetchall()
        return [(row.job_id, row.fail_count) for row in rows]

    async def _check_stale_data(self) -> list[str]:
        """Find data sources that are stale beyond 2× their threshold."""
        hs = HealthService(self.session)
        freshness = await hs.get_data_freshness()

        now_utc = datetime.now(timezone.utc)
        stale_sources = []
        for item in freshness:
            if item["is_stale"] and item["latest"] is not None:
                # Compute actual age and only alert if beyond 2× threshold (D-15-05)
                latest = datetime.fromisoformat(item["latest"])
                if latest.tzinfo is None:
                    latest = latest.replace(tzinfo=timezone.utc)
                age_hours = (now_utc - latest).total_seconds() / 3600
                if age_hours > item["threshold_hours"] * 2:
                    stale_sources.append(
                        f"{item['data_type']} (>{item['threshold_hours'] * 2}h)"
                    )
        return stale_sources

    def _check_pool_exhaustion(self) -> list[str]:
        """Check if DB pool utilization exceeds 80%."""
        pool = engine.pool
        size = pool.size()
        checked_out = pool.checkedout()

        if size > 0 and (checked_out / size) > 0.8:
            pct = int((checked_out / size) * 100)
            return [f"{checked_out}/{size} kết nối đang sử dụng ({pct}%)"]
        return []

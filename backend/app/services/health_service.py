"""Health monitoring service — aggregation queries on existing data."""
import re
from collections import defaultdict
from datetime import date as date_type, datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.scheduler.manager import _JOB_NAMES

_STATUS_COLORS = {"success": "green", "partial": "yellow", "failed": "red"}

# Vietnamese job name mapping for pipeline timeline (D-15-03)
_JOB_NAMES_VN = {
    "daily_price_crawl_hose": "Crawl giá HOSE",
    "daily_price_crawl_hnx": "Crawl giá HNX",
    "daily_price_crawl_upcom": "Crawl giá UPCOM",
    "daily_indicator_compute_triggered": "Tính chỉ báo KT",
    "daily_ai_analysis_triggered": "Phân tích AI",
    "daily_news_crawl_triggered": "Crawl tin tức",
    "daily_sentiment_triggered": "Phân tích sentiment",
    "daily_combined_triggered": "Phân tích kết hợp",
}

# Whitelist of allowed table/column identifiers for freshness queries
_VALID_SQL_IDENTIFIER = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

_FRESHNESS_SOURCES = [
    ("daily_prices", "Giá cổ phiếu", "date", 48),
    ("technical_indicators", "Chỉ báo kỹ thuật", "date", 48),
    ("ai_analyses", "Phân tích AI", "analysis_date", 48),
    ("news_articles", "Tin tức", "created_at", 48),
    ("financials", "Báo cáo tài chính", "created_at", 168),
]

# Validate all identifiers at import time
for _table, _label, _col, _ in _FRESHNESS_SOURCES:
    assert _VALID_SQL_IDENTIFIER.match(_table), f"Invalid table name: {_table}"
    assert _VALID_SQL_IDENTIFIER.match(_col), f"Invalid column name: {_col}"


class HealthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_job_statuses(self) -> list[dict]:
        """Latest execution per job with status color."""
        result = await self.session.execute(
            text(
                "SELECT DISTINCT ON (job_id) "
                "job_id, status, started_at, completed_at, result_summary, error_message "
                "FROM job_executions "
                "ORDER BY job_id, started_at DESC"
            )
        )
        rows = result.fetchall()
        jobs = []
        for row in rows:
            duration = None
            if row.completed_at and row.started_at:
                duration = (row.completed_at - row.started_at).total_seconds()
            jobs.append({
                "job_id": row.job_id,
                "job_name": _JOB_NAMES.get(row.job_id, row.job_id.replace("_", " ").title()),
                "status": row.status,
                "color": _STATUS_COLORS.get(row.status, "red"),
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                "duration_seconds": duration,
                "result_summary": row.result_summary,
                "error_message": row.error_message,
            })
        return jobs

    async def get_data_freshness(self) -> list[dict]:
        """Latest timestamp per data type with stale flags."""
        items = []
        now_utc = datetime.now(timezone.utc)
        today = date_type.today()

        for table, label, col, threshold_h in _FRESHNESS_SOURCES:
            result = await self.session.execute(
                text(f"SELECT MAX({col}) as latest FROM {table}")
            )
            latest = result.scalar_one_or_none()

            is_stale = True
            latest_str = None
            if latest is not None:
                if isinstance(latest, date_type) and not isinstance(latest, datetime):
                    age_hours = (today - latest).days * 24
                else:
                    if latest.tzinfo is None:
                        latest = latest.replace(tzinfo=timezone.utc)
                    age_hours = (now_utc - latest).total_seconds() / 3600
                is_stale = age_hours > threshold_h
                latest_str = latest.isoformat()

            items.append({
                "data_type": label,
                "table_name": table,
                "latest": latest_str,
                "is_stale": is_stale,
                "threshold_hours": threshold_h,
            })
        return items

    async def get_error_rates(self, days: int = 7) -> list[dict]:
        """Error counts grouped by job and day over the last N days."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            text(
                "SELECT job_id, DATE(started_at AT TIME ZONE 'UTC') as day, "
                "COUNT(*) as total, "
                "COUNT(*) FILTER (WHERE status = 'failed') as failed "
                "FROM job_executions "
                "WHERE started_at >= :since "
                "GROUP BY job_id, day "
                "ORDER BY job_id, day"
            ),
            {"since": since},
        )
        rows = result.fetchall()

        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            grouped[row.job_id].append({
                "day": row.day.isoformat(),
                "total": row.total,
                "failed": row.failed,
            })

        jobs = []
        for job_id, day_items in grouped.items():
            total_runs = sum(d["total"] for d in day_items)
            total_failures = sum(d["failed"] for d in day_items)
            jobs.append({
                "job_id": job_id,
                "job_name": _JOB_NAMES.get(job_id, job_id.replace("_", " ").title()),
                "days": day_items,
                "total_runs": total_runs,
                "total_failures": total_failures,
            })
        return jobs

    async def get_pipeline_timeline(self, days: int = 7) -> list[dict]:
        """Pipeline execution timeline grouped by date for Gantt visualization.

        Per D-15-08: Query job_executions for last N days, group by date,
        compute duration, map to Vietnamese names.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session.execute(
            text(
                "SELECT job_id, started_at, completed_at, status "
                "FROM job_executions "
                "WHERE started_at >= :since "
                "ORDER BY started_at"
            ),
            {"since": since},
        )
        rows = result.fetchall()

        # Group by date
        date_groups: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            duration = None
            if row.completed_at and row.started_at:
                duration = (row.completed_at - row.started_at).total_seconds()

            date_key = row.started_at.strftime("%Y-%m-%d")
            date_groups[date_key].append({
                "job_id": row.job_id,
                "job_name": _JOB_NAMES_VN.get(
                    row.job_id,
                    _JOB_NAMES.get(row.job_id, row.job_id.replace("_", " ").title()),
                ),
                "started_at": row.started_at.isoformat(),
                "duration_seconds": duration,
                "status": row.status,
            })

        # Build sorted runs (most recent first)
        runs = []
        for date_key in sorted(date_groups.keys(), reverse=True):
            steps = date_groups[date_key]
            total_seconds = sum(
                s["duration_seconds"] for s in steps if s["duration_seconds"] is not None
            )
            runs.append({
                "date": date_key,
                "total_seconds": total_seconds,
                "steps": steps,
            })

        return runs

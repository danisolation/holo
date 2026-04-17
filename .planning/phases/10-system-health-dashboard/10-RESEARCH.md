# Phase 10: System Health Dashboard - Research

**Researched:** 2025-07-18
**Domain:** Health monitoring dashboard (FastAPI backend + Next.js frontend)
**Confidence:** HIGH

## Summary

Phase 10 adds a system health monitoring page at `/dashboard/health` with backend API endpoints. The backend work is straightforward — querying `job_executions` for status/errors, running `MAX()` timestamp queries on 5 data tables, reading `engine.pool` stats from SQLAlchemy, and using APScheduler's `add_job()` for manual triggers. The frontend builds a standard dashboard page using the project's existing patterns (React Query hooks, shadcn/ui Card/Table/Badge, Recharts for charts).

The codebase is well-structured with clear patterns to follow. The existing `system.py` handles basic health/scheduler endpoints; the new health endpoints should live in a separate `health.py` router to keep concerns separated. All 12 job IDs are already tracked in `job_executions` with status, timestamps, and JSONB summaries. The pool stats are synchronous reads from `engine.pool` — no async complexity.

**Primary recommendation:** Create `backend/app/api/health.py` with a `/health` prefix router containing 6 endpoints, add a `HealthService` class for database queries, then build the frontend page with status cards grid + freshness table + error sparklines + trigger buttons — all using existing project patterns.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-10-01:** New API router at `/api/system/health` with endpoints: GET /health (summary), GET /health/jobs, GET /health/data-freshness, GET /health/errors, GET /health/db-pool, POST /health/trigger/{job_name}
- **D-10-02:** Data freshness from daily_prices, financials, news_articles, ai_analyses, technical_indicators. Stale thresholds: prices > 1 business day, financials > 1 week, etc.
- **D-10-03:** Job status from job_executions table. Green=success, Yellow=partial, Red=failed or no runs in expected window
- **D-10-04:** POST trigger adds job to scheduler with immediate run, reuses job functions from scheduler/jobs.py
- **D-10-05:** Frontend at /dashboard/health with status cards, freshness table, error sparklines, trigger buttons with confirmation dialog

### Deferred Ideas (OUT OF SCOPE)
- HEALTH-08: Gemini API usage tracker
- HEALTH-09: Pipeline execution timeline Gantt chart
- HEALTH-10: Telegram health notifications
</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| HEALTH-01 | Health dashboard shows data freshness with stale flags | MAX(timestamp) queries on 5 tables; stale thresholds per data type |
| HEALTH-02 | Health dashboard shows last crawl status per job (green/yellow/red) | Query job_executions for latest per job_id; status field already has success/partial/failed |
| HEALTH-03 | Health dashboard shows error rate per job over last 7 days | COUNT with status filter grouped by date from job_executions |
| HEALTH-04 | Health dashboard shows database connection pool status | engine.pool.size()/checkedin()/checkedout()/overflow() — sync reads |
| HEALTH-05 | Health dashboard page exists at /dashboard/health | Next.js App Router: create src/app/dashboard/health/page.tsx |
| HEALTH-06 | Scheduler status enhanced with last run result | Extend existing /scheduler/status or add to /health/jobs endpoint |
| HEALTH-07 | User can manually trigger jobs from health dashboard | POST endpoint + scheduler.add_job() immediate run pattern (already used for chaining) |

</phase_requirements>

## Standard Stack

### Core (already installed — no new dependencies)

**Backend:**

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | (installed) | API router + Pydantic response models | Already used for all endpoints |
| SQLAlchemy 2.0 | 2.0.49 | Async queries on job_executions and data tables | Already the ORM layer [VERIFIED: pip in venv] |
| APScheduler | 3.11.2 | Immediate job triggers via `scheduler.add_job()` | Already the scheduler [VERIFIED: pip in venv] |

**Frontend:**

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React Query | ^5.99.0 | Data fetching hooks for health endpoints | Already used for all data fetching [VERIFIED: package.json] |
| Recharts | ^3.8.1 | Error rate sparklines (AreaChart/LineChart) | Already used for PieChart on dashboard [VERIFIED: package.json] |
| shadcn/ui | ^4.2.0 | Card, Table, Badge, Dialog, Tabs components | Already used throughout frontend [VERIFIED: package.json] |
| lucide-react | ^1.8.0 | Icons for status indicators | Already used everywhere [VERIFIED: package.json] |
| date-fns | ^4.1.0 | Relative time formatting ("5 giờ trước") | Already installed [VERIFIED: package.json] |

### No New Dependencies Needed
This phase uses only existing libraries. No `npm install` or `pip install` required.

## Architecture Patterns

### Backend File Structure
```
backend/app/
├── api/
│   ├── health.py          # NEW — /health prefix router (6 endpoints)
│   └── router.py           # EDIT — add health_router include
├── services/
│   └── health_service.py   # NEW — all health-related DB queries
├── schemas/
│   └── health.py           # NEW — Pydantic response models
├── database.py             # READ ONLY — engine.pool for pool stats
└── scheduler/
    ├── manager.py           # READ ONLY — scheduler + _JOB_NAMES
    └── jobs.py              # READ ONLY — job functions for manual trigger
```

### Frontend File Structure
```
frontend/src/
├── app/
│   └── dashboard/
│       └── health/
│           └── page.tsx     # NEW — health dashboard page
├── components/
│   ├── health-status-cards.tsx    # NEW — colored job status cards grid
│   ├── data-freshness-table.tsx   # NEW — freshness table with stale flags
│   ├── error-rate-chart.tsx       # NEW — 7-day error sparklines per job
│   ├── db-pool-status.tsx         # NEW — connection pool display
│   └── job-trigger-buttons.tsx    # NEW — manual trigger with confirmation
├── lib/
│   ├── api.ts               # EDIT — add health fetch functions
│   └── hooks.ts             # EDIT — add health React Query hooks
└── components/
    └── navbar.tsx            # EDIT — add "Hệ thống" nav link
```

### Pattern 1: Health API Router (follows existing system.py pattern)
**What:** Separate router file with Pydantic response models
**When to use:** All 6 health endpoints
**Example:**
```python
# backend/app/api/health.py
# Source: follows exact pattern from backend/app/api/system.py + analysis.py

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.database import engine, async_session
from app.services.health_service import HealthService
from app.scheduler.manager import scheduler

router = APIRouter(prefix="/health", tags=["health"])

# --- Response Models in schemas/health.py ---

@router.get("/jobs")
async def get_job_status():
    async with async_session() as session:
        svc = HealthService(session)
        return await svc.get_job_statuses()

@router.get("/data-freshness")
async def get_data_freshness():
    async with async_session() as session:
        svc = HealthService(session)
        return await svc.get_data_freshness()

@router.get("/errors")
async def get_error_rates():
    async with async_session() as session:
        svc = HealthService(session)
        return await svc.get_error_rates()

@router.get("/db-pool")
async def get_db_pool_status():
    pool = engine.pool  # sync access — just reads internal counters
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "max_overflow": engine.pool._max_overflow,  # from engine config
    }

@router.post("/trigger/{job_name}")
async def trigger_job(job_name: str, background_tasks: BackgroundTasks):
    # Map job_name to function — only allow known jobs
    ...
```
[VERIFIED: codebase patterns from system.py, analysis.py, router.py]

### Pattern 2: Health Service (follows existing service pattern)
**What:** Service class with async session for DB queries
**When to use:** All health aggregation queries
**Example:**
```python
# backend/app/services/health_service.py
# Source: follows pattern from job_execution_service.py

from datetime import datetime, timezone, timedelta
from sqlalchemy import select, func, case, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_execution import JobExecution

class HealthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_job_statuses(self) -> list[dict]:
        """Get latest execution for each job_id."""
        # Use DISTINCT ON (PostgreSQL) for latest per job_id
        # Or subquery approach for portability
        ...

    async def get_error_rates(self) -> list[dict]:
        """Error rate per job over last 7 days."""
        since = datetime.now(timezone.utc) - timedelta(days=7)
        stmt = (
            select(
                JobExecution.job_id,
                func.date_trunc('day', JobExecution.started_at).label('day'),
                func.count().label('total'),
                func.count().filter(JobExecution.status == 'failed').label('failed'),
            )
            .where(JobExecution.started_at >= since)
            .group_by(JobExecution.job_id, 'day')
            .order_by(JobExecution.job_id, 'day')
        )
        ...
```
[VERIFIED: codebase pattern from job_execution_service.py]

### Pattern 3: React Query Hook (follows existing hooks.ts pattern)
**What:** useQuery hooks with staleTime for health endpoints
**When to use:** All health data fetching
**Example:**
```typescript
// frontend/src/lib/hooks.ts additions
// Source: follows exact pattern from existing hooks

export function useJobStatuses() {
  return useQuery({
    queryKey: ["health-jobs"],
    queryFn: () => fetchJobStatuses(),
    staleTime: 30 * 1000, // 30 seconds — health data should be relatively fresh
    refetchInterval: 60 * 1000, // Auto-refresh every 60 seconds
  });
}
```
[VERIFIED: codebase pattern from lib/hooks.ts]

### Pattern 4: Dashboard Page (follows existing page layout)
**What:** Page component with section headers, card grids, tables
**When to use:** Health dashboard page structure
**Example:**
```tsx
// frontend/src/app/dashboard/health/page.tsx
// Source: follows pattern from dashboard/page.tsx and dashboard/portfolio/page.tsx

export default function HealthPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
          <Activity className="size-6" />
          Hệ thống
        </h2>
        <p className="text-sm text-muted-foreground mt-1">
          Tình trạng hệ thống và dữ liệu
        </p>
      </div>
      <HealthStatusCards />
      <DataFreshnessTable />
      <ErrorRateChart />
      <DbPoolStatus />
      <JobTriggerButtons />
    </div>
  );
}
```
[VERIFIED: codebase patterns from dashboard/page.tsx, dashboard/portfolio/page.tsx]

### Anti-Patterns to Avoid
- **Don't add health endpoints to existing system.py:** It's already 180+ lines. Create separate `health.py` router for cleanliness. [VERIFIED: system.py is 183 lines]
- **Don't poll the backend every second:** Health data doesn't change that fast. Use 30s staleTime + 60s refetchInterval. [ASSUMED — reasonable for health dashboard]
- **Don't use raw SQL for everything:** Use SQLAlchemy ORM where possible, but raw `text()` is fine for `DISTINCT ON` (PostgreSQL-specific). [VERIFIED: codebase uses both patterns]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sparkline charts | Custom SVG | Recharts AreaChart with minimal props | Already in project, handles responsive sizing |
| Status color logic | Manual if/else in frontend | Map from backend status field | Backend already returns "success"/"partial"/"failed" |
| Relative time ("5 phút trước") | Manual date math | `date-fns` `formatDistanceToNow` | Already installed, handles i18n |
| Confirmation dialog | Custom modal | shadcn/ui Dialog component | Already in project with consistent styling |
| Pool stats | Custom connection counting | `engine.pool.size()` etc. | SQLAlchemy provides these natively |

**Key insight:** This phase is pure glue — aggregating existing data (job_executions, table timestamps, pool stats) and displaying it. No new complex logic needed.

## Common Pitfalls

### Pitfall 1: Router Prefix Collision with Existing /health
**What goes wrong:** The existing `system.py` has `GET /health` (basic health check). Adding a new router with prefix `/health` could create confusion.
**Why it happens:** FastAPI matches routes by first match, so `/api/health` (existing) vs `/api/health/jobs` (new) should work fine, but it's confusing.
**How to avoid:** The new health router uses prefix `/health` which creates paths like `/health/jobs`, `/health/data-freshness`. The existing `/health` endpoint on the system router (no prefix) serves as the basic health check. These don't conflict — FastAPI distinguishes `/health` from `/health/jobs`. Document this clearly.
**Warning signs:** 404 on new endpoints after adding router.

### Pitfall 2: DISTINCT ON for Latest Job Execution
**What goes wrong:** Getting the latest job execution per job_id requires either PostgreSQL `DISTINCT ON` or a subquery. Using basic `GROUP BY` loses the row data.
**Why it happens:** Standard SQL can't easily "get the latest row per group."
**How to avoid:** Use PostgreSQL `DISTINCT ON (job_id) ORDER BY started_at DESC` or a correlated subquery. Both work. `DISTINCT ON` is cleaner for PostgreSQL-only (which this project is). [VERIFIED: project uses PostgreSQL/asyncpg only]
**Warning signs:** Getting random rows instead of latest, or N+1 queries per job.

### Pitfall 3: Manual Trigger Concurrency
**What goes wrong:** User triggers a job while the same job is already running from the scheduler, causing duplicate executions or data corruption.
**Why it happens:** APScheduler allows multiple instances of the same job function.
**How to avoid:** Use `replace_existing=True` and check if the job is currently running. The existing chaining pattern uses `replace_existing=True` which is sufficient — if the same `_manual` ID is already pending, it gets replaced. Also, manual triggers should use distinct IDs like `{job_name}_manual` (already in _JOB_NAMES map). [VERIFIED: manager.py uses replace_existing=True for chained jobs]
**Warning signs:** Two job_execution rows with overlapping time ranges for the same job_id.

### Pitfall 4: Stale Data Detection Threshold Logic
**What goes wrong:** Flagging data as stale when the market is simply closed (weekends, holidays).
**Why it happens:** Prices don't update on weekends/holidays. A "1 business day" threshold needs to account for non-trading days.
**How to avoid:** Use a generous threshold: prices stale if > 2 calendar days old on weekdays, > 3 on Monday (covers weekend). Or simpler: stale if > 48 hours. Vietnamese holidays are harder — just use calendar day thresholds. [ASSUMED — project doesn't have a holiday calendar]
**Warning signs:** All jobs showing red on Monday mornings.

### Pitfall 5: Pool Stats _max_overflow is Private Attribute
**What goes wrong:** Accessing `engine.pool._max_overflow` relies on a private attribute.
**Why it happens:** SQLAlchemy doesn't expose `max_overflow` as a public method on the pool.
**How to avoid:** It's fine for an internal monitoring tool — it's been stable across SQLAlchemy 2.x. Alternatively, read from the engine creation config. But for a single-user health dashboard, accessing `_max_overflow` is pragmatic. [VERIFIED: SQLAlchemy 2.0.49 pool class has _max_overflow]
**Warning signs:** AttributeError after SQLAlchemy major version upgrade.

### Pitfall 6: Timezone Handling in Freshness Queries
**What goes wrong:** Comparing UTC timestamps with local timezone expectations.
**Why it happens:** `job_executions.started_at` is stored as `TIMESTAMP WITH TIMEZONE` (UTC), but the user thinks in Asia/Ho_Chi_Minh.
**How to avoid:** Always compare in UTC on the backend. Return ISO timestamps to the frontend. Let the frontend format to local time using `date-fns`. [VERIFIED: existing models use TIMESTAMP(timezone=True), config uses Asia/Ho_Chi_Minh]
**Warning signs:** Data appearing 7 hours more stale than expected.

## Code Examples

### Backend: Data Freshness Query
```python
# Source: derived from existing model schemas [VERIFIED: model files]

async def get_data_freshness(self) -> list[dict]:
    """Get latest update timestamp for each data type."""
    tables = [
        ("daily_prices", "Giá cổ phiếu", "date", 48),       # hours threshold
        ("technical_indicators", "Chỉ báo kỹ thuật", "date", 48),
        ("ai_analyses", "Phân tích AI", "analysis_date", 48),
        ("news_articles", "Tin tức", "created_at", 48),
        ("financials", "Báo cáo tài chính", "created_at", 168),  # 7 days
    ]
    results = []
    for table, label, col, threshold_hours in tables:
        row = await self.session.execute(
            text(f"SELECT MAX({col}) as latest FROM {table}")
        )
        latest = row.scalar_one_or_none()
        is_stale = False
        if latest:
            # Convert date to datetime for comparison
            if hasattr(latest, 'hour'):
                age_hours = (datetime.now(timezone.utc) - latest).total_seconds() / 3600
            else:
                from datetime import date as date_type
                age_hours = (date_type.today() - latest).days * 24
            is_stale = age_hours > threshold_hours
        results.append({
            "data_type": label,
            "table": table,
            "latest": latest.isoformat() if latest else None,
            "is_stale": is_stale or latest is None,
            "threshold_hours": threshold_hours,
        })
    return results
```

### Backend: DB Pool Stats Endpoint
```python
# Source: verified via SQLAlchemy 2.0.49 QueuePool API [VERIFIED: live introspection]

@router.get("/db-pool")
async def get_db_pool_status():
    """Database connection pool statistics."""
    pool = engine.pool
    return {
        "pool_size": pool.size(),         # configured max pool size (5)
        "checked_in": pool.checkedin(),   # idle connections in pool
        "checked_out": pool.checkedout(), # connections currently in use
        "overflow": pool.overflow(),       # extra connections beyond pool_size
        "max_overflow": 3,                 # hardcoded from database.py config
    }
```

### Backend: Manual Job Trigger
```python
# Source: follows chaining pattern from manager.py [VERIFIED: manager.py lines 78-100]

from app.scheduler.jobs import (
    daily_price_crawl, daily_indicator_compute, daily_ai_analysis,
    daily_news_crawl, daily_sentiment_analysis, daily_combined_analysis,
)

JOB_TRIGGER_MAP = {
    "crawl": ("daily_price_crawl_manual", daily_price_crawl),
    "indicators": ("daily_indicator_compute_manual", daily_indicator_compute),
    "ai": ("daily_ai_analysis_manual", daily_ai_analysis),
    "news": ("daily_news_crawl_manual", daily_news_crawl),
    "sentiment": ("daily_sentiment_manual", daily_sentiment_analysis),
    "combined": ("daily_combined_manual", daily_combined_analysis),
}

@router.post("/trigger/{job_name}")
async def trigger_job(job_name: str):
    if job_name not in JOB_TRIGGER_MAP:
        raise HTTPException(404, f"Unknown job: {job_name}")
    job_id, job_func = JOB_TRIGGER_MAP[job_name]
    scheduler.add_job(
        job_func,
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600,
    )
    return {"message": f"Job '{job_name}' triggered", "triggered": True}
```

### Backend: Latest Job Status with DISTINCT ON
```python
# Source: PostgreSQL DISTINCT ON pattern [VERIFIED: project uses PostgreSQL only]

async def get_job_statuses(self) -> list[dict]:
    """Get latest execution per job_id with status color."""
    stmt = text("""
        SELECT DISTINCT ON (job_id)
            job_id, status, started_at, completed_at,
            result_summary, error_message
        FROM job_executions
        ORDER BY job_id, started_at DESC
    """)
    result = await self.session.execute(stmt)
    rows = result.mappings().all()
    return [
        {
            "job_id": r["job_id"],
            "status": r["status"],
            "color": _status_color(r["status"]),
            "started_at": r["started_at"].isoformat() if r["started_at"] else None,
            "completed_at": r["completed_at"].isoformat() if r["completed_at"] else None,
            "result_summary": r["result_summary"],
            "error_message": r["error_message"],
        }
        for r in rows
    ]

def _status_color(status: str) -> str:
    return {"success": "green", "partial": "yellow", "failed": "red"}.get(status, "red")
```

### Frontend: Recharts Sparkline for Error Rate
```tsx
// Source: follows existing Recharts PieChart pattern from dashboard/page.tsx [VERIFIED]

import { AreaChart, Area, ResponsiveContainer, Tooltip } from "recharts";

interface SparklineProps {
  data: { day: string; failed: number; total: number }[];
}

function ErrorSparkline({ data }: SparklineProps) {
  return (
    <div className="h-10 w-24">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <Area
            type="monotone"
            dataKey="failed"
            stroke="#ef5350"
            fill="#ef5350"
            fillOpacity={0.2}
            strokeWidth={1.5}
            dot={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "hsl(var(--popover))",
              border: "1px solid hsl(var(--border))",
              borderRadius: "0.5rem",
              color: "hsl(var(--popover-foreground))",
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### Frontend: Status Card with Color
```tsx
// Source: follows Card pattern from dashboard/page.tsx + portfolio-summary.tsx [VERIFIED]

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, AlertTriangle, XCircle } from "lucide-react";

const STATUS_CONFIG = {
  green: { icon: CheckCircle, color: "text-[#26a69a]", bg: "bg-[#26a69a]/10", label: "OK" },
  yellow: { icon: AlertTriangle, color: "text-amber-500", bg: "bg-amber-500/10", label: "Cảnh báo" },
  red: { icon: XCircle, color: "text-[#ef5350]", bg: "bg-[#ef5350]/10", label: "Lỗi" },
};
```

## Key Data Inventory

### All 12 Job IDs (from job_executions table)
[VERIFIED: grep of scheduler/jobs.py `job_svc.start()` calls]

| Job ID | Human Name | Schedule | Type |
|--------|-----------|----------|------|
| `daily_price_crawl` | Daily Price Crawl | Mon-Fri 15:30 | Cron |
| `weekly_ticker_refresh` | Weekly Ticker Refresh | Sun 10:00 | Cron |
| `weekly_financial_crawl` | Weekly Financial Crawl | Sat 08:00 | Cron |
| `daily_indicator_compute` | Daily Indicator Compute | Chained after price crawl | Event |
| `daily_ai_analysis` | Daily AI Analysis | Chained after indicators | Event |
| `daily_news_crawl` | Daily News Crawl | Chained after AI | Event |
| `daily_sentiment_analysis` | Daily Sentiment Analysis | Chained after news | Event |
| `daily_combined_analysis` | Daily Combined Analysis | Chained after sentiment | Event |
| `daily_signal_alert_check` | Daily Signal Alert Check | Chained after combined | Event |
| `daily_price_alert_check` | Daily Price Alert Check | Chained after price crawl | Event |
| `daily_summary_send` | Daily Market Summary | Mon-Fri 16:00 | Cron |
| `daily_corporate_action_check` | Daily Corporate Action Check | Chained after price crawl | Event |

### Data Freshness Tables
[VERIFIED: all model files inspected]

| Table | Timestamp Column | Freshness Metric | Stale Threshold |
|-------|-----------------|-----------------|-----------------|
| `daily_prices` | `date` (Date) | `MAX(date)` | > 2 calendar days (accounts for weekends) |
| `technical_indicators` | `date` (Date) | `MAX(date)` | > 2 calendar days |
| `ai_analyses` | `analysis_date` (Date) | `MAX(analysis_date)` | > 2 calendar days |
| `news_articles` | `created_at` (Timestamp) | `MAX(created_at)` | > 2 calendar days |
| `financials` | `created_at` (Timestamp) | `MAX(created_at)` | > 7 calendar days |

### Pool Configuration
[VERIFIED: database.py]

| Setting | Value |
|---------|-------|
| pool_size | 5 |
| max_overflow | 3 |
| pool_pre_ping | True |
| Total max connections | 8 |

### Job Name Mapping (for manual triggers)
[VERIFIED: manager.py _JOB_NAMES dict]

The `_JOB_NAMES` dict in `manager.py` already has `_manual` suffix IDs for: indicator_compute, ai_analysis, news_crawl, sentiment, combined. These are the IDs used when manually triggering. The health API should expose a subset of triggerable jobs:

| Trigger Name | Job Function | Manual ID |
|-------------|-------------|-----------|
| `crawl` | `daily_price_crawl` | `daily_price_crawl_manual` (new) |
| `indicators` | `daily_indicator_compute` | `daily_indicator_compute_manual` |
| `ai` | `daily_ai_analysis` | `daily_ai_analysis_manual` |
| `news` | `daily_news_crawl` | `daily_news_crawl_manual` |
| `sentiment` | `daily_sentiment_analysis` | `daily_sentiment_manual` |
| `combined` | `daily_combined_analysis` | `daily_combined_manual` |

### Navbar Links (current)
[VERIFIED: navbar.tsx]

```typescript
const NAV_LINKS = [
  { href: "/", label: "Tổng quan" },
  { href: "/watchlist", label: "Danh mục" },
  { href: "/dashboard", label: "Bảng điều khiển" },
  { href: "/dashboard/portfolio", label: "Đầu tư" },
  // ADD: { href: "/dashboard/health", label: "Hệ thống" },
];
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SQLAlchemy 1.x pool stats via `pool.status()` string parsing | SQLAlchemy 2.x `pool.size()`, `pool.checkedin()`, `pool.checkedout()`, `pool.overflow()` methods | SQLAlchemy 2.0 | Use individual methods, not string parsing |
| APScheduler 3.x `add_job()` with `trigger='date'` for immediate | APScheduler 3.x `add_job()` with no trigger (runs immediately) | Stable pattern | No trigger arg = immediate execution |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 30s staleTime + 60s refetchInterval is appropriate for health dashboard | Architecture Patterns | Low — easy to tune later |
| A2 | Stale thresholds (48h for prices, 168h for financials) account for weekends | Code Examples | Medium — could show false stale on Monday mornings. Mitigation: use generous thresholds |
| A3 | Project doesn't have a Vietnamese holiday calendar | Pitfall 4 | Low — worst case shows data as stale on holidays (informational only) |
| A4 | `engine.pool._max_overflow` is stable across SQLAlchemy 2.x minor versions | Pitfall 5 | Low — can hardcode to 3 from database.py config instead |

## Open Questions

1. **Should the overall /health endpoint be enhanced or kept separate?**
   - What we know: Existing `GET /api/health` returns basic status. CONTEXT says add `GET /health` (summary).
   - What's unclear: Does D-10-01's "GET /health — Overall health summary" mean enhance the existing endpoint or create a new one at `/api/health/summary`?
   - Recommendation: Create a new `GET /api/health/summary` that aggregates all health data (jobs + freshness + pool). Keep existing `GET /api/health` as-is for backward compatibility.

2. **Which jobs should be triggerable?**
   - What we know: D-10-04 mentions "crawl, indicators, AI analysis." The context lists these three.
   - What's unclear: Should news, sentiment, combined also be triggerable?
   - Recommendation: Expose all 6 pipeline jobs (crawl, indicators, ai, news, sentiment, combined) since the UI has room and users may want to re-run any step. Exclude ticker refresh, financial crawl, summary send, alert checks (these are less useful to trigger manually or could cause side effects).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (with unittest.mock) |
| Config file | backend/tests/ directory with conftest.py |
| Quick run command | `cd backend && python -m pytest tests/test_api.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| HEALTH-01 | Data freshness endpoint returns timestamps + stale flags | unit | `pytest tests/test_health_api.py::TestDataFreshness -x` | ❌ Wave 0 |
| HEALTH-02 | Job status endpoint returns latest per job with color | unit | `pytest tests/test_health_api.py::TestJobStatus -x` | ❌ Wave 0 |
| HEALTH-03 | Error rates endpoint returns 7-day counts per job | unit | `pytest tests/test_health_api.py::TestErrorRates -x` | ❌ Wave 0 |
| HEALTH-04 | DB pool endpoint returns pool statistics | unit | `pytest tests/test_health_api.py::TestDbPool -x` | ❌ Wave 0 |
| HEALTH-05 | Health page renders at /dashboard/health | manual-only | Visual check — Next.js page renders | N/A |
| HEALTH-06 | Job status includes last run result | unit | `pytest tests/test_health_api.py::TestJobStatus -x` | ❌ Wave 0 |
| HEALTH-07 | Trigger endpoint calls scheduler.add_job | unit | `pytest tests/test_health_api.py::TestJobTrigger -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_health_api.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_health_api.py` — covers HEALTH-01 through HEALTH-07 (backend endpoints)
- [ ] Follows existing `test_api.py` pattern with `TestClient` + mocked DB

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user app — no auth [VERIFIED: no auth middleware in main.py] |
| V3 Session Management | No | Stateless API |
| V4 Access Control | Minimal | Manual triggers should be POST-only (prevent CSRF via method check) |
| V5 Input Validation | Yes | `job_name` path param must be validated against allowlist (not arbitrary) |
| V6 Cryptography | No | No sensitive data in health endpoints |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Arbitrary job trigger via unvalidated job_name | Tampering | Validate against hardcoded `JOB_TRIGGER_MAP` allowlist |
| Pool stats info disclosure | Information Disclosure | Acceptable for single-user app. No sensitive data exposed |
| SQL injection via table name in freshness query | Tampering | Use hardcoded table names, not user input. Never interpolate user input into `text()` queries |

## Sources

### Primary (HIGH confidence)
- **Codebase inspection** — All backend files: system.py, jobs.py, manager.py, database.py, all model files, all frontend pages and components
- **SQLAlchemy 2.0.49** — Pool API verified via live Python introspection in project venv
- **APScheduler 3.11.2** — Version verified, `add_job()` pattern verified from existing codebase usage

### Secondary (MEDIUM confidence)
- **Recharts 3.x AreaChart** — API assumed stable based on existing PieChart usage in project [VERIFIED: package.json has ^3.8.1]
- **date-fns 4.x formatDistanceToNow** — Available for relative time formatting [VERIFIED: package.json has ^4.1.0]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, all verified in existing project
- Architecture: HIGH — follows exact patterns from existing codebase
- Pitfalls: HIGH — identified from codebase patterns and common PostgreSQL/async patterns

**Research date:** 2025-07-18
**Valid until:** 2025-08-18 (stable — all libraries already locked in project)

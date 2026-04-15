---
phase: 01-data-foundation
plan: "03"
subsystem: scheduler-api
tags: [apscheduler, fastapi-lifespan, cron-jobs, api-endpoints, background-tasks]
dependency_graph:
  requires: [01-01, 01-02]
  provides: [scheduler-automation, management-api, manual-crawl-triggers, backfill-endpoint]
  affects: []
tech_stack:
  added: [apscheduler-3.11-asyncio]
  patterns: [AsyncIOScheduler-in-lifespan, CronTrigger-scheduling, BackgroundTasks-for-manual-triggers, own-session-per-job]
key_files:
  created:
    - backend/app/scheduler/manager.py
    - backend/app/scheduler/jobs.py
    - backend/app/api/system.py
    - backend/app/api/router.py
    - backend/tests/test_scheduler.py
    - backend/tests/test_api.py
  modified:
    - backend/app/main.py
decisions:
  - "APScheduler AsyncIOScheduler embedded in FastAPI process — no external broker needed"
  - "Daily OHLCV crawl at 15:30 UTC+7 Mon-Fri — 45 min after market close for data finalization"
  - "Weekly ticker refresh Sun 10:00 — catch IPOs/delistings before trading week"
  - "Weekly financial crawl Sat 08:00 — avoid competing with daily price crawl"
  - "Jobs create own DB sessions via async_session() — run outside HTTP request context"
  - "Manual triggers use BackgroundTasks — non-blocking API responses"
  - "Backfill orchestrates tickers→prices→financials in sequence"
  - "misfire_grace_time 1h daily/2h weekly — handles scheduler downtime gracefully"
metrics:
  duration: 5m
  completed: "2026-04-15T12:41:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 1
  test_count: 24
  test_pass: 24
---

# Phase 01 Plan 03: Scheduler & API Endpoints Summary

APScheduler AsyncIOScheduler with 3 cron jobs (daily OHLCV Mon-Fri 15:30, weekly tickers Sun 10:00, weekly financials Sat 08:00) wired into FastAPI lifespan, plus 6 API endpoints for health monitoring, scheduler status, manual crawl triggers, and full backfill orchestration — all with BackgroundTasks for non-blocking operation.

## What Was Built

### APScheduler Setup (backend/app/scheduler/manager.py)
AsyncIOScheduler instance configured with Asia/Ho_Chi_Minh timezone. `configure_jobs()` registers 3 cron jobs with `replace_existing=True` and misfire grace times (1h daily, 2h weekly). Uses deferred imports to avoid circular dependencies.

### Job Functions (backend/app/scheduler/jobs.py)
Three async job functions, each creating its own DB session via `async with async_session()` (since jobs run outside HTTP request context). Structured logging with `=== START/COMPLETE/FAILED ===` markers for easy log parsing. All exceptions are logged and re-raised for APScheduler's error handling.

### API Endpoints (backend/app/api/system.py)
- **GET /api/health** — Checks DB connection (`SELECT 1`) and scheduler running state. Returns `healthy`/`degraded` status. DB errors truncated to 100 chars (T-01-11 mitigation).
- **GET /api/scheduler/status** — Lists all scheduled jobs with next run times.
- **POST /api/crawl/daily** — Manual OHLCV crawl trigger (background).
- **POST /api/crawl/tickers** — Manual ticker sync trigger (background).
- **POST /api/crawl/financials** — Manual financial crawl trigger (background).
- **POST /api/backfill** — Full initial data load: tickers → prices → financials (background). Accepts optional start_date/end_date query params.

### FastAPI Wiring (backend/app/main.py)
Updated lifespan: `configure_jobs()` → `scheduler.start()` on startup, `scheduler.shutdown(wait=False)` → `engine.dispose()` on shutdown. API router mounted at `/api` prefix.

### Router (backend/app/api/router.py)
Main API router combining sub-routers. Currently includes system_router only — extensible for future API groups.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | APScheduler setup with daily/weekly jobs and FastAPI lifespan wiring | 13047ea | manager.py, jobs.py, main.py, test_scheduler.py, router.py |
| 2 | API endpoints for health, scheduler status, manual triggers, and backfill | 6ee1d0b | system.py, router.py, test_api.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created minimal api/router.py in Task 1**
- **Found during:** Task 1
- **Issue:** Updated main.py imports `from app.api.router import api_router` but router.py didn't exist yet (Task 2 file). Task 1 verification would fail without it.
- **Fix:** Created minimal `router.py` with just `api_router = APIRouter()` in Task 1; Task 2 completed it with system_router include.
- **Files modified:** backend/app/api/router.py
- **Commit:** 13047ea

**2. [Rule 1 - Bug] Mocked async_session in crawl trigger tests**
- **Found during:** Task 2
- **Issue:** Plan's test code didn't mock `async_session` for POST /api/crawl/* tests. Starlette TestClient runs BackgroundTasks synchronously, causing real DB connection attempts (asyncpg tried connecting to dummy localhost:5432).
- **Fix:** Added `patch("app.api.system.async_session")` and service class patches to all 4 crawl trigger tests. Background tasks now run with mocked sessions.
- **Files modified:** backend/tests/test_api.py
- **Commit:** 6ee1d0b

## Test Results

```
24 passed in 14.77s
```

- 4 crawler tests (from Plan 02)
- 4 financial service tests (from Plan 02)
- 3 price service tests (from Plan 02)
- 6 scheduler tests: timezone check, job registration, schedule verification, 3 job function mocks
- 7 API tests: health endpoint, root endpoint, scheduler status, 4 crawl trigger endpoints

## Verification Results

- ✅ `from app.scheduler.manager import scheduler` — timezone is Asia/Ho_Chi_Minh
- ✅ `configure_jobs()` registers 3 jobs: daily_price_crawl, weekly_ticker_refresh, weekly_financial_crawl
- ✅ `from app.main import app` — 11 routes including /api/health, /api/scheduler/status, /api/crawl/daily, /api/backfill
- ✅ All 24 tests pass across 4 test files
- ✅ Health endpoint returns status, database, scheduler, timestamp fields
- ✅ Scheduler starts in lifespan, shuts down with wait=False

## Threat Mitigations Applied

| Threat ID | Mitigation | Status |
|-----------|-----------|--------|
| T-01-09 | start_date/end_date passed as str query params to PriceService; no SQL interpolation | ✅ Applied |
| T-01-10 | Background tasks prevent blocking; personal app not publicly exposed | ✅ Accepted |
| T-01-11 | DB error messages truncated via str(e)[:100]; connection string never in response | ✅ Applied |
| T-01-12 | Personal single-user app; no authentication per project constraints | ✅ Accepted |

## Known Stubs

None — all files are fully implemented per plan specification.

## Self-Check: PASSED

All 6 created files and 1 modified file verified on disk. Both task commits (13047ea, 6ee1d0b) confirmed in git log.

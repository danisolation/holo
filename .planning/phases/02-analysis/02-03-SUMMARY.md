---
phase: 02-analysis
plan: "03"
subsystem: analysis-pipeline
tags: [scheduler, job-chaining, api, testing, apscheduler, fastapi]
dependency_graph:
  requires: [02-01, 02-02]
  provides: [analysis-pipeline, analysis-api, job-chaining]
  affects: [scheduler, api-router]
tech_stack:
  added: []
  patterns: [event-listener-job-chaining, background-task-triggers, lazy-imports]
key_files:
  created:
    - backend/app/api/analysis.py
    - backend/tests/test_indicator_service.py
    - backend/tests/test_ai_analysis_service.py
  modified:
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
    - backend/app/api/router.py
    - backend/tests/test_scheduler.py
    - backend/tests/test_api.py
decisions:
  - "Lazy imports in job functions to avoid circular dependency (IndicatorService, AIAnalysisService imported inside async def)"
  - "Job chaining uses both 'daily_indicator_compute_triggered' and 'daily_indicator_compute_manual' IDs to chain AI analysis regardless of trigger source"
  - "Analysis API trigger endpoints use BackgroundTasks (non-blocking) matching existing system.py pattern"
  - "Query result endpoints capped at max 60 indicator rows per request (DoS mitigation per threat model)"
metrics:
  duration: 5m
  completed: "2026-04-15T06:44:19Z"
  tasks: 2
  files: 8
---

# Phase 2 Plan 3: Scheduler Job Chaining + API + Tests Summary

**Wired indicator and AI services into operational pipeline: APScheduler EVENT_JOB_EXECUTED chaining (crawl→indicators→AI), 5 analysis API endpoints, 20 new tests (44 total, 0 regressions)**

## What Was Done

### Task 1: Scheduler job chaining + API endpoints
- **jobs.py**: Added `daily_indicator_compute()` and `daily_ai_analysis()` job functions with lazy imports to avoid circular dependencies
- **manager.py**: Added `_on_job_executed()` event listener that chains `daily_price_crawl → daily_indicator_compute → daily_ai_analysis` on successful completion; listener registered in `configure_jobs()` via `scheduler.add_listener(_on_job_executed, events.EVENT_JOB_EXECUTED)`
- **analysis.py**: Created 5 endpoints:
  - `POST /api/analysis/trigger/indicators` — manual indicator computation trigger (background)
  - `POST /api/analysis/trigger/ai` — manual AI analysis trigger with type validation (background)
  - `GET /api/analysis/{symbol}/indicators` — latest indicator values (limit 5, max 60)
  - `GET /api/analysis/{symbol}/technical` — latest AI technical analysis
  - `GET /api/analysis/{symbol}/fundamental` — latest AI fundamental analysis
- **router.py**: Added `analysis_router` to main `api_router` (11 total routes)

### Task 2: Comprehensive unit tests
- **test_indicator_service.py** (8 tests): computation returns 12 indicators, series length, RSI/SMA200 warm-up NaN, safe_decimal conversion, skip low-data tickers
- **test_ai_analysis_service.py** (3 tests): ValueError without API key, technical prompt includes symbols, fundamental prompt includes financial data
- **test_scheduler.py** (+9 tests): chains indicators after price crawl, chains AI after indicators, skips on failure, original jobs still registered, new job functions call services
- **test_api.py** (+3 tests): trigger indicators 200, trigger AI 200, invalid type 400

## Verification Results

```
44 passed in 14.17s — 0 failures, 0 regressions
Jobs registered: [daily_price_crawl, weekly_ticker_refresh, weekly_financial_crawl]
Listeners: 1 registered (EVENT_JOB_EXECUTED)
Analysis routes: 5 endpoints
Main router: 11 total API routes
```

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **Lazy imports in job functions**: `IndicatorService` and `AIAnalysisService` imported inside async def bodies to avoid circular dependency (services → models → database → config at module level)
2. **Dual job ID matching for AI chain**: `_on_job_executed` matches both `daily_indicator_compute_triggered` (from auto-chain) and `daily_indicator_compute_manual` (from API trigger) to ensure AI analysis runs regardless of how indicators were triggered
3. **BackgroundTasks for triggers**: Analysis trigger endpoints use FastAPI `BackgroundTasks` (non-blocking) matching the existing `system.py` pattern for crawl triggers
4. **Max 60 indicator rows**: Query endpoint caps results at 60 rows per request per threat model T-02-07 (DoS mitigation)

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | f0e106b | feat(02-03): scheduler job chaining + analysis API endpoints |
| 2 | 08addec | test(02-03): comprehensive tests for indicator service, AI service, job chaining, API endpoints |

## Self-Check: PASSED

All 8 files verified present. Both commits (f0e106b, 08addec) confirmed in git log.

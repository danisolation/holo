---
phase: 97-ai-analysis-coverage
plan: 01
subsystem: scheduler, api
tags: [ai-analysis, scheduler-chain, coverage, morning-chain]
dependency_graph:
  requires: [ai_analysis_service, dead_letter_service, user_watchlist]
  provides: [morning_unified_analysis_job, coverage_endpoint]
  affects: [morning_chain, dashboard_coverage]
tech_stack:
  added: []
  patterns: [retry-before-DLQ, job-chaining]
key_files:
  created: []
  modified:
    - backend/app/scheduler/manager.py
    - backend/app/scheduler/jobs.py
    - backend/app/api/analysis.py
    - backend/app/schemas/analysis.py
decisions:
  - Used _dlq_failures helper (DeadLetterService) for DLQ instead of DLQService used by daily_unified_analysis — consistent with morning_trading_signal pattern
  - Coverage endpoint filters DLQ by unresolved entries only (resolved_at IS NULL) to avoid stale failures
metrics:
  duration: ~3min
  completed: 2025-05-14
  tasks: 2/2
  files: 4
---

# Phase 97 Plan 01: Re-enable Morning Unified Analysis + Coverage API Summary

Morning unified AI analysis re-enabled in scheduler chain with retry-before-DLQ, plus GET /api/analysis/coverage endpoint returning today's analyzed count vs watchlist size.

## Task Completion

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Re-enable morning unified analysis chain + retry | 548f240 | manager.py, jobs.py |
| 2 | Add GET /api/analysis/coverage endpoint | 325d422 | analysis.py, schemas/analysis.py |

## Changes Made

### Task 1: Morning Unified Analysis Chain
- **manager.py**: Replaced disabled comment block for `morning_indicator_compute_triggered` with chaining to `morning_unified_analysis`
- **manager.py**: Added `morning_unified_analysis_triggered` to `_JOB_NAMES` dict
- **manager.py**: Updated chain log string to reflect re-enabled analysis
- **jobs.py**: Created `morning_unified_analysis()` function with:
  - Watchlist gating via `_get_watchlist_ticker_map`
  - Calls `AIAnalysisService.run_unified_analysis()` for all watchlist tickers
  - D-06 retry: retries failed tickers once before DLQ
  - DLQ via `_dlq_failures` for permanently failed symbols
  - Standard job execution tracking (start/complete/fail)

### Task 2: Coverage Endpoint
- **schemas/analysis.py**: Added `CoverageResponse` model (analyzed_today, total_watchlist, coverage_pct, last_run_at, failed_today)
- **api/analysis.py**: Added `GET /analysis/coverage` endpoint querying:
  - `UserWatchlist` count for total
  - `AIAnalysis` count where type=UNIFIED and date=today
  - `AIAnalysis` max(created_at) for last_run_at
  - `FailedJob` unresolved entries for failed_today symbols

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] DLQ model name mismatch**
- **Found during:** Task 2
- **Issue:** Plan referenced `DeadLetterEntry` model, actual model is `FailedJob` in `app/models/failed_job.py`
- **Fix:** Used `FailedJob` with `ticker_symbol` and `failed_at` fields instead
- **Files modified:** backend/app/api/analysis.py

**2. [Rule 2 - Missing functionality] DLQ unresolved filter**
- **Found during:** Task 2
- **Issue:** Plan's DLQ query didn't filter by `resolved_at IS NULL`, would show already-resolved failures
- **Fix:** Added `FailedJob.resolved_at.is_(None)` filter to only show current failures
- **Files modified:** backend/app/api/analysis.py

## Verification

- ✅ `from app.scheduler.jobs import morning_unified_analysis` — OK
- ✅ `from app.scheduler.manager import _on_job_executed` — OK
- ✅ `/analysis/coverage` route registered in router
- ✅ 499 tests pass (0 failures)

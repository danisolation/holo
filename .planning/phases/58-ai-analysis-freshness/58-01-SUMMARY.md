---
phase: 58-ai-analysis-freshness
plan: 01
subsystem: scheduler, watchlist-api
tags: [morning-refresh, cron, ai-analysis, freshness]
dependency_graph:
  requires: [APScheduler CronTrigger, AIAnalysis model, watchlist API]
  provides: [morning AI refresh chain, last_analysis_at API field]
  affects: [scheduler/manager.py, scheduler/jobs.py, api/watchlist.py, schemas/watchlist.py]
tech_stack:
  added: []
  patterns: [morning chain via _on_job_executed with morning_ prefix job IDs]
key_files:
  created: []
  modified:
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
    - backend/app/api/watchlist.py
    - backend/app/schemas/watchlist.py
decisions:
  - "Morning chain reuses daily_price_crawl_for_exchange via thin wrapper for proper job ID routing"
  - "last_analysis_at uses MAX(created_at) across ALL analysis types (not just combined) to reflect morning chain freshness"
metrics:
  duration: ~4m
  completed: 2026-05-06
  tasks: 2/2
---

# Phase 58 Plan 01: Morning AI Refresh Chain + Watchlist Freshness Summary

Morning CronTrigger at 8:30 AM Mon-Fri running shortened pipeline (price→indicators→AI→signals) for watchlist tickers, plus last_analysis_at timestamp in watchlist API for frontend freshness display.

## Completed Tasks

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Add morning refresh jobs and chain routing | `09bcf69` | 4 morning job functions + CronTrigger + chain routing in _on_job_executed |
| 2 | Add last_analysis_at to watchlist API response | `5fae3f5` | WatchlistItemResponse schema + MAX(created_at) subquery in enriched query |

## Implementation Details

### Task 1: Morning Refresh Chain
- `morning_price_crawl_hose()` — thin wrapper delegating to `daily_price_crawl_for_exchange("HOSE")`
- `morning_indicator_compute()` — mirrors daily pattern with "morning_indicator_compute" job tracking
- `morning_ai_analysis()` — runs technical+fundamental (`analysis_type="both"`) with watchlist gating
- `morning_trading_signal_analysis()` — generates trading signals with watchlist gating
- CronTrigger registered at 8:30 AM Mon-Fri Asia/Ho_Chi_Minh
- Chain routing: morning_price_crawl_hose → morning_indicator_compute_triggered → morning_ai_analysis_triggered → morning_trading_signal_triggered (ends, no picks)
- All 4 morning job names added to `_JOB_NAMES` dict

### Task 2: Watchlist Freshness API
- Added `last_analysis_at: str | None = None` to `WatchlistItemResponse` schema
- Added `latest_created` subquery: `MAX(AIAnalysis.created_at)` grouped by ticker_id across ALL analysis types
- LEFT JOINed subquery to main enriched watchlist query
- Response includes ISO timestamp string or null

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

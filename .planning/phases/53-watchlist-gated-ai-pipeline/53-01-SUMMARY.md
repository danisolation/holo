---
phase: 53-watchlist-gated-ai-pipeline
plan: "01"
subsystem: backend-pipeline
tags: [ai-gating, watchlist, scheduler, gemini-optimization]
dependency_graph:
  requires: [UserWatchlist model, AIAnalysisService.analyze_all_tickers ticker_filter param]
  provides: [Watchlist-gated AI pipeline, Watchlist-gated pick generation]
  affects: [scheduler jobs, pick_service, ai_analysis_service]
tech_stack:
  added: []
  patterns: [watchlist-ticker-map-helper, empty-watchlist-guard, ticker_filter-passthrough]
key_files:
  created:
    - backend/tests/test_watchlist_gating.py
  modified:
    - backend/app/scheduler/jobs.py
    - backend/app/services/pick_service.py
    - backend/app/services/ai_analysis_service.py
    - backend/tests/test_ai_analysis_tiered.py
    - backend/tests/test_scheduler.py
decisions:
  - Helper _get_watchlist_ticker_map placed in jobs.py (all consumers in same file)
  - Empty watchlist returns status=skipped with normal return (preserves scheduler chain)
  - News crawl intentionally ungated (CafeF HTTP, no Gemini calls)
  - PickService accepts watchlist_symbols as set[str] (lightweight vs full ticker_filter dict)
metrics:
  duration: ~6m
  completed: 2026-05-04
---

# Phase 53 Plan 01: Watchlist-Gated AI Pipeline Summary

Gate all Gemini-powered AI analysis and daily picks to process only watchlist tickers (~15-30) instead of ~400 HOSE tickers, reducing API usage by ~70% via `_get_watchlist_ticker_map()` helper + `ticker_filter` passthrough to existing `analyze_all_tickers()` method.

## What Was Done

### Task 1: Implement watchlist gating across AI pipeline and pick service
**Commit:** `11478e1`

- Added `_get_watchlist_ticker_map(session)` helper to `jobs.py` — JOINs `UserWatchlist.symbol → Ticker.symbol` to produce `{symbol: ticker_id}` dict filtered by `is_active`
- Gated 4 AI analysis jobs (`daily_ai_analysis`, `daily_sentiment_analysis`, `daily_combined_analysis`, `daily_trading_signal_analysis`) with watchlist ticker_filter passthrough
- Gated `daily_pick_generation` with `watchlist_symbols` set extracted from ticker map
- Added `watchlist_symbols: set[str] | None = None` parameter to `PickService.generate_daily_picks()` with `Ticker.symbol.in_()` WHERE clause
- Removed broken `analyze_watchlisted_tickers()` method from `AIAnalysisService` (referenced non-existent `UserWatchlist.ticker_id` column)
- All 5 gated jobs return `status="skipped"` on empty watchlist (normal return preserves scheduler chain)

### Task 2: Write comprehensive tests for watchlist gating
**Commit:** `91a0223`

- Created `test_watchlist_gating.py` with 16 tests (251 lines) across 4 test classes:
  - `TestGetWatchlistTickerMap` (3 tests): helper returns correct map, empty dict, single ticker
  - `TestAIAnalysisGating` (8 tests): all 4 AI jobs pass filter + skip on empty watchlist
  - `TestPickGenerationGating` (2 tests): pick job passes symbols + skips on empty
  - `TestPickServiceWatchlistFilter` (3 tests): signature validation, default None, broken method removed
- Removed dead `TestAnalyzeWatchlistedTickers` class from `test_ai_analysis_tiered.py` (tested deleted method)
- Updated 3 existing scheduler tests to mock `_get_watchlist_ticker_map` and verify `ticker_filter` passthrough

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed dead tests for deleted analyze_watchlisted_tickers method**
- **Found during:** Task 2 (full test suite regression check)
- **Issue:** 3 tests in `test_ai_analysis_tiered.py` tested the now-removed `analyze_watchlisted_tickers()` method
- **Fix:** Removed the entire `TestAnalyzeWatchlistedTickers` class
- **Files modified:** `backend/tests/test_ai_analysis_tiered.py`
- **Commit:** `91a0223`

**2. [Rule 1 - Bug] Fixed 3 existing scheduler tests broken by watchlist gating**
- **Found during:** Task 2 (full test suite regression check)
- **Issue:** Old tests for `daily_ai_analysis`, `daily_sentiment_analysis`, `daily_combined_analysis` didn't mock `_get_watchlist_ticker_map`, causing `TypeError: 'coroutine' object is not iterable`
- **Fix:** Added `_get_watchlist_ticker_map` mock to each test and updated assertions to verify `ticker_filter` is passed
- **Files modified:** `backend/tests/test_scheduler.py`
- **Commit:** `91a0223`

## Requirements Satisfied

| ID | Description | Evidence |
|----|-------------|----------|
| WL-01 | AI analysis runs only on watchlist tickers | 4 AI jobs fetch watchlist map and pass as `ticker_filter` |
| WL-02 | Daily picks selected exclusively from watchlist | `generate_daily_picks()` filters signal query with `Ticker.symbol.in_()` |

## Pre-existing Test Failures (NOT caused by this plan)

- `test_combined_batch_response_validates` — CombinedBatchResponse schema missing 4 required fields
- `test_on_job_executed_chains_ai_after_indicators` — chains to discovery_scoring (Phase 52 change)
- `test_config_trading_signal_settings` — batch_size default 8 vs expected 15

## Self-Check: PASSED

- All 4 key files exist on disk
- Commit `11478e1` found (Task 1: implementation)
- Commit `91a0223` found (Task 2: tests)
- 16/16 new tests pass
- 3 pre-existing test failures unchanged (not caused by this plan)

---
phase: 72-n1-query-fixes-pagination
plan: 01
subsystem: backend-queries
tags: [performance, n+1, batch-queries, sqlalchemy]
dependency_graph:
  requires: []
  provides: [batch-rumor-summary, batch-context-builder]
  affects: [rumor-watchlist-api, ai-analysis-pipeline]
tech_stack:
  added: []
  patterns: [window-functions, group-by-aggregates, batch-fetch]
key_files:
  created: []
  modified:
    - backend/app/api/rumors.py
    - backend/app/services/analysis/context_builder.py
    - backend/app/services/ai_analysis_service.py
decisions:
  - Used DISTINCT ON with subquery for dominant direction (simpler than mode() aggregate)
  - Kept per-ticker methods intact for single-ticker on-demand analysis
  - Used ROW_NUMBER window functions for batch latest-per-ticker queries
metrics:
  duration: ~5min
  completed: 2026-05-06
  tasks_completed: 2
  tasks_total: 2
  test_results: 514 passed
---

# Phase 72 Plan 01: Batch Aggregate Queries — Eliminate N+1 Patterns

Replaced N+1 per-ticker query loops with batch GROUP BY aggregates in rumor summary and ROW_NUMBER window function batches in AI context builder, reducing query count from O(N) to O(1) with ticker count.

## Task Summary

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Batch aggregate rumor watchlist summary | bf1d754 | backend/app/api/rumors.py |
| 2 | Batch context builder methods | bf1d754 | backend/app/services/analysis/context_builder.py, backend/app/services/ai_analysis_service.py |

## Changes Made

### Task 1: Batch Aggregate Rumor Watchlist Summary (DB-N1-01)

Replaced the per-ticker loop in `get_watchlist_rumor_summary()` (which issued 3 queries × N tickers = 3N queries) with 3 batch queries:

- **Query A**: Rumor counts via `GROUP BY ticker_id` with `IN` clause
- **Query B**: Score averages (credibility, impact) via `GROUP BY ticker_id`
- **Query C**: Dominant direction via subquery with `DISTINCT ON` ordered by count DESC

Results assembled via dict lookups — single pass over watchlist items.

### Task 2: Batch Context Builder Methods (DB-N1-02)

Added 3 new batch methods to `ContextBuilder`:

- **`batch_get_technical_contexts`**: 3 queries total (indicators via ROW_NUMBER window, latest prices, volumes) for all tickers
- **`batch_get_fundamental_contexts`**: 1 query total (latest Financial per ticker via ROW_NUMBER window)
- **`batch_get_sentiment_contexts`**: 1 query total (all news titles, grouped in Python)

Wired into `AIAnalysisService`:
- `run_technical_analysis` → `batch_get_technical_contexts`
- `run_fundamental_analysis` → `batch_get_fundamental_contexts`
- `run_sentiment_analysis` → `batch_get_sentiment_contexts`

Original per-ticker methods preserved for `analyze_single_ticker` on-demand use.

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- ✅ No per-ticker await loops in rumor summary endpoint
- ✅ All 3 batch methods present in ContextBuilder
- ✅ All 3 batch methods called in AIAnalysisService
- ✅ 514 tests passed (0 failures)

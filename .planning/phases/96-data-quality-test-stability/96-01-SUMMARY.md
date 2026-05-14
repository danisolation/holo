---
phase: 96-data-quality-test-stability
plan: "01"
subsystem: backend-tests
tags: [test-fix, scheduler, mock-alignment]
dependency_graph:
  requires: []
  provides: [stable-scheduler-tests]
  affects: [backend/tests/test_scheduler.py]
tech_stack:
  patterns: [mock-at-import-source]
key_files:
  modified:
    - backend/tests/test_scheduler.py
decisions:
  - "Patch CafeFFinancialCrawler at app.crawlers.cafef_financial_crawler module (import source) since weekly_financial_crawl imports it inside function body"
metrics:
  duration: ~3min
  completed: 2025-05-14
---

# Phase 96 Plan 01: Fix Pre-existing Scheduler Test Failure Summary

**One-liner:** Fixed stale mock target in weekly_financial_crawl test — FinancialService → CafeFFinancialCrawler at import source module path.

## What Was Done

### Task 1: Fix test_weekly_financial_crawl_calls_service test ✅

The `test_weekly_financial_crawl_calls_service` test was mocking `app.scheduler.jobs.FinancialService` but the production code (`weekly_financial_crawl()`) now imports and uses `CafeFFinancialCrawler` from `app.crawlers.cafef_financial_crawler` inside the function body.

**Changes made to `backend/tests/test_scheduler.py`:**
1. Changed mock target from `app.scheduler.jobs.FinancialService` to `app.crawlers.cafef_financial_crawler.CafeFFinancialCrawler`
2. Updated variable names from `MockFinancialService`/`mock_service` to `MockCrawler`/`mock_crawler`
3. Updated assertion: `MockCrawler.assert_called_once_with(mock_session)` (verifies session passed to constructor)
4. Removed stale `period="quarter"` argument from `crawl_financials` assertion
5. Updated docstring to reference `CafeFFinancialCrawler`

### Task 2: Full test suite verification ✅

All 469 tests pass with 0 failures. No other stale mock issues found.

## Commits

| Task | Commit | Message |
|------|--------|---------|
| 1-2 | f971b45 | fix(96-01): fix scheduler test mock target for CafeFFinancialCrawler |

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- `pytest tests/test_scheduler.py -k test_weekly_financial_crawl -x -v` → 1 passed ✅
- `pytest tests/ --tb=short -q` → 469 passed, 0 failures ✅

## Self-Check: PASSED

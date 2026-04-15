---
phase: 01-data-foundation
plan: "02"
subsystem: data-crawling
tags: [vnstock, crawler, ticker-service, price-service, financial-service, async]
dependency_graph:
  requires: [01-01]
  provides: [VnstockCrawler, TickerService, PriceService, FinancialService]
  affects: [01-03]
tech_stack:
  added: [tenacity, vnstock, loguru]
  patterns: [asyncio.to_thread wrapping, batch processing with rate limiting, ON CONFLICT upsert]
key_files:
  created:
    - backend/app/crawlers/vnstock_crawler.py
    - backend/app/services/ticker_service.py
    - backend/app/services/price_service.py
    - backend/app/services/financial_service.py
    - backend/tests/test_crawler.py
    - backend/tests/test_services.py
  modified: []
decisions:
  - "asyncio.to_thread for all vnstock sync calls — prevents event loop blocking"
  - "tenacity retry with exponential backoff 2s-8s, 3 attempts — handles transient API failures"
  - "Batch size 50 with 2s delay — rate limiting for VCI API"
  - "ON CONFLICT upsert for all storage — idempotent re-crawls"
  - "adjusted_close=NULL — corporate actions deferred to Phase 2"
  - "_safe_decimal/_safe_int guards — handles malformed vnstock output gracefully"
metrics:
  duration: 5m
  completed: "2026-04-15T05:33:30Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 0
  test_count: 11
  test_pass: 11
---

# Phase 01 Plan 02: Data Crawling Services Summary

Async vnstock wrapper, ticker management (top 400 HOSE), OHLCV batch crawling with backfill, and financial ratio service — all with tenacity retry, rate limiting, and ON CONFLICT upsert for idempotency.

## What Was Built

### VnstockCrawler (backend/app/crawlers/vnstock_crawler.py)
Async wrapper around synchronous vnstock library. Every vnstock call goes through `asyncio.to_thread()` to prevent blocking FastAPI's event loop. Four methods: `fetch_listing`, `fetch_ohlcv`, `fetch_financial_ratios`, `fetch_industry_classification`. All decorated with `@retry(stop_after_attempt=3, wait_exponential(2s-8s))`.

### TickerService (backend/app/services/ticker_service.py)
Manages the active ticker list (top 400 HOSE stocks). `fetch_and_sync_tickers()` fetches HOSE listing + industry classification, upserts via `ON CONFLICT DO UPDATE`, and deactivates removed tickers. `get_active_symbols()` and `get_ticker_id_map()` provide data for other services.

### PriceService (backend/app/services/price_service.py)
OHLCV batch crawling with rate limiting. `crawl_daily()` fetches last 5 days for all active tickers. `backfill()` loads 1-2 years of historical data. `_crawl_batch()` processes in batches of 50 with 2s delay between tickers. Failed tickers are logged and skipped — batch continues. `_store_ohlcv()` uses `ON CONFLICT DO UPDATE` on `(ticker_id, date)`.

### FinancialService (backend/app/services/financial_service.py)
Financial ratio crawling. `crawl_financials()` fetches P/E, P/B, EPS, ROE, ROA, revenue, net_profit, revenue_growth, profit_growth, current_ratio, debt_to_equity for all active tickers. Handles vnstock's MultiIndex DataFrame output. `_safe_decimal()` and `_safe_int()` guard against malformed data. `ON CONFLICT DO UPDATE` on `(ticker_id, period)`.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | vnstock async crawler wrapper and ticker service | 9e38e01 | vnstock_crawler.py, ticker_service.py, test_crawler.py |
| 2 | Price service with batch crawling/backfill and financial service | bf9806d | price_service.py, financial_service.py, test_services.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed invalid `reraise` import from tenacity v9.x**
- **Found during:** Task 1
- **Issue:** Plan's exact code included `from tenacity import ... reraise` but `reraise` is not an importable name in tenacity v9.x; it's only a parameter of `@retry()`
- **Fix:** Removed `reraise` from import statement; `reraise=True` parameter was already correctly used in decorators
- **Files modified:** backend/app/crawlers/vnstock_crawler.py
- **Commit:** 9e38e01

## Test Results

```
11 passed in 14.00s
```

- 4 crawler tests: verify asyncio.to_thread wrapping for each fetch method
- 3 price service tests: batch processing, empty data skip, failure continuation
- 4 financial service tests: safe_decimal valid/NaN, safe_int valid/None

## Verification Results

- ✅ `VnstockCrawler().source` returns "VCI"
- ✅ `from app.services.price_service import PriceService` — imports OK
- ✅ `from app.services.financial_service import FinancialService` — imports OK
- ✅ 4x `await asyncio.to_thread` in vnstock_crawler.py (one per fetch method)
- ✅ `on_conflict_do_update` in both price_service.py and financial_service.py
- ✅ All 11 tests pass

## Self-Check: PASSED

- ✅ All 6 created files exist on disk
- ✅ Commit 9e38e01 found in git log
- ✅ Commit bf9806d found in git log

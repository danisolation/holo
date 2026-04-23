---
phase: quick
plan: 260423-feq
title: "Tier 2 Batch B: Market overview sorting, CafeF retry, realtime diff, home error states"
subsystem: backend-api, crawler, realtime, frontend-ui
tags: [api-params, tenacity-retry, diff-broadcast, error-handling]
dependency_graph:
  requires: []
  provides:
    - market-overview-sort-order-top
    - cafef-tenacity-retry
    - realtime-diff-detection
    - home-page-error-states
  affects:
    - /tickers/market-overview endpoint
    - CafeF crawler resilience
    - WebSocket broadcast efficiency
    - Home page UX on failure
tech_stack:
  added: []
  patterns:
    - tenacity retry with exponential backoff on CafeF crawler
    - Python-level sort/limit on computed fields (change_pct)
    - Dict equality diff detection for realtime price cache
key_files:
  created: []
  modified:
    - backend/app/api/tickers.py
    - backend/app/crawlers/cafef_crawler.py
    - backend/app/services/realtime_price_service.py
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/page.tsx
decisions:
  - "Python-level sorting instead of SQL for change_pct (computed field not in DB)"
  - "Removed SQL ORDER BY Ticker.symbol since Python sort handles all cases"
  - "tenacity retry placed on _fetch_news_raw (inside circuit breaker, not outside)"
  - "Full cache always updated regardless of diff; only broadcast is conditional"
metrics:
  duration: "3.4 minutes"
  completed: "2026-04-23"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 6
---

# Quick Task 260423-feq: Tier 2 Batch B Summary

Market overview API sorting/limiting, CafeF tenacity retry, realtime diff detection, and home page error states with retry buttons.

## Task Results

### Task 1: Backend — Market overview sort/order/top, CafeF retry, realtime diff
**Commit:** `3c0e625`

**1a. Market overview sort/order/top (`tickers.py`):**
- Added `sort` (change_pct|market_cap|symbol), `order` (desc|asc), `top` (1-500) query params
- Added ALLOWED_SORTS/ALLOWED_ORDERS sets with 400 validation
- Removed SQL ORDER BY — Python-level sort on computed items list with None-safe keys
- `top` slicing applied after sort

**1b. CafeF tenacity retry (`cafef_crawler.py`):**
- Added `_is_retryable()` predicate: True for TimeoutException, ConnectError, HTTPStatusError 5xx
- Decorated `_fetch_news_raw` with `@retry(stop_after_attempt(3), wait_exponential(2, min=2, max=8))`
- Retry sits inside circuit breaker (on raw method, not the breaker-wrapped method)
- Debug logging on each retry attempt with symbol and exception info

**1c. Realtime diff detection (`realtime_price_service.py`):**
- Compare each symbol's price dict against `_latest_prices` cache
- Always update full cache (for `get_latest_prices` endpoint)
- Only broadcast changed symbols; skip broadcast entirely if 0 changes
- Debug log: "N of M symbols changed — broadcasting/skipping"

### Task 2: Frontend — API params + home page error states
**Commit:** `fee5e52`

**2a. fetchMarketOverview API (`api.ts`):**
- New `MarketOverviewParams` interface with exchange/sort/order/top
- Builds URLSearchParams dynamically; backward compatible (no params = same as before)

**2b. useMarketOverview hook (`hooks.ts`):**
- Extended with optional `opts` parameter for sort/order/top
- QueryKey includes all params for proper React Query cache separation

**2c. Home page error states (`page.tsx`):**
- Market stats section: error card with "Không thể tải dữ liệu thị trường" + "Thử lại" retry button
- Heatmap section: added "Thử lại" retry button to existing error card
- Both use `refetch()` from React Query for retry

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- ✅ Backend imports compile: tickers, cafef_crawler, realtime_price_service
- ✅ Backend tests: 277 passed, 0 failed
- ✅ Frontend TypeScript: `tsc --noEmit` clean

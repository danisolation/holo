---
phase: quick
plan: 260423-fuy
title: "TIER 2 Batch C: News Skeleton, Tickers Pagination, Crawler Types, Exchange-Aware Realtime"
subsystem: backend-api, backend-crawlers, frontend-ui
tags: [pagination, skeleton-loader, type-safety, realtime-priority]
dependency_graph:
  requires: []
  provides:
    - "Paginated GET /tickers/ endpoint (limit/offset)"
    - "NewsCrawlResult TypedDict for type-safe crawler returns"
    - "Exchange-priority symbol sorting in RealtimePriceService"
    - "NewsListSkeleton component for article-shaped loading state"
  affects:
    - backend/app/api/tickers.py
    - backend/app/crawlers/types.py
    - backend/app/crawlers/cafef_crawler.py
    - backend/app/services/realtime_price_service.py
    - backend/app/config.py
    - frontend/src/components/news-list-skeleton.tsx
    - frontend/src/app/ticker/[symbol]/page.tsx
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
tech_stack:
  added: []
  patterns:
    - "TypedDict for structured crawler return types"
    - "Exchange-priority sorting with configurable order"
key_files:
  created:
    - backend/app/crawlers/types.py
    - frontend/src/components/news-list-skeleton.tsx
  modified:
    - backend/app/api/tickers.py
    - backend/app/crawlers/cafef_crawler.py
    - backend/app/services/realtime_price_service.py
    - backend/app/config.py
    - frontend/src/app/ticker/[symbol]/page.tsx
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
decisions:
  - "Used TypedDict (not dataclass) for crawler results — matches existing dict return pattern"
  - "Exchange map defaults to empty dict — populated lazily, unknown exchanges sort last"
  - "No wrapper model for paginated tickers — list[TickerResponse] kept simple"
metrics:
  duration: ~3min
  completed: "2026-04-23T04:31:21Z"
  tasks_completed: 2
  tasks_total: 2
---

# Quick Task 260423-fuy: TIER 2 Batch C Summary

Tickers pagination with limit/offset, NewsCrawlResult TypedDict for type-safe CafeF crawler returns, exchange-priority symbol sorting in realtime service, and article-shaped news skeleton loader on ticker page.

## Task Results

### Task 1: Backend — tickers pagination, crawler TypedDicts, exchange-aware realtime
**Commit:** `1b4c540`

- **Tickers pagination:** Added `limit` (1-500, default 100) and `offset` (>=0, default 0) query params to `GET /tickers/`. Applied `.offset(offset).limit(limit)` to SQLAlchemy query.
- **Crawler TypedDicts:** Created `backend/app/crawlers/types.py` with `NewsCrawlResult(TypedDict)`. Updated `CafeFCrawler.crawl_all_tickers()` return annotation from `-> dict` to `-> NewsCrawlResult`.
- **Exchange-aware realtime:** Added `realtime_priority_exchanges` config (HOSE > HNX > UPCOM). `RealtimePriceService` now sorts subscribed symbols by exchange priority before truncating to max. Added `set_exchange_map()` method for lazy population.
- **Tests:** All 277 backend tests pass.

### Task 2: Frontend — news skeleton loader + fetchTickers pagination params
**Commit:** `09c92a8`

- **NewsListSkeleton:** Created component with 5 article-shaped skeleton rows (title line + date line) matching NewsList layout.
- **Ticker page:** Replaced generic `<Skeleton className="h-[200px]" />` with `<NewsListSkeleton />` in news loading state.
- **fetchTickers:** Added optional `limit` and `offset` params. Backwards compatible — no args = no pagination params sent.
- **useTickers:** Added optional `limit` and `offset` params to hook signature and queryKey.
- **TypeScript:** Compiles clean, zero errors.

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

| Check | Result |
|-------|--------|
| Backend imports validate | ✅ types OK, realtime OK, tickers OK |
| Backend pytest (277 tests) | ✅ All pass |
| Frontend TypeScript --noEmit | ✅ Zero errors |

## Self-Check: PASSED

- [x] `backend/app/crawlers/types.py` — FOUND
- [x] `frontend/src/components/news-list-skeleton.tsx` — FOUND
- [x] Commit `1b4c540` — FOUND
- [x] Commit `09c92a8` — FOUND

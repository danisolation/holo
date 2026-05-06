---
phase: 72-n1-query-fixes-pagination
plan: "02"
subsystem: backend-api
tags: [pagination, performance, stable-ordering]
dependency_graph:
  requires: [72-01]
  provides: [paginated-watchlist, paginated-rumor-summary, paginated-rumor-posts]
  affects: [frontend-watchlist, frontend-rumors]
tech_stack:
  added: []
  patterns: [offset-limit-pagination, count-query, stable-ordering-tiebreaker]
key_files:
  created: []
  modified:
    - backend/app/schemas/watchlist.py
    - backend/app/schemas/rumor.py
    - backend/app/api/watchlist.py
    - backend/app/api/rumors.py
    - backend/tests/test_watchlist_sector.py
decisions:
  - "Used offset/limit pagination (matching existing PickHistoryListResponse pattern) over cursor-based"
  - "Added symbol ASC as tiebreaker for watchlist ordering to ensure deterministic pagination"
  - "posts_total added as optional field (None default) to RumorScoreResponse for backward compat"
  - "migrate endpoint returns PaginatedWatchlistResponse (page 1, per_page 50) instead of raw list"
metrics:
  duration: ~5min
  completed: "2026-05-06"
  tasks_completed: 1
  tasks_total: 1
  tests_passed: 514
  tests_failed: 0
---

# Phase 72 Plan 02: Pagination with Stable Ordering Summary

Offset/limit pagination with COUNT totals on watchlist GET, rumor summary, and rumor posts endpoints following PickHistoryListResponse pattern ({items, total, page, per_page}).

## Changes Made

### Schemas
- **PaginatedWatchlistResponse** added to `watchlist.py`: wraps `list[WatchlistItemResponse]` with total/page/per_page
- **PaginatedRumorSummaryResponse** added to `rumor.py`: wraps `list[WatchlistRumorSummary]` with total/page/per_page
- **posts_total** field added to `RumorScoreResponse` (optional, default None for backward compat)

### Watchlist GET (`/api/watchlist/`)
- Accepts `page` (default 1) and `per_page` (default 50, max 100)
- COUNT query added before main query for total
- Stable ordering: `ORDER BY created_at DESC, symbol ASC`
- Returns `PaginatedWatchlistResponse`

### Rumor Summary (`/api/rumors/watchlist/summary`)
- Accepts `page` (default 1) and `per_page` (default 50, max 100)
- COUNT query on UserWatchlist for total
- Stable ordering: `ORDER BY symbol ASC`
- Returns `PaginatedRumorSummaryResponse`

### Rumor Posts (`/api/rumors/{symbol}`)
- Accepts `page` (default 1) and `per_page` (default 20, max 50)
- COUNT query on Rumor for posts_total
- Existing `ORDER BY posted_at DESC` kept (already stable)
- `posts_total` included in response

### Migrate Endpoint
- Updated `POST /api/watchlist/migrate` response_model to `PaginatedWatchlistResponse` (returns page 1, per_page 50)

## Breaking Changes

**Frontend callers** that currently expect a raw list from:
- `GET /api/watchlist/` — must now access `.items` array
- `GET /api/rumors/watchlist/summary` — must now access `.items` array

These endpoints now return `{items: [...], total, page, per_page}` instead of a flat array.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test expecting list response**
- **Found during:** Task 1 verification
- **Issue:** `test_get_enriched_includes_sector_group` called `len(response)` on PaginatedWatchlistResponse
- **Fix:** Updated test to mock COUNT query (side_effect), assert on `response.items` and `response.total`
- **Files modified:** backend/tests/test_watchlist_sector.py
- **Commit:** 577b885

**2. [Rule 2 - Missing] Updated migrate endpoint response_model**
- **Found during:** Task 1 implementation
- **Issue:** `POST /migrate` called `_get_enriched_watchlist()` which now returns PaginatedWatchlistResponse, but response_model was still `list[WatchlistItemResponse]`
- **Fix:** Changed response_model to `PaginatedWatchlistResponse`
- **Files modified:** backend/app/api/watchlist.py
- **Commit:** 577b885

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 577b885 | Add pagination to watchlist, rumor summary, and rumor posts endpoints |

## Self-Check: PASSED

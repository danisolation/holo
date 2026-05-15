---
phase: 101-sector-analysis-backend
plan: "01"
subsystem: backend/services
tags: [sector-analysis, api, sql-window-functions, ttl-cache]
dependency_graph:
  requires: [100-01]
  provides: [GET /api/market/sectors, GET /api/market/sector-flow, SectorAnalysisService]
  affects: [frontend-sector-heatmap, frontend-rotation-analysis]
tech_stack:
  added: []
  patterns: [CTE-with-LAG-window-function, COALESCE-NULLIF-for-null-grouping, TTLCache-300s]
key_files:
  created:
    - backend/app/services/sector_analysis_service.py
    - backend/app/schemas/sector.py
    - backend/tests/test_sector_analysis_service.py
  modified:
    - backend/app/api/market.py
decisions:
  - Used CTE + LAG window function approach for prev_close computation (avoids self-join)
  - LAG(1), LAG(5), LAG(22) for today/7D/30D trading day offsets
  - COALESCE(NULLIF(sector, ''), 'Khác') handles both NULL and empty string sectors
  - Date range clamped to 365 days max per T-101-01 threat mitigation
metrics:
  duration: ~5min
  completed: 2026-05-15
  tasks_completed: 2
  tasks_total: 2
  test_count: 7
  files_created: 3
  files_modified: 1
---

# Phase 101 Plan 01: Sector Analysis Backend Summary

**SectorAnalysisService with CTE+LAG window functions computing avg % change (today/7D/30D) and net volume flow per sector, exposed via two cached GET endpoints on the market router.**

## Tasks Completed

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | SectorAnalysisService + schemas + tests (TDD) | b79a47c, e98b830 | Service with get_sector_performance/get_sector_flow, Pydantic schemas, 7 unit tests |
| 2 | API endpoints + TTLCache + router wiring | 7840b5b | GET /sectors, GET /sector-flow on market router, TTLCache 300s, 365-day clamp |

## Implementation Details

### SectorAnalysisService
- **get_sector_performance(start_date, end_date)**: Uses CTE with LAG(close, 1/5/22) window functions partitioned by ticker_id, then GROUP BY sector with AVG of % changes. Returns sector name, ticker_count, avg_change_today/7d/30d.
- **get_sector_flow(start_date, end_date)**: Uses CTE with LAG(close, 1) for direction detection, then SUM(volume * sign) for net_volume, separate buy/sell volume aggregation. Returns sector, date, net_volume, buy_volume, sell_volume.
- Null/empty sectors grouped as "Khác" via `COALESCE(NULLIF(Ticker.sector, ''), 'Khác')`.

### API Endpoints
- `GET /api/market/sectors` — default 30-day range, TTLCache(maxsize=8, ttl=300)
- `GET /api/market/sector-flow` — default 7-day range, TTLCache(maxsize=16, ttl=300)
- Both accept optional `start_date` and `end_date` query params with FastAPI date validation
- Date range clamped to max 365 days (threat mitigation T-101-01)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Security] Added date range clamping (T-101-01)**
- **Found during:** Task 2
- **Issue:** Threat model T-101-01 requires clamping date range to prevent heavy queries
- **Fix:** Added 365-day max clamp in both endpoints
- **Files modified:** backend/app/api/market.py

No other deviations — plan executed as written.

## Decisions Made

1. CTE approach chosen over subquery for LAG window functions — cleaner SQL, same performance
2. `func.nullif(Ticker.sector, '')` combined with `func.coalesce` handles both NULL and empty string sectors
3. `cast(Float)` on aggregation results for consistent JSON serialization

## Test Results

```
514 passed, 12 warnings in 33.26s
```

All 7 sector analysis tests pass. Full suite (514 tests) passes with 0 failures.

## Known Stubs

None — all data flows are wired to real database queries.

## Self-Check: PASSED

---
phase: 54-sector-grouping-heatmap-rework
plan: "01"
subsystem: backend-watchlist-api
tags: [sector-group, watchlist, api, orm, tdd]
dependency_graph:
  requires: []
  provides:
    - "UserWatchlist.sector_group ORM field"
    - "PATCH /api/watchlist/{symbol} endpoint"
    - "GET /api/tickers/sectors endpoint"
    - "POST /api/watchlist auto-populate sector_group"
    - "WatchlistUpdateRequest schema"
  affects:
    - "backend/app/models/user_watchlist.py"
    - "backend/app/schemas/watchlist.py"
    - "backend/app/api/watchlist.py"
    - "backend/app/api/tickers.py"
tech_stack:
  added: []
  patterns:
    - "Pydantic Field(max_length=100) for input validation at trust boundary"
    - "SQLAlchemy scalar_one_or_none() for ICB sector lookup"
    - "Route ordering in FastAPI to avoid path parameter conflicts"
key_files:
  created:
    - "backend/tests/test_watchlist_sector.py"
  modified:
    - "backend/app/models/user_watchlist.py"
    - "backend/app/schemas/watchlist.py"
    - "backend/app/api/watchlist.py"
    - "backend/app/api/tickers.py"
decisions:
  - "No Alembic migration needed — sector_group column already exists from migration 026"
  - "Sectors endpoint placed BEFORE /{symbol}/prices to avoid FastAPI path conflict"
  - "sector_group auto-populate uses user-provided > ICB lookup > None priority chain"
metrics:
  duration: "~4 minutes"
  completed: "2026-05-04T09:42:19Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 8
  tests_passing: 8
---

# Phase 54 Plan 01: Sector Group Backend API Summary

**One-liner:** ORM sector_group field + PATCH/POST/GET endpoints with ICB auto-populate and Pydantic max_length=100 validation

## What Was Done

### Task 1: Add sector_group to model, schemas, and API endpoints
**Commit:** `18b9c26` — feat(54-01)

1. **UserWatchlist model** — Added `sector_group: Mapped[str | None] = mapped_column(String(100), nullable=True)` to expose the existing DB column (migration 026) to the ORM.

2. **Pydantic schemas** — Added `sector_group` to `WatchlistItemResponse`, created `WatchlistUpdateRequest` with `Field(None, max_length=100)`, added optional `sector_group` to `WatchlistAddRequest`.

3. **Watchlist API** — Three changes:
   - `_get_enriched_watchlist()` now selects and returns `sector_group`
   - `add_to_watchlist()` POST handler auto-populates `sector_group` from `Ticker.sector` when not provided by user
   - New `PATCH /{symbol}` endpoint updates `sector_group` with 404 handling

4. **Tickers API** — Added `GET /tickers/sectors` endpoint returning distinct non-null ICB sector names from active tickers, alphabetically sorted. Placed before `/{symbol}/prices` to prevent FastAPI path conflict.

### Task 2: Backend unit tests for sector group endpoints
**Commit:** `8f30d7f` — test(54-01)

Created `backend/tests/test_watchlist_sector.py` (280 lines, 8 tests):
- **TestPatchWatchlistItem** (3 tests): update sector_group, 404 for nonexistent, clear with null
- **TestAddWithAutoSector** (2 tests): auto-populate from Ticker.sector, explicit value skips lookup
- **TestEnrichedWatchlistIncludesSector** (1 test): GET returns sector_group in each item
- **TestListSectors** (2 tests): sorted distinct results, null exclusion

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

| Check | Result |
|-------|--------|
| 8 sector tests pass | ✅ `pytest tests/test_watchlist_sector.py -x -v` — 8 passed |
| Model import check | ✅ `UserWatchlist.sector_group` attribute exists |
| Schema imports | ✅ `WatchlistUpdateRequest`, `WatchlistItemResponse` importable |
| Endpoint imports | ✅ `update_watchlist_item`, `list_sectors` callable |
| Watchlist regression | ✅ 39 tests pass across sector, gating, and api suites |
| Test file min lines | ✅ 280 lines (>80 required) |

## Known Stubs

None — all endpoints are fully wired to database operations.

## Threat Flags

None — all new endpoints match the plan's threat model. T-54-01 mitigated (Pydantic `max_length=100`), T-54-03 mitigated (same validation).

## Out-of-Scope Discoveries

Pre-existing test failure in `test_ai_analysis_service.py::TestSentimentSchema::test_combined_batch_response_validates` — `CombinedBatchResponse` schema missing required fields. Logged to `deferred-items.md`. Not related to sector changes.

## Self-Check: PASSED

All files exist, all commits verified, all content checks pass.

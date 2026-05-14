---
phase: 96-data-quality-test-stability
plan: 03
subsystem: backend-health
tags: [data-integrity, health-endpoint, data-quality]
dependency_graph:
  requires: []
  provides: [data-integrity-endpoint, DataIntegrityService]
  affects: [health-api]
tech_stack:
  added: []
  patterns: [service-pattern, async-sqlalchemy-queries, mock-based-testing]
key_files:
  created:
    - backend/app/services/data_integrity_service.py
    - backend/tests/test_data_integrity.py
  modified:
    - backend/app/api/health.py
decisions:
  - "Adapted for UserWatchlist symbol-based model (joins via Ticker.symbol instead of FK)"
  - "Used async_session context manager pattern matching existing health.py endpoints"
metrics:
  duration: ~3min
  completed: 2026-05-14
---

# Phase 96 Plan 03: Data Integrity Check Service Summary

DataIntegrityService with 3 checks (price gaps, duplicates, stale analysis) exposed at /health/data-integrity endpoint, with 6 passing unit tests.

## What Was Built

### DataIntegrityService (`backend/app/services/data_integrity_service.py`)
- `check_all()` — orchestrates all checks, returns structured report with status
- `check_price_gaps(max_gap_days=3)` — detects gaps > 3 calendar days in daily_prices for watchlist tickers (last 45 days, capped at 50 tickers, 20 results)
- `check_duplicates()` — finds duplicate (ticker_id, date) entries in daily_prices (limit 20)
- `check_stale_analysis()` — finds watchlist tickers with latest AI analysis > 48h old or no analysis (limit 20)

### Endpoint (`/health/data-integrity`)
- GET endpoint added to existing health router
- Uses `async_session` context manager (matching existing endpoint patterns)
- Returns JSON: `{status, total_issues, price_gaps, duplicates, stale_analysis}`

### Tests (`backend/tests/test_data_integrity.py`)
- 6 tests using AsyncMock sessions (no real DB needed)
- Covers: response structure, healthy status, duplicate detection, empty watchlist handling, stale analysis detection, issues_found status

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] UserWatchlist uses symbol column, not ticker_id FK**
- **Found during:** Task 1
- **Issue:** Plan assumed `UserWatchlist.ticker_id` but actual model stores `symbol` (String) with no FK to tickers
- **Fix:** Join via `Ticker.symbol == UserWatchlist.symbol` instead of using `ticker_id` directly
- **Files modified:** backend/app/services/data_integrity_service.py
- **Commit:** d21edfb

**2. [Rule 3 - Blocking] Endpoint uses async_session context manager, not Depends(get_session)**
- **Found during:** Task 2
- **Issue:** All existing health.py endpoints use `async with async_session() as session` pattern, not FastAPI Depends
- **Fix:** Followed existing pattern for consistency
- **Files modified:** backend/app/api/health.py
- **Commit:** d21edfb

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1+2 | d21edfb | feat(96-03): add data integrity check service and endpoint |

## Self-Check: PASSED

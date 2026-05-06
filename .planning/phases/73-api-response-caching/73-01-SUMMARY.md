---
phase: 73-api-response-caching
plan: 01
subsystem: backend-api
tags: [caching, performance, ttlcache]
dependency_graph:
  requires: []
  provides: [ttlcache-sectors, ttlcache-discovery, ttlcache-weekly-review, ttlcache-analysis-summary, ttlcache-watchlist-rumor-summary]
  affects: [tickers-api, discovery-api, goals-api, analysis-api, rumors-api]
tech_stack:
  added: []
  patterns: [ttlcache-check-work-store]
key_files:
  created: []
  modified:
    - backend/app/api/tickers.py
    - backend/app/api/discovery.py
    - backend/app/api/goals.py
    - backend/app/api/analysis.py
    - backend/app/api/rumors.py
    - backend/tests/test_watchlist_sector.py
decisions:
  - Cache keys use validated/clamped params only (T-73-03 mitigation)
  - Cache check placed before DB query in all endpoints for max benefit
  - analysis/summary caches before ticker lookup (invalid symbols won't be in cache, fall through to 404)
metrics:
  duration: ~5min
  completed: 2026-05-06
  tasks_completed: 2
  tasks_total: 2
  files_modified: 6
---

# Phase 73 Plan 01: TTLCache for Expensive Read Endpoints Summary

**One-liner:** In-memory TTLCache on 5 expensive read endpoints (sectors 300s, discovery 120s, weekly-review 300s, analysis/summary 60s, watchlist/rumor/summary 120s) using cachetools check→work→store pattern.

## What Was Done

Added `cachetools.TTLCache` instances to 5 read-heavy API endpoints, following the existing pattern established in `tickers.py` `market-overview` (line 148). Each endpoint now checks cache before executing DB queries and stores results before returning.

### Task 1: Sectors, Discovery, Goals/Weekly-Review

| Endpoint | Cache Variable | TTL | Maxsize | Cache Key |
|----------|---------------|-----|---------|-----------|
| `/tickers/sectors` | `_sectors_cache` | 300s | 1 | `"sectors"` (static) |
| `/discovery/` | `_discovery_cache` | 120s | 32 | `f"{sector}:{signal_type}:{min_score}:{limit}"` |
| `/goals/weekly-review` | `_weekly_review_cache` | 300s | 1 | `"latest"` (static) |

- **Commit:** `5eb2f43`

### Task 2: Analysis/Summary, Rumors/Watchlist/Summary

| Endpoint | Cache Variable | TTL | Maxsize | Cache Key |
|----------|---------------|-----|---------|-----------|
| `/analysis/{symbol}/summary` | `_summary_cache` | 60s | 128 | `symbol.upper()` |
| `/rumors/watchlist/summary` | `_watchlist_rumor_cache` | 120s | 8 | `f"{page}:{per_page}"` |

- **Commit:** `5eb2f43` (combined with Task 1)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed cache interference in sector tests**
- **Found during:** Task 1 verification (test run)
- **Issue:** `test_excludes_null_sectors` failed because `_sectors_cache` retained data from `test_returns_sorted_distinct_sectors` — both tests share the module-level cache.
- **Fix:** Added `_sectors_cache.clear()` before each test's `list_sectors()` call in `tests/test_watchlist_sector.py`.
- **Files modified:** `backend/tests/test_watchlist_sector.py`
- **Commit:** `5eb2f43`

## Verification

- ✅ All 5 cache instances importable with correct TTL values
- ✅ No import errors when starting backend (`from app.api.router import api_router`)
- ✅ 514 tests pass (0 failures)
- ✅ Cache pattern matches existing market-overview implementation

## Self-Check: PASSED

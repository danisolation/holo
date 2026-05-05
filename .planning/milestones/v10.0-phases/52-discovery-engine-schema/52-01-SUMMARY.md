---
phase: 52-discovery-engine-schema
plan: "01"
title: "Discovery Engine Schema & Scoring Service"
one_liner: "DiscoveryResult model + 6-dimension scoring engine with batch queries and 14-day retention"
completed: "2026-05-04T08:27:06Z"
duration: "~5 min"
tasks_completed: 2
tasks_total: 2
subsystem: backend
tags: [discovery, scoring, schema, alembic, tdd]
dependency_graph:
  requires: [technical_indicators, financials, daily_prices, tickers]
  provides: [discovery_results_table, DiscoveryService]
  affects: [scheduler-job-chain, discovery-api]
tech_stack:
  added: []
  patterns: [batch-query, upsert-on-conflict, pure-scoring-functions, tdd]
key_files:
  created:
    - backend/app/models/discovery_result.py
    - backend/alembic/versions/026_discovery_results.py
    - backend/app/services/discovery_service.py
    - backend/tests/test_discovery_service.py
  modified:
    - backend/app/models/__init__.py
key_decisions:
  - "Pure scoring functions at module level (not methods) for testability"
  - "3 batch queries total for ~400 tickers (indicators, financials, volumes) — no N+1"
  - "PostgreSQL INSERT ON CONFLICT DO UPDATE for idempotent upserts"
  - "MIN_DIMENSIONS=2 skip threshold — tickers with insufficient data excluded"
metrics:
  duration: "~5 min"
  completed: "2026-05-04"
  tasks: 2
  files: 5
  tests_added: 27
---

# Phase 52 Plan 01: Discovery Engine Schema & Scoring Service Summary

DiscoveryResult model + 6-dimension scoring engine with batch queries and 14-day retention

## What Was Done

### Task 1: Create Alembic migration and DiscoveryResult model
- Created `DiscoveryResult` SQLAlchemy model with 6 per-dimension score columns (rsi, macd, adx, volume, pe, roe), composite `total_score`, and `dimensions_scored`
- Created Alembic migration 026 that creates `discovery_results` table and adds `sector_group` nullable column to `user_watchlist`
- Registered model in `backend/app/models/__init__.py`
- **Commit:** `5b2ba9e`

### Task 2: Implement DiscoveryService with scoring engine (TDD)
- **RED:** Created 27 failing tests covering all 6 scoring functions + service cleanup/structure/skip logic → `be894ad`
- **GREEN:** Implemented `DiscoveryService` with:
  - 6 pure scoring functions (0-10 scale, None-safe)
  - 3 batch queries for all ~400 tickers (indicators, financials, volumes)
  - Bulk upsert via `INSERT ON CONFLICT DO UPDATE`
  - 14-day retention cleanup at start of each run
  - `MIN_DIMENSIONS=2` skip logic
- All 27 tests pass → `1690cb4`

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `5b2ba9e` | feat(52-01): create DiscoveryResult model and migration 026 |
| 2 | `be894ad` | test(52-01): add failing tests for DiscoveryService scoring engine |
| 3 | `1690cb4` | feat(52-01): implement DiscoveryService scoring engine |

## Verification Results

```
✓ from app.models.discovery_result import DiscoveryResult → "discovery_results"
✓ from app.services.discovery_service import DiscoveryService → importable
✓ score_rsi(25.0) == 10.0, score_rsi(None) is None
✓ score_macd(2.0) == 10.0, score_pe(-5.0) == 0.0
✓ 27/27 tests pass
```

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

All 4 created files exist. All 3 commit hashes verified in git log.

---
phase: 71-database-indexes-pool-tuning
plan: 01
title: "Database Indexes & Pool Tuning"
subsystem: database
tags: [performance, indexes, connection-pool, postgresql]
dependency_graph:
  requires: [migration-030]
  provides: [composite-indexes-5-tables, tuned-pool-config]
  affects: [query-latency, connection-stability]
tech_stack:
  added: []
  patterns: [composite-index-with-desc, pool-recycle]
key_files:
  created:
    - backend/alembic/versions/031_add_composite_indexes.py
  modified:
    - backend/app/database.py
decisions:
  - "Pool sized to 10+10=20 max, within Aiven ~25 limit"
  - "pool_recycle=1800 to prevent Aiven idle connection drops"
  - "Skipped daily_prices and rumors — already indexed"
metrics:
  duration: "~2 min"
  completed: "2026-05-06"
  tasks_completed: 1
  tasks_total: 1
  test_results: "514 passed, 0 failed"
requirements: [DB-IDX-01, DB-POOL-01]
---

# Phase 71 Plan 01: Database Indexes & Pool Tuning Summary

Composite indexes on 5 hot tables (technical_indicators, ai_analyses, daily_picks, weekly_reviews, job_executions) with DESC ordering for time-series queries, plus connection pool tuned to 10+10 with 30-min recycle for Aiven stability.

## Task Results

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Alembic migration + pool tuning | `64d378e` | `031_add_composite_indexes.py`, `database.py` |

## What Was Done

### Part A — Alembic Migration 031

Created `backend/alembic/versions/031_add_composite_indexes.py` with 5 composite indexes:

1. **ix_technical_indicators_ticker_date** — `technical_indicators(ticker_id, date DESC)`
2. **ix_ai_analyses_ticker_type_date** — `ai_analyses(ticker_id, analysis_type, analysis_date DESC)`
3. **ix_daily_picks_date_ticker** — `daily_picks(pick_date DESC, ticker_id)`
4. **ix_weekly_reviews_week_start** — `weekly_reviews(week_start DESC)`
5. **ix_job_executions_job_started** — `job_executions(job_id, started_at DESC)`

Downgrade drops all 5 in reverse order. Follows exact pattern from migration 027 (sa.text for DESC).

### Part B — Pool Tuning

Updated `backend/app/database.py`:
- `pool_size`: 5 → 10
- `max_overflow`: 3 → 10
- Added `pool_recycle=1800`
- `pool_pre_ping=True` retained

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- ✅ Alembic head revision = 031
- ✅ All 514 tests pass (0 failures)
- ✅ Migration chain unbroken (030 → 031)
- ✅ No duplicate indexes for daily_prices or rumors

## Self-Check: PASSED

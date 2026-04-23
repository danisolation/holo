---
phase: 45-coach-dashboard-pick-performance
plan: "01"
subsystem: backend/picks
tags: [pick-outcome, performance-stats, scheduler, api, migration]
dependency_graph:
  requires: [daily_picks table, DailyPrice model, Trade model, scheduler chain]
  provides: [PickOutcome enum, compute_pick_outcome, GET /picks/history, GET /picks/performance, daily_pick_outcome_check job]
  affects: [coach dashboard frontend (45-02), scheduler pipeline]
tech_stack:
  added: []
  patterns: [pure-function-testing, scheduler-job-chaining, paginated-api, left-join-subquery]
key_files:
  created:
    - backend/alembic/versions/021_pick_outcome_columns.py
    - backend/tests/test_pick_outcome.py
  modified:
    - backend/app/models/daily_pick.py
    - backend/app/services/pick_service.py
    - backend/app/schemas/picks.py
    - backend/app/api/picks.py
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
decisions:
  - "compute_pick_outcome placed in pick_service.py alongside other pure functions (not in model)"
  - "SL check before TP1 check — if both trigger on same candle, SL takes priority"
  - "Performance avg_risk_reward computed in Python (not SQL) due to division-by-zero edge cases"
  - "Streak treats expired picks as streak-breaker (current_streak=0 when most recent is expired)"
metrics:
  duration: ~6 minutes
  completed: 2026-04-23T10:45:54Z
  tasks_completed: 2
  tasks_total: 2
  test_count: 13
  files_changed: 8
---

# Phase 45 Plan 01: Pick Outcome Backend Summary

Complete backend for pick outcome tracking and performance analytics — migration 021, model updates, pure outcome computation with TDD, PickService methods, Pydantic schemas, two API endpoints, scheduler job chain, and 13 unit tests.

## Tasks Completed

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Migration 021 + DailyPick model + PickOutcome enum + compute_pick_outcome + tests (TDD) | 8bcd8af | Migration adds 6 columns + partial index; PickOutcome enum; pure function with 9 test cases |
| 2 | PickService methods + schemas + API endpoints + scheduler job chain | c5123ea | 3 PickService methods; 3 Pydantic schemas; 2 API endpoints; scheduler job + chain; 4 more tests |

## What Was Built

### Migration 021 — Pick Outcome Columns
- 6 new columns on `daily_picks`: `pick_outcome` (String, default "pending"), `days_held`, `hit_stop_loss`, `hit_take_profit_1`, `hit_take_profit_2`, `actual_return_pct`
- Partial index `ix_daily_picks_outcome_pending` for efficient scheduler queries on pending picks only

### DailyPick Model Updates
- `PickOutcome` enum: PENDING, WINNER, LOSER, EXPIRED
- 6 new mapped columns matching migration (all nullable or with server_default)

### Pure Function: compute_pick_outcome
- Module-level pure function in pick_service.py (follows existing pattern)
- Takes entry_price, stop_loss, take_profit_1, take_profit_2, daily_closes list
- Returns dict with outcome, days_held, hit flags, actual_return_pct
- Logic: close <= SL → LOSER; close >= TP1 → WINNER (check TP2 bonus); 10+ days → EXPIRED; else PENDING

### PickService Methods
- `compute_pick_outcomes()` — Batch processes pending picked picks, queries DailyPrice, updates outcomes. Idempotent (only touches pending). Skips "almost" picks.
- `get_performance_stats()` — Win rate, total realized P&L (SELL trades linked via daily_pick_id), avg R:R, current streak, counts.
- `get_pick_history(page, per_page, status)` — Upgraded from placeholder. Paginated, filterable by outcome status, includes has_trades boolean via LEFT JOIN subquery.

### Pydantic Schemas
- `PickHistoryItem` — Single pick with outcome data and has_trades flag
- `PickHistoryListResponse` — Paginated list response (items, total, page, per_page)
- `PickPerformanceResponse` — Win rate, total P&L, avg R:R, streak, counts

### API Endpoints
- `GET /api/picks/history?page=1&per_page=20&status=all` → `PickHistoryListResponse`
  - per_page capped at 100 (T-45-02 mitigation)
  - status validated against whitelist (T-45-01 mitigation)
- `GET /api/picks/performance` → `PickPerformanceResponse`

### Scheduler Job Chain
- `daily_pick_outcome_check` job function in jobs.py
- Chains after `daily_pick_generation_triggered` / `daily_pick_generation_manual` in manager.py
- Added to _JOB_NAMES dict for human-readable logging

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|------------|
| T-45-01 | Status param validated against enum whitelist {"all","winner","loser","expired","pending"} with 422 error |
| T-45-02 | per_page capped at 100 via FastAPI Query(le=100); page validated Query(ge=1) |
| T-45-03 | Division by zero protected in avg_risk_reward (entry_price != stop_loss filter + risk_pct > 0 check) |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- All 8 key files exist on disk ✓
- Commit 8bcd8af (Task 1) verified ✓
- Commit c5123ea (Task 2) verified ✓
- 13/13 tests passing ✓

---
phase: 23-position-monitoring-auto-track
plan: "02"
subsystem: scheduler
tags: [paper-trading, position-monitor, SL-TP, timeout, BEARISH, PT-04, PT-06]
dependency_graph:
  requires:
    - "Phase 22: PaperTrade model, calculate_pnl, apply_partial_tp, calculate_position_size"
    - "Plan 23-01: paper_trade_auto_track job, _JOB_NAMES pre-added, manager chain after trading_signal"
    - "Phase 2: DailyPrice model, daily_price_crawl_upcom chain point"
  provides:
    - "evaluate_long_position() and evaluate_bearish_position() pure functions"
    - "TIMEOUT_TRADING_DAYS constant (swing=15, position=60)"
    - "paper_position_monitor() async scheduler job"
    - "Chain: daily_price_crawl_upcom → paper_position_monitor (parallel)"
  affects:
    - "backend/app/services/paper_trade_service.py (extended)"
    - "backend/app/scheduler/jobs.py (new job function)"
    - "backend/app/scheduler/manager.py (new chain point)"
tech_stack:
  added: []
  patterns: ["pure-function evaluation", "batch query (2 queries)", "SL-first ambiguous bar", "gap-through at open"]
key_files:
  created:
    - backend/tests/test_position_monitor.py
  modified:
    - backend/app/services/paper_trade_service.py
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
key_decisions:
  - "SL checked FIRST on every bar — ambiguous bars resolve to SL (conservative)"
  - "Gap-through fills at open price, not at SL/TP level"
  - "BEARISH inverts all comparisons (high >= SL hit, low <= TP hit)"
  - "Timeout uses trading day count from daily_prices rows, not calendar days"
  - "Newly activated PENDING trades skip same-day evaluation (no lookahead)"
  - "Timeout query is per-trade (bounded by ~30 open positions max) vs batch complexity"
metrics:
  duration: "3 min"
  completed: "2026-04-20"
  tasks: 1
  tests: 21
  files_changed: 4
---

# Phase 23 Plan 02: Position Monitor Job Summary

Position evaluation engine with SL-first ambiguous bar rule, BEARISH-inverted comparisons, D+1 open activation, and trading-day timeout — 21 pure function tests, batch query pattern (2 queries)

## What Was Done

### Task 1: Position Evaluation Functions + Monitor Job + Manager Chain (TDD)

**RED:** Created `test_position_monitor.py` with 21 tests covering LONG evaluation (9 tests), BEARISH evaluation (7 tests), PENDING activation (2 tests), and timeout constants (3 tests). Tests failed because `evaluate_long_position`, `evaluate_bearish_position`, and `TIMEOUT_TRADING_DAYS` didn't exist.

**GREEN:** Implemented all production code:

1. **`paper_trade_service.py`** — Added two pure evaluation functions at end of file:
   - `evaluate_long_position()`: Checks SL first (gap-through at open, then low <= SL), then TP2 (PARTIAL_TP state only), then TP1 (ACTIVE state only)
   - `evaluate_bearish_position()`: Same priority but inverted comparisons (high >= SL, low <= TP)
   - `TIMEOUT_TRADING_DAYS = {"swing": 15, "position": 60}`

2. **`jobs.py`** — Added `paper_position_monitor()` async job:
   - Query 1: All open positions (PENDING, ACTIVE, PARTIAL_TP) in one batch
   - Query 2: Today's prices for all relevant tickers in one batch
   - PENDING activation: `bar.date > trade.signal_date` → set ACTIVE, overwrite entry_price with bar.open
   - ACTIVE/PARTIAL_TP: Dispatch to evaluate_long/bearish based on direction
   - PARTIAL_TP result → `apply_partial_tp()` from Phase 22
   - Terminal close (SL/TP2) → set exit_price, calculate P&L via `calculate_pnl()`
   - No SL/TP → check timeout via trading day count query
   - Follows `job_svc.start/complete/fail` pattern with try/except

3. **`manager.py`** — Added chain point inside `daily_price_crawl_upcom` handler, parallel with indicator_compute, price_alerts, and corporate_action_check

**Commits:**
- `cabcb7b` — RED: Failing tests for position evaluation
- `46ad3d1` — GREEN: Implementation + all 21 tests pass

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| SL checked first on every bar | Conservative: ambiguous daily bars (both SL and TP breached) resolve to SL loss |
| Gap-through fills at open price | Actual fill would be at market open, not at the SL/TP level |
| BEARISH inverts comparisons | high >= SL (price rises against), low <= TP (price drops in favor) |
| D+1 open activation, no same-day eval | Prevents lookahead bias — can't fill and evaluate on the bar you activated |
| Timeout counts trading days from DB | Uses `daily_prices` row count, not calendar days (handles holidays correctly) |
| Per-trade timeout query (N+1) | Bounded by ~30 max open positions; batch alternative adds significant complexity for minimal gain |
| Batch query pattern (2 queries) | Respects Aiven pool constraint (pool_size=5, max_overflow=3) |

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

```
tests/test_position_monitor.py — 21 passed (0.49s)
tests/test_paper_trade_auto_track.py — 7 passed (regression)
tests/test_paper_trade_pnl.py — 14 passed (regression)
Total: 42 passed, 0 failed
```

## Self-Check

Self-Check: PASSED — All 4 files found, both commits (cabcb7b, 46ad3d1) verified.

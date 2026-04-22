---
phase: 32-backtest-engine-portfolio-simulation
plan: "02"
subsystem: backtest-engine
tags: [backtest, gemini, engine, position-management, equity, checkpoint]
dependency_graph:
  requires: [32-01]
  provides: [backtest-engine, backtest-analysis-service]
  affects: [backtest-api]
tech_stack:
  added: []
  patterns: [date-aware-subclass, checkpoint-resume, D+1-entry, slippage-model]
key_files:
  created:
    - backend/app/services/backtest_analysis_service.py
    - backend/app/services/backtest_engine.py
    - backend/tests/test_backtest_engine.py
  modified:
    - backend/app/api/backtest.py
decisions:
  - BacktestAnalysisService overrides _store_analysis to use self.as_of_date (ignoring parent date.today())
  - Engine does NOT call fundamental or sentiment analysis (per RESEARCH.md — quarterly data same, historical sentiment unavailable)
  - Slippage applied via is_buy flag — LONG buys higher/sells lower, BEARISH direction inverted correctly
  - Timeout counts actual trading days via daily_prices COUNT query (not calendar days)
metrics:
  duration: ~8min
  completed: "2026-04-22T05:35:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 1
  test_count: 24
  test_pass: 24
---

# Phase 32 Plan 02: Backtest Engine Core & Analysis Service Summary

**One-liner:** Date-aware Gemini analysis subclass + full backtest engine with D+1 entry, slippage, position evaluation, equity tracking, checkpoint/resume, and cancel support

## What Was Built

### BacktestAnalysisService (294 lines)
Subclass of `AIAnalysisService` that makes all Gemini analysis date-aware for backtesting:
- **`_get_technical_context`**: Queries `TechnicalIndicator` and `DailyPrice` with `WHERE date <= as_of_date` — prevents lookahead bias on indicator data
- **`_get_combined_context`**: Reads from `backtest_analyses` table (NOT `ai_analyses`), filtered by `run_id` — prevents live data contamination
- **`_get_trading_signal_context`**: Date-filtered indicators/prices, 52-week high/low computed relative to `as_of_date` (NOT `date.today()`)
- **`_store_analysis`**: UPSERT into `backtest_analyses` with `run_id`, analysis_type as plain string (no CAST), uses `self.as_of_date` as analysis_date

All prompt builders, batch analyzers, and `_run_batched_analysis` inherited unchanged via polymorphism.

### BacktestEngine (590 lines)
Core engine class with `run(run_id)` as the main entry point:

1. **Date-first iteration**: Each session processes ALL tickers before advancing to next date
2. **AI pipeline per date**: `technical → combined → trading_signal` (no fundamental/sentiment per RESEARCH.md)
3. **D+1 activation**: Signals on day D create PENDING trades → activated at D+1 open price with slippage
4. **Position evaluation**: Reuses `evaluate_long_position`/`evaluate_bearish_position`/`apply_partial_tp`/`calculate_pnl` from paper_trade_service
5. **Timeout handling**: Counts actual trading days from `daily_prices` (not calendar days)
6. **Cash tracking**: Deducted on trade activation, returned on trade close (with slippage on all prices)
7. **Equity snapshots**: `cash + Σ(close_price × remaining_quantity)` per session, pending positions = 0 exposure
8. **Checkpoint**: Updates `last_completed_date` + `completed_sessions` atomically after each day
9. **Resume**: Skips dates ≤ `last_completed_date`, restores cash from last equity snapshot, reloads open positions from DB
10. **Cancel**: Checks `is_cancelled` flag per day, sets status=CANCELLED and stops gracefully
11. **Error handling**: Wraps entire run in try/except, sets FAILED status on unhandled exception

### API Wiring
Updated `POST /backtest/runs` to:
- Accept `BackgroundTasks` parameter (FastAPI DI)
- Launch `BacktestEngine().run(run.id)` via `bg.add_task()` after creating the run

### Tests (24 tests, all passing)
- `apply_slippage`: buy higher, sell lower, zero slippage, realistic VN prices
- Signal→trade: PENDING creation, D+1 activation rule, same-day rejection
- Position evaluation: SL close, TP1 partial, timeout trading day count
- Cash tracking: deduct on open, add on close
- Equity: cash + positions value, pending = 0
- Resume: skip completed dates, no-resume returns all
- Cancel: flag stops engine, no-flag continues
- Status: RUNNING→COMPLETED, RUNNING→CANCELLED, RUNNING→FAILED
- Class: instantiation without params, async run method exists

## Commits

| Commit | Type | Description |
|--------|------|-------------|
| `29511e1` | feat | BacktestAnalysisService — date-aware Gemini pipeline |
| `6c28f93` | test | Failing tests for BacktestEngine (TDD RED) |
| `51b8d7b` | feat | BacktestEngine core loop, positions, equity, checkpoint, cancel |

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

```
cd backend && python -m pytest tests/test_backtest_engine.py -x -v → 24 passed
cd backend && python -c "from app.services.backtest_analysis_service import BacktestAnalysisService" → OK
cd backend && python -c "from app.services.backtest_engine import BacktestEngine, apply_slippage" → OK
cd backend && python -m pytest tests/test_backtest_models.py tests/test_backtest_api.py tests/test_backtest_engine.py -x -v → 74 passed
```

## Artifact Line Counts

| File | Lines | Min Required | Status |
|------|-------|-------------|--------|
| `backend/app/services/backtest_analysis_service.py` | 294 | 150 | ✅ |
| `backend/app/services/backtest_engine.py` | 590 | 300 | ✅ |
| `backend/tests/test_backtest_engine.py` | 257 | 150 | ✅ |

## Self-Check: PASSED

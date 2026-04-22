---
phase: 32-backtest-engine-portfolio-simulation
plan: "01"
subsystem: backtest-engine
tags: [database, models, api, schemas, migration, backtest]
dependency_graph:
  requires: []
  provides: [BacktestRun, BacktestTrade, BacktestEquity, BacktestAnalysis, BacktestStatus, backtest-api-endpoints]
  affects: [backend/app/api/router.py, backend/app/models/__init__.py]
tech_stack:
  added: []
  patterns: [SQLAlchemy-mapped-column, Pydantic-v2-model-validator, computed-field, singleton-pattern]
key_files:
  created:
    - backend/app/models/backtest.py
    - backend/alembic/versions/014_backtest_tables.py
    - backend/app/schemas/backtest.py
    - backend/app/api/backtest.py
    - backend/tests/test_backtest_models.py
    - backend/tests/test_backtest_api.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/api/router.py
key_decisions:
  - "analysis_type in BacktestAnalysis uses String(20) not Enum — avoids enum dependency per RESEARCH.md A3"
  - "BacktestTrade reuses TradeStatus and TradeDirection enums from paper_trade.py — no duplication"
  - "Alembic migration reuses existing trade_status and trade_direction PostgreSQL types — does NOT recreate them"
  - "effective_stop_loss property tested via FakeTrade pattern to bypass SQLAlchemy descriptor protocol"
metrics:
  duration: "5 minutes"
  completed: "2026-04-22"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 50
  tests_passing: 50
  files_created: 6
  files_modified: 2
---

# Phase 32 Plan 01: Database Models, Schemas & API Endpoints Summary

4 SQLAlchemy models (BacktestRun/Trade/Equity/Analysis) with Alembic migration 014, Pydantic schemas with date-range and singleton validation, and 6 REST endpoints wired into the main router

## Task Completion

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Backtest database models + Alembic migration | `0cc6ed1` | backtest.py, __init__.py, 014_backtest_tables.py, test_backtest_models.py |
| 2 | Pydantic schemas + API endpoints + router wiring | `02f76b2` | backtest.py (schemas), backtest.py (api), router.py, test_backtest_api.py |

## What Was Built

### Database Models (backend/app/models/backtest.py)
- **BacktestStatus** enum: running, completed, cancelled, failed
- **BacktestRun**: date range, initial_capital (default 100M VND), slippage_pct (default 0.5%), status, progress tracking (total/completed sessions), is_cancelled flag, timestamps
- **BacktestTrade**: mirrors PaperTrade exactly with added run_id FK and backtest_analysis_id FK; reuses TradeStatus/TradeDirection enums; includes effective_stop_loss property
- **BacktestAnalysis**: mirrors AIAnalysis but with String(20) analysis_type (not Enum), unique constraint on (run_id, ticker_id, analysis_type, analysis_date)
- **BacktestEquity**: per-session equity snapshots with cash, positions_value, total_equity, daily/cumulative returns, unique constraint on (run_id, date)

### Alembic Migration (backend/alembic/versions/014_backtest_tables.py)
- Creates backtest_status PostgreSQL enum type
- Creates 4 tables: backtest_runs, backtest_analyses, backtest_trades, backtest_equity
- Reuses existing trade_status and trade_direction enum types (does NOT recreate)
- 5 indexes: trades(run_id), trades(status), trades(run_id, signal_date), analyses(run_id, analysis_date), equity(run_id, date)
- CHECK constraints: end_date > start_date, capital > 0, slippage 0-5, quantity > 0, confidence 1-10, etc.
- Clean downgrade drops tables in reverse FK order, then drops backtest_status type

### Pydantic Schemas (backend/app/schemas/backtest.py)
- **BacktestStartRequest**: validates start_date < end_date, range 20-180 days, capital > 0, slippage 0.0-5.0
- **BacktestRunResponse**: computed progress_pct field (completed/total × 100)
- **BacktestTradeResponse**: mirrors PaperTradeResponse with run_id and backtest_analysis_id
- **BacktestEquityResponse**: equity snapshot fields
- List wrapper schemas for trades and equity

### API Endpoints (backend/app/api/backtest.py)
1. **POST /api/backtest/runs** (201): Singleton enforcement (409 if running), counts trading days from daily_prices, creates run
2. **GET /api/backtest/runs/latest**: Most recent run or 404
3. **GET /api/backtest/runs/{id}**: Run details with progress
4. **POST /api/backtest/runs/{id}/cancel**: Sets is_cancelled=True on running backtest only
5. **GET /api/backtest/runs/{id}/trades**: Paginated trades with ticker symbol JOIN, optional status/direction filters
6. **GET /api/backtest/runs/{id}/equity**: Equity curve ordered by date ASC

### Router Wiring
- backtest_router added as 8th sub-router in api_router (after paper_trading_router)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed effective_stop_loss property test approach**
- **Found during:** Task 1 RED→GREEN
- **Issue:** `__new__` on SQLAlchemy mapped class doesn't initialize descriptor protocol state; both `__setattr__` and `__dict__` access trigger AttributeError
- **Fix:** Used FakeTrade class pattern to test property getter function directly via `BacktestTrade.effective_stop_loss.fget(FakeTrade())`
- **Files modified:** backend/tests/test_backtest_models.py
- **Commit:** 0cc6ed1

## Verification Results

All 4 plan verification checks passed:
1. ✅ `pytest tests/test_backtest_models.py tests/test_backtest_api.py -x -v` — 50 passed
2. ✅ Model imports succeed: `from app.models.backtest import BacktestRun, ...`
3. ✅ Schema validates: `BacktestStartRequest(start_date='2025-01-01', end_date='2025-06-01')`
4. ✅ Migration file exists: `backend/alembic/versions/014_backtest_tables.py`

## Self-Check: PASSED

- [x] backend/app/models/backtest.py exists
- [x] backend/app/models/__init__.py updated with backtest imports
- [x] backend/alembic/versions/014_backtest_tables.py exists
- [x] backend/app/schemas/backtest.py exists
- [x] backend/app/api/backtest.py exists
- [x] backend/app/api/router.py updated with backtest_router
- [x] backend/tests/test_backtest_models.py exists
- [x] backend/tests/test_backtest_api.py exists
- [x] Commit 0cc6ed1 exists
- [x] Commit 02f76b2 exists

---
phase: 107-dual-portfolio-backend
plan: 01
subsystem: simulator
tags: [dual-portfolio, ai-portfolio, user-portfolio, simulator, auto-trade]
dependency_graph:
  requires: []
  provides: [dual-portfolio-backend, ai-portfolio-auto-trade, portfolio-type-api-param]
  affects: [frontend-simulator-pages, phase-109-performance-comparison]
tech_stack:
  added: []
  patterns: [portfolio-name-routing, dual-portfolio-scoping]
key_files:
  created:
    - backend/alembic/versions/ad67af37a9a1_dual_portfolio_split.py
    - backend/tests/test_dual_portfolio.py
  modified:
    - backend/app/models/simulator_portfolio.py
    - backend/app/services/simulator_service.py
    - backend/app/services/auto_trade_service.py
    - backend/app/api/simulator.py
    - backend/app/schemas/simulator.py
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
decisions:
  - "Existing 'default' portfolio renamed to 'user' via migration (preserves trade history)"
  - "AI portfolio created fresh with 100M VND starting capital"
  - "Default portfolio_name='user' on all service methods for backward compatibility"
  - "Auto-buy job chains after accuracy_tracking, before sl_tp_check in scheduler pipeline"
  - "portfolio_type validation at API layer rejects invalid values with 400 (T-107-01)"
metrics:
  duration: ~5min
  completed: 2026-05-15
  tasks: 3/3
  files: 9
---

# Phase 107 Plan 01: Dual Portfolio Backend Summary

Split single simulator portfolio into independent AI and User portfolios with full API scoping and automated AI trade execution.

## One-liner
Dual AI/User portfolio split with independent cash balances, portfolio_type param on all endpoints, and server-side auto-buy scheduler job.

## What Was Done

### Task 1: Migration + SimulatorService dual portfolio support
- Created Alembic migration `ad67af37a9a1`: renames "default"→"user", creates "ai" portfolio with 100M VND, adds unique constraint on name
- Updated `SimulatorPortfolio` model: unique constraint on `name`, server_default changed to "user"
- Updated `get_or_create_portfolio(name="user")` — accepts portfolio name parameter
- All 8 service methods now accept `portfolio_name` parameter (default "user")
- Added `portfolio_type` field to `SimulatorTradeCreate` schema (validated: "ai"|"user")
- Added `PortfolioSummaryItem` and `PortfolioListResponse` schemas
- Added `get_all_portfolios_summary()` method for dual portfolio comparison
- **Commit:** `cdb6376`

### Task 2: AutoTradeService + scheduler auto-buy for AI portfolio
- `execute_ai_signals()` now passes `portfolio_name="ai"` to `create_trade`
- `execute_sell_signals()` now gets AI portfolio via `get_or_create_portfolio("ai")`
- `check_sl_tp_hits()` called with `portfolio_name="ai"` from scheduler
- Created `daily_simulator_auto_buy()` job that auto-executes ALL pending signals
- Scheduler chain updated: `accuracy_tracking → auto_buy → sl_tp_check → sector_intelligence`
- **Commit:** `fe1f532`

### Task 3: API endpoints + dual portfolio tests
- All GET endpoints accept `portfolio_type` query param (default "user")
- `POST /trades` uses `data.portfolio_type` from request body
- `POST /reset` requires `portfolio_type` param (no default — explicit choice required)
- Added `GET /simulator/portfolios` endpoint for both portfolio summaries
- `POST /check-auto-sell` scoped to AI portfolio
- Input validation via `_validate_portfolio_type()` helper (rejects non-"ai"/"user" with 400)
- Created 21 new tests covering schema validation, routing defaults, source inspection
- **Commit:** `0b3a05f`

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

- All 550 tests pass (33 simulator + dual portfolio tests, 517 existing tests)
- New tests verify: default parameters, schema validation, AI portfolio targeting, import availability

## Self-Check: PASSED

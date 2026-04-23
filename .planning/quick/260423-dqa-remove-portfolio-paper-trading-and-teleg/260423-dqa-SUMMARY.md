---
phase: quick
plan: 260423-dqa
subsystem: full-stack
tags: [removal, portfolio, paper-trading, telegram, consolidation]
dependency_graph:
  requires: [260423-d83-remove-entire-backtest-feature-backend-f]
  provides: [clean-codebase-without-portfolio-paper-trading-telegram]
  affects: [backend/app, frontend/src, frontend/e2e]
tech_stack:
  removed: [telegram-bot, portfolio-api, paper-trading-api, paper-trade-scheduler-jobs]
  patterns: [feature-removal, dead-code-cleanup]
key_files:
  modified:
    - backend/app/api/router.py
    - backend/app/models/__init__.py
    - backend/app/main.py
    - backend/app/scheduler/manager.py
    - backend/app/scheduler/jobs.py
    - backend/tests/test_resilience.py
    - backend/tests/test_scheduler.py
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/components/navbar.tsx
    - frontend/src/components/trading-plan-panel.tsx
    - frontend/src/app/ticker/[symbol]/page.tsx
    - frontend/e2e/api-smoke.spec.ts
    - frontend/e2e/page-smoke.spec.ts
    - frontend/e2e/navigation.spec.ts
    - frontend/e2e/visual-pages.spec.ts
    - frontend/e2e/visual-charts.spec.ts
    - frontend/e2e/visual-responsive.spec.ts
    - frontend/e2e/api-errors.spec.ts
    - frontend/e2e/fixtures/test-helpers.ts
    - frontend/e2e/fixtures/api-helpers.ts
  created:
    - backend/alembic/versions/018_drop_portfolio_paper_trading_tables.py
  deleted:
    - backend/app/api/portfolio.py
    - backend/app/api/paper_trading.py
    - backend/app/services/portfolio_service.py
    - backend/app/services/csv_import_service.py
    - backend/app/services/paper_trade_service.py
    - backend/app/services/paper_trade_analytics_service.py
    - backend/app/services/analytics_base.py
    - backend/app/services/exdate_alert_service.py
    - backend/app/services/health_alert_service.py
    - backend/app/schemas/portfolio.py
    - backend/app/schemas/paper_trading.py
    - backend/app/schemas/trade.py
    - backend/app/models/trade.py
    - backend/app/models/lot.py
    - backend/app/models/paper_trade.py
    - backend/app/models/simulation_config.py
    - backend/app/telegram/ (entire directory)
    - backend/tests/test_portfolio.py
    - backend/tests/test_csv_import.py
    - backend/tests/test_paper_trade_api.py
    - backend/tests/test_paper_trade_analytics.py
    - backend/tests/test_paper_trade_auto_track.py
    - backend/tests/test_paper_trade_model.py
    - backend/tests/test_paper_trade_pnl.py
    - backend/tests/test_paper_trade_state_machine.py
    - backend/tests/test_position_monitor.py
    - backend/tests/test_position_sizing.py
    - backend/tests/test_analytics_base.py
    - backend/tests/test_telegram.py
    - backend/tests/test_exdate_alerts.py
    - backend/tests/test_health_alerts.py
    - frontend/src/app/dashboard/portfolio/
    - frontend/src/app/dashboard/paper-trading/
    - frontend/src/components/portfolio-summary.tsx
    - frontend/src/components/holdings-table.tsx
    - frontend/src/components/allocation-chart.tsx
    - frontend/src/components/performance-chart.tsx
    - frontend/src/components/trade-form.tsx
    - frontend/src/components/trade-edit-dialog.tsx
    - frontend/src/components/trade-delete-confirm.tsx
    - frontend/src/components/trade-history.tsx
    - frontend/src/components/csv-import-dialog.tsx
    - frontend/src/components/csv-preview-table.tsx
    - frontend/src/components/paper-trading/ (entire directory)
    - frontend/src/components/shared/ (entire directory)
    - frontend/e2e/api-paper-trading.spec.ts
    - frontend/e2e/flow-paper-trading-dashboard.spec.ts
    - frontend/e2e/flow-settings.spec.ts
    - frontend/e2e/flow-ticker-to-trade.spec.ts
    - frontend/e2e/interact-pt-settings.spec.ts
    - frontend/e2e/interact-pt-tabs.spec.ts
    - frontend/e2e/interact-trades-table.spec.ts
decisions:
  - "Removed Follow button from trading-plan-panel.tsx (was creating paper trades)"
  - "Removed PTSignalOutcomes component from ticker detail page"
  - "Left telegram config vars in config.py as dead config (non-breaking)"
  - "Updated docstring in manager.py _on_job_error to say 'formerly sent Telegram notification'"
metrics:
  duration: "16 minutes"
  completed: "2026-04-23"
  files_deleted: 62
  files_modified: 22
  files_created: 1
  lines_removed: ~14700
---

# Quick Task 260423-dqa: Remove Portfolio, Paper Trading & Telegram Bot

Complete removal of Portfolio, Paper Trading, and Telegram Bot features from full-stack codebase as v7.0 consolidation. Alembic migration 018 drops 4 tables + 2 enums.

## Changes Made

### Backend (Task 1)

**Deleted (33 files):**
- 8 portfolio files (API, service, schema, model, tests)
- 17 paper trading files (API, services, schemas, models, 9 test files)
- 8 telegram/alert files (entire telegram directory + exdate/health alert services + tests)

**Edited (7 files):**
- `router.py`: Removed portfolio_router and paper_trading_router imports + include_router calls
- `models/__init__.py`: Removed Trade, Lot, PaperTrade, TradeStatus, TradeDirection, SimulationConfig imports
- `main.py`: Removed telegram_bot import, start/stop lifecycle. Scheduler still starts in non-test mode
- `scheduler/manager.py`: Removed MessageFormatter import, 6 dead job names from _JOB_NAMES, replaced _on_job_error with log-only version, removed 3 dead chains (paper_position_monitor, exdate_alert_check, signal_alert_check + paper_trade_auto_track), removed daily_summary_send and health_alert_check job registrations
- `scheduler/jobs.py`: Deleted 6 functions (daily_signal_alert_check, daily_summary_send, daily_exdate_alert_check, health_alert_check, paper_trade_auto_track, paper_position_monitor), removed unused Decimal import
- `test_resilience.py`: Deleted TestTelegramNotification + TestAlertJobsNeverRaise classes
- `test_scheduler.py`: Updated job count 9→7, removed daily_summary_send/health_alert_check assertions

**Created (1 file):**
- `backend/alembic/versions/018_drop_portfolio_paper_trading_tables.py`: Drops lots, trades, paper_trades, simulation_config tables + trade_status, trade_direction enums

### Frontend (Task 2)

**Deleted (29 files):**
- 2 page directories (portfolio, paper-trading)
- 10 portfolio components
- 11+ paper trading components (entire paper-trading/ directory)
- 2 shared components (generic-trades-table, equity-curve-chart) — no remaining consumers
- 7 E2E test files specific to paper trading

**Edited (14 files):**
- `api.ts`: Removed all portfolio types (15 interfaces) + fetch functions (10), all paper trading types (20+ interfaces) + fetch functions (15)
- `hooks.ts`: Removed all portfolio hooks (8) and paper trading hooks (14)
- `navbar.tsx`: Removed "Đầu tư" and "Paper Trading" nav links
- `trading-plan-panel.tsx`: Removed Follow button + useCreateManualFollow dependency
- `ticker/[symbol]/page.tsx`: Removed PTSignalOutcomes import and usage
- 8 E2E test files cleaned of paper-trading/portfolio test cases
- `test-helpers.ts` + `api-helpers.ts`: Removed dead routes and API methods

### Verification (Task 3)

- Fixed accidental function name collision in jobs.py (daily_corporate_action_check was wrongly renamed)
- All 270 backend tests pass
- Frontend TypeScript compiles clean (0 errors)
- Frontend production build succeeds
- Stale visual regression snapshots cleaned (5 PNG files, untracked)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed ticker detail page importing deleted PTSignalOutcomes**
- **Found during:** Task 2 (TypeScript verification)
- **Issue:** `frontend/src/app/ticker/[symbol]/page.tsx` imported PTSignalOutcomes from deleted paper-trading directory
- **Fix:** Removed import and `<PTSignalOutcomes>` JSX usage
- **Files modified:** `frontend/src/app/ticker/[symbol]/page.tsx`

**2. [Rule 3 - Blocking] Fixed trading-plan-panel.tsx importing deleted useCreateManualFollow**
- **Found during:** Task 2 (TypeScript verification)
- **Issue:** Component used useCreateManualFollow hook and Follow button that depends on paper trading API
- **Fix:** Removed hook import, removed Follow button from DirectionColumn, removed symbol prop
- **Files modified:** `frontend/src/components/trading-plan-panel.tsx`

**3. [Rule 1 - Bug] Fixed daily_corporate_action_check function name collision**
- **Found during:** Task 3 (backend test run)
- **Issue:** During removal of daily_summary_send and daily_exdate_alert_check, the replacement accidentally renamed daily_corporate_action_check to daily_hnx_upcom_analysis
- **Fix:** Restored correct function name
- **Files modified:** `backend/app/scheduler/jobs.py`
- **Commit:** c6a0c7a

## Known Stubs

None — this is a removal task. No stubs were introduced.

## Self-Check: PASSED

- [x] backend/alembic/versions/018_drop_portfolio_paper_trading_tables.py exists
- [x] Commit 464d18c (backend) exists
- [x] Commit 727fd53 (frontend) exists
- [x] Commit c6a0c7a (verification fix) exists
- [x] 270 backend tests pass
- [x] Frontend builds successfully
- [x] Zero code-level leftover references (only docstring mentions remain)

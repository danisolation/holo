---
phase: 48-backend-cleanup-scheduler-simplification
plan: 01
subsystem: backend/scheduler, backend/api, backend/models
tags: [scheduler, cleanup, hose-only, corporate-events-removal]
dependency_graph:
  requires: []
  provides: [hose-only-scheduler, clean-requirements, alembic-024]
  affects: [backend/app/scheduler, backend/app/api, backend/app/models, backend/requirements.txt]
tech_stack:
  added: []
  patterns: [hose-only-scheduler-chain, direct-chain-trading-signal-to-picks]
key_files:
  created:
    - backend/alembic/versions/024_drop_corporate_events.py
  modified:
    - backend/app/scheduler/manager.py
    - backend/app/scheduler/jobs.py
    - backend/app/api/router.py
    - backend/app/api/tickers.py
    - backend/app/models/__init__.py
    - backend/requirements.txt
    - backend/tests/test_scheduler.py
    - backend/tests/test_ticker_service_multi.py
  deleted:
    - backend/app/api/corporate_events.py
    - backend/app/models/corporate_event.py
    - backend/app/crawlers/corporate_event_crawler.py
    - backend/tests/test_corporate_actions.py
    - backend/tests/test_corporate_actions_enhancements.py
    - backend/tests/test_corporate_events_api.py
decisions:
  - Chain trigger rewired from UPCOM to HOSE — pipeline fires from daily_price_crawl_hose
  - trading_signal chains directly to pick_generation (hnx_upcom_analysis step removed)
  - VALID_EXCHANGES and ALLOWED_EXCHANGES restricted to HOSE only
  - python-telegram-bot dependency removed from requirements.txt
metrics:
  duration: 397s
  completed: 2026-04-24T06:46:47Z
  tasks_completed: 2
  tasks_total: 2
  files_changed: 14
---

# Phase 48 Plan 01: Backend Cleanup & Scheduler Simplification Summary

HOSE-only scheduler chain with corporate events subsystem fully removed and clean dependencies.

## What Was Done

### Task 1: Rewire scheduler chain to HOSE-only and remove dead job functions
**Commit:** `ee94aa8`

Rewired the entire scheduler pipeline:
- Chain trigger changed from `daily_price_crawl_upcom` → `daily_price_crawl_hose`
- Removed corporate_action_check parallel branch from chain
- Direct chain: `trading_signal → pick_generation` (removed `hnx_upcom_analysis` intermediate step)
- `EXCHANGE_CRAWL_SCHEDULE` reduced to `{"HOSE": {"hour": 15, "minute": 30}}`
- `VALID_EXCHANGES` changed to `("HOSE",)`
- Deleted `daily_corporate_action_check()` and `daily_hnx_upcom_analysis()` functions from jobs.py
- Removed 5 dead job IDs from `_JOB_NAMES` dict

### Task 2: Remove corporate events subsystem, clean deps, update tickers API, Alembic migration, update tests
**Commit:** `801fb66`

Complete corporate events subsystem removal:
- **Deleted files:** corporate_events.py (API), corporate_event.py (model), corporate_event_crawler.py (crawler), 3 test files
- **Router:** Removed corporate_events_router import and registration
- **Models:** Removed CorporateEvent from `__init__.py` and `__all__`
- **Tickers API:** `ALLOWED_EXCHANGES` changed to `{"HOSE"}`
- **Dependencies:** Removed `python-telegram-bot==22.7` from requirements.txt
- **Migration:** Created Alembic 024 — drops `corporate_events` table, deactivates HNX/UPCOM tickers via `UPDATE tickers SET is_active = false`
- **Tests:** Updated test_scheduler.py (8 registered jobs, HOSE-only chain assertions, removed stagger test), updated test_ticker_service_multi.py (removed HNX/UPCOM max ticker tests)

## Final Pipeline Chain

```
daily_price_crawl_hose → indicators → AI → news → sentiment → combined → trading_signal → pick_generation → pick_outcome_check → consecutive_loss_check
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed stale docstring in daily_price_crawl_for_exchange**
- **Found during:** Task 2 verification
- **Issue:** Docstring still referenced "staggered cron triggers: HOSE at 15:30, HNX at 16:00, UPCOM at 16:30"
- **Fix:** Updated to "Called by cron trigger: HOSE at 15:30 Mon-Fri"
- **Files modified:** backend/app/scheduler/jobs.py
- **Commit:** 801fb66

## Verification Results

| Check | Result |
|-------|--------|
| `from app.scheduler.manager import configure_jobs` | ✅ OK |
| `from app.api.router import api_router` | ✅ OK |
| `from app.models import Base` | ✅ OK |
| `VALID_EXCHANGES == ('HOSE',)` | ✅ OK |
| No `daily_corporate_action_check` in jobs.py | ✅ OK |
| No `daily_hnx_upcom_analysis` in jobs.py | ✅ OK |
| No corporate_event references in backend/app/ | ✅ OK |
| No python-telegram-bot in requirements.txt | ✅ OK |
| Migration 024 contains drop_table + ticker deactivation | ✅ OK |
| `pytest tests/test_scheduler.py` — 20 passed | ✅ OK |

## Self-Check: PASSED

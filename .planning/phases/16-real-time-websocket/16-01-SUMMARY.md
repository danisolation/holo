---
phase: 16
plan: 16-01
title: "Backend WebSocket — Connection Manager + VCI Polling + WS Endpoint"
subsystem: backend
tags: [websocket, real-time, scheduler, vci-polling]
dependency_graph:
  requires: []
  provides: [websocket-endpoint, connection-manager, realtime-price-service, market-hours-utility]
  affects: [scheduler-manager, vnstock-crawler, main-app]
tech_stack:
  added: []
  patterns: [connection-manager, asyncio-to-thread, interval-scheduler-jobs]
key_files:
  created:
    - backend/app/services/realtime_price_service.py
    - backend/app/ws/__init__.py
    - backend/app/ws/prices.py
    - backend/tests/test_realtime_prices.py
  modified:
    - backend/app/config.py
    - backend/app/crawlers/vnstock_crawler.py
    - backend/app/main.py
    - backend/app/scheduler/manager.py
    - backend/app/scheduler/jobs.py
    - backend/tests/test_scheduler.py
    - backend/tests/test_health_alerts.py
decisions:
  - "Trading module used for fetch_price_board (not Quote.history fallback) — confirmed available in vnstock 3.5.1"
  - "WebSocket route mounted directly on FastAPI app via app.websocket() decorator — not APIRouter"
  - "No retry/circuit-breaker on fetch_price_board — transient failures acceptable for 30s polling"
  - "Scheduler interval jobs run continuously — poll_and_broadcast skips VCI call when market closed or no subscribers"
metrics:
  duration: "9m"
  completed: "2026-04-17"
  tasks_completed: 2
  tasks_total: 2
  test_count: 37
  total_tests: 395
---

# Phase 16 Plan 01: Backend WebSocket — Connection Manager + VCI Polling + WS Endpoint Summary

**One-liner:** WebSocket infrastructure with ConnectionManager, VCI price_board polling via Trading module, market hours logic (9:00-11:30/13:00-14:45 VN), and APScheduler 30s/15s interval jobs.

## What Was Built

### T-16-01: Market hours utility + VCI price polling (TDD)
- **`realtime_price_service.py`**: `is_market_open()` and `get_market_session()` functions checking VN timezone weekday + two trading windows (morning 9:00-11:30, afternoon 13:00-14:45)
- **`RealtimePriceService`** class: in-memory `_latest_prices` cache, `poll_and_broadcast()` that fetches VCI then broadcasts to ConnectionManager, `get_latest_prices(symbols)` for cache reads
- **`vnstock_crawler.py`**: Added `fetch_price_board(symbols)` using `vnstock.explorer.vci.trading.Trading.price_board()` via `asyncio.to_thread()`, returns `dict[str, dict]` with price/change/change_pct/volume
- **`config.py`**: Added `realtime_poll_interval: int = 30` and `realtime_max_symbols: int = 50`
- **23 tests**: market hours boundaries, session names, price board parsing, cache update, broadcast, empty symbols, max symbols limit

### T-16-02: WebSocket connection manager + endpoint (TDD)
- **`ws/prices.py`**: `ConnectionManager` class with `connect()`, `disconnect()`, `subscribe()`, `get_all_subscribed_symbols()`, `broadcast()` (filtered per-client), `send_heartbeat()`, `send_market_status()`
- **WebSocket endpoint** at `/ws/prices`: accepts connection, listens for `{"type": "subscribe", "symbols": [...]}`, validates max 50 symbols, normalizes to uppercase
- **`main.py`**: WebSocket route wired via `app.websocket("/ws/prices")(websocket_prices)`
- **`scheduler/manager.py`**: Added `realtime_price_poll` (IntervalTrigger 30s) and `realtime_heartbeat` (IntervalTrigger 15s) jobs with IDs in `_JOB_NAMES`
- **`scheduler/jobs.py`**: `realtime_price_poll()` sends market_status then conditionally polls VCI; `realtime_heartbeat()` sends heartbeat to all clients
- **14 new tests**: ConnectionManager subscribe/broadcast/heartbeat/market_status/dead connection handling, endpoint route exists, scheduler job registration
- **Updated tests**: `test_scheduler.py` (7→9 jobs), `test_health_alerts.py` (mock settings fix)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated test_scheduler job count assertion**
- **Found during:** Task 2
- **Issue:** `test_configure_jobs_registers_six_jobs` asserted 7 jobs, now 9 with 2 new realtime jobs
- **Fix:** Updated assertion from 7 to 9, added realtime job ID checks
- **Files modified:** backend/tests/test_scheduler.py
- **Commit:** c6884d5

**2. [Rule 1 - Bug] Fixed health_alerts test mock settings**
- **Found during:** Task 2
- **Issue:** `test_scheduler_registers_job` patches `settings` globally but didn't mock `realtime_poll_interval`, causing `MagicMock` to be passed to `IntervalTrigger(seconds=...)` which expects an int
- **Fix:** Added `mock_settings.realtime_poll_interval = 30` to the test
- **Files modified:** backend/tests/test_health_alerts.py
- **Commit:** c6884d5

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| T-16-01 | 3ff7d22 | Market hours utility + VCI price polling service |
| T-16-02 | c6884d5 | WebSocket connection manager + endpoint + scheduler jobs |

## Self-Check: PASSED

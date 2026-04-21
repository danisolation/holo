---
phase: 27
plan: 2
subsystem: backend
tags: [test-infrastructure, config, lifespan, test-mode]
dependency_graph:
  requires: []
  provides: [holo_test_mode setting, guarded lifespan]
  affects: [backend/app/config.py, backend/app/main.py]
tech_stack:
  added: []
  patterns: [environment-variable guard, conditional startup]
key_files:
  created: []
  modified:
    - backend/app/config.py
    - backend/app/main.py
decisions:
  - "holo_test_mode defaults to False — normal operation is never affected"
  - "Guard both startup and shutdown blocks — don't stop what wasn't started"
  - "Log explicitly when test mode is active for debugging visibility"
metrics:
  duration: "2m 14s"
  completed: "2026-04-21"
  tasks: 2
  files: 2
---

# Phase 27 Plan 2: HOLO_TEST_MODE Environment Guard Summary

**One-liner:** Added `holo_test_mode: bool = False` to backend Settings and guarded APScheduler + Telegram bot startup/shutdown in lifespan, so E2E test runs don't trigger scheduled jobs or bot connections.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add holo_test_mode setting to Settings class | `0ac1de6` | backend/app/config.py |
| 2 | Guard scheduler and telegram startup with test mode check | `bca431c` | backend/app/main.py |

## What Was Done

### Task 1: holo_test_mode setting
Added `holo_test_mode: bool = False` field to the `Settings` class in `backend/app/config.py`, placed after `trading_signal_max_tokens`. The field reads from `HOLO_TEST_MODE` env var via pydantic-settings. Default is `False` so production/dev operation is completely unaffected.

### Task 2: Lifespan guards
Modified `backend/app/main.py` lifespan function:
- Added `from app.config import settings` import
- **Startup:** Wrapped `configure_jobs()`, `scheduler.start()`, and `telegram_bot.start()` inside `if not settings.holo_test_mode` block. When test mode is active, logs "HOLO_TEST_MODE=true — skipping scheduler and Telegram bot" instead.
- **Shutdown:** Wrapped `telegram_bot.stop()` and `scheduler.shutdown()` inside `if not settings.holo_test_mode` — avoids stopping services that were never started. `engine.dispose()` always runs regardless (DB cleanup is needed even in test mode).

## Verification

- `backend/app/config.py` contains `holo_test_mode: bool = False` ✅
- `backend/app/main.py` contains `from app.config import settings` ✅
- `backend/app/main.py` contains 2 occurrences of `settings.holo_test_mode` guard (startup + shutdown) ✅
- `backend/app/main.py` contains "HOLO_TEST_MODE=true — skipping scheduler and Telegram bot" log message ✅
- Root endpoint `@app.get("/")` unchanged — still returns `{"status": "ok", "service": "holo"}` ✅
- Backend tests pass: 26 passed (test_api.py + test_trading_signal_schemas.py) ✅

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

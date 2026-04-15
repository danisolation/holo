---
phase: 04-telegram
plan: "03"
title: "AlertService, Scheduler Jobs, Bot Lifecycle Integration"
subsystem: telegram-bot
tags: [alerts, scheduler, bot-lifecycle, signal-detection, price-alerts, daily-summary]
dependency_graph:
  requires: [04-01, 04-02]
  provides: [alert-service, signal-alerts, price-alerts, daily-summary-job, bot-lifecycle]
  affects: [scheduler-manager, main-lifespan]
tech_stack:
  added: []
  patterns: [lazy-import-circular-avoidance, parallel-job-chaining, exception-swallowing-alerts]
key_files:
  created:
    - backend/app/telegram/services.py
    - backend/tests/test_telegram.py
  modified:
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
    - backend/app/main.py
    - backend/tests/test_scheduler.py
decisions:
  - "Alert jobs swallow all exceptions — never block data pipeline (D-3.4)"
  - "Price alert check chains as parallel branch from price_crawl (alongside indicators)"
  - "Signal alert check chains sequentially after combined analysis (end of pipeline)"
  - "daily_summary_send uses CronTrigger at 16:00 Mon-Fri (not event-chained)"
  - "AlertService uses lazy imports for telegram_bot to avoid circular dependencies"
metrics:
  duration: "4m"
  completed: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  test_count: 96
  test_pass: 96
  files_changed: 6
---

# Phase 4 Plan 3: AlertService, Scheduler Jobs, Bot Lifecycle Integration Summary

AlertService with signal change detection (today vs yesterday combined signal), price threshold checking (mark triggered + notify), and daily summary generation; 3 new scheduler jobs chained into pipeline with exception-swallowing semantics; Telegram bot lifecycle integrated into FastAPI lifespan.

## What Was Built

### AlertService (`backend/app/telegram/services.py`)
- `check_signal_changes()` — queries watched tickers' combined signals for today vs yesterday, sends Telegram alert on change
- `check_price_alerts()` — queries active (non-triggered) price alerts, checks latest close against threshold, marks triggered + sends notification
- `build_daily_summary()` — builds dict with top 5 movers (by absolute % change), watchlist signal changes, and strong recommendations (mua >= 7 score)
- `send_daily_summary()` — calls build + format + send as a single operation for the scheduled job

### Scheduler Jobs (`backend/app/scheduler/jobs.py`)
- `daily_signal_alert_check()` — chains after combined analysis, calls AlertService
- `daily_price_alert_check()` — chains after price crawl, calls AlertService
- `daily_summary_send()` — cron at 16:00, calls AlertService
- All 3 jobs: own session, try/except, **never re-raise** (unlike data pipeline jobs)

### Scheduler Manager (`backend/app/scheduler/manager.py`)
- Extended `_on_job_executed` with combined→signal_alert chain and price_crawl→price_alert parallel branch
- Added `daily_summary_send` cron job registration (Mon-Fri 16:00 Asia/Ho_Chi_Minh)
- Full pipeline chain: `price_crawl → [indicators → AI → news → sentiment → combined → signal_alerts] + [price_alerts]`

### FastAPI Lifespan (`backend/app/main.py`)
- `telegram_bot.start()` in startup (after scheduler)
- `telegram_bot.stop()` in shutdown (before scheduler)
- Bot's start() handles missing config gracefully (logs warning, returns)

### Tests (`backend/tests/test_telegram.py`)
- 25 new tests across 5 test classes
- TestMessageFormatter: 13 tests for all formatter methods
- TestAlertService: 3 tests for edge cases (no chat_id, empty summary)
- TestTelegramBot: 4 tests for configuration states and send failure
- TestSchedulerChaining: 4 tests for new chain behavior
- TestHandlerRegistration: 1 test for all 7 command handlers

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated existing scheduler tests for new behavior**
- **Found during:** Task 2
- **Issue:** `test_configure_jobs_registers_three_jobs` asserted exactly 3 jobs (now 4 with daily_summary_send); `test_on_job_executed_chains_indicators_after_price_crawl` asserted `assert_called_once()` (now 2 calls with price_alert parallel branch); `test_configure_jobs_still_registers_original_jobs` needed daily_summary_send assertion
- **Fix:** Updated test assertions to reflect new job count (4) and dual-chain behavior from price_crawl
- **Files modified:** `backend/tests/test_scheduler.py`
- **Commit:** e0ef0b7

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Alert jobs swallow exceptions | D-3.4: Telegram failures must never block the data pipeline |
| Price alerts parallel-branch from price_crawl | price_crawl already chains to indicators; price alerts can run independently |
| Signal alerts sequential after combined | Signal detection needs combined analysis data to compare signals |
| Lazy imports for telegram_bot in services | Avoids circular: services.py → bot.py → handlers.py → services.py |

## Known Stubs

None — all code paths are wired to real AlertService logic, formatter output, and telegram_bot.send_message.

## Self-Check: PASSED

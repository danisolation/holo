---
phase: 14-corporate-actions-enhancements
plan: 02
subsystem: backend
tags: [exdate-alerts, telegram, scheduler, corporate-actions]
dependency_graph:
  requires: [RIGHTS_ISSUE-event-type, alert_sent-column]
  provides: [ExDateAlertService, exdate-alert-formatter, exdate-alert-job-chain]
  affects: [scheduler-manager, telegram-formatter, scheduler-jobs]
tech_stack:
  added: []
  patterns: [TDD-red-green, never-raises-alert, job-chaining, lazy-import]
key_files:
  created:
    - backend/app/services/exdate_alert_service.py
    - backend/tests/test_exdate_alerts.py
  modified:
    - backend/app/telegram/formatter.py
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
decisions:
  - "Lot model (remaining_quantity > 0) used for held tickers instead of Trade CASE/SUM"
  - "Lazy-import telegram_bot to avoid circular dependency"
  - "5 calendar day window covers 3 business days worst-case (Friday start)"
metrics:
  duration: ~4m
  completed: "2026-04-17T19:58:00Z"
  tests_added: 18
  tests_total: 39
  files_changed: 5
requirements: [CORP-07]
---

# Phase 14 Plan 02: Ex-Date Telegram Alert Service Summary

**One-liner:** ExDateAlertService with Telegram alerts for upcoming ex-dates on watchlisted/held tickers, scheduler chain from corporate_action_check, Vietnamese formatter

## What Was Built

### ExDateAlertService
- `check_upcoming_exdates(chat_id=None)` — finds corporate events with ex_date within 3 business days
- Filters to tickers in user's watchlist (UserWatchlist) OR with open positions (Lot.remaining_quantity > 0)
- Weekday filtering (Mon-Fri only, skips weekend ex-dates)
- `alert_sent=True` dedup: each event alerts exactly once (T-14-04 mitigation)
- Never raises — catches all exceptions, returns partial count (T-14-06 mitigation)
- Detail line: dividend amount for cash dividends (`2,000đ/cp`), ratio for stock events (`35:100`)

### MessageFormatter.exdate_alert
- Vietnamese HTML alert with event type label and ex-date
- `EVENT_TYPE_LABELS` dict: CASH_DIVIDEND→"Cổ tức tiền mặt", STOCK_DIVIDEND→"Cổ tức cổ phiếu", BONUS_SHARES→"Thưởng cổ phiếu", RIGHTS_ISSUE→"Phát hành quyền mua"
- Optional detail line (amount or ratio)

### Scheduler Job + Chain
- `daily_exdate_alert_check()` job in jobs.py — never-raises pattern matching daily_signal_alert_check
- Chain: `daily_corporate_action_check_triggered` → `daily_exdate_alert_check_triggered`
- `_JOB_NAMES` updated with "Daily Ex-Date Alert Check"
- Chain log message updated

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1-RED | Failing tests for service + formatter | `b0d3939` | tests/test_exdate_alerts.py |
| 1-GREEN | ExDateAlertService + formatter | `c02e500` | exdate_alert_service.py, formatter.py, tests |
| 2-RED | Failing tests for scheduler wiring | `e246e7b` | tests/test_exdate_alerts.py |
| 2-GREEN | Job function + chain integration | `939aec0` | jobs.py, manager.py, tests |

## Test Results

**18 new tests** across 4 test classes:

- `TestExdateAlertFormatter` (8): cash/stock/bonus/rights labels, unknown fallback, HTML structure, detail included/omitted
- `TestExDateAlertService` (5): no chat_id returns 0, returns count, never raises, dedup, explicit chat_id
- `TestExDateAlertServiceEventTypeLabels` (2): all 4 types present, Vietnamese labels correct
- `TestExDateAlertScheduler` (3): job callable, _JOB_NAMES entry, chain source verification

**21 existing scheduler tests** all pass (zero regressions).

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **Lot model for held tickers**: Used `Lot.remaining_quantity > 0` grouped by ticker_id instead of Trade CASE/SUM. Simpler query, directly tracks open positions.
2. **Lazy-import telegram_bot**: Global module-level import with `_get_bot()` helper to avoid circular dependency between services and bot modules.
3. **5 calendar day window**: Covers worst-case 3 business days (Friday start → Mon/Tue/Wed of next week).

## Self-Check: PASSED

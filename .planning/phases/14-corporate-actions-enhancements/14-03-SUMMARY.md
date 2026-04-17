---
phase: 14-corporate-actions-enhancements
plan: 03
subsystem: backend
tags: [corporate-events, calendar-api, adjusted-price, api-endpoint]
dependency_graph:
  requires: [RIGHTS_ISSUE-event-type, CorporateEvent-model]
  provides: [corporate-events-api, adjusted-price-toggle]
  affects: [router, tickers-api, frontend-calendar, frontend-chart]
tech_stack:
  added: []
  patterns: [TDD-red-green, extract-based-date-filter, strict-param-validation]
key_files:
  created:
    - backend/app/api/corporate_events.py
    - backend/tests/test_corporate_events_api.py
  modified:
    - backend/app/api/router.py
    - backend/app/api/tickers.py
decisions:
  - "extract() for SQL month filtering — prevents SQL injection via string concat (T-14-07)"
  - "adjusted=true default for backward compatibility — existing consumers unaffected"
  - "±90 day default range when no month param — balances past events and upcoming"
metrics:
  duration: ~3m
  completed: "2026-04-17T13:05:00Z"
  tests_added: 15
  tests_total: 30
  files_changed: 4
requirements: [CORP-08, CORP-09]
---

# Phase 14 Plan 03: Corporate Events Calendar API & Adjusted Price Toggle Summary

**One-liner:** GET /api/corporate-events with month/type/symbol filters + adjusted/raw price toggle param on /{symbol}/prices endpoint

## What Was Built

### Corporate Events Calendar API (CORP-08)
- `GET /api/corporate-events/` endpoint with three optional filters:
  - `month` (YYYY-MM format): filters by ex_date year/month using SQL `extract()` (T-14-07)
  - `type`: validates against `{CASH_DIVIDEND, STOCK_DIVIDEND, BONUS_SHARES, RIGHTS_ISSUE}` set (T-14-08)
  - `symbol`: case-insensitive ticker symbol filter
- Default behavior (no params): returns events within ±90 days of today
- CorporateEventResponse schema: id, symbol, name, event_type, ex_date, record_date, announcement_date, dividend_amount, ratio, note
- Joins CorporateEvent with Ticker to include symbol and name in response
- Results ordered by ex_date DESC, limited to 500 (T-14-09)
- Strict validation: invalid month format → 400, invalid event type → 400

### Adjusted/Raw Price Toggle (CORP-09)
- Added `adjusted` boolean query parameter to `GET /api/tickers/{symbol}/prices` (default: `true`)
- `adjusted=true`: close field uses `adjusted_close` when available, falls back to raw `close` when null
- `adjusted=false`: close field always uses raw `close` value
- `adjusted_close` response field always populated from stored value regardless of toggle
- Fully backward compatible: existing consumers without the param get adjusted prices (same as before)
- PriceResponse schema unchanged — no breaking API changes

### Router Registration
- `corporate_events_router` registered in `api_router` (router.py)

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1-RED | Failing tests for calendar API | `d21c13e` | tests/test_corporate_events_api.py |
| 1-GREEN | Corporate events API + router | `e33a20c` | corporate_events.py, router.py |
| 2-RED | Failing tests for adjusted toggle | `f316adf` | tests/test_corporate_events_api.py |
| 2-GREEN | Adjusted param on price endpoint | `c91d737` | tickers.py, tests |

## Test Results

**15 new tests** across 3 test classes:

- `TestCorporateEventsCalendarEndpoint` (9): returns list, response schema, month filter, type filter, symbol filter, default no-params, sort order, invalid type 400, invalid month 400
- `TestRouterRegistration` (1): corporate_events route registered in api_router
- `TestAdjustedPriceToggle` (5): adjusted=true uses adjusted_close, adjusted=false uses raw close, default returns adjusted, fallback when adjusted_close null, schema unchanged

**15 existing API tests** all pass (zero regressions).

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **extract() for SQL date filtering**: Uses `extract('year', ex_date)` and `extract('month', ex_date)` instead of string manipulation — prevents SQL injection and is database-agnostic (T-14-07 mitigation).
2. **adjusted=true as default**: Backward compatible — existing frontend consumers that don't pass the param continue to receive adjusted prices without any code changes.
3. **±90 day default range**: When no month param is provided, returns events from 90 days ago to 90 days ahead. Covers both recent past events and upcoming events for the calendar view.

## Self-Check: PASSED

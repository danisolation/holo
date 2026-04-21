---
phase: 29
plan: 1
subsystem: e2e-interaction-tests
tags: [playwright, interaction, e2e, paper-trading, watchlist, ticker]
dependency_graph:
  requires: [phase-27-test-infrastructure, phase-28-smoke-tests]
  provides: [interaction-test-coverage]
  affects: [frontend/e2e]
tech_stack:
  added: []
  patterns: [data-testid selectors, zustand localStorage persistence, structure-based assertions]
key_files:
  created:
    - frontend/e2e/interact-pt-settings.spec.ts
    - frontend/e2e/interact-pt-tabs.spec.ts
    - frontend/e2e/interact-trades-table.spec.ts
    - frontend/e2e/interact-watchlist.spec.ts
    - frontend/e2e/interact-ticker.spec.ts
  modified: []
decisions:
  - Watchlist persistence tested via localStorage injection (zustand persist with key "holo-watchlist")
  - Empty state handling for trades table — tests gracefully handle both data and no-data scenarios
  - Chart controls tested by button visibility check before click (canvas chart can't assert DOM content)
metrics:
  duration: 3m
  completed: "2026-04-21T10:46:51Z"
  tasks_completed: 5
  tasks_total: 5
  test_count: 23
---

# Phase 29 Plan 1: User Interaction Tests Summary

23 Playwright interaction tests across 5 files covering form submission with persistence, tab switching, table sorting/filtering, watchlist CRUD with reload verification, and ticker chart controls.

## Task Results

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Paper trading settings form test | df5b7a3 | frontend/e2e/interact-pt-settings.spec.ts |
| 2 | Paper trading tab switching test | 28ec71f | frontend/e2e/interact-pt-tabs.spec.ts |
| 3 | Trades table sorting/filtering test | 319903d | frontend/e2e/interact-trades-table.spec.ts |
| 4 | Watchlist interaction test | c16b202 | frontend/e2e/interact-watchlist.spec.ts |
| 5 | Ticker detail interaction test | 3377232 | frontend/e2e/interact-ticker.spec.ts |

## What Was Built

### INTERACT-01: Settings Form Submit + Persistence (3 tests)
- Form submit with modified capital value, wait for success, reload, verify persisted value
- All form fields render (capital, auto-track toggle, confidence threshold)
- Auto-track Bật/Tắt toggle switching

### INTERACT-04: Tab Switching (4 tests)
- All 5 tab triggers visible (overview, trades, analytics, calendar, settings)
- Overview tab active by default (data-state="active")
- Click each tab → verify corresponding content with data-testid assertions
- Previous content hidden after tab switch

### INTERACT-02: Trades Table Sort/Filter (5 tests)
- Table or empty state rendering
- Sortable column headers (ghost buttons with ArrowUpDown) clickable
- Direction filter buttons (Tất cả / Long / Bearish)
- Symbol filter input with text entry and clear
- Sort order change verification with data rows

### INTERACT-03: Watchlist Add/Remove + Persistence (4 tests)
- Add ticker via detail page star button → verify on /watchlist
- Persistence via page.reload() with zustand localStorage
- Remove via ticker detail page (Đang theo dõi → Theo dõi)
- Remove via X button on watchlist table row

### INTERACT-05: Ticker Detail Controls (7 tests)
- Chart container + heading visibility
- Time range buttons (1T, 3T, 6T, 1N, 2N) click-through
- Adjusted/original price toggle (Giá ĐC / Giá gốc)
- Ticker header with symbol and back button
- Watchlist star button toggle + restore
- Indicator and analysis section headings render
- Rapid time range switching stability (no crash)

## Decisions Made

1. **Watchlist localStorage injection**: Used `page.evaluate()` to inject zustand persist state directly for reliable test setup, avoiding UI interaction race conditions
2. **Empty state handling**: All table tests use `.or()` pattern to handle both data-present and empty-state scenarios gracefully
3. **Canvas chart assertions**: Chart control tests verify button visibility and click-without-crash rather than DOM content (lightweight-charts renders to canvas)

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None — all tests use real DOM selectors from actual components.

## Verification

- `npx playwright test --list` shows all 23 interaction tests across 5 files
- All tests use data-testid selectors from Phase 27
- Persistence tests include page.reload()
- No specific data value assertions (structure-based only)

## Self-Check: PASSED

All 5 test files exist. All 5 commit hashes verified. SUMMARY.md created.

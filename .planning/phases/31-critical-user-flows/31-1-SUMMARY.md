---
phase: 31
plan: 1
subsystem: e2e-tests
tags: [e2e, playwright, user-flows, multi-page]
dependency_graph:
  requires: [phase-27-test-infrastructure, phase-28-smoke-tests, phase-29-interaction-tests]
  provides: [critical-user-flow-coverage]
  affects: [frontend/e2e/]
tech_stack:
  added: []
  patterns: [multi-page-flow-tests, graceful-empty-state-handling, localStorage-injection-for-watchlist]
key_files:
  created:
    - frontend/e2e/flow-ticker-to-trade.spec.ts
    - frontend/e2e/flow-paper-trading-dashboard.spec.ts
    - frontend/e2e/flow-watchlist.spec.ts
    - frontend/e2e/flow-settings.spec.ts
  modified: []
decisions:
  - "FLOW-01: Trading plan Follow handled conditionally — test passes with or without active trading signal"
  - "FLOW-03: Watchlist uses localStorage cleanup in beforeEach for deterministic starting state"
  - "FLOW-04: Settings tests restore original values after modification to avoid polluting live data"
metrics:
  duration: ~3m
  completed: 2026-04-21
---

# Phase 31 Plan 1: Critical User Flow Tests Summary

**One-liner:** 8 multi-page E2E flow tests covering ticker→trade, dashboard exploration, watchlist CRUD with persistence, and settings persistence with effect verification.

## What Was Done

Created 4 Playwright test files implementing critical user journeys that span multiple pages/tabs:

### FLOW-01: Ticker to Trade (`flow-ticker-to-trade.spec.ts`)
- Navigates `/ticker/VNM` → verifies chart, analysis sections → looks for trading plan
- If Follow button exists (trading signal available): clicks Follow, navigates to `/dashboard/paper-trading`, verifies trade
- If no signal: verifies page structure is complete without crash
- 2 tests: full flow + structure-only validation

### FLOW-02: Paper Trading Dashboard (`flow-paper-trading-dashboard.spec.ts`)
- Navigates `/dashboard/paper-trading` → Overview tab (default) → Trades tab
- On Trades tab: sorts by date column, filters by direction (Long), resets filter (Tất cả)
- Switches to Analytics tab → verifies `[data-testid="pt-analytics-content"]`
- Switches to Calendar tab → verifies tab state transitions
- 2 tests: full exploration flow + return-to-overview test

### FLOW-03: Watchlist Management (`flow-watchlist.spec.ts`)
- Adds ticker via star button on `/ticker/VNM` → navigates to `/watchlist` → verifies presence
- Reloads page → verifies localStorage persistence (zustand persist key `holo-watchlist`)
- Removes ticker via star button → navigates back to `/watchlist` → verifies removal
- Uses `beforeEach` localStorage cleanup for deterministic state
- 2 tests: full CRUD flow + cross-navigation persistence test

### FLOW-04: Settings Persistence (`flow-settings.spec.ts`)
- Opens Settings tab → reads current capital → modifies (+1M VND) → submits
- Reloads page → verifies persisted value matches
- Switches to Overview tab → verifies overview renders (cards or fallback)
- Restores original value in cleanup step
- 2 tests: capital persistence + confidence threshold persistence

## Key Patterns

- **Graceful empty states:** All tests handle cases where no data exists (no trades, no trading signals)
- **No specific data assertions:** Tests verify structure and navigation, never hardcoded financial values
- **Multi-page journeys:** Each test navigates across 2+ distinct pages/routes
- **Deterministic setup:** Watchlist tests inject localStorage state for predictable starting conditions
- **Cleanup:** Settings tests restore original values to avoid side effects on live data

## Deviations from Plan

None — plan executed exactly as written.

## Task Commits

| Task | Description | Commit | Files |
|------|-------------|--------|-------|
| 1 | Ticker-to-trade flow (FLOW-01) | `782429b` | `frontend/e2e/flow-ticker-to-trade.spec.ts` |
| 2 | Paper trading dashboard flow (FLOW-02) | `dc608d5` | `frontend/e2e/flow-paper-trading-dashboard.spec.ts` |
| 3 | Watchlist management flow (FLOW-03) | `4999af5` | `frontend/e2e/flow-watchlist.spec.ts` |
| 4 | Settings persistence flow (FLOW-04) | `60b52b1` | `frontend/e2e/flow-settings.spec.ts` |

## Verification

Playwright `--list` confirms all 8 tests across 4 files are registered:
- `flow-ticker-to-trade.spec.ts` — 2 tests
- `flow-paper-trading-dashboard.spec.ts` — 2 tests
- `flow-watchlist.spec.ts` — 2 tests
- `flow-settings.spec.ts` — 2 tests

## Self-Check: PASSED

All 5 files found on disk. All 4 task commits verified in git log.

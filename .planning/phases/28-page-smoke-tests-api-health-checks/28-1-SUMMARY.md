---
phase: 28
plan: 1
subsystem: frontend-e2e
tags: [playwright, smoke-tests, navigation, theme, e2e]
dependency_graph:
  requires: [27-1, 27-3, 27-4]
  provides: [page-smoke-coverage, navigation-tests, theme-toggle-tests]
  affects: [frontend/e2e]
tech_stack:
  added: []
  patterns: [data-testid selectors, APP_ROUTES loop, Vietnamese nav labels]
key_files:
  created:
    - frontend/e2e/page-smoke.spec.ts
    - frontend/e2e/navigation.spec.ts
    - frontend/e2e/theme.spec.ts
  modified: []
decisions:
  - "28.1: Loop over APP_ROUTES for smoke tests — single test per route, 8th route tested separately"
  - "28.1: Navigation tests use Vietnamese labels via getByText for real-world accuracy"
  - "28.1: Theme persistence checked via html class attribute comparison across navigation"
metrics:
  duration: ~3min
  completed: 2026-04-21
---

# Phase 28 Plan 1: Page Smoke Tests Summary

Playwright E2E tests covering all 8 app routes for loading, navbar navigation via Vietnamese labels, key component rendering (tabs, tables, charts), and dark/light theme toggle persistence.

## Task Results

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Page smoke tests for all 8 routes | b8ce1cf | frontend/e2e/page-smoke.spec.ts |
| 2 | Navigation tests via navbar links | 850b0a9 | frontend/e2e/navigation.spec.ts |
| 3 | Theme toggle tests | ed8a27b | frontend/e2e/theme.spec.ts |

## What Was Built

### page-smoke.spec.ts (Task 1)
- **Page Smoke Tests**: Loops over all 7 `APP_ROUTES` verifying body visible + navbar present
- **Ticker Detail**: Separate test for `/ticker/VNM` (8th route) checking `ticker-page` testid
- **Key Components Render**: 7 tests verifying specific components per page:
  - Dashboard: main content container
  - Paper Trading: `pt-tabs` and `pt-tab-overview` testids
  - Watchlist: `watchlist-page` testid
  - Ticker detail: `ticker-chart` with 15s timeout for canvas rendering
  - System Health, Corporate Events, Portfolio: main content containers

### navigation.spec.ts (Task 2)
- **Link Navigation**: Sequential click test — Danh mục → Bảng điều khiển → Paper Trading → Tổng quan with URL assertions
- **Navbar Visibility**: Loop over 5 routes verifying navbar present on each

### theme.spec.ts (Task 3)
- **Toggle Cycle**: Click toggle twice, verify navbar + body visible after each toggle
- **Theme Persistence**: Toggle theme, navigate to /watchlist, verify `html` class attribute matches

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all tests are complete with real selectors and assertions.

## Requirements Addressed

- **SMOKE-01**: All 8 routes tested for successful loading ✅
- **SMOKE-02**: Navigation between pages works via navbar links ✅
- **SMOKE-03**: Key components render on each page (tabs, tables, chart container) ✅
- **SMOKE-04**: Dark/light theme toggle doesn't break layout ✅

## Self-Check: PASSED

- [x] frontend/e2e/page-smoke.spec.ts exists
- [x] frontend/e2e/navigation.spec.ts exists
- [x] frontend/e2e/theme.spec.ts exists
- [x] Commit b8ce1cf verified
- [x] Commit 850b0a9 verified
- [x] Commit ed8a27b verified
- [x] All acceptance criteria met for all 3 tasks

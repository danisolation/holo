---
phase: 27
plan: 3
subsystem: frontend
tags: [testing, data-testid, playwright, ui-components]
dependency_graph:
  requires: [27-1]
  provides: [data-testid-attributes]
  affects: [frontend/src/components/navbar.tsx, frontend/src/app/dashboard/paper-trading/page.tsx, frontend/src/components/paper-trading/pt-settings-form.tsx, frontend/src/components/paper-trading/pt-trades-table.tsx, frontend/src/components/paper-trading/pt-analytics-tab.tsx, frontend/src/app/watchlist/page.tsx, frontend/src/app/ticker/[symbol]/page.tsx]
tech_stack:
  added: []
  patterns: [data-testid attributes for Playwright selectors]
key_files:
  modified:
    - frontend/src/components/navbar.tsx
    - frontend/src/app/dashboard/paper-trading/page.tsx
    - frontend/src/components/paper-trading/pt-settings-form.tsx
    - frontend/src/components/paper-trading/pt-trades-table.tsx
    - frontend/src/components/paper-trading/pt-analytics-tab.tsx
    - frontend/src/app/watchlist/page.tsx
    - frontend/src/app/ticker/[symbol]/page.tsx
decisions:
  - data-testid attributes added as props to existing elements — no DOM restructuring
  - File names differ from plan (pt-settings-form.tsx not pt-settings-tab.tsx, pt-trades-table.tsx not pt-trades-tab.tsx) — adapted to actual codebase
  - watchlist-table testid added via wrapper div since WatchlistTable is an imported component
metrics:
  duration: 2m
  completed: 2026-04-21
  tasks: 4/4
  files_modified: 7
---

# Phase 27 Plan 3: Add data-testid Attributes to Key Components Summary

**One-liner:** 17 stable `data-testid` attributes added across navbar, paper trading tabs/sub-components, watchlist, and ticker pages for reliable Playwright E2E selectors.

## What Was Done

### Task 1: Navbar Component (9c40939)
Added 3 data-testid attributes to `frontend/src/components/navbar.tsx`:
- `data-testid="navbar"` on the `<header>` element
- `data-testid="nav-desktop"` on the desktop `<nav>` element
- `data-testid="theme-toggle"` on the dark mode toggle `<Button>`

### Task 2: Paper Trading Dashboard Tabs (8e66889)
Added 6 data-testid attributes to `frontend/src/app/dashboard/paper-trading/page.tsx`:
- `data-testid="pt-tabs"` on the `<Tabs>` root element
- `data-testid="pt-tab-overview"` on Overview TabsTrigger
- `data-testid="pt-tab-trades"` on Trades TabsTrigger
- `data-testid="pt-tab-analytics"` on Analytics TabsTrigger
- `data-testid="pt-tab-calendar"` on Calendar TabsTrigger
- `data-testid="pt-tab-settings"` on Settings TabsTrigger

### Task 3: Paper Trading Sub-components (d0b1a90)
Added 4 data-testid attributes across 3 files:
- `pt-settings-form.tsx`: `data-testid="pt-settings-form"` on Card wrapper, `data-testid="pt-settings-submit"` on save button
- `pt-trades-table.tsx`: `data-testid="pt-trades-table"` on Card wrapper
- `pt-analytics-tab.tsx`: `data-testid="pt-analytics-content"` on main content div

### Task 4: Watchlist & Ticker Pages (88af221)
Added 4 data-testid attributes across 2 files:
- `watchlist/page.tsx`: `data-testid="watchlist-page"` on page wrapper, `data-testid="watchlist-table"` on table wrapper div
- `ticker/[symbol]/page.tsx`: `data-testid="ticker-page"` on page wrapper, `data-testid="ticker-chart"` on chart section

## Verification Results

- **Total data-testid count:** 17 attributes across frontend/src (exceeds 15+ requirement)
- **Frontend build:** ✅ Clean — `npm run build` succeeds with no errors
- **All acceptance criteria met:** Every required testid from plan present in correct files

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] File names differ from plan**
- **Found during:** Task 3
- **Issue:** Plan referenced `pt-settings-tab.tsx` and `pt-trades-tab.tsx` but actual files are `pt-settings-form.tsx` and `pt-trades-table.tsx`
- **Fix:** Used correct file names from actual codebase
- **Files modified:** pt-settings-form.tsx, pt-trades-table.tsx

**2. [Rule 2 - Missing functionality] WatchlistTable wrapper needed**
- **Found during:** Task 4
- **Issue:** `<WatchlistTable />` is an imported component — can't add prop directly from page. Needed a wrapper div for the testid.
- **Fix:** Wrapped in `<div data-testid="watchlist-table">` — minimal DOM impact, clean selector for Playwright
- **Files modified:** frontend/src/app/watchlist/page.tsx

## Known Stubs

None — all data-testid attributes are final values wired to real elements.

## Self-Check: PASSED

All 7 modified files verified to exist. All 4 task commits (9c40939, 8e66889, d0b1a90, 88af221) verified in git log. Frontend build clean.

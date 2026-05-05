---
phase: 57-search-fix
plan: 01
subsystem: frontend-search
tags: [bugfix, search, ux, localStorage]
dependency_graph:
  requires: []
  provides: [full-ticker-search, recent-searches]
  affects: [ticker-search, trade-entry-dialog]
tech_stack:
  added: []
  patterns: [localStorage-persistence, cmdk-unfiltered-rendering]
key_files:
  created:
    - frontend/src/lib/recent-searches.ts
  modified:
    - frontend/src/components/ticker-search.tsx
    - frontend/src/components/trade-entry-dialog.tsx
decisions:
  - "Pass limit=500 to useTickers() to fetch all ~400 HOSE tickers in one request"
  - "Remove .slice(0,50) to let cmdk shouldFilter handle client-side filtering on full dataset"
  - "Store recent searches as {symbol, name} array in localStorage under 'holo-recent-searches'"
metrics:
  duration: "2m"
  completed: 2026-05-06
---

# Phase 57 Plan 01: Search Fix Summary

**One-liner:** Remove .slice(0,50) truncation + pass limit=500 to useTickers so all ~400 HOSE tickers are searchable; add localStorage-backed recent searches in navbar search dialog.

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Remove .slice(0,50) and pass limit=500 | `6c93bd7` | ticker-search.tsx, trade-entry-dialog.tsx |
| 2 | Add recent searches with localStorage | `41774f9` | recent-searches.ts, ticker-search.tsx |

## What Was Done

### Task 1: Fix ticker truncation (SRCH-01)
- Removed `.slice(0, 50)` from both `ticker-search.tsx` and `trade-entry-dialog.tsx`
- Changed `useTickers()` to `useTickers(undefined, undefined, 500)` in both components
- All ~400 HOSE tickers now rendered in DOM, enabling cmdk's `shouldFilter={true}` to search the full set

### Task 2: Recent searches (SRCH-02)
- Created `frontend/src/lib/recent-searches.ts` with `getRecentSearches()` and `addRecentSearch()` helpers
- localStorage key: `holo-recent-searches`, max 5 items, most recent first
- Integrated into `ticker-search.tsx`: loads recent searches on dialog open, saves on ticker selection
- "Tìm kiếm gần đây" CommandGroup appears above main ticker list when recent searches exist
- Defensive coding: try/catch around all localStorage operations, Array.isArray guard on parse

## Deviations from Plan

None — plan executed exactly as written.

## Requirements Satisfied

- **SRCH-01**: Ticker search returns all ~400 HOSE tickers (fix .slice(0,50) truncation + API limit=100 cap)
- **SRCH-02**: Search supports recent searches history (client-side, localStorage)

## Self-Check: PASSED

- [x] `frontend/src/lib/recent-searches.ts` exists
- [x] `frontend/src/components/ticker-search.tsx` modified (no .slice, limit=500, recent searches)
- [x] `frontend/src/components/trade-entry-dialog.tsx` modified (no .slice, limit=500)
- [x] Commit `6c93bd7` exists
- [x] Commit `41774f9` exists
- [x] TypeScript compiles without errors

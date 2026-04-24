---
phase: 48-backend-cleanup-scheduler-simplification
plan: 02
subsystem: frontend
tags: [cleanup, corporate-events, exchange-filter, HNX, UPCOM, HOSE-only]
dependency_graph:
  requires: []
  provides:
    - "Clean frontend with no corporate events page"
    - "No exchange filter/badge components"
    - "No HNX/UPCOM references in frontend"
    - "localStorage cleanup for stale exchange filter key"
  affects:
    - "frontend/src/lib/store.ts"
    - "frontend/src/app/page.tsx"
    - "frontend/src/components/heatmap.tsx"
    - "frontend/src/components/navbar.tsx"
tech_stack:
  added: []
  patterns:
    - "One-time localStorage cleanup on module import for removed zustand persist keys"
key_files:
  created: []
  modified:
    - "frontend/src/lib/api.ts"
    - "frontend/src/lib/hooks.ts"
    - "frontend/src/lib/store.ts"
    - "frontend/src/components/navbar.tsx"
    - "frontend/src/components/heatmap.tsx"
    - "frontend/src/components/ticker-search.tsx"
    - "frontend/src/components/watchlist-table.tsx"
    - "frontend/src/app/page.tsx"
    - "frontend/src/app/dashboard/page.tsx"
    - "frontend/src/app/watchlist/page.tsx"
    - "frontend/src/app/ticker/[symbol]/page.tsx"
    - "frontend/src/app/layout.tsx"
    - "frontend/e2e/api-errors.spec.ts"
    - "frontend/e2e/api-smoke.spec.ts"
    - "frontend/e2e/page-smoke.spec.ts"
    - "frontend/e2e/fixtures/test-helpers.ts"
  deleted:
    - "frontend/src/app/dashboard/corporate-events/page.tsx"
    - "frontend/src/components/corporate-events-calendar.tsx"
    - "frontend/src/components/exchange-filter.tsx"
    - "frontend/src/components/exchange-badge.tsx"
decisions:
  - "Removed AnalyzeNowButton entirely — it only showed for HNX/UPCOM tickers, all dead code now"
  - "Used one-time localStorage.removeItem at module-level in store.ts to clear stale zustand persist key"
  - "Updated APP_ROUTES in test helpers (deviation Rule 1) to prevent E2E smoke test failures"
metrics:
  duration: "~8 minutes"
  completed: "2026-04-24"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 20
---

# Phase 48 Plan 02: Remove Corporate Events & HNX/UPCOM Frontend Summary

Remove all corporate events and HNX/UPCOM frontend code — pages, components, store, API types, hooks, nav links, E2E tests — simplifying UI to HOSE-only with localStorage cleanup for stale exchange filter state.

## Tasks Completed

### Task 1: Remove corporate events frontend and clean API/hooks/navbar
**Commit:** `94d7658`

- Deleted `frontend/src/app/dashboard/corporate-events/page.tsx` and entire directory
- Deleted `frontend/src/components/corporate-events-calendar.tsx`
- Removed `CorporateEventResponse` interface and `fetchCorporateEvents` function from `api.ts`
- Removed `useCorporateEvents` hook and `fetchCorporateEvents` import from `hooks.ts`
- Removed `{ href: "/dashboard/corporate-events", label: "Sự kiện" }` from navbar NAV_LINKS (now 6 entries)

### Task 2: Remove HNX/UPCOM frontend — exchange components, page cleanups, localStorage, E2E tests
**Commit:** `8633770`

- Deleted `exchange-filter.tsx` and `exchange-badge.tsx` components
- Rewrote `store.ts` — removed `Exchange` type, `useExchangeStore`, added `localStorage.removeItem("holo-exchange-filter")` cleanup
- Cleaned `page.tsx` (home) — removed ExchangeFilter import/JSX, useExchangeStore, exchange prop on Heatmap, static subtitle
- Cleaned `dashboard/page.tsx` — removed ExchangeFilter import/JSX, useExchangeStore, exchange arg from useMarketOverview
- Cleaned `watchlist/page.tsx` — removed ExchangeFilter import/JSX
- Cleaned `ticker/[symbol]/page.tsx` — removed ExchangeBadge, AnalyzeNowButton (entire component + JSX usage), unused imports (useState, useEffect, Sparkles, Check, Loader2, useTriggerAnalysis)
- Cleaned `heatmap.tsx` — removed ExchangeBadge import/usage, EXCHANGE_BORDER_COLORS, border-2 class, exchange prop, exchange-conditional empty state text
- Cleaned `ticker-search.tsx` — removed ExchangeBadge import/usage from CommandItem
- Cleaned `watchlist-table.tsx` — removed ExchangeBadge import/usage, useExchangeStore, exchange column definition, exchange-based filtering, exchange-conditional empty state text
- Updated `layout.tsx` metadata description from "(HOSE, HNX, UPCOM)" to "(HOSE)"
- Updated `api-errors.spec.ts` — removed corporate events month format test
- Updated `api-smoke.spec.ts` — removed entire Corporate Events test block
- Updated `page-smoke.spec.ts` — removed Corporate Events page render test
- Updated `test-helpers.ts` — removed corporate-events from APP_ROUTES

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated APP_ROUTES in test-helpers.ts**
- **Found during:** Task 2
- **Issue:** `APP_ROUTES` in `frontend/e2e/fixtures/test-helpers.ts` still contained `/dashboard/corporate-events`, which would cause the page smoke test loop to try loading a deleted route
- **Fix:** Removed the corporate-events entry from `APP_ROUTES`
- **Files modified:** `frontend/e2e/fixtures/test-helpers.ts`
- **Commit:** `8633770`

**2. [Rule 2 - Missing cleanup] Removed unused imports from ticker detail page**
- **Found during:** Task 2
- **Issue:** After removing AnalyzeNowButton, `useState`, `useEffect`, `Sparkles`, `Check`, `Loader2`, `useTriggerAnalysis`, and `hasRecentAnalysis` were all dead code
- **Fix:** Removed all unused imports and variables
- **Files modified:** `frontend/src/app/ticker/[symbol]/page.tsx`
- **Commit:** `8633770`

## Threat Mitigations Applied

| Threat ID | Component | Mitigation |
|-----------|-----------|------------|
| T-48-04 | store.ts | `localStorage.removeItem("holo-exchange-filter")` on module import prevents zustand hydration errors |
| T-48-05 | E2E tests | Removed all test cases referencing deleted corporate events endpoints and pages |

## Verification Results

- `npx next build` — ✅ Clean build, zero errors, all 8 routes compiled
- No `ExchangeFilter`, `ExchangeBadge`, `useExchangeStore`, `exchange-filter`, `exchange-badge` references in frontend/src/
- No `corporate-events`, `CorporateEvent`, `fetchCorporateEvents`, `useCorporateEvents` references in frontend/src/
- No `HNX`, `UPCOM` references in frontend/src/ layout metadata
- `store.ts` contains `localStorage.removeItem("holo-exchange-filter")`
- All 20 acceptance criteria passed

## Self-Check: PASSED

- [x] `frontend/src/app/dashboard/corporate-events/` — NOT EXISTS ✓
- [x] `frontend/src/components/corporate-events-calendar.tsx` — NOT EXISTS ✓
- [x] `frontend/src/components/exchange-filter.tsx` — NOT EXISTS ✓
- [x] `frontend/src/components/exchange-badge.tsx` — NOT EXISTS ✓
- [x] Commit `94d7658` — EXISTS ✓
- [x] Commit `8633770` — EXISTS ✓

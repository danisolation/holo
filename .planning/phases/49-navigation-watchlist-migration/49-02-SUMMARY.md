---
phase: 49-navigation-watchlist-migration
plan: 02
subsystem: frontend-navigation-watchlist
tags: [navigation, watchlist, migration, ai-signal, react-query]
dependency_graph:
  requires: [watchlist-api, watchlist-db-schema]
  provides: [server-backed-watchlist-ui, simplified-navigation]
  affects: [home-page, dashboard-page, watchlist-page, ticker-detail-page]
tech_stack:
  added: []
  patterns: [React Query mutations for watchlist CRUD, localStorage-to-server migration bridge, AI signal enrichment display]
key_files:
  created: []
  modified:
    - frontend/src/components/navbar.tsx
    - frontend/src/app/page.tsx
    - frontend/src/app/dashboard/page.tsx
    - frontend/next.config.ts
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/lib/store.ts
    - frontend/src/components/watchlist-table.tsx
    - frontend/src/app/watchlist/page.tsx
    - frontend/src/app/ticker/[symbol]/page.tsx
    - frontend/e2e/navigation.spec.ts
    - frontend/e2e/fixtures/test-helpers.ts
    - frontend/e2e/interact-watchlist.spec.ts
    - frontend/e2e/flow-watchlist.spec.ts
decisions:
  - "Merged dashboard top movers into home page; skipped pie chart (redundant with heatmap)"
  - "Used React Query mutations (useAddToWatchlist/useRemoveFromWatchlist) with cache invalidation for optimistic-feel UX"
  - "Removed zustand watchlist store entirely; replaced with migrateLocalWatchlist() one-time bridge"
  - "AI signal+score rendered inline in watchlist table row (no more N+1 SignalCell API calls)"
  - "E2E tests converted to UI-only flows — no localStorage injection"
metrics:
  duration: 8m
  completed: 2026-04-24T14:26:22Z
  tasks_completed: 2
  tasks_total: 2
  files_created: 0
  files_modified: 14
---

# Phase 49 Plan 02: Frontend Navigation & Watchlist Migration Summary

Simplified navigation from 6→5 items (merging /dashboard into home with top movers), migrated watchlist from zustand/localStorage to server-backed React Query hooks calling /api/watchlist, with AI signal label + numeric score display per row.

## Tasks Completed

### Task 1: Reduce navigation to 5 items — merge dashboard into home
- **Commit:** `1a1df78`
- Removed "Bảng điều khiển" from NAV_LINKS (6→5 items: Tổng quan, Danh mục, Huấn luyện, Nhật ký, Hệ thống)
- Added top movers section (Top tăng / Top giảm cards with top 5 each) to home page via useMemo on marketData
- Replaced dashboard/page.tsx with client-side `router.replace("/")` redirect
- Added permanent `/dashboard → /` redirect in next.config.ts
- Updated E2E navigation.spec.ts: replaced "Bảng điều khiển" click with "Huấn luyện" test, removed /dashboard from route loop
- Updated test-helpers.ts: removed /dashboard from APP_ROUTES
- **Files:** navbar.tsx, page.tsx, dashboard/page.tsx, next.config.ts, navigation.spec.ts, test-helpers.ts

### Task 2: Migrate watchlist to server API with localStorage bridge and AI score display
- **Commit:** `bb6824f`
- Added `WatchlistItem` interface + 4 API functions (fetchWatchlist, addWatchlistItem, removeWatchlistItem, migrateWatchlist) to api.ts
- Added `useWatchlist`, `useAddToWatchlist`, `useRemoveFromWatchlist` React Query hooks to hooks.ts
- Replaced zustand store with `migrateLocalWatchlist()` function: parses zustand persist format, calls /api/watchlist/migrate, clears localStorage on success
- Rewrote watchlist-table.tsx: uses server data via useWatchlist, removed N+1 SignalCell component, renders ai_signal badge + ai_score (X/10) inline from server response
- Updated watchlist/page.tsx: uses useWatchlist for count badge, triggers migrateLocalWatchlist on mount
- Updated ticker/[symbol]/page.tsx: replaced useWatchlistStore with useWatchlist + useAddToWatchlist + useRemoveFromWatchlist hooks
- Updated E2E tests: removed all localStorage.setItem/getItem patterns, all tests work through UI buttons only
- **Files:** api.ts, hooks.ts, store.ts, watchlist-table.tsx, watchlist/page.tsx, ticker/[symbol]/page.tsx, interact-watchlist.spec.ts, flow-watchlist.spec.ts

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|------------|
| T-49-05 | localStorage JSON parsed in try/catch, validates symbols is string array, logs error on failure without crashing |
| T-49-07 | staleTime 2min on useWatchlist, mutations invalidate cache only on success |

## Known Stubs

None — all components are fully wired to server API with real data.

## Self-Check: PASSED

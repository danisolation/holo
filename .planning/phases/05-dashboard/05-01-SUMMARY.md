---
phase: 05-dashboard
plan: 01
subsystem: frontend-setup
tags: [cors, endpoints, nextjs, react-query, zustand, shadcn-ui, data-layer]
dependency_graph:
  requires: [backend-api, database-models]
  provides: [frontend-project, api-client, react-query-hooks, watchlist-store, theme-provider]
  affects: [05-02, 05-03]
tech_stack:
  added: [Next.js 16.2.3, Tailwind CSS 4, shadcn/ui, @tanstack/react-query, @tanstack/react-table, lightweight-charts, recharts, zustand, next-themes, lucide-react, date-fns]
  patterns: [type-safe-api-client, react-query-hooks, zustand-persist, dark-theme-default]
key_files:
  created:
    - backend/app/api/tickers.py
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/lib/store.ts
    - frontend/src/app/providers.tsx
  modified:
    - backend/app/main.py
    - backend/app/api/router.py
    - frontend/src/app/layout.tsx
decisions:
  - "Geist font: latin-only subset (Vietnamese not available in font)"
  - "Next.js 16.2.3 installed (latest stable at project creation time)"
  - "Dark theme as default via next-themes with class attribute strategy"
metrics:
  duration: 13m
  completed: "2026-04-15"
  tasks_completed: 2
  tasks_total: 2
  files_created: 37
  files_modified: 3
---

# Phase 5 Plan 1: Frontend Setup + Data Layer Summary

**One-liner:** Next.js 16 frontend with shadcn/ui, type-safe API client, React Query hooks, zustand watchlist store, and backend CORS + ticker/price endpoints.

## What Was Done

### Task 1: Backend — CORS + Missing Endpoints (02be46a)

1. **CORS middleware** added to `backend/app/main.py` — allows `localhost:3000` and `127.0.0.1:3000` with credentials
2. **Tickers endpoint** (`backend/app/api/tickers.py`):
   - `GET /api/tickers/` — lists all active tickers with optional `sector` filter, ordered by symbol
   - `GET /api/tickers/{symbol}/prices` — OHLCV data with `days` param (1–730, default 365), ordered by date ASC for charting
   - Pydantic response models: `TickerResponse`, `PriceResponse`
3. **Router registration** — `tickers_router` included in `api_router` at `backend/app/api/router.py`

### Task 2: Frontend — Project Setup + Data Layer (197a609)

1. **Next.js 16.2.3** initialized at `frontend/` with TypeScript, Tailwind CSS 4, ESLint, App Router, `src/` dir
2. **Dependencies installed:** React Query, React Table, lightweight-charts, recharts, zustand, lucide-react, date-fns, next-themes
3. **shadcn/ui** initialized with 12 components: button, card, input, table, tabs, badge, separator, skeleton, sheet, command, dialog, textarea, input-group
4. **API client** (`frontend/src/lib/api.ts`):
   - Full TypeScript interfaces matching all backend Pydantic schemas
   - `ApiError` class with status code
   - Generic `apiFetch<T>()` with error handling
   - `fetchTickers()`, `fetchPrices()`, `fetchIndicators()`, `fetchAnalysisSummary()`
5. **React Query hooks** (`frontend/src/lib/hooks.ts`):
   - `useTickers(sector?)` — staleTime 5min
   - `usePrices(symbol, days?)` — staleTime 5min, enabled only when symbol provided
   - `useIndicators(symbol, limit?)` — staleTime 5min
   - `useAnalysisSummary(symbol)` — staleTime 30min
6. **Zustand store** (`frontend/src/lib/store.ts`):
   - `useWatchlistStore` with `addToWatchlist`, `removeFromWatchlist`, `isInWatchlist`
   - Persisted to localStorage as `holo-watchlist`
7. **Providers** (`frontend/src/app/providers.tsx`):
   - `QueryClientProvider` with 5min default staleTime, no refetch on focus, 1 retry
   - `ThemeProvider` from next-themes — dark default, class attribute, no system detection
8. **Layout** updated: title "Holo — Stock Intelligence", Vietnamese locale (`lang="vi"`), `suppressHydrationWarning` for theme, wrapped with `<Providers>`

## Verification

- `npm run build` passes successfully (TypeScript check + static generation)
- Backend tests: no regressions from changes (pre-existing failures unrelated to CORS/tickers)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Geist font Vietnamese subset not available**
- **Found during:** Task 2, build verification
- **Issue:** `subsets: ["latin", "vietnamese"]` fails TypeScript check — Geist font only supports `latin`, `latin-ext`, `cyrillic`
- **Fix:** Removed `"vietnamese"` from subsets, kept `"latin"` only
- **Files modified:** `frontend/src/app/layout.tsx`

**2. [Rule 3 - Blocking] Nested .git from create-next-app**
- **Found during:** Task 2, git staging
- **Issue:** `create-next-app` initializes its own `.git` inside `frontend/`, causing git submodule detection
- **Fix:** Removed `frontend/.git` directory before staging
- **Files modified:** None (filesystem cleanup only)

## Self-Check: PASSED

All 9 key files verified as existing. Both commit hashes (02be46a, 197a609) confirmed in git log.

---
phase: 102-sector-breadth-frontend
plan: 01
subsystem: frontend
tags: [market-page, sector-heatmap, api-layer, react-query]
dependency_graph:
  requires: [backend-market-breadth-api, backend-sector-api]
  provides: [market-page, sector-tab, market-api-hooks]
  affects: [navbar, api.ts, hooks.ts]
tech_stack:
  added: []
  patterns: [sector-heatmap-grid, price-volume-toggle, sector-drilldown]
key_files:
  created:
    - frontend/src/app/market/page.tsx
    - frontend/src/components/market/sector-tab.tsx
    - frontend/src/components/market/sector-heatmap.tsx
    - frontend/src/components/market/sector-drilldown.tsx
    - frontend/src/components/market/sector-ranking.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/components/navbar.tsx
decisions:
  - Used CSS grid with col-span sizing instead of Recharts Treemap for simpler, lighter heatmap
  - Copied getChangeColor logic locally rather than importing from heatmap.tsx (not exported as utility)
  - Volume view uses blue-shade gradient instead of green/red to differentiate from price view
  - Drilldown uses useMarketOverview hook filtered by sector for real ticker data
metrics:
  duration_seconds: 176
  completed: 2026-05-15T02:46:13Z
  tasks_completed: 2
  tasks_total: 2
---

# Phase 102 Plan 01: API types/hooks + navbar + /market page + Sector tab Summary

CSS grid sector heatmap with price/volume toggle, drilldown to constituent tickers, and sortable ranking table on new /market page

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | API types, fetch functions, hooks, navbar link, /market page skeleton | ef73541 | api.ts, hooks.ts, navbar.tsx, market/page.tsx |
| 2 | Sector tab — heatmap with toggle, drilldown panel, ranking table | 040d115 | sector-tab.tsx, sector-heatmap.tsx, sector-drilldown.tsx, sector-ranking.tsx |

## What Was Built

### API Layer (api.ts)
- 6 TypeScript interfaces mirroring backend schemas: ADLineItem, MABreadthItem, HighsLowsItem, MarketBreadthResponse, SectorPerformanceItem, SectorFlowItem
- 3 fetch functions: fetchMarketBreadth, fetchSectorPerformance, fetchSectorFlow — all using apiFetch helper with optional date params

### React Query Hooks (hooks.ts)
- useMarketBreadth, useSectorPerformance, useSectorFlow — all with staleTime: 60s for intraday data
- Mitigates T-102-02 (DoS) by preventing excessive refetching

### Navigation (navbar.tsx)
- Added "Thị trường" link in NAV_LINKS after "Mô phỏng", pointing to /market

### /market Page
- 3 tabs: Sector (fully functional), Breadth (placeholder for Plan 02), Dòng tiền (placeholder for Plan 02)
- Follows existing Tabs pattern from simulator page

### Sector Tab Components
- **SectorTab**: Container with skeleton loading (15 blocks + 1 bar) and error state
- **SectorHeatmap**: CSS grid blocks sized proportionally to ticker_count, colored by avg_change_today (red↔gray↔green). Toggle switches to volume view (blue gradient by ticker_count). Click opens drilldown.
- **SectorDrilldown**: Card showing constituent tickers via useMarketOverview filtered by sector. Table with symbol, name, price, % change (colored), market cap. Skeleton while loading.
- **SectorRanking**: Sortable table with columns: Ngành, Mã count, Hôm nay, 7 ngày, 30 ngày, Xu hướng (▲/▼ comparing 7d vs 30d momentum). Clickable headers to change sort.

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- TypeScript: `npx tsc --noEmit` — zero errors
- Build: `npm run build` — compiled successfully, /market route generated as static page
- All 7 files created/modified verified in git

## Self-Check: PASSED

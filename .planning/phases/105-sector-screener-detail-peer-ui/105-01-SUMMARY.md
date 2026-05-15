---
phase: 105-sector-screener-detail-peer-ui
plan: "01"
subsystem: frontend-screener
tags: [screener, market, filters, sorting, react-query]
dependency_graph:
  requires: [backend-screener-schemas]
  provides: [screener-page, screener-hooks, screener-types]
  affects: [market-page]
tech_stack:
  added: []
  patterns: [react-query-hooks, url-search-params, sortable-table]
key_files:
  created:
    - frontend/src/app/market/screener/page.tsx
    - frontend/src/components/market/screener-filters.tsx
    - frontend/src/components/market/screener-table.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/market/page.tsx
decisions:
  - "Used native <select> for sector dropdown since shadcn Select component not installed"
  - "Used useSectorPerformance() hook to populate sector dropdown (reuses existing data)"
metrics:
  duration: ~5min
  completed: 2026-05-15T11:05:22Z
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 3
---

# Phase 105 Plan 01: Screener Types, Hooks & Page Summary

Screener page at /market/screener with sector/industry dropdowns, volume/change/PE filters, sortable results table with ticker links, and pagination.

## Completed Tasks

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add TypeScript interfaces, fetch functions, and React Query hooks | 1955a63 | api.ts, hooks.ts |
| 2 | Build /market/screener page with filters and sortable table | 1955a63 | screener/page.tsx, screener-filters.tsx, screener-table.tsx, market/page.tsx |

## What Was Built

### TypeScript Interfaces (api.ts)
- `ScreenerTickerItem`, `ScreenerResponse`, `ScreenerParams` — matches backend `screener.py` exactly
- `PeerComparisonItem`, `PeerComparisonResponse` — for future peer comparison views
- `SectorDetailTickerItem`, `SectorDetailResponse` — for future sector detail views

### Fetch Functions (api.ts)
- `fetchScreener(params?)` — builds URLSearchParams from all filter/sort/pagination params
- `fetchSectorDetail(sectorName)` — GET `/market/sector/{name}`
- `fetchPeerComparison(symbol)` — GET `/market/peers/{symbol}`

### React Query Hooks (hooks.ts)
- `useScreener(params?)` — staleTime 60s, queryKey includes full params object
- `useSectorDetail(sectorName)` — enabled only when sectorName defined
- `usePeerComparison(symbol)` — enabled only when symbol defined

### Screener Page (/market/screener)
- **ScreenerFilters**: Sector dropdown (populated from useSectorPerformance), industry text input, min volume, min/max change %, min/max P/E. "Lọc" and "Xóa bộ lọc" buttons.
- **ScreenerTable**: 10-column sortable table (Mã, Tên, Ngành, Giá, KL, %1D, %7D, %30D, P/E, Vốn hóa). Clickable headers with ▲/▼ indicators. Symbol links to `/ticker/{symbol}`. Color-coded change values.
- **Pagination**: Shows "Hiển thị X–Y / total" with Prev/Next buttons.

### Market Page Update
- Added "Bộ lọc cổ phiếu" outline button linking to /market/screener.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] No shadcn Select component available**
- **Found during:** Task 2
- **Issue:** Plan called for shadcn Select but no `select.tsx` exists in ui components
- **Fix:** Used native HTML `<select>` with matching styling (border, rounded, height classes)
- **Files modified:** frontend/src/components/market/screener-filters.tsx

## Decisions Made

1. Used native `<select>` element styled to match shadcn Input since Select component not installed — avoids adding new dependency for a single dropdown.
2. Reused `useSectorPerformance()` hook to populate sector dropdown options, avoiding a separate API call.

## Self-Check: PASSED

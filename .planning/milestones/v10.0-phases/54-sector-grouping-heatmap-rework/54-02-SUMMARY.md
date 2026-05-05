---
phase: 54-sector-grouping-heatmap-rework
plan: "02"
subsystem: frontend-sector-editing-heatmap
tags: [sector-group, watchlist, heatmap, combobox, inline-editing]
dependency_graph:
  requires:
    - "UserWatchlist.sector_group ORM field"
    - "PATCH /api/watchlist/{symbol} endpoint"
    - "GET /api/tickers/sectors endpoint"
  provides:
    - "SectorCombobox reusable component"
    - "Inline sector editing in watchlist table"
    - "Watchlist-filtered sector-grouped heatmap"
    - "useSectors() and useUpdateSectorGroup() hooks"
    - "updateWatchlistSector() and fetchSectors() API functions"
  affects:
    - "frontend/src/lib/api.ts"
    - "frontend/src/lib/hooks.ts"
    - "frontend/src/components/sector-combobox.tsx"
    - "frontend/src/components/watchlist-table.tsx"
    - "frontend/src/app/page.tsx"
tech_stack:
  added: []
  patterns:
    - "Popover + Command combobox pattern (base-ui/cmdk) for inline editing"
    - "data-checked attribute for built-in CheckIcon in shadcn v4 CommandItem"
    - "useMemo join of watchlist + market data for heatmap filtering"
    - "sector_group override with ICB sector fallback for heatmap grouping"
key_files:
  created:
    - "frontend/src/components/sector-combobox.tsx"
  modified:
    - "frontend/src/lib/api.ts"
    - "frontend/src/lib/hooks.ts"
    - "frontend/src/components/watchlist-table.tsx"
    - "frontend/src/app/page.tsx"
decisions:
  - "Used data-checked attribute instead of manual Check icon to leverage shadcn v4 CommandItem built-in CheckIcon"
  - "Heatmap empty state uses Card component for consistent styling with error states"
  - "Market stats cards remain full-market scope — only heatmap is watchlist-filtered"
metrics:
  duration: "~3 minutes"
  completed: "2026-05-04T09:47:43Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 0
  tests_passing: 0
---

# Phase 54 Plan 02: Frontend Sector Editing & Heatmap Rework Summary

**One-liner:** SectorCombobox with Popover+Command inline editing in watchlist table + watchlist-only sector-grouped heatmap on home page

## What Was Done

### Task 1: Add sector types, API functions, hooks, and SectorCombobox component
**Commit:** `1260b7b` — feat(54-02)

1. **WatchlistItem type** — Added `sector_group: string | null` to the `WatchlistItem` interface in `api.ts`.

2. **API functions** — Added `updateWatchlistSector()` (PATCH `/watchlist/{symbol}`) and `fetchSectors()` (GET `/tickers/sectors`) to `api.ts`.

3. **React Query hooks** — Added `useSectors()` (staleTime: 10 min) and `useUpdateSectorGroup()` (invalidates `["watchlist"]` on success) to `hooks.ts`.

4. **SectorCombobox component** — Created `sector-combobox.tsx` using project's existing `@base-ui/react` Popover + `cmdk` Command components. Uses `data-checked` attribute for the built-in CheckIcon in shadcn v4 CommandItem. Features: fuzzy search, click-to-deselect, stopPropagation to prevent table row navigation.

### Task 2: Add sector column to watchlist table and rework home page heatmap
**Commit:** `6222b69` — feat(54-02)

1. **Watchlist table sector column** — Added "Ngành" column with `SectorCombobox` inline editing between "Tên" and "Giá" columns. Uses `useSectors()` for auto-suggest list and `useUpdateSectorGroup()` for persistence.

2. **Home page heatmap rework** — Changed from showing all ~400 market tickers to showing only watchlist tickers. Added `watchlistHeatmapData` useMemo that joins watchlist + market-overview data and overrides `sector` with user's `sector_group` (fallback to ICB sector → "Khác"). Added empty state card for empty watchlist.

3. **Subtitle update** — Dynamic subtitle shows watchlist count when items exist, or CTA to add items when empty.

4. **Market stats preservation** — Stats cards (gainers/losers/unchanged/total) and top movers section still use full market data from `useMarketOverview()`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Adapted SectorCombobox to use data-checked instead of manual Check icon**
- **Found during:** Task 1
- **Issue:** Plan's code included a manual `<Check>` icon from lucide-react, but the project's shadcn v4 `CommandItem` already renders a built-in `CheckIcon` that responds to `data-checked` attribute. Using both would produce duplicate check marks.
- **Fix:** Removed manual Check icon, added `data-checked={value === sector || undefined}` to CommandItem
- **Files modified:** `frontend/src/components/sector-combobox.tsx`
- **Commit:** `1260b7b`

## Verification Results

| Check | Result |
|-------|--------|
| TypeScript compilation (Task 1) | ✅ `npx tsc --noEmit` — zero errors |
| TypeScript compilation (Task 2) | ✅ `npx tsc --noEmit` — zero errors |
| WatchlistItem has sector_group | ✅ Field present in interface |
| API functions exist | ✅ `updateWatchlistSector`, `fetchSectors` exported |
| Hooks exist | ✅ `useSectors`, `useUpdateSectorGroup` exported |
| SectorCombobox min lines | ✅ 62 lines (>40 required) |
| Watchlist table has sector column | ✅ "Ngành" column with SectorCombobox |
| Home page uses watchlist data | ✅ `useWatchlist` imported and used |
| Heatmap filters to watchlist | ✅ `watchlistHeatmapData` passed to Heatmap |
| Empty state present | ✅ Card with CTA shown when no watchlist items |

## Known Stubs

None — all components are fully wired to API functions and hooks. The SectorCombobox, watchlist table column, and heatmap all connect to real backend endpoints delivered in Plan 01.

## Threat Flags

None — no new network endpoints, auth paths, or trust boundary changes. All frontend changes consume existing APIs.

## Self-Check: PASSED

All files exist, all commits verified, all content checks pass.

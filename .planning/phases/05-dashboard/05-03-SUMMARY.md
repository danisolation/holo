---
phase: 05-dashboard
plan: 03
subsystem: frontend-dashboard
tags: [navbar, watchlist, dashboard, responsive, recharts, tanstack-table]
dependency_graph:
  requires: [05-01, 05-02]
  provides: [responsive-navbar, watchlist-page, dashboard-summary]
  affects: [frontend/src/app/layout.tsx, frontend/src/app/page.tsx, frontend/src/app/ticker/[symbol]/page.tsx]
tech_stack:
  added: []
  patterns: [responsive-dual-view, per-cell-data-fetch, zustand-to-table-bridge]
key_files:
  created:
    - frontend/src/components/navbar.tsx
    - frontend/src/components/watchlist-table.tsx
    - frontend/src/app/watchlist/page.tsx
    - frontend/src/app/dashboard/page.tsx
  modified:
    - frontend/src/app/layout.tsx
    - frontend/src/app/page.tsx
    - frontend/src/app/ticker/[symbol]/page.tsx
    - frontend/src/components/heatmap.tsx
decisions:
  - "CSS-only dark mode toggle (Sun/Moon icon swap via dark: classes) avoids hydration mismatch"
  - "Per-ticker SignalCell component in watchlist table — each row fetches its own analysis summary"
  - "Heatmap dual-view: mobile scrollable list (< md) + desktop dense grid (>= md)"
  - "Refactored home + ticker pages to remove inline headers — global Navbar in layout.tsx"
metrics:
  duration: 10m
  completed: "2026-04-15"
  tasks_completed: 2
  files_changed: 8
---

# Phase 5 Plan 3: Navbar, Watchlist & Dashboard Summary

Responsive navbar with dark mode toggle, watchlist page with @tanstack/react-table sortable data table, dashboard summary with Recharts PieChart and top movers, plus responsive polish across all pages.

## What Was Built

### Navbar (`navbar.tsx`)
- Logo "Holo" linking to `/`
- Desktop nav links: Tổng quan (/), Danh mục (/watchlist), Bảng điều khiển (/dashboard)
- Active link highlighting via `usePathname()`
- Compact `TickerSearch` trigger in navbar (hidden on small mobile)
- Dark mode toggle with CSS-only Sun/Moon icon transition (no hydration issues)
- Mobile: hamburger → Sheet slide-out drawer with full nav + search
- Sticky top with blur backdrop

### Watchlist Table (`watchlist-table.tsx`)
- @tanstack/react-table with `getCoreRowModel` + `getSortedRowModel`
- 6 columns: Mã (Symbol), Tên (Name), Giá (Price), Thay đổi (Change %), Tín hiệu (Signal), Actions (remove)
- Sortable column headers via `ArrowUpDown` toggle buttons
- Per-row `SignalCell` component fetches `useAnalysisSummary` for combined signal badge
- Row click navigates to `/ticker/[symbol]`
- Remove button calls `removeFromWatchlist` from zustand store
- Empty state: Vietnamese guidance to browse market overview
- Loading state: skeleton rows

### Watchlist Page (`/watchlist`)
- Title "Danh mục theo dõi" with ticker count badge
- Renders `WatchlistTable` component

### Dashboard Page (`/dashboard`)
- Section 1: Watchlist summary cards — per-ticker `TickerSummaryCard` with signal badge, score, truncated reasoning
- Section 2: Market stats — gainers/losers/unchanged cards from `useMarketOverview`
- Section 3: Recharts `PieChart` (donut) showing market distribution (gainers/losers/unchanged)
- Section 4: Top movers — top 5 gainers + top 5 losers as clickable links
- Responsive grid: 1 col mobile → 2-3 cols desktop
- Loading states with skeletons throughout

### Layout Update
- Global `Navbar` imported in `layout.tsx` (server component importing client component)
- `<main className="flex-1 container mx-auto px-4 py-6 max-w-7xl">` wrapper for all pages
- Home page (`page.tsx`): removed inline header + outer wrapper
- Ticker detail page: removed sticky header + wrapper, converted to `<div className="space-y-6">`

### Responsive Polish
- Heatmap: dual-view — mobile shows scrollable list with colored left border, desktop keeps dense grid
- Tables: shadcn `Table` already wraps in `overflow-x-auto`
- Dashboard cards: `grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`
- Analysis cards: already `grid-cols-1 md:grid-cols-3`
- Navbar: hamburger Sheet menu on mobile

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed duplicate page-level headers**
- **Found during:** Task 2 (layout update)
- **Issue:** Home page and ticker detail page had their own inline `<header>` + `<main>` wrappers. Adding global Navbar in layout would create duplicate headers.
- **Fix:** Refactored both pages to remove their inline wrappers, relying on layout's Navbar + main container.
- **Files modified:** `frontend/src/app/page.tsx`, `frontend/src/app/ticker/[symbol]/page.tsx`
- **Commits:** e32d888

## Verification Results

- `npm run build`: ✅ Zero TypeScript errors, all 5 routes compiled (/, /_not-found, /dashboard, /ticker/[symbol], /watchlist)
- `pytest tests/ -v`: ✅ 96/96 tests passed

## Known Stubs

None — all data flows are wired to real API hooks (`useMarketOverview`, `useAnalysisSummary`, `useWatchlistStore`).

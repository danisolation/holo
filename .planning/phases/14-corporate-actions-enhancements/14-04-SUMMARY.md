---
phase: 14-corporate-actions-enhancements
plan: 04
subsystem: frontend
tags: [corporate-events, calendar, price-toggle, dilution-badge, ui-components]
dependency_graph:
  requires: [corporate-events-api, adjusted-price-toggle]
  provides: [corporate-events-calendar-page, price-toggle-ui, dilution-badge-ui]
  affects: [navbar, candlestick-chart, holdings-table, globals-css]
tech_stack:
  added: [shadcn-popover]
  patterns: [popover-day-click, css-custom-properties-event-colors, adjusted-price-refetch]
key_files:
  created:
    - frontend/src/components/corporate-events-calendar.tsx
    - frontend/src/app/dashboard/corporate-events/page.tsx
    - frontend/src/components/dilution-badge.tsx
    - frontend/src/components/ui/popover.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/components/candlestick-chart.tsx
    - frontend/src/components/holdings-table.tsx
    - frontend/src/components/navbar.tsx
    - frontend/src/app/ticker/[symbol]/page.tsx
    - frontend/src/app/globals.css
decisions:
  - "Popover-based day click instead of expand-below for better UX (UI-SPEC alignment)"
  - "Event type colors via CSS custom properties for theme-aware light/dark support"
  - "DilutionBadge as separate component for reusability and clean HoldingsTable code"
  - "font-semibold (600) used per UI-SPEC typography contract, not font-bold (700)"
metrics:
  duration: ~9m
  completed: "2026-04-17T13:17:52Z"
  tests_added: 0
  tests_total: 0
  files_changed: 11
requirements: [CORP-06, CORP-08, CORP-09]
---

# Phase 14 Plan 04: Corporate Events Frontend Components Summary

**One-liner:** Calendar page with monthly grid and event type filters at /dashboard/corporate-events, adjusted/raw price toggle on candlestick chart, and amber dilution badge on holdings table for RIGHTS_ISSUE events

## What Was Built

### Corporate Events Calendar (CORP-08)
- `CorporateEventsCalendar` component (316 lines) with:
  - Monthly grid using CSS grid-cols-7, Mon-Sun (T2-CN) Vietnamese headers
  - Month navigation with ← → buttons ("Tháng MM/YYYY" label)
  - Event type filter tabs (line variant): Tất cả, Cổ tức tiền, Cổ tức CP, Thưởng CP, Quyền mua
  - Colored event dots per day cell (4 event type colors via CSS custom properties)
  - Popover on day click showing event list with type badges, symbol links, ex-date details
  - Today indicator with primary ring, outside-month days at 40% opacity
  - Empty state: "Không có sự kiện trong tháng này"
  - Loading state: Skeleton grid
- Dashboard page at `/dashboard/corporate-events` with page heading and description
- Navbar updated with "Sự kiện" link between "Đầu tư" and "Hệ thống"

### Adjusted/Raw Price Toggle (CORP-09)
- CandlestickChart props extended: `adjusted?: boolean`, `onAdjustedChange?: (adjusted: boolean) => void`
- Toggle button group: "Giá ĐC" (adjusted) / "Giá gốc" (raw) with vertical separator
- Left button `rounded-r-none border-r-0`, right button `rounded-l-none` (connected buttons)
- Ticker detail page owns state: `useState(true)` → passed to usePrices and CandlestickChart
- React Query automatic refetch on adjusted change via queryKey `["prices", symbol, days, adjusted]`
- Label prefix "Hiển thị:" matching existing "Khoảng thời gian:" pattern

### Dilution Badge (CORP-06 UI)
- `DilutionBadge` component with amber RIGHTS_ISSUE color, AlertTriangle icon
- Formula: `dilution_pct = (ratio / (100 + ratio)) * 100`
- Native tooltip: "Quyền mua {ratio}:100 — Ex-date: DD/MM/YYYY"
- HoldingsTable fetches RIGHTS_ISSUE events, cross-references against holdings symbols
- Only shows for future ex_date events, keeps nearest event per symbol

### API & Hooks Layer
- `CorporateEventResponse` interface in api.ts matching backend schema
- `fetchCorporateEvents(params?)` with month/type/symbol query params
- `fetchPrices` updated: accepts `adjusted: boolean` param (default true)
- `useCorporateEvents` hook with 10-min staleTime
- `usePrices` hook updated: accepts `adjusted` param, included in queryKey

### CSS Custom Properties
- Event type colors in both `:root` (light) and `.dark`:
  - `--event-cash-dividend`: green (#16a34a / #4ade80)
  - `--event-stock-dividend`: blue (#2563eb / #60a5fa)
  - `--event-bonus-shares`: purple (#9333ea / #c084fc)
  - `--event-rights-issue`: amber (#d97706 / #fbbf24)
- Registered in `@theme inline` block for Tailwind v4 color access

## Task Commits

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | API types + calendar page + navbar | `4f573e0` | api.ts, hooks.ts, corporate-events-calendar.tsx, page.tsx, navbar.tsx, globals.css, popover.tsx |
| 2 | Adjusted/raw price toggle | `bff794b` | candlestick-chart.tsx, ticker/[symbol]/page.tsx |
| 3 | Dilution impact badge | `c6dee75` | dilution-badge.tsx, holdings-table.tsx |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Functionality] Popover-based day click instead of expand-below**
- **Found during:** Task 1
- **Issue:** Plan described "expands below the grid" for day click, but UI-SPEC specified EventDayPopover with better UX
- **Fix:** Used shadcn Popover (per UI-SPEC) anchored to day cells — better spatial association and doesn't push content down
- **Files modified:** `frontend/src/components/corporate-events-calendar.tsx`
- **Commit:** `4f573e0`

**2. [Rule 2 - Missing Functionality] CSS custom properties for event type colors**
- **Found during:** Task 1
- **Issue:** Plan didn't explicitly mention CSS custom properties for event colors, but UI-SPEC required them for theme-aware styling
- **Fix:** Added `--event-*` properties to globals.css in both `:root` and `.dark` blocks, registered in `@theme inline`
- **Files modified:** `frontend/src/app/globals.css`
- **Commit:** `4f573e0`

## Decisions Made

1. **Popover-based day click**: Used shadcn Popover instead of expand-below for better UX — popover stays spatially anchored to the clicked day, doesn't shift layout.
2. **Event type colors via CSS custom properties**: Theme-aware colors (light/dark) following the `--exchange-*` pattern from Phase 12. Allows Tailwind v4 `bg-event-*` classes.
3. **DilutionBadge as separate component**: Extracted to `dilution-badge.tsx` for clean separation. Can be reused in other contexts (e.g., watchlist).
4. **font-semibold (600) per UI-SPEC**: All new text uses `font-semibold` instead of `font-bold` to comply with typography contract.

## Self-Check: PASSED

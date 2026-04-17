---
phase: 12-multi-market-foundation
plan: "04"
subsystem: frontend
tags: [exchange-filter, exchange-badge, watchlist, dashboard, ticker-detail, analyze-now, ticker-search, multi-exchange]
dependency_graph:
  requires: [exchange-filter-component, exchange-badge-component, exchange-store, exchange-aware-hooks, exchange-css-variables]
  provides: [exchange-aware-watchlist, exchange-aware-dashboard, ticker-detail-exchange-badge, analyze-now-button, exchange-aware-search]
  affects: [frontend/src/components/watchlist-table.tsx, frontend/src/app/watchlist/page.tsx, frontend/src/app/dashboard/page.tsx, frontend/src/app/layout.tsx, frontend/src/app/ticker/[symbol]/page.tsx, frontend/src/components/ticker-search.tsx]
tech_stack:
  added: []
  patterns: [exchange-filtered-table-rows, analyze-now-cooldown-60s, inline-component-pattern]
key_files:
  created: []
  modified:
    - frontend/src/components/watchlist-table.tsx
    - frontend/src/app/watchlist/page.tsx
    - frontend/src/app/dashboard/page.tsx
    - frontend/src/app/layout.tsx
    - frontend/src/app/ticker/[symbol]/page.tsx
    - frontend/src/components/ticker-search.tsx
decisions:
  - AnalyzeNowButton defined inline in ticker detail page (not separate component file) — single-use, tightly coupled to page context
  - 60-second cooldown for AnalyzeNow covers both success and error states to prevent Gemini API spam
  - Exchange badge hidden on mobile in watchlist table (hidden sm:inline) — exchange column header also hidden sm:flex
metrics:
  duration: "4m 37s"
  completed: "2026-04-17T18:07:13Z"
  tasks: 3
  tests_added: 0
  tests_total: 222
  files_changed: 6
requirements:
  - MKT-02
  - MKT-04
---

# Phase 12 Plan 04: Frontend Page Exchange Integration + AnalyzeNow Summary

**One-liner:** Exchange badges and filter tabs on watchlist/dashboard/ticker-detail/search pages, plus AnalyzeNowButton with 60s cooldown for on-demand HNX/UPCOM AI analysis.

## What Was Built

### Task 1: Watchlist + Dashboard + Layout Exchange Integration

**Watchlist Table (watchlist-table.tsx):**
- Added exchange column ("Sàn") with sortable header and ExchangeBadge per row
- Added `useExchangeStore` integration to filter rows by selected exchange
- `filteredRows` useMemo filters by `selectedExchange`, used as `useReactTable` data
- Exchange-aware empty state: shows exchange-specific message when filtered

**Watchlist Page (watchlist/page.tsx):**
- Added `<ExchangeFilter />` tabs between page title and `<WatchlistTable />`
- Filter persists across pages via zustand persist store

**Dashboard Page (dashboard/page.tsx):**
- Added `<ExchangeFilter />` tabs after page title
- `useExchangeStore` exchange passed to `useMarketOverview(exchange)` — market stats recalculate per exchange
- All stat cards (gainers/losers/unchanged), pie chart, and top movers respond to exchange filter

**Layout (layout.tsx):**
- Updated metadata description to include all 3 exchanges: "HOSE, HNX, UPCOM"

### Task 2: Ticker Detail Page + Search Exchange Integration

**Ticker Detail Page (ticker/[symbol]/page.tsx):**
- Added `ExchangeBadge` in header next to symbol, after BarChart3 icon
- Added `AnalyzeNowButton` inline component with full state machine:
  - **Idle:** Primary button with Sparkles icon + "Phân tích ngay"
  - **Loading:** Disabled, Loader2 spinning, "Đang phân tích..."
  - **Success:** Outline variant, Check icon, "Đã phân tích"
  - **Error:** Error text below button, "Không thể phân tích. Thử lại sau."
  - **Cooldown:** "Thử lại sau {N}s" with 60-second timer
- Visibility conditions: only for HNX/UPCOM, non-watchlisted, no recent analysis
- `useTriggerAnalysis` mutation hook triggers on-demand Gemini analysis
- Updated empty analysis state copy to reference "Phân tích ngay" button

**Ticker Search (ticker-search.tsx):**
- Added `ExchangeBadge` inline in each `CommandItem` between symbol and company name

### Task 3: Visual Verification (Auto-Approved)

Programmatic verification confirmed all multi-exchange UI elements:
- ✅ Exchange filter tabs on market overview, watchlist, and dashboard pages
- ✅ Exchange-colored heatmap borders (from Plan 03)
- ✅ Exchange badge column in watchlist table
- ✅ ExchangeBadge in ticker detail header and search results
- ✅ AnalyzeNowButton on ticker detail for HNX/UPCOM tickers
- ✅ Updated layout metadata with all 3 exchanges
- ✅ TypeScript compiles with zero errors

## Commits

| # | Hash | Type | Description |
|---|------|------|-------------|
| 1 | `901ba2d` | feat | Watchlist + dashboard + layout exchange integration |
| 2 | `71fe741` | feat | Ticker detail ExchangeBadge + AnalyzeNowButton + search badges |

## Backward Compatibility

- Watchlist table renders correctly when no exchange filter is active (default "all")
- Dashboard market stats work without exchange parameter (backward compatible)
- AnalyzeNowButton gracefully handles missing exchange (defaults to "HOSE", hidden)
- Ticker search ExchangeBadge fallback to "HOSE" when exchange field is undefined

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations

| Threat ID | Disposition | Implementation |
|-----------|-------------|----------------|
| T-12-09 (DoS: AnalyzeNowButton spam) | mitigated | 60-second cooldown timer starts on success or error; button disabled during cooldown and pending states |
| T-12-10 (Spoofing: search badge) | accepted | Exchange value comes from API response (trusted server data) — client displays as-is |

## Self-Check: PASSED

All files exist, all commits verified.

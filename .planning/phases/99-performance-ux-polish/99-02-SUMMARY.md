---
phase: 99-performance-ux-polish
plan: "02"
subsystem: frontend-ux
tags: [page-transitions, homepage-redesign, dashboard, css-animations]
dependency_graph:
  requires: [useSimulatorPortfolio, usePendingSignals, useAnalysisCoverage, useMarketOverview]
  provides: [page-transition-animation, homepage-key-metrics]
  affects: [frontend/src/app/layout.tsx, frontend/src/app/page.tsx]
tech_stack:
  added: []
  patterns: [CSS transitions, VND formatting, graceful null fallback]
key_files:
  created:
    - frontend/src/components/page-transition.tsx
  modified:
    - frontend/src/app/layout.tsx
    - frontend/src/app/page.tsx
decisions:
  - Used pure CSS transitions (150ms fade) instead of framer-motion to avoid dependency bloat
  - Used total_equity from SimulatorPortfolioResponse (not total_value which doesn't exist in type)
  - Displayed signal rank instead of signal_type since PendingSignalResponse has no signal_type field
metrics:
  duration: 211s
  completed: 2026-05-14
---

# Phase 99 Plan 02: Page Transitions & Homepage Redesign Summary

Pure CSS 150ms fade transitions on route changes + homepage redesigned with 4 key metric cards (portfolio, P&L, AI coverage, market ratio) and AI signals/quick stats row above existing heatmap.

## Completed Tasks

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | CSS page transition animation | `e625307` | `page-transition.tsx`, `layout.tsx` |
| 2 | Homepage redesign with key metrics | `e4b2621` | `page.tsx` |

## What Was Built

### Task 1: Page Transition Animation
- Created `PageTransition` client component using `usePathname` to detect route changes
- 150ms CSS opacity transition (fade-out → swap content → fade-in)
- Wrapped `{children}` in `layout.tsx` with `<PageTransition>` wrapper
- No new npm dependencies — pure Tailwind CSS transitions

### Task 2: Homepage Dashboard Redesign
- **Row 1 (4 metric cards):**
  - Danh mục — portfolio total equity formatted as VND millions
  - Lãi/Lỗ hôm nay — total P&L with green/red coloring
  - AI phân tích — coverage ratio (analyzed_today / total_watchlist)
  - Thị trường — gainers↑ / losers↓ with colored counts
- **Row 2 (2 cards):**
  - Tín hiệu AI mới — up to 3 pending signals with ticker, rank, entry price; link to /simulator
  - Thống kê nhanh — total tickers, unchanged count, watchlist size
- Existing heatmap and top movers sections preserved unchanged
- All text in Vietnamese, graceful "—" fallback when data unavailable

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed type mismatch for portfolio fields**
- **Found during:** Task 2
- **Issue:** Plan referenced `total_value` and `cash_balance` but `SimulatorPortfolioResponse` uses `total_equity` and `current_cash`
- **Fix:** Used correct field names from the actual TypeScript interface
- **Files modified:** frontend/src/app/page.tsx
- **Commit:** e4b2621

**2. [Rule 1 - Bug] Fixed PendingSignalResponse field names**
- **Found during:** Task 2
- **Issue:** Plan assumed `id`, `symbol`, `signal_type` fields but actual type uses `daily_pick_id`, `ticker_symbol`, and has no `signal_type` field
- **Fix:** Used correct field names; displayed rank badge instead of signal_type
- **Files modified:** frontend/src/app/page.tsx
- **Commit:** e4b2621

## Verification

- ✅ `cd frontend && npx next build` passes clean
- ✅ No new npm dependencies added
- ✅ All text in Vietnamese
- ✅ Heatmap and top movers sections preserved
- ✅ Portfolio, P&L, AI coverage, market stats, and AI signals shown above the fold

## Self-Check: PASSED

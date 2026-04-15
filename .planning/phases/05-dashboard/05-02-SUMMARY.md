---
phase: 05-dashboard
plan: 02
subsystem: dashboard-pages
tags: [heatmap, candlestick, indicators, analysis-cards, market-overview, ticker-detail, lightweight-charts]
dependency_graph:
  requires: [05-01, backend-api, database-models]
  provides: [market-overview-page, ticker-detail-page, heatmap-component, chart-components, analysis-cards]
  affects: [05-03]
tech_stack:
  added: []
  patterns: [window-function-query, sector-grouped-heatmap, lightweight-charts-v5-candlestick, resizeobserver-responsive, zustand-watchlist-toggle]
key_files:
  created:
    - backend/app/api/tickers.py (market-overview endpoint)
    - frontend/src/components/heatmap.tsx
    - frontend/src/components/ticker-search.tsx
    - frontend/src/components/candlestick-chart.tsx
    - frontend/src/components/indicator-chart.tsx
    - frontend/src/components/analysis-card.tsx
    - frontend/src/app/ticker/[symbol]/page.tsx
  modified:
    - backend/app/api/tickers.py
    - frontend/src/app/page.tsx
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
decisions:
  - "ROW_NUMBER() window function for efficient latest-2-prices-per-ticker query in market-overview endpoint"
  - "CSS Grid heatmap with color interpolation: deep red (-5%) → gray (0%) → deep green (+5%)"
  - "Separate lightweight-charts instances for RSI and MACD sub-panes (independent scaling)"
  - "Vietnamese UI labels throughout: Tổng quan thị trường, Biểu đồ giá, Phân tích AI đa chiều"
metrics:
  duration: 6m
  completed: "2026-04-15"
---

# Phase 5 Plan 2: Dashboard Core Pages Summary

Market overview heatmap with 400 tickers color-coded by daily change %, plus ticker detail page with lightweight-charts v5 candlestick, MA/BB overlays, RSI/MACD sub-panes, and AI verdict cards.

## What Was Built

### Backend: Market Overview Endpoint
- **`GET /tickers/market-overview`** — returns all active tickers with `last_price`, `change_pct`
- Uses SQL `ROW_NUMBER()` window function partitioned by ticker_id, ordered by date desc
- Joins latest close (rn=1) and previous close (rn=2) to compute daily change %
- Efficient single-query approach avoids N+1 problem for 400+ tickers

### Frontend: Market Overview Page (Home)
- **Heatmap component** — CSS Grid, cells grouped by sector with headers and counts
- Color scale: deep red (≤-5%) → gray (0%) → deep green (≥+5%) via RGB interpolation
- Each cell shows symbol + change %, hover shows full name, click navigates to detail
- **Ticker search** — shadcn Command dialog (cmdk) with fuzzy search by symbol/name
- **Stats cards** — total tickers, gainers (green), losers (red), unchanged counts
- Loading skeletons, error states with Vietnamese messages

### Frontend: Ticker Detail Page (`/ticker/[symbol]`)
- **Candlestick chart** — lightweight-charts v5 with OHLCV data
  - MA overlays: SMA 20 (blue), SMA 50 (orange), SMA 200 (purple)
  - Bollinger Bands: upper/middle/lower (gray dashed)
  - Volume histogram below price (green/red by candle direction)
  - Time range selector: 1T, 3T, 6T, 1N, 2N (client-side filtering)
  - ResizeObserver for responsive chart width
- **Indicator sub-charts** — separate lightweight-charts instances
  - RSI (14): line with overbought (70) and oversold (30) reference lines
  - MACD (12,26,9): MACD line + signal line + histogram bars
- **Analysis cards** — AI verdict display for all 4 dimensions
  - Signal badge with Vietnamese labels (MUA/BÁN/GIỮ) and color coding
  - Score bar (1-10 scale with color gradient)
  - Reasoning text + metadata (date, model version)
  - Combined recommendation: prominent card with large signal display
- **Watchlist toggle** — zustand-powered star button (add/remove)
- Loading skeletons, error states with retry buttons

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| # | Hash | Description |
|---|------|-------------|
| 1 | 9b2991d | feat(05-02): market overview page with heatmap and search |
| 2 | eb644a9 | feat(05-02): ticker detail page with candlestick charts and AI verdict |

## Verification

- `npm run build` passes successfully
- All routes render: `/` (static), `/ticker/[symbol]` (dynamic)
- TypeScript compilation clean
- No unresolved imports or type errors

## Self-Check: PASSED

All 11 files verified present. Both commits (9b2991d, eb644a9) found in git log.

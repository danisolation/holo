---
phase: 34-backtest-dashboard
plan: "01"
subsystem: frontend
tags: [backtest, dashboard, recharts, react-query, shadcn]
dependency_graph:
  requires: [Phase 32 backtest engine API, Phase 33 analytics/benchmark API]
  provides: [/dashboard/backtest page, backtest API layer, config form, results tab]
  affects: [navbar.tsx, api.ts, hooks.ts]
tech_stack:
  added: []
  patterns: [polling via refetchInterval, Recharts AreaChart + Line overlay, Tailwind progress bar]
key_files:
  created:
    - frontend/src/app/dashboard/backtest/page.tsx
    - frontend/src/components/backtest/bt-config-tab.tsx
    - frontend/src/components/backtest/bt-results-tab.tsx
    - frontend/src/components/backtest/bt-trades-tab.tsx
    - frontend/src/components/backtest/bt-analytics-tab.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/components/navbar.tsx
decisions:
  - Used Tailwind div-based progress bar instead of shadcn Progress (component not installed)
  - Equity chart uses AreaChart for AI line with gradient fill + Line for VN-Index overlay
  - Polling interval 5s for running backtest status via useBacktestLatest refetchInterval
metrics:
  duration: ~12min
  completed: 2026-04-22
---

# Phase 34 Plan 01: Backtest Dashboard Page with Config, Progress, and Results Summary

Backtest dashboard page at /dashboard/backtest with 4-tab layout, config form with real-time progress polling, and results tab with AI vs VN-Index equity curve overlay plus 5 performance stats cards — all Vietnamese UI text.

## What Was Built

### Task 1: API Types + Fetch Functions + Hooks + Navbar + Page Scaffold + Stubs
- **api.ts**: Added 14 TypeScript interfaces matching all backend Pydantic schemas (BacktestRunResponse, BacktestTradeResponse, BacktestEquityResponse, BenchmarkComparisonResponse, PerformanceSummaryResponse, BacktestAnalyticsResponse, sector/confidence/timeframe breakdowns, etc.)
- **api.ts**: Added 8 fetch functions (fetchStartBacktest, fetchBacktestLatest, fetchBacktestRun, fetchCancelBacktest, fetchBacktestTrades, fetchBacktestEquity, fetchBacktestAnalytics, fetchBacktestBenchmark)
- **hooks.ts**: Added 8 React Query hooks (useBacktestLatest with polling, useBacktestRun, useStartBacktest mutation, useCancelBacktest mutation, useBacktestTrades, useBacktestEquity, useBacktestAnalytics, useBacktestBenchmark)
- **navbar.tsx**: Added "Backtest" link between "Paper Trading" and "Sự kiện" in NAV_LINKS
- **page.tsx**: 4-tab layout (Cấu hình, Kết quả, Lệnh, Phân tích) with data-testid attributes and FlaskConical icon
- **bt-trades-tab.tsx** and **bt-analytics-tab.tsx**: Stub files showing "Đang phát triển..." for Plan 02

### Task 2: Config Tab + Results Tab
- **bt-config-tab.tsx**: Full config form with 4 fields (start date, end date, capital with default 100M VND, slippage 0.5%), "Chạy Backtest" / "Hủy Backtest" buttons, real-time progress bar with status badges (Đang chạy/Hoàn thành/Đã hủy/Lỗi), ETA calculation, and session/run details grid
- **bt-results-tab.tsx**: Equity curve card with Recharts AreaChart overlaying AI Strategy (blue with gradient) and VN-Index (orange line) on same chart, custom tooltip with dd/MM/yyyy format, benchmark summary row (AI Return, VN-Index Return, Outperformance), and 5 stats cards (Tỷ lệ thắng, Tổng P&L, Max Drawdown, Sharpe Ratio, Tổng lệnh)

## Decisions Made

1. **Tailwind progress bar**: shadcn Progress component not installed — used a div-based progress bar with `h-2 rounded-full bg-primary` and percentage width, matching visual style
2. **Recharts AreaChart + Line combo**: Used Area for AI with gradient fill + Line for VN-Index overlay on same chart — matches existing pt-equity-chart.tsx pattern
3. **Polling strategy**: useBacktestLatest(polling=true) uses refetchInterval: 5000 and staleTime: 0 when a run is active

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

| File | Line | Reason |
|------|------|--------|
| bt-trades-tab.tsx | 6 | Stub "Đang phát triển..." — Plan 34-02 will implement trades table |
| bt-analytics-tab.tsx | 6 | Stub "Đang phát triển..." — Plan 34-02 will implement analytics breakdowns |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 0c7b3a9 | API types, fetch functions, hooks, navbar link, page scaffold, stub tabs |
| 2 | 19f7d74 | Config tab with form/progress and results tab with equity chart/stats cards |

## Verification

- `npx tsc --noEmit` — passes with 0 errors
- `npx next build` — compiled successfully
- Page at /dashboard/backtest renders 4-tab layout
- Navbar shows "Backtest" link between Paper Trading and Sự kiện
- All UI text in Vietnamese

## Self-Check: PASSED

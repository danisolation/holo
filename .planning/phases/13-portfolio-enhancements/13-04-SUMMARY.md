---
phase: 13-portfolio-enhancements
plan: "04"
subsystem: portfolio-frontend
tags: [portfolio, charts, recharts, performance, allocation, dividend, frontend]
dependency_graph:
  requires: [fetchPerformanceData, fetchAllocationData, usePerformanceData, useAllocationData, PortfolioSummaryResponse.dividend_income]
  provides: [PerformanceChart, AllocationChart, DividendIncomeCard, Phase13_types, Phase13_hooks, Phase13_fetch_functions]
  affects: [portfolio-summary.tsx, portfolio/page.tsx, api.ts, hooks.ts]
tech_stack:
  added: []
  patterns: [recharts-area-chart, recharts-pie-chart, base-ui-tabs-controlled, responsive-chart-grid]
key_files:
  created:
    - frontend/src/components/performance-chart.tsx
    - frontend/src/components/allocation-chart.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/components/portfolio-summary.tsx
    - frontend/src/app/dashboard/portfolio/page.tsx
decisions:
  - "Recharts AreaChart with monotone interpolation and blue-500 gradient for performance chart"
  - "base-ui Tabs with controlled value/onValueChange for period and mode selectors"
  - "AllocationChart groups >7 items into Khác (Others) with gray-400 color"
  - "Compact VND formatting via Intl.NumberFormat vi-VN notation compact"
metrics:
  duration: "3m"
  completed: "2026-04-17"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 6
---

# Phase 13 Plan 04: Frontend Charts & Dividend Card Summary

All Phase 13 frontend types, API functions, and hooks pre-created; PerformanceChart AreaChart with period tabs, AllocationChart donut PieChart with ticker/sector toggle, and 5-card PortfolioSummary with dividend income card.

## One-liner

Performance line chart, allocation donut chart, dividend income card, and all Phase 13 frontend types/hooks/fetch functions for the portfolio dashboard.

## What Was Built

### Task 1: All Frontend Types, API Functions, and Hooks

**Updated existing types:**
- `HoldingResponse` — added `dividend_income: number` and `sector: string | null` fields
- `PortfolioSummaryResponse` — added `dividend_income: number` field

**New types added to api.ts:**
- `PerformanceDataPoint` — `{ date: string, value: number }`
- `PerformanceResponse` — `{ data: PerformanceDataPoint[], period: string }`
- `AllocationItem` — `{ name: string, value: number, percentage: number }`
- `AllocationResponse` — `{ data: AllocationItem[], mode: string, total_value: number }`
- `TradeUpdateRequest` — `{ side, quantity, price, trade_date, fees? }`
- `CSVPreviewRow` — per-row validation with status (valid/warning/error)
- `CSVDryRunResponse` — `{ format_detected, rows, total_valid, total_warnings, total_errors }`
- `CSVImportResponse` — `{ trades_imported, tickers_recalculated }`

**New fetch functions:**
- `fetchPerformanceData(period)` — GET /portfolio/performance
- `fetchAllocationData(mode)` — GET /portfolio/allocation
- `updateTrade(tradeId, data)` — PUT /portfolio/trades/{id}
- `deleteTrade(tradeId)` — DELETE /portfolio/trades/{id}
- `uploadCSVDryRun(file)` — POST /portfolio/import?dry_run=true (raw fetch for multipart)
- `importCSV(file)` — POST /portfolio/import?dry_run=false (raw fetch for multipart)

**New hooks:**
- `usePerformanceData(period)` — queryKey `["portfolio-performance", period]`, staleTime 5min
- `useAllocationData(mode)` — queryKey `["portfolio-allocation", mode]`, staleTime 2min
- `useUpdateTrade()` — mutation, invalidates holdings/summary/trades/performance/allocation
- `useDeleteTrade()` — mutation, same invalidation pattern
- `useCSVDryRun()` — mutation for dry-run preview
- `useCSVImport()` — mutation, invalidates all portfolio queries on success

### Task 2: Charts + Dividend Card + Page Layout

**PerformanceChart** (`performance-chart.tsx`):
- Recharts `AreaChart` with `Area` type monotone, stroke `#3b82f6`, gradient fill
- Period selector via base-ui `Tabs`: 1T/3T/6T/1N/Tất cả (default 3M)
- Custom tooltip with `var(--popover)` background, formatted VND + date
- XAxis: DD/MM for ≤6M, MM/YY for >6M periods
- YAxis: compact VND formatting (e.g., "1,2B", "500M")
- Loading: Skeleton h-80. Empty: Vietnamese message
- Responsive: tabs wrap below title on mobile (<640px)

**AllocationChart** (`allocation-chart.tsx`):
- Recharts donut `PieChart` with innerRadius=60, outerRadius=100, paddingAngle=2
- Mode toggle: "Mã CK" (ticker) / "Ngành" (sector) via Tabs
- 8-color palette: blue, emerald, amber, rose, violet, cyan, orange, gray
- Groups >7 items into "Khác" with gray-400
- Center label: compact VND total + "Tổng giá trị" subtitle (absolute positioned)
- Legend: horizontal wrapped, colored dots + name + percentage
- Custom tooltip: name + VND value + percentage

**PortfolioSummary update:**
- Grid changed from `grid-cols-2 lg:grid-cols-4` → `grid-cols-2 lg:grid-cols-5`
- 5th card: "Cổ tức nhận" with Coins icon, `text-[#26a69a]` green
- Skeleton count 4 → 5
- Last card spans `col-span-2 lg:col-span-1` for mobile visual balance

**Portfolio page update:**
- Charts section between summary cards and holdings table
- Grid: `grid-cols-1 lg:grid-cols-5 gap-4`
- Performance: `lg:col-span-3` (60% width)
- Allocation: `lg:col-span-2` (40% width)

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `7e1604e` | feat(13-04): add all Phase 13 types, API functions, and hooks |
| 2 | `1eb01aa` | feat(13-04): add performance/allocation charts, dividend card, and page layout |

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **Recharts AreaChart with monotone interpolation** — Smooth curve for daily portfolio value, blue-500 neutral color (not bullish/bearish)
2. **base-ui Tabs controlled mode** — `value` + `onValueChange` for period/mode selectors, consistent with project's base-ui component library
3. **AllocationChart Khác grouping** — Items beyond 7th grouped into "Khác" (Others) with gray-400 to maintain chart readability
4. **Compact VND via Intl.NumberFormat** — `notation: "compact"` with vi-VN locale for Y-axis and center label formatting

## Self-Check: PASSED

All 6 files exist. Both commits verified. All key artifacts (fetchPerformanceData, CSVImportResponse, dividend_income, usePerformanceData, useCSVImport, PerformanceChart, AllocationChart, dividend card) confirmed present.

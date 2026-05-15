---
phase: 102-sector-breadth-frontend
plan: "02"
title: "Breadth tab + Dòng tiền tab"
subsystem: frontend
tags: [market-breadth, sector-flow, recharts, visualization]
dependency_graph:
  requires: [102-01]
  provides: [breadth-tab, flow-tab, ad-line-chart, ma-breadth-chart, highs-lows-chart, sector-radar]
  affects: [market-page]
tech_stack:
  added: []
  patterns: [recharts-line-chart, recharts-bar-chart, recharts-radar-chart, date-range-selector]
key_files:
  created:
    - frontend/src/components/market/breadth-tab.tsx
    - frontend/src/components/market/ad-line-chart.tsx
    - frontend/src/components/market/ma-breadth-chart.tsx
    - frontend/src/components/market/highs-lows-chart.tsx
    - frontend/src/components/market/flow-tab.tsx
    - frontend/src/components/market/sector-radar.tsx
  modified:
    - frontend/src/app/market/page.tsx
key_decisions:
  - "Used BarChart for highs/lows (side-by-side bars are clearer than overlapping lines)"
  - "Flow summary uses div-based horizontal bars (simple, no extra Recharts chart needed)"
  - "Date range default 90d to show broader market context"
metrics:
  duration: "2.8 minutes"
  completed: "2026-05-15T02:51:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 1
---

# Phase 102 Plan 02: Breadth Tab + Dòng Tiền Tab Summary

Breadth tab with 3 Recharts time-series charts (A/D line, MA breadth %, 52-week highs/lows) and Dòng tiền tab with RadarChart sector comparison and net flow horizontal bars — completes all 3 tabs on /market page.

## What Was Built

### Task 1: Breadth Tab (A/D Line, MA Breadth, Highs/Lows Charts)

- **BreadthTab** (`breadth-tab.tsx`): Container with `7D/30D/90D` date range selector buttons, calls `useMarketBreadth(startDate)`, shows 3 charts stacked vertically with Skeleton loading states
- **ADLineChart** (`ad-line-chart.tsx`): Recharts LineChart — green (#26a69a) "Tăng" and red (#ef5350) "Giảm" lines with custom tooltip showing date + net
- **MABreadthChart** (`ma-breadth-chart.tsx`): Recharts LineChart — blue (#2196f3) "% > MA50" and orange (#ff9800) "% > MA200" lines, Y-axis 0-100%, dashed 50% reference line
- **HighsLowsChart** (`highs-lows-chart.tsx`): Recharts BarChart — green/red side-by-side bars for 52-week highs vs lows

### Task 2: Dòng Tiền Tab (Sector Radar + Flow Summary)

- **SectorRadar** (`sector-radar.tsx`): Recharts RadarChart comparing 7D (blue) vs 30D (orange) avg sector performance with PolarGrid, tooltips showing full sector name
- **FlowTab** (`flow-tab.tsx`): Container fetching `useSectorPerformance()` + `useSectorFlow()`, renders radar chart + horizontal bar flow summary
- **Flow Summary**: Latest net_volume per sector as colored horizontal bars — green (mua ròng) for positive, red (bán ròng) for negative, sorted by net_volume descending

### Market Page Update

- Replaced both placeholder divs in `/market` page — all 3 tabs (Sector, Breadth, Dòng tiền) now render real components

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `6f98da5` | feat(102-02): Breadth tab with A/D line, MA breadth, highs/lows charts |
| 2 | `644b615` | feat(102-02): Dòng tiền tab with sector radar chart and flow summary |

## Verification

- TypeScript: `npx tsc --noEmit` — 0 errors
- Build: `npm run build` — compiled successfully, all pages generated
- All 6 new components created with `"use client"` directive
- All charts use ResponsiveContainer for mobile responsiveness
- Skeleton loading states on both tabs
- Vietnamese labels throughout

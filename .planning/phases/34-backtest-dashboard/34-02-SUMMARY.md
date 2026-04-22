---
phase: 34-backtest-dashboard
plan: "02"
subsystem: frontend
tags: [backtest, trades-table, analytics, recharts, tanstack-react-table]
dependency_graph:
  requires: [Plan 34-01 page scaffold + config + results tabs]
  provides: [BTTradesTab trade log table, BTAnalyticsTab breakdown charts]
  affects: [bt-trades-tab.tsx, bt-analytics-tab.tsx]
tech_stack:
  added: []
  patterns: [tanstack/react-table with getSortedRowModel, Recharts BarChart with Cell conditional coloring, useMemo client-side filtering]
key_files:
  created: []
  modified:
    - frontend/src/components/backtest/bt-trades-tab.tsx
    - frontend/src/components/backtest/bt-analytics-tab.tsx
decisions:
  - Client-side symbol and direction filtering via useMemo (backtest trades are finite, no server-side needed)
  - Holding time computed from date difference in browser (entry_date/closed_date)
  - Confidence chart uses Cell-based conditional coloring (green/red per bar) instead of dual-axis approach
metrics:
  duration: ~8min
  completed: 2026-04-22
---

# Phase 34 Plan 02: Trade Log Table & Analytics Breakdown Charts Summary

**One-liner:** Full trade log table with 11 sortable columns via @tanstack/react-table, plus 3 Recharts BarChart analytics breakdowns (sector, confidence, timeframe) — completing the backtest dashboard.

## What Was Built

### Task 1: Trade Log Table (DASH-05)
Replaced the `bt-trades-tab.tsx` stub with a fully-featured trade table using `@tanstack/react-table`.

**Features:**
- 11 columns: signal_date, symbol, direction, entry_price, exit_price, realized_pnl, realized_pnl_pct, holding_time (computed), confidence, timeframe, status
- Sortable columns: Ngày (date), Entry (price), P&L, AI (confidence) — via `getSortedRowModel`
- Client-side symbol filter (Input with uppercase conversion)
- Direction toggle buttons: Tất cả / Long / Bearish — via `useMemo` filtering
- Holding time computed as `Math.round((closedDate - entryDate) / 86400000)` days
- Vietnamese status badges: Chờ, Đang mở, Chốt 1 phần, Chốt TP2, Cắt lỗ, Hết hạn
- P&L coloring: green (#26a69a) for positive, red (#ef5350) for negative
- Empty state + no-completed-run state messages
- Footer showing total trade count

**Commit:** `c0e882d` — 258 lines

### Task 2: Analytics Breakdown Charts (DASH-06)
Replaced the `bt-analytics-tab.tsx` stub with 3 Recharts chart sections.

**Section 1 — Sector Breakdown:**
- Horizontal `BarChart` (layout="vertical") showing total P&L (blue) and avg P&L (purple) per sector
- Dynamic height based on sector count
- Custom tooltip with Vietnamese labels

**Section 2 — Confidence Breakdown:**
- Vertical `BarChart` with conditional Cell coloring per bracket (green if avg_pnl ≥ 0, red otherwise)
- "Best bracket" summary annotation below chart
- Custom tooltip showing bracket details

**Section 3 — Timeframe/Holding Period Breakdown:**
- Vertical `BarChart` with conditional Cell coloring for total P&L per bucket
- Summary stats table below chart: Nhóm, Lệnh, Win Rate (Badge), TB Ngày giữ, Tổng P&L

**Commit:** `ffb224a` — 321 lines

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **Client-side filtering:** Backtest trades are a finite completed dataset (≤200 trades fetched), so symbol/direction filtering is done via `useMemo` rather than re-fetching from server.
2. **Holding time in browser:** Computed from `entry_date` and `closed_date` string difference — simpler than adding a server-side field.
3. **Confidence chart approach:** Used single Bar with Cell conditional coloring per bracket instead of the dual-axis approach (cleaner, satisfies DASH-06).

## Verification

- TypeScript compilation: ✅ `npx tsc --noEmit` passes
- Full build: ✅ `npx next build` passes with no errors
- bt-trades-tab.tsx: 258 lines (≥150 required) ✅
- bt-analytics-tab.tsx: 321 lines (≥100 required) ✅
- All columns present with correct formatters ✅
- All 3 chart sections with tooltips ✅

## Self-Check: PASSED

- [x] bt-trades-tab.tsx exists (258 lines)
- [x] bt-analytics-tab.tsx exists (321 lines)
- [x] 34-02-SUMMARY.md exists
- [x] Commit c0e882d found
- [x] Commit ffb224a found
- [x] `next build` passes

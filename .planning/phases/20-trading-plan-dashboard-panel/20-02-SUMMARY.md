---
phase: 20-trading-plan-dashboard-panel
plan: 02
title: "TradingPlanPanel Component + Page Integration"
one_liner: "Two-column LONG/BEARISH trading plan panel with Vietnamese labels, confidence ScoreBar, entry/SL/TP/R:R rows, and recommended-direction highlighting"
completed: "2026-04-20T12:10:16Z"
duration: "2.3m"
tasks_completed: 2
tasks_total: 2
subsystem: "frontend-ui"
tags: [trading-plan, react-component, ticker-page, vietnamese-ui]
dependency_graph:
  requires: ["ScoreBar export (20-01)", "TickerTradingSignal types (20-01)", "useTradingSignal hook (20-01)", "fetchTradingSignal (20-01)"]
  provides: ["TradingPlanPanel component", "TradingPlanEmpty component", "Trading plan section on ticker detail page"]
  affects: []
tech_stack:
  added: []
  patterns: ["cn() utility for dynamic class composition", "Conditional border-l-2 accent highlighting", "Vietnamese price formatting toLocaleString('vi-VN')"]
key_files:
  created:
    - frontend/src/components/trading-plan-panel.tsx
  modified:
    - frontend/src/app/ticker/[symbol]/page.tsx
key_decisions:
  - "Used cn() for all dynamic className composition (project convention over template literals)"
  - "TP2 row conditionally rendered only when Math.abs(tp2 - tp1) > 1 (avoid duplicate display)"
  - "TradingPlanEmpty exported but not used on page — matches 'no data = no panel' page convention"
  - "Panel uses its own independent hook (useTradingSignal) — not coupled to analysisLoading state"
metrics:
  duration: "2.3m"
  completed: "2026-04-20"
  tasks: 2
  files: 2
requirements: [DISP-01]
---

# Phase 20 Plan 02: TradingPlanPanel Component + Page Integration Summary

Two-column LONG/BEARISH trading plan panel with Vietnamese labels, confidence ScoreBar, entry/SL/TP/R:R rows, and recommended-direction highlighting

## What Was Done

### Task 1: Create TradingPlanPanel component
**Commit:** `a1199b5`

- Created `frontend/src/components/trading-plan-panel.tsx` (189 lines)
- `TradingPlanPanel` — main component with Card wrapper, two-column grid layout (LONG left, BEARISH right)
- `DirectionColumn` — internal sub-component rendering confidence ScoreBar, 7 dense price/data rows, reasoning text
- Recommended direction highlighted with `border-l-2` accent + tinted background (`bg-[color]/5`) + "Khuyến nghị" badge
- Vietnamese labels: "Kế Hoạch Giao Dịch", "Giá vào", "Cắt lỗ", "Chốt lời 1/2", "Tỷ lệ R:R", "Khối lượng", "Khung thời gian"
- Stop-loss colored `#ef5350`, take-profits colored `#26a69a`
- TP2 conditionally rendered only when different from TP1 by >1
- Invalid signal state (confidence=0): "Tín hiệu không hợp lệ" with muted styling
- `TradingPlanEmpty` exported for empty state: "Chưa có kế hoạch giao dịch"
- Responsive: `grid-cols-1 md:grid-cols-2` (stacked on mobile)
- `next build` passes

### Task 2: Integrate TradingPlanPanel into ticker detail page
**Commit:** `8d36104`

- Added `TradingPlanPanel` import from `@/components/trading-plan-panel`
- Added `useTradingSignal` to hooks import
- Called `useTradingSignal(upperSymbol)` independently (own loading state)
- Inserted Trading Plan section between Combined Recommendation and Analysis Cards Grid
- Loading: `Skeleton h-[320px] rounded-xl`
- Data exists: renders `<TradingPlanPanel data={tradingSignal} />`
- No data: renders nothing (matches existing page pattern)
- `next build` passes with zero errors

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **cn() utility**: Used `cn()` from `@/lib/utils` for all conditional className composition instead of template literals — follows project convention
2. **TP2 conditional**: Renders only when `Math.abs(tp2 - tp1) > 1` to avoid showing duplicate row
3. **Independent hook**: `useTradingSignal` runs independently from `useAnalysisSummary` — panel has its own loading state
4. **No empty state on page**: `TradingPlanEmpty` exported but not rendered on page — "no data = no panel" matches existing `CombinedRecommendationCard` pattern

## Verification Results

| Check | Result |
|-------|--------|
| `TradingPlanPanel` exported | ✅ trading-plan-panel.tsx |
| `TradingPlanEmpty` exported | ✅ trading-plan-panel.tsx |
| ScoreBar imported from analysis-card | ✅ |
| Vietnamese labels match copywriting contract | ✅ All 13 labels verified |
| Price formatting `toLocaleString("vi-VN")` | ✅ |
| Recommended direction accent border + badge | ✅ |
| Page integration position correct | ✅ After CombinedRecommendation, before Analysis Cards |
| `useTradingSignal` hook called | ✅ Independent from analysisLoading |
| `next build` Task 1 | ✅ Compiled successfully |
| `next build` Task 2 | ✅ Compiled successfully |

## Self-Check: PASSED

All 2 files verified present. Both commits (a1199b5, 8d36104) confirmed. All exports verified via grep.

---
phase: 21-chart-price-line-overlays
plan: 01
subsystem: frontend
tags: [chart, price-lines, lightweight-charts, trading-signal, overlay]
dependency_graph:
  requires: [useTradingSignal hook (Phase 20), CandlestickChart (Phase 5)]
  provides: [Price line overlays on candlestick chart, TradingPlanOverlay interface]
  affects: [candlestick-chart.tsx, ticker detail page.tsx]
tech_stack:
  added: []
  patterns: [createPriceLine API, conditional TP2 rendering, useMemo-derived chart prop]
key_files:
  created: []
  modified:
    - frontend/src/components/candlestick-chart.tsx
    - frontend/src/app/ticker/[symbol]/page.tsx
decisions:
  - "LineStyle.Dashed import used instead of magic number 2 for type safety"
  - "Price lines added in existing useEffect (not separate effect) — chart.remove() handles cleanup"
  - "TP2 conditional threshold: Math.abs(tp2 - tp1) > 1 — same logic as TradingPlanPanel"
  - "Legend uses dashed borderTop style to visually distinguish from solid MA swatches"
metrics:
  duration: 2.1m
  completed: "2026-04-20T12:27:28Z"
  tasks: 2
  files: 2
---

# Phase 21 Plan 01: Chart Price Line Overlays Summary

Price line overlays (Entry/SL/TP1/TP2) on candlestick chart via lightweight-charts createPriceLine API, driven by recommended direction from useTradingSignal hook.

## What Was Done

### Task 1: Add price line rendering and legend to CandlestickChart (740ca9b)

Modified `frontend/src/components/candlestick-chart.tsx`:

1. **Import:** Added `LineStyle` to lightweight-charts import block
2. **Interface:** Added `TradingPlanOverlay` interface with `entry_price`, `stop_loss`, `take_profit_1`, `take_profit_2`
3. **Props:** Extended `CandlestickChartProps` with optional `tradingPlan?: TradingPlanOverlay`
4. **Price lines:** Added 4 `candleSeries.createPriceLine()` calls inside existing useEffect, after indicator overlays and before `fitContent()`:
   - Entry: `#26a69a` (teal), dashed, 1px, axis label visible
   - SL: `#ef5350` (red), dashed, 1px, axis label visible
   - TP1: `#42a5f5` (blue), dashed, 1px, axis label visible
   - TP2: `#7e57c2` (purple), conditional — only when `|tp2 - tp1| > 1`
5. **Dependencies:** Added `tradingPlan` to useEffect dependency array
6. **Legend:** Added conditionally rendered legend row with dashed border swatches matching line colors

### Task 2: Extract recommended direction and pass tradingPlan to chart (5422fb6)

Modified `frontend/src/app/ticker/[symbol]/page.tsx`:

1. **Import:** Added `useMemo` to React imports
2. **Derivation:** Added `tradingPlanForChart` useMemo that:
   - Returns undefined when no tradingSignal
   - Picks recommended direction's analysis (long or bearish)
   - Returns undefined when confidence === 0
   - Extracts 4 price values from trading_plan
3. **Prop passing:** Added `tradingPlan={tradingPlanForChart}` to CandlestickChart JSX

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `npx next build` — compiled successfully with zero errors (both tasks verified independently)
- Price lines created AFTER setData, BEFORE fitContent (correct ordering)
- Chart cleanup via chart.remove() destroys all price lines (no manual cleanup needed)
- TP2 conditional gating matches TradingPlanPanel logic
- Zero-confidence signals produce no price lines

## Self-Check: PASSED

All files exist, both commits verified (740ca9b, 5422fb6), all key patterns confirmed in source files.

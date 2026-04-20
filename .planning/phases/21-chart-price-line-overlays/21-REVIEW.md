---
phase: 21-chart-price-line-overlays
reviewed: 2026-04-20T12:31:14Z
depth: standard
files_reviewed: 2
files_reviewed_list:
  - frontend/src/components/candlestick-chart.tsx
  - frontend/src/app/ticker/[symbol]/page.tsx
findings:
  critical: 0
  warning: 1
  info: 2
  total: 3
status: issues_found
---

# Phase 21: Code Review Report

**Reviewed:** 2026-04-20T12:31:14Z
**Depth:** standard
**Files Reviewed:** 2
**Status:** issues_found

## Summary

Reviewed the Phase 21 changes that add trading plan price line overlays (Entry, SL, TP1, TP2) to the candlestick chart and a corresponding legend. The implementation is clean overall — price lines are created correctly using `lightweight-charts` `createPriceLine` API, the `LineStyle.Dashed` import is properly used, the `TradingPlanOverlay` interface is well-defined, and the `useMemo` in the page correctly extracts the recommended direction's plan with an early exit on zero confidence.

One logic inconsistency was found: the TP2 legend entry is always rendered when a trading plan exists, but the actual TP2 chart line is conditionally hidden when TP2 ≈ TP1. Two minor info-level items were also noted (magic number, unused type imports).

## Warnings

### WR-01: TP2 Legend Shown Even When TP2 Line Is Hidden

**File:** `frontend/src/components/candlestick-chart.tsx:360-362`
**Issue:** The TP2 legend item (line 360-362) is always rendered when `tradingPlan` is truthy, but the actual TP2 price line on the chart is conditionally rendered only when `Math.abs(take_profit_2 - take_profit_1) > 1` (line 253). When TP2 ≈ TP1 and the line is hidden, the legend still displays a TP2 entry, misleading the user into looking for a line that doesn't exist.
**Fix:** Apply the same condition to the legend. Extract the condition into a variable for DRY:

```tsx
// Inside the component, near the top or in a useMemo:
const showTP2 = tradingPlan
  ? Math.abs(tradingPlan.take_profit_2 - tradingPlan.take_profit_1) > 1
  : false;

// In the useEffect (chart price lines):
if (showTP2) {
  candleSeries.createPriceLine({ /* ... TP2 config ... */ });
}

// In the legend JSX:
{tradingPlan && (
  <div className="flex items-center gap-4 text-xs">
    {/* ... Entry, SL, TP1 ... */}
    {showTP2 && (
      <span className="flex items-center gap-1">
        <span className="inline-block w-3 h-0.5" style={{ borderTop: "1px dashed #7e57c2" }} /> TP2
      </span>
    )}
  </div>
)}
```

Note: `showTP2` should be computed outside the `useEffect` (e.g., via `useMemo`) and added to the effect's dependency array, or simply computed inline in both places.

## Info

### IN-01: Magic Number for TP2 Dedup Threshold

**File:** `frontend/src/components/candlestick-chart.tsx:253`
**Issue:** The threshold `> 1` is a magic number. For VND stock prices (typically 1,000–250,000), this effectively means "not identical" since any real price difference would exceed 1 VND. The intent is correct, but the number `1` reads as if it were a meaningful tolerance when it's really just a near-zero guard.
**Fix:** Extract to a named constant with a comment:

```tsx
/** Minimum price difference (VND) to show TP2 as distinct from TP1 */
const TP2_MIN_DIFF = 1;

// Usage:
if (Math.abs(tradingPlan.take_profit_2 - tradingPlan.take_profit_1) > TP2_MIN_DIFF) {
```

### IN-02: Unused Type Imports

**File:** `frontend/src/components/candlestick-chart.tsx:11-12`
**Issue:** `ISeriesApi` and `SeriesType` are imported as types but never referenced in the file. These are compile-time-erased so there's zero runtime cost, but they add noise.
**Fix:** Remove the unused type imports:

```tsx
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  LineStyle,
  type IChartApi,
} from "lightweight-charts";
```

---

_Reviewed: 2026-04-20T12:31:14Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

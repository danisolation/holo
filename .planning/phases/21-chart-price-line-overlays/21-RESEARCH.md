# Phase 21: Chart Price Line Overlays - Research

**Researched:** 2026-04-20
**Domain:** lightweight-charts v5 PriceLine API, React useEffect lifecycle
**Confidence:** HIGH

## Summary

This phase adds horizontal price line overlays (entry, stop-loss, TP1, TP2) to the existing `CandlestickChart` component using the lightweight-charts v5 `createPriceLine()` API. The project already uses lightweight-charts 5.1.0 (latest on npm) and the chart component already renders candlestick data with MA/BB overlays. The trading signal data is already fetched via the `useTradingSignal` hook (Phase 20) and available in the ticker detail page.

The implementation is straightforward: extend `CandlestickChartProps` with an optional `tradingPlan` prop, call `series.createPriceLine()` for each level inside the existing `useEffect`, and pass the recommended direction's plan from `page.tsx`. No new packages, no new API endpoints, no backend changes.

**Primary recommendation:** Add price lines inside the existing chart `useEffect` cleanup cycle, using the series-level `createPriceLine()` API with the exact color scheme specified in CONTEXT.md decisions.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Use series-level createPriceLine() on the CandlestickSeries (not chart-level)
- lightweight-charts v5: series.createPriceLine({ price, color, lineWidth, lineStyle, title, axisLabelVisible })
- Store price line references to remove/update when data changes
- Entry price: #26a69a (teal/green), Stop loss: #ef5350 (red), Take profit 1: #42a5f5 (blue), Take profit 2: #7e57c2 (purple)
- Line style: dashed (LineStyle.Dashed) for all price lines, Line width: 1px
- Show axis labels: true (axisLabelVisible), Title text: "Entry", "SL", "TP1", "TP2" (abbreviated English)
- CandlestickChart receives trading signal data as new optional prop
- Pass recommended direction's trading plan (entry/SL/TP1/TP2)
- If no trading signal or score=0: show no price lines
- Lines update when ticker changes (useEffect dependency)
- Show only the RECOMMENDED direction's price lines (not both)
- Extend CandlestickChartProps with optional tradingPlan?: { entry_price, stop_loss, take_profit_1, take_profit_2 }
- In the useEffect, after series data is set, add price lines
- Cleanup: remove price lines on data change or unmount
- Pass data from page.tsx using useTradingSignal hook data

### Agent's Discretion
- Exact line opacity/transparency
- Whether to use a legend/tooltip for price line labels
- Ordering of createPriceLine calls
- Whether to also show on volume histogram (no — only candlestick series)

### Deferred Ideas (OUT OF SCOPE)
- Interactive price line dragging for custom entry/SL/TP — out of v3.0 scope
- Support/resistance level overlays — separate feature
- Multi-timeframe price line comparison — future enhancement
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DISP-02 | User can see entry/stop-loss/take-profit price lines overlaid on the candlestick chart | lightweight-charts v5 `createPriceLine()` API on `ISeriesApi`, verified in installed typings. Color scheme, line style, and labels all specified in CONTEXT.md locked decisions. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lightweight-charts | 5.1.0 | Candlestick chart with PriceLine API | Already installed; `createPriceLine()` is native API — no plugins needed [VERIFIED: node_modules/lightweight-charts/dist/typings.d.ts] |
| React | 19.2.4 | Component framework | Already installed [VERIFIED: package.json] |
| Next.js | 16.2.3 | App framework | Already installed [VERIFIED: package.json] |
| TypeScript | ^5 | Type safety | Already installed [VERIFIED: package.json] |

### Supporting
No additional packages needed. This phase uses only existing dependencies.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| series.createPriceLine() | Custom plugin / canvas overlay | Unnecessary complexity; native API does exactly what's needed |

**Installation:** None required — all dependencies already installed.

**Version verification:**
- lightweight-charts: 5.1.0 installed = 5.1.0 latest [VERIFIED: npm view + node_modules]

## Architecture Patterns

### Existing Chart Architecture (Key Context)

```
frontend/src/
├── components/
│   ├── candlestick-chart.tsx    # CandlestickChart — MODIFY (add price lines)
│   └── trading-plan-panel.tsx   # TradingPlanPanel — READ ONLY (reference)
├── lib/
│   ├── api.ts                   # Types: TradingPlanDetail, TickerTradingSignal
│   └── hooks.ts                 # useTradingSignal(symbol) hook
└── app/ticker/[symbol]/
    └── page.tsx                 # Ticker detail — MODIFY (pass tradingPlan prop)
```

### Pattern 1: Props Extension for Trading Plan Data
**What:** Add optional `tradingPlan` prop to `CandlestickChartProps`
**When to use:** When chart needs external data that it doesn't fetch itself
**Rationale:** The chart component doesn't own data fetching — `page.tsx` does via hooks. This matches the existing pattern where `priceData` and `indicatorData` are passed as props. [VERIFIED: candlestick-chart.tsx lines 25-30]

```typescript
// Source: Existing pattern in candlestick-chart.tsx
interface CandlestickChartProps {
  priceData: PriceData[];
  indicatorData?: IndicatorData[];
  adjusted?: boolean;
  onAdjustedChange?: (adjusted: boolean) => void;
  tradingPlan?: {                  // NEW — Phase 21
    entry_price: number;
    stop_loss: number;
    take_profit_1: number;
    take_profit_2: number;
  };
}
```

### Pattern 2: Price Lines Inside Existing useEffect
**What:** Add `createPriceLine()` calls after series data is set, within the same useEffect that creates the chart
**When to use:** Since the entire chart is destroyed and recreated on data change (the useEffect returns `chart.remove()`), price lines are automatically cleaned up
**Rationale:** The existing chart `useEffect` already handles the full lifecycle: create chart → add series → set data → fit content → return cleanup. Price lines should go between "set data" and "fit content". [VERIFIED: candlestick-chart.tsx lines 63-230]

```typescript
// Source: lightweight-charts v5 typings.d.ts line 2448
// Within the existing useEffect, after candleSeries.setData(...)
if (tradingPlan) {
  candleSeries.createPriceLine({
    price: tradingPlan.entry_price,
    color: '#26a69a',
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: 'Entry',
  });
  // ... repeat for SL, TP1, TP2
}
```

### Pattern 3: Conditional TP2 Display
**What:** Only show TP2 if it differs meaningfully from TP1 (match the TradingPlanPanel pattern)
**When to use:** When TP2 ≈ TP1, showing both clutters the chart
**Rationale:** The `TradingPlanPanel` already uses `Math.abs(plan.take_profit_2 - plan.take_profit_1) > 1` as the threshold. Price lines should use the same logic for consistency. [VERIFIED: trading-plan-panel.tsx line 96]

### Pattern 4: Recommended Direction Extraction in page.tsx
**What:** Extract the recommended direction's trading plan before passing to chart
**When to use:** At the page level, where `tradingSignal` data is available
**Rationale:** Decision is locked — show only recommended direction. The extraction logic:

```typescript
// Source: CONTEXT.md locked decisions + api.ts types
const recommendedPlan = tradingSignal
  ? tradingSignal.recommended_direction === 'long'
    ? tradingSignal.long_analysis.trading_plan
    : tradingSignal.bearish_analysis.trading_plan
  : undefined;

// Also check confidence > 0
const recommendedAnalysis = tradingSignal
  ? tradingSignal.recommended_direction === 'long'
    ? tradingSignal.long_analysis
    : tradingSignal.bearish_analysis
  : undefined;

const tradingPlanForChart = recommendedAnalysis?.confidence > 0
  ? recommendedPlan
  : undefined;
```

### Anti-Patterns to Avoid
- **Separate useEffect for price lines:** Don't create a second useEffect to add/remove price lines — the chart is torn down entirely on any data change, so a separate effect would reference a stale chart/series. Keep everything in the single existing useEffect. [VERIFIED: candlestick-chart.tsx line 226-229 — cleanup removes chart]
- **Storing IPriceLine refs separately:** Don't use useRef to store price line references for manual removal — since `chart.remove()` on cleanup destroys everything, manual removal is only needed if you want to update lines without recreating the chart. The current architecture recreates the chart on every render, so this is unnecessary.
- **Using chart-level API:** Don't look for `chart.createPriceLine()` — in v5 it's `series.createPriceLine()`. Chart-level doesn't exist. [VERIFIED: typings.d.ts — createPriceLine is on ISeriesApi only]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Horizontal line overlays | Custom canvas drawing / HTML overlay positioned manually | `series.createPriceLine()` | Native API handles price-to-pixel mapping, scrolling, zooming, axis label rendering [VERIFIED: typings.d.ts] |
| Axis label badges | Custom DOM elements positioned at price scale | `axisLabelVisible: true` + `axisLabelColor` / `axisLabelTextColor` | Built into PriceLine API [VERIFIED: typings.d.ts line 3562-3581] |
| Line styling | CSS border tricks | `lineStyle: LineStyle.Dashed`, `lineWidth: 1` | PriceLine supports Solid/Dotted/Dashed/LargeDashed/SparseDotted [VERIFIED: typings.d.ts lines 73-94] |

**Key insight:** lightweight-charts PriceLine API handles all the hard parts (coordinate mapping, rescaling, scroll sync). Zero custom drawing code needed.

## Common Pitfalls

### Pitfall 1: Missing tradingPlan in useEffect Dependencies
**What goes wrong:** Price lines don't update when trading signal data loads asynchronously (after price data)
**Why it happens:** `tradingPlan` is passed as a prop; if not in the useEffect dependency array, the chart recreates only when prices/indicators change, not when trading plan arrives.
**How to avoid:** Add `tradingPlan` to the useEffect dependency array: `[filteredPrices, filteredIndicators, tradingPlan]`
**Warning signs:** Price lines appear only after manually changing time range (which triggers re-render)

### Pitfall 2: Price Lines Showing for Zero-Confidence Signals
**What goes wrong:** Nonsensical entry/SL/TP lines appear for tickers where the AI produced a zero-confidence signal
**Why it happens:** The API returns trading plan numbers even when confidence=0 (the schema always includes them)
**How to avoid:** Check confidence > 0 in `page.tsx` before passing `tradingPlan` prop. Decision: "If no trading signal or score=0: show no price lines"
**Warning signs:** Random price lines on tickers without meaningful signals

### Pitfall 3: LineStyle Import as Number Literal
**What goes wrong:** Using magic number `2` instead of `LineStyle.Dashed` works but is fragile
**Why it happens:** Existing BB code uses `lineStyle: 2` directly (line 185-186 in candlestick-chart.tsx)
**How to avoid:** Import `LineStyle` enum from `lightweight-charts` and use `LineStyle.Dashed`. More readable and type-safe.
**Warning signs:** N/A — both work, but enum is cleaner

### Pitfall 4: TP2 Line Overlap with TP1
**What goes wrong:** Two price lines stacked exactly on top of each other when TP2 ≈ TP1
**Why it happens:** AI sometimes returns same value for both take-profit levels
**How to avoid:** Apply the same `Math.abs(tp2 - tp1) > 1` threshold used in `TradingPlanPanel` (line 96)
**Warning signs:** A thick/blurry line that looks like a rendering bug

### Pitfall 5: Price Lines Outside Visible Range
**What goes wrong:** Price lines exist but are invisible because they're above/below the candlestick price range
**Why it happens:** AI-generated targets can be far from current price (e.g., very aggressive TP)
**How to avoid:** This is actually fine — lightweight-charts auto-adjusts the price scale to include price lines when `axisLabelVisible: true`. The axis label will always be visible even if the line is at the edge. [VERIFIED: this is default behavior of lightweight-charts price scale auto-fit]
**Warning signs:** If `fitContent()` is called BEFORE price lines are added, the scale may not include them. Add price lines BEFORE `chart.timeScale().fitContent()`.

## Code Examples

### Complete Price Line Creation Block
```typescript
// Source: lightweight-charts typings.d.ts (PriceLineOptions, CreatePriceLineOptions, LineStyle)
// Verified against: candlestick-chart.tsx existing patterns

import { LineStyle, type IPriceLine } from "lightweight-charts";

// Inside the useEffect, after candleSeries.setData(...)
// and BEFORE chart.timeScale().fitContent()
if (tradingPlan) {
  candleSeries.createPriceLine({
    price: tradingPlan.entry_price,
    color: '#26a69a',
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: 'Entry',
  });

  candleSeries.createPriceLine({
    price: tradingPlan.stop_loss,
    color: '#ef5350',
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: 'SL',
  });

  candleSeries.createPriceLine({
    price: tradingPlan.take_profit_1,
    color: '#42a5f5',
    lineWidth: 1,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: 'TP1',
  });

  // Only show TP2 if meaningfully different from TP1
  if (Math.abs(tradingPlan.take_profit_2 - tradingPlan.take_profit_1) > 1) {
    candleSeries.createPriceLine({
      price: tradingPlan.take_profit_2,
      color: '#7e57c2',
      lineWidth: 1,
      lineStyle: LineStyle.Dashed,
      axisLabelVisible: true,
      title: 'TP2',
    });
  }
}
```

### PriceLineOptions Full Interface Reference
```typescript
// Source: lightweight-charts v5.1.0 typings.d.ts lines 3522-3582
interface PriceLineOptions {
  id?: string;                    // optional identifier
  price: number;                  // REQUIRED — the price level
  color: string;                  // line color (default: '')
  lineWidth: LineWidth;           // 1 | 2 | 3 | 4 (default: 1)
  lineStyle: LineStyle;           // Solid=0, Dotted=1, Dashed=2, LargeDashed=3, SparseDotted=4
  lineVisible: boolean;           // show the line (default: true)
  axisLabelVisible: boolean;      // show label on price axis (default: true)
  title: string;                  // text shown ON the line (default: '')
  axisLabelColor: string;         // background color for axis label (defaults to line color)
  axisLabelTextColor: string;     // text color for axis label (default: '')
}

// CreatePriceLineOptions = Partial<PriceLineOptions> & Pick<PriceLineOptions, "price">
// Only 'price' is required; everything else has defaults
```

### Props Extraction in page.tsx
```typescript
// Source: api.ts types + CONTEXT.md decision
// In ticker/[symbol]/page.tsx, compute the prop to pass to CandlestickChart

const recommendedAnalysis = tradingSignal
  ? tradingSignal.recommended_direction === 'long'
    ? tradingSignal.long_analysis
    : tradingSignal.bearish_analysis
  : undefined;

const tradingPlanForChart =
  recommendedAnalysis && recommendedAnalysis.confidence > 0
    ? {
        entry_price: recommendedAnalysis.trading_plan.entry_price,
        stop_loss: recommendedAnalysis.trading_plan.stop_loss,
        take_profit_1: recommendedAnalysis.trading_plan.take_profit_1,
        take_profit_2: recommendedAnalysis.trading_plan.take_profit_2,
      }
    : undefined;

// Pass to CandlestickChart:
<CandlestickChart
  priceData={priceData}
  indicatorData={indicatorData ?? undefined}
  adjusted={adjusted}
  onAdjustedChange={setAdjusted}
  tradingPlan={tradingPlanForChart}
/>
```

### Price Line Legend Extension
```typescript
// Source: Existing MA Legend pattern in candlestick-chart.tsx lines 281-294
// Add below existing legend, conditionally when tradingPlan is present

{tradingPlan && (
  <div className="flex items-center gap-4 text-xs">
    <span className="flex items-center gap-1">
      <span className="inline-block w-3 h-0.5 bg-[#26a69a] border-t border-dashed border-[#26a69a]" /> Entry
    </span>
    <span className="flex items-center gap-1">
      <span className="inline-block w-3 h-0.5 bg-[#ef5350] border-t border-dashed border-[#ef5350]" /> SL
    </span>
    <span className="flex items-center gap-1">
      <span className="inline-block w-3 h-0.5 bg-[#42a5f5] border-t border-dashed border-[#42a5f5]" /> TP1
    </span>
    <span className="flex items-center gap-1">
      <span className="inline-block w-3 h-0.5 bg-[#7e57c2] border-t border-dashed border-[#7e57c2]" /> TP2
    </span>
  </div>
)}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Chart-level priceLine in v3 | Series-level `createPriceLine()` in v4+ | lightweight-charts v4 (2023) | PriceLine is always on a specific series |
| `chart.addSeries(chart.CandlestickSeries)` | `chart.addSeries(CandlestickSeries)` | lightweight-charts v5 (2024) | Series types imported as standalone, not from chart instance |

**Deprecated/outdated:**
- `chart.addCandlestickSeries()` — replaced by `chart.addSeries(CandlestickSeries, options)` in v5 [VERIFIED: existing code uses v5 pattern]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Price scale auto-adjusts to include price lines when `axisLabelVisible: true` | Pitfall 5 | Price lines could be invisible if outside initial viewport — low risk, `fitContent()` after price lines should handle it |

**All other claims verified** against installed typings and existing codebase.

## Open Questions

1. **Legend placement for price line labels**
   - What we know: The chart already has an MA legend row (SMA 20/50/200, BB). Price lines have on-chart `title` text ("Entry", "SL", etc.)
   - What's unclear: Whether a legend row for price lines adds value or is redundant with on-chart labels
   - Recommendation: Add a small legend row (agent's discretion area) — it provides at-a-glance context and is consistent with existing patterns. Show conditionally only when `tradingPlan` prop is present.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | None installed in frontend |
| Config file | none |
| Quick run command | `cd frontend && npx next build` (type-check + build) |
| Full suite command | `cd frontend && npx next build` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DISP-02 | Price lines rendered on candlestick chart | manual-only | Visual inspection in browser | N/A |
| DISP-02-a | Props interface accepts tradingPlan | build | `cd frontend && npx next build` | ✅ existing |
| DISP-02-b | Price lines update on ticker change | manual-only | Navigate between tickers in browser | N/A |
| DISP-02-c | No price lines when confidence=0 | manual-only | Check ticker with zero-confidence signal | N/A |

**Justification for manual-only:** Price line rendering is a canvas-based visual feature inside lightweight-charts WebGL/Canvas. No DOM output to assert against. The `next build` command validates TypeScript types and import correctness. Visual verification requires a running browser.

### Sampling Rate
- **Per task commit:** `cd frontend && npx next build`
- **Per wave merge:** `cd frontend && npx next build` + visual inspection
- **Phase gate:** Build green + visual confirmation of price lines on a ticker with trading signals

### Wave 0 Gaps
None — no test infrastructure needed for this visual-only, canvas-based feature. TypeScript build validation is sufficient for correctness of API usage.

## Security Domain

This phase is frontend-only, adds no new data paths, no user input, no API calls, no authentication changes. All data is read-only from existing API.

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | no | Data comes from trusted backend API, not user input |
| V6 Cryptography | no | — |

No security concerns for this phase.

## Sources

### Primary (HIGH confidence)
- `frontend/node_modules/lightweight-charts/dist/typings.d.ts` — PriceLineOptions (lines 3522-3582), IPriceLine (lines 2136-2158), ISeriesApi.createPriceLine (line 2448), LineStyle enum (lines 73-94), CreatePriceLineOptions (line 4567)
- `frontend/src/components/candlestick-chart.tsx` — Existing chart component (300 lines), useEffect lifecycle, series creation pattern
- `frontend/src/components/trading-plan-panel.tsx` — TP2 threshold logic (line 96), color references
- `frontend/src/lib/api.ts` — TradingPlanDetail interface (lines 79-87), TickerTradingSignal (lines 96-101)
- `frontend/src/app/ticker/[symbol]/page.tsx` — Current page layout, existing tradingSignal hook usage
- `frontend/package.json` — lightweight-charts ^5.1.0 installed
- npm registry — lightweight-charts 5.1.0 is latest

### Secondary (MEDIUM confidence)
- None needed — all claims verified from installed source

### Tertiary (LOW confidence)
- A1: Price scale auto-adjustment behavior — based on lightweight-charts default behavior, not explicitly verified in docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified installed versions match latest, API confirmed in typings
- Architecture: HIGH — all patterns verified against existing code
- Pitfalls: HIGH — derived from concrete code analysis of existing chart lifecycle

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (stable — lightweight-charts releases infrequently)

# Phase 21: Chart Price Line Overlays - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Add horizontal price lines on the candlestick chart to visualize entry, stop-loss, and take-profit levels from the active trading signal. Uses lightweight-charts v5 PriceLine API on the CandlestickSeries. Frontend-only phase — data already available via useTradingSignal hook (Phase 20).

</domain>

<decisions>
## Implementation Decisions

### PriceLine API
- Use series-level createPriceLine() on the CandlestickSeries (not chart-level)
- lightweight-charts v5: series.createPriceLine({ price, color, lineWidth, lineStyle, title, axisLabelVisible })
- Store price line references to remove/update when data changes

### Color Scheme
- Entry price: #26a69a (teal/green — matches LONG accent)
- Stop loss: #ef5350 (red — matches BEARISH accent)
- Take profit 1: #42a5f5 (blue)
- Take profit 2: #7e57c2 (purple — distinct from TP1)
- Line style: dashed (LineStyle.Dashed) for all price lines
- Line width: 1px

### Label Format
- Show axis labels: true (axisLabelVisible)
- Title text on line: "Entry", "SL", "TP1", "TP2" (abbreviated English — chart space is limited)
- No Vietnamese for chart labels (too long, overlaps)

### Data Flow
- CandlestickChart receives trading signal data as new optional prop
- Pass recommended direction's trading plan (entry/SL/TP1/TP2)
- If no trading signal or score=0: show no price lines
- Lines update when ticker changes (useEffect dependency)

### Which Direction to Show
- Show only the RECOMMENDED direction's price lines (not both)
- User already sees both directions in the TradingPlanPanel below
- Showing both would be visually cluttered on the chart

### Component Changes
- Extend CandlestickChartProps with optional tradingPlan?: { entry_price, stop_loss, take_profit_1, take_profit_2 }
- In the useEffect, after series data is set, add price lines
- Cleanup: remove price lines on data change or unmount
- Pass data from page.tsx using useTradingSignal hook data

### Agent's Discretion
- Exact line opacity/transparency
- Whether to use a legend/tooltip for price line labels
- Ordering of createPriceLine calls
- Whether to also show on volume histogram (no — only candlestick series)

</decisions>

<code_context>
## Existing Code Insights

### Chart Architecture
- `frontend/src/components/candlestick-chart.tsx` — CandlestickChart component
- Chart created via createChart() in useEffect
- chartRef stores IChartApi instance
- CandlestickSeries created at line 92
- Series reference needed for createPriceLine()

### Data Available
- `useTradingSignal(symbol)` hook returns TickerTradingSignal | null
- TickerTradingSignal has recommended_direction, long_analysis, bearish_analysis
- Each DirectionAnalysis has trading_plan: TradingPlanDetail with entry_price, stop_loss, take_profit_1, take_profit_2

</code_context>

<deferred>
## Deferred Ideas

- Interactive price line dragging for custom entry/SL/TP — out of v3.0 scope
- Support/resistance level overlays — separate feature
- Multi-timeframe price line comparison — future enhancement

</deferred>

---

*Phase: 21-chart-price-line-overlays*
*Context gathered: 2026-04-20 via autonomous mode*

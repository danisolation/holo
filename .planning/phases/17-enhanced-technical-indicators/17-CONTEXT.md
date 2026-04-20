# Phase 17: Enhanced Technical Indicators - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Add ATR (Average True Range), ADX (Average Directional Index with +DI/-DI), and Stochastic oscillator (%K/%D) to the existing indicator computation pipeline. Extend the technical_indicators table, compute alongside existing 12 indicators, expose via API, and display as sub-charts on the ticker detail page. These indicators provide the foundation context for trading signal generation in Phase 19.

</domain>

<decisions>
## Implementation Decisions

### Indicator Parameters
- ATR window: 14 (industry standard, matches existing RSI-14)
- ADX window: 14 (Wilder's standard period)
- Stochastic window: 14 for %K, smoothing 3 for %D (standard parameters)
- Store ADX + +DI + -DI (all three) — +DI/-DI crossovers are critical for directional analysis in Phase 19

### Database & Migration
- Add new columns to existing technical_indicators table (not a separate table) — consistent with existing 12 indicators in same row per ticker/date
- Column precision: Numeric(12,4) — matches existing indicator columns (sma_20, bb_upper, etc.)
- Migration number: 010 (continues from 009 gemini_usage)
- New columns: atr_14, adx_14, plus_di_14, minus_di_14, stoch_k_14, stoch_d_14 (6 columns total)

### Frontend Display
- Each new indicator gets a separate sub-chart below candlestick, matching RSI/MACD chart pattern
- ATR: line chart showing volatility value
- ADX: line chart with ADX + reference line at 25 (strong trend threshold)
- Stochastic: %K/%D dual lines with 80/20 overbought/oversold zones
- Sub-charts use collapsible accordion — user picks which to show, avoids page bloat

### Agent's Discretion
- Chart colors for new indicators (follow existing color scheme: purple RSI, blue/red MACD)
- Accordion default state (collapsed or expanded)
- Sub-chart heights (match existing 160px from RSI chart)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/indicator_service.py` — IndicatorService with `_compute_indicators()` method, currently computes 12 indicators from close prices only
- `backend/app/models/technical_indicator.py` — TechnicalIndicator model with all indicator columns as Nullable Decimal
- `frontend/src/components/indicator-chart.tsx` — RSIChart and MACDChart components using lightweight-charts LineSeries
- `ta` library already imported: RSIIndicator, MACD, SMAIndicator, EMAIndicator, BollingerBands

### Established Patterns
- Indicator computation: instantiate ta class → call method → return pd.Series → store as dict mapping column→series
- Database: bulk upsert with `on_conflict_do_update` on unique constraint (ticker_id, date)
- Frontend charts: lightweight-charts `createChart()` per sub-chart, 160px height, dark theme (#0f172a), ResizeObserver cleanup
- API: GET /api/analysis/{symbol}/indicators returns IndicatorData list

### Integration Points
- `_compute_indicators()` currently only receives `close` Series — must extend to accept `high`, `low` for ATR/ADX/Stochastic
- `compute_for_ticker()` query only fetches `DailyPrice.date, DailyPrice.close` — must add `DailyPrice.high, DailyPrice.low`
- Frontend ticker detail page already renders RSIChart and MACDChart from indicator-chart.tsx — add new charts in same pattern
- API response type IndicatorData needs new fields for ATR/ADX/Stochastic

</code_context>

<specifics>
## Specific Ideas

No specific requirements — standard indicator computation following established patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

# Phase 18: Support & Resistance Levels - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Add pivot-point-based support/resistance levels (S1/S2/R1/R2) and Fibonacci retracement levels (23.6%, 38.2%, 50%, 61.8%) to the indicator pipeline. Store in the existing technical_indicators table alongside current 18 indicators, expose via API, and display as a data panel on the ticker detail page. These levels are consumed by Phase 19's AI trading signal pipeline as context for entry/SL/TP generation.

</domain>

<decisions>
## Implementation Decisions

### Pivot Point Calculation
- Use Classic (Floor) Pivot Point formula: PP = (H + L + C) / 3
- S1 = 2*PP - H, R1 = 2*PP - L
- S2 = PP - (H - L), R2 = PP + (H - L)
- Calculate from previous day's High/Low/Close (1-day lookback)
- Store 5 values: pivot_point, support_1, support_2, resistance_1, resistance_2

### Fibonacci Retracement Calculation
- Use 20-day lookback window to identify swing high and swing low
- Swing High = max(high) over 20 days, Swing Low = min(low) over 20 days
- Fibonacci levels: 23.6%, 38.2%, 50%, 61.8% between swing low and swing high
- Store 4 values: fib_236, fib_382, fib_500, fib_618
- Formula: level = swing_low + (swing_high - swing_low) * percentage

### Database & Migration
- Add new columns to existing technical_indicators table (same pattern as Phase 17)
- Migration number: 011 (continues from 010)
- 9 new columns: pivot_point, support_1, support_2, resistance_1, resistance_2, fib_236, fib_382, fib_500, fib_618
- Column precision: Numeric(12,4) — matches existing indicator columns
- All nullable (warm-up: pivot needs 1 prior day, Fibonacci needs 20 days)

### Computation Integration
- Add `_compute_support_resistance()` private method to IndicatorService
- Takes high, low, close Series + returns dict of 9 Series
- Call from `_compute_indicators()` alongside existing ATR/ADX/Stochastic
- Pivot uses .shift(1) on H/L/C for previous-day values
- Fibonacci uses .rolling(20).max()/.min() on high/low

### Frontend Display
- NOT chart sub-charts — S/R levels are discrete price values, not time-series curves
- Display as a data card/table below the accordion charts
- Show current (latest) pivot point levels in a structured layout
- Show current Fibonacci levels in same card
- Use Vietnamese labels: "Hỗ trợ 1", "Hỗ trợ 2", "Kháng cự 1", "Kháng cự 2", "Điểm xoay"
- Fibonacci labels: "Fib 23.6%", "Fib 38.2%", "Fib 50%", "Fib 61.8%"
- Price values formatted with comma separator (VN style: 25,400)

### Agent's Discretion
- Card layout details (grid columns, spacing)
- Color coding for support vs resistance levels
- Whether to show swing high/low values alongside Fibonacci
- Empty state text when no S/R data available

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/indicator_service.py` — IndicatorService with `_compute_indicators()` method computing 18 indicators
- `backend/app/models/technical_indicator.py` — TechnicalIndicator model with 18 indicator columns
- `backend/app/schemas/analysis.py` — IndicatorResponse Pydantic schema
- `backend/app/api/analysis.py` — GET /api/analysis/{symbol}/indicators endpoint
- `frontend/src/components/indicator-chart.tsx` — Accordion with 5 sub-charts

### Architecture Constraint
- compute_for_ticker() queries DailyPrice.date, .close, .high, .low — already has all data needed for pivot/fibonacci
- Upsert pattern handles new columns automatically (ON CONFLICT DO UPDATE includes all mapped columns)
- Incremental compute (only new dates since last_computed) applies to S/R too
- Frontend IndicatorData type needs 9 new fields added to api.ts

### Migration Lineage
- 009: gemini_usage
- 010: enhanced_indicators (Phase 17)
- 011: support_resistance_levels (this phase)

</code_context>

<deferred>
## Deferred Ideas

- Woodie/Camarilla/DeMark pivot variants — only Classic pivot for now
- Multi-timeframe S/R (weekly, monthly pivots) — daily only for v3.0
- Automatic swing point detection with zig-zag indicator — simple rolling max/min for now
- Chart overlay lines for S/R on candlestick chart — handled in Phase 21

</deferred>

---

*Phase: 18-support-resistance-levels*
*Context gathered: 2026-04-20 via autonomous mode*

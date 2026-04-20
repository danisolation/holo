# Phase 20: Trading Plan Dashboard Panel - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Create a dedicated Trading Plan panel on the ticker detail page showing LONG and BEARISH analysis side-by-side. Display entry/SL/TP targets, R:R ratio, timeframe, position sizing, and Vietnamese rationale for each direction. Panel shows which direction is recommended with color-coded confidence. This is a frontend-only phase — all data already available from Phase 19's API.

</domain>

<decisions>
## Implementation Decisions

### Panel Placement
- Insert AFTER Combined Recommendation card, BEFORE Analysis Cards grid
- Full-width panel (not in the 3-column grid)
- Position: between line 301 (CombinedRecommendationCard) and line 304 (Analysis Cards grid)

### Panel Layout
- Two-column layout: LONG analysis (left), BEARISH analysis (right)
- Recommended direction column highlighted with accent border/background
- Each column shows: direction badge, confidence score (1-10), trading plan details, Vietnamese reasoning
- Trading plan details: entry price, stop loss, take profit 1 & 2, R:R ratio, position size %, timeframe

### Data Flow
- AnalysisSummary already has trading_signal field from backend (Phase 19)
- Need to add trading_signal to frontend AnalysisSummary type
- Need to fetch raw_response JSONB for full trading plan data (AnalysisResult only has signal/score/reasoning)
- Create new API function or extend existing one to get full TickerTradingSignal data
- New endpoint: GET /api/analysis/{symbol}/trading-signal already exists (Phase 19)

### Frontend Types
- Add TradingPlanDetail interface: entry_price, stop_loss, take_profit_1, take_profit_2, risk_reward_ratio, position_size_pct, timeframe
- Add DirectionAnalysis interface: direction, confidence, trading_plan, reasoning
- Add TickerTradingSignal interface: ticker, recommended_direction, long_analysis, bearish_analysis
- Add fetchTradingSignal() API function

### Visual Design
- Vietnamese labels: "Kế Hoạch Giao Dịch" (heading), "LONG" / "XU HƯỚNG GIẢM" (direction labels)
- Entry: "Giá vào", SL: "Cắt lỗ", TP1: "Chốt lời 1", TP2: "Chốt lời 2"
- R:R: "Tỷ lệ R:R", Position: "Khối lượng", Timeframe: "Khung thời gian"
- Timeframe labels: "Swing (3-15 ngày)" / "Position (vài tuần+)"
- Color: green for LONG confidence, red for BEARISH confidence
- Recommended direction: highlighted with primary accent + "Khuyến nghị" badge
- Invalid signals (score=0): show "Tín hiệu không hợp lệ" with muted styling
- Empty state: "Chưa có kế hoạch giao dịch" when no trading signal data

### Price Formatting
- Vietnamese comma format: 25,400 (matching existing S/R card pattern)
- R:R ratio: display as "1:2.5" format
- Position size: display as "15%" format
- Confidence: color-coded badge (1-3 low/red, 4-6 medium/yellow, 7-10 high/green)

### Agent's Discretion
- Exact card styling (shadow, border radius, padding)
- Responsive breakpoint for mobile stacking
- Whether to use tabs or side-by-side columns on mobile
- Loading skeleton design
- Animation/transitions

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/analysis-card.tsx` — AnalysisCard + CombinedRecommendationCard patterns
- `frontend/src/components/support-resistance-card.tsx` — Two-column card with Vietnamese labels (Phase 18)
- `frontend/src/lib/api.ts` — AnalysisSummary, AnalysisResult types, fetchAnalysisSummary()
- `frontend/src/app/ticker/[symbol]/page.tsx` — Ticker detail page layout

### Architecture Constraint
- Backend already serves GET /api/analysis/{symbol}/trading-signal (Phase 19)
- Backend /summary endpoint includes trading_signal in response
- AnalysisSummary type needs trading_signal?: AnalysisResult added
- Full TickerTradingSignal data available via dedicated endpoint

</code_context>

<deferred>
## Deferred Ideas

- Historical trading signal performance tracking — out of v3.0 scope
- Comparison with previous day's signals — future enhancement
- Chart overlay of entry/SL/TP — handled in Phase 21

</deferred>

---

*Phase: 20-trading-plan-dashboard-panel*
*Context gathered: 2026-04-20 via autonomous mode*

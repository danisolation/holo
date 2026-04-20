# Phase 19: AI Trading Signal Pipeline - Context

**Gathered:** 2026-04-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Add a 5th analysis type "trading_signal" to the existing AI analysis pipeline. Generates dual-direction (LONG + BEARISH) trading plans with concrete entry/SL/TP targets, R:R ratios, position sizing, and timeframe recommendations per ticker. Uses Gemini structured output with nested Pydantic schemas. Integrates Phase 17 indicators (ATR/ADX/Stochastic) and Phase 18 S/R levels as prompt context for grounded price targets.

</domain>

<decisions>
## Implementation Decisions

### VN Market Framing (CRITICAL)
- VN retail investors CANNOT short-sell — reframe "SHORT" as "BEARISH OUTLOOK" (xu hướng GIẢM)
- System instruction explicitly states: "SHORT analysis means bearish outlook, NOT literal short-selling. Recommend 'giảm vị thế' (reduce position) or 'tránh mua' (avoid buying)."
- Still generate concrete SHORT entry/SL/TP — useful as stop-loss levels for LONG positions
- Direction enum: LONG, BEARISH (NOT "SHORT" — avoid confusion)

### Schema Design (3-level nested Pydantic)
- Level 1: TradingSignalBatchResponse → signals: list[TickerTradingSignal]
- Level 2: TickerTradingSignal → ticker, recommended_direction, long_analysis, bearish_analysis
- Level 3: DirectionAnalysis → direction, confidence (1-10), trading_plan: TradingPlanDetail, reasoning (Vietnamese, max 300 chars)
- TradingPlanDetail → entry_price, stop_loss, take_profit_1, take_profit_2, risk_reward_ratio (ge=0.5), position_size_pct (1-100), timeframe (SWING/POSITION enum)
- Timeframe enum: SWING (3-15 days) and POSITION (weeks+) only — NO intraday/scalp (T+2.5 kills it)

### Gemini Prompt Strategy
- Include in prompt context per ticker: current_price, atr_14, adx_14, rsi_14, pivot_point, support_1, support_2, resistance_1, resistance_2, fib_236, fib_382, fib_500, fib_618, bollinger bands, 52-week high/low
- System instruction constraints: "Entry within ±5% of current price. SL within 2×ATR of entry. TP anchored to S/R or Fibonacci levels."
- Post-validation: reject signals where SL > 3×ATR from entry, TP > 5×ATR from entry
- Temperature: 0.2 (same as combined analysis — balanced creativity)
- max_output_tokens: 32768 (doubled from 16K — trading signals need ~300 tokens/ticker)
- thinking_budget: 2048 (doubled — complex dual-direction reasoning)

### Batch Processing
- Batch size: 15 tickers (reduced from 25 — trading signal output is ~5x larger per ticker)
- Delay between batches: 4.0s (same as existing)
- 800 tickers ÷ 15 = ~54 batches → 216s ≈ 3.6 min
- Total 5-type pipeline: ~37.6 min (within daily window)
- RPD impact: 54 extra calls/day → total ~182/day (12.1% of 1500 RPD limit) ✅

### Database Migration
- Migration 012: ALTER TYPE analysis_type ADD VALUE 'trading_signal'
- No new table — reuse existing ai_analyses with raw_response JSONB storing full signal data
- signal field: store recommended_direction.value ("long" or "bearish")
- score field: store recommended_direction's confidence (1-10)
- reasoning field: store recommended_direction's reasoning
- raw_response JSONB: full TickerTradingSignal.model_dump()

### Pipeline Integration
- Add run_trading_signal_analysis() method to AIAnalysisService
- Follow exact same pattern as run_technical_analysis() etc.
- Build prompt with _build_trading_signal_prompt() — includes indicators + S/R levels
- Register in analyze_all_tickers() as 5th step after combined analysis
- Daily schedule trigger: runs after combined analysis completes

### Config Settings
- Add trading_signal_batch_size: int = 15 to Settings
- Add trading_signal_thinking_budget: int = 2048 to Settings
- Add trading_signal_max_tokens: int = 32768 to Settings

### API Endpoint
- Extend existing GET /api/analysis/{symbol}/latest to include trading_signal in response
- No new endpoint needed — trading_signal is just another analysis_type in ai_analyses

### Post-Validation
- After Gemini returns signals, validate each ticker's trading plan:
  - entry_price within ±5% of current_price (reject if outside)
  - stop_loss within 3×ATR of entry_price (warn if outside, keep)
  - take_profit within 5×ATR of entry_price (warn if outside, keep)
  - risk_reward_ratio recalculated from actual entry/SL/TP and compared to Gemini's value
  - If validation fails: store with signal="invalid", score=0, reasoning="Validation failed: {reason}"

### Agent's Discretion
- Exact system instruction wording (follow Vietnamese guidance from research)
- Prompt formatting/structure details
- Logging verbosity for trading signal pipeline
- Whether to run trading signals for all tickers or only those with recent price data

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/ai_analysis_service.py` — AIAnalysisService with _run_batched_analysis(), _call_gemini(), _store_analysis() methods
- `backend/app/models/ai_analysis.py` — AIAnalysis model with analysis_type enum, raw_response JSONB
- `backend/app/schemas/analysis.py` — Existing analysis schemas (TechnicalBatchResponse, etc.)
- `backend/app/core/config.py` — Settings with gemini_batch_size, gemini_delay_seconds

### Architecture Constraint
- _gemini_lock serializes all Gemini access — trading signals queue behind existing 4 types
- Circuit breaker (3 failures) applies across all types — trading signal failures affect others
- Retry strategy (tenacity + 429/503 handling) inherited automatically
- GeminiUsage tracking per batch — no changes needed
- Existing prompt builders (_build_technical_prompt etc.) are the template for _build_trading_signal_prompt

### Migration Lineage
- 010: enhanced_indicators (Phase 17)
- 011: support_resistance_levels (Phase 18)
- 012: trading_signal_type (this phase)

</code_context>

<deferred>
## Deferred Ideas

- Telegram alert formatting for trading signals — Phase 19 only adds backend pipeline
- Dashboard display of trading signals — handled in Phase 20
- Chart overlay of entry/SL/TP lines — handled in Phase 21
- Multi-model consensus (Gemini + Claude for signal verification) — future consideration
- Backtesting validation of generated signals — out of v3.0 scope

</deferred>

---

*Phase: 19-ai-trading-signal-pipeline*
*Context gathered: 2026-04-20 via autonomous mode*

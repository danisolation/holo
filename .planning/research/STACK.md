# Technology Stack — v3.0 Smart Trading Signals

**Project:** Holo — Stock Intelligence Platform
**Milestone:** v3.0 Smart Trading Signals
**Researched:** 2026-04-20
**Overall confidence:** HIGH

## Executive Summary

v3.0 needs **zero new Python packages** and **zero new frontend npm packages**. The entire smart trading signals feature — dual-direction LONG/SHORT analysis, full trading plans with entry/SL/TP, risk-reward ratios, position sizing, and timeframe recommendations — is implementable with the existing stack. This is not a compromise; the existing stack is genuinely well-suited:

- **Gemini structured output** (`google-genai >=1.73`): Already uses Pydantic `BaseModel` as `response_schema` with `response.parsed` for type-safe JSON. Verified that **nested Pydantic models work** — a `TradingSignalBatchResponse` containing `DirectionAnalysis` containing `TradingPlanDetail` serializes correctly and is accepted by `GenerateContentConfig`. The existing `_call_gemini()` pattern with circuit breaker + tenacity retry is reusable as-is.

- **Support/resistance & price levels**: Pivot points (Classic, Fibonacci) are pure arithmetic on OHLC data — no library needed. ATR (for stop-loss distance) is already in `ta==0.11.0` via `AverageTrueRange`. ADX (trend strength for direction confidence) and Stochastic (overbought/oversold confirmation) are also in `ta` but require `high`+`low` series, which `DailyPrice` already stores.

- **Frontend trading plan panel**: shadcn/ui `Card`, `Badge`, `Tabs` components + Tailwind CSS 4 + Lucide icons cover the UI needs. No chart library needed for the trading plan display — it's structured data (prices, ratios, percentages), not a chart.

- **Token budget**: Adding a 5th analysis type (`trading_signal`) adds ~32 API calls/day (800 tickers ÷ 25/batch). Daily total rises from ~128 to ~160 calls — well within 1,500 RPD free tier. Output tokens increase ~5x per signal (detailed plans for both directions), but spread over 40+ minutes, stays within 1M tokens/min limit.

The deliberate decision: **do NOT add** `scipy` for peak detection, `plotly` for trading plan charts, or `ta-lib` (C wrapper) for "more indicators." The existing stack does everything needed, and Gemini generates the trading plan targets based on the indicator context — not a deterministic algorithm.

---

## What the Existing Stack Already Covers

Before listing changes, map every v3.0 feature to what handles it:

| v3.0 Feature | Covered By (Existing) | How |
|---|---|---|
| Dual-direction analysis (LONG+SHORT) | **google-genai >=1.73** structured output | New Pydantic schema with `Direction` enum + nested `DirectionAnalysis` per direction. Same `_call_gemini()` API pattern. |
| Entry/stop-loss/take-profit targets | **google-genai** structured output + **ta 0.11.0** ATR | Gemini generates price levels informed by ATR-based volatility context. ATR already available, just not computed yet. |
| Risk-reward ratio calculation | **Python stdlib math** | `R:R = abs(tp - entry) / abs(entry - sl)` — pure arithmetic, validated in Pydantic `Field(ge=0.5)`. |
| Position sizing suggestion | **Gemini structured output** | % of portfolio based on confidence + R:R. Pydantic `Field(ge=1, le=100)` constrains output. |
| Timeframe recommendation | **Gemini structured output** | `Timeframe` enum: `scalp` / `swing` / `position`. Schema-enforced. |
| Support/resistance levels | **pandas + numpy** (ta dependencies) | Classic pivot points: `PP = (H+L+C)/3`, `S1 = 2*PP - H`, `R1 = 2*PP - L`. Pure math on `DailyPrice` OHLC. |
| Fibonacci retracement | **Python stdlib** | Levels at 0.236, 0.382, 0.5, 0.618, 0.786 of recent swing range. No library needed. |
| ATR for stop-loss distance | **ta 0.11.0** `AverageTrueRange` | `ATR(high, low, close, window=14)` — already installed, just not imported. Needs `high`+`low` from `DailyPrice`. |
| ADX for trend strength | **ta 0.11.0** `ADXIndicator` | `ADX(high, low, close, window=14)` — trend strength 0-100. Helps direction confidence. |
| Stochastic oscillator | **ta 0.11.0** `StochasticOscillator` | `Stoch(high, low, close, window=14)` — overbought/oversold confirmation. |
| Trading plan dashboard panel | **shadcn/ui** Card + Badge + Tabs | Structured layout: entry zone, SL/TP levels, R:R badge, timeframe badge. No chart needed. |
| Price level visualization | **lightweight-charts 5.1.0** | Horizontal price lines on existing candlestick chart for entry/SL/TP overlay. Already supports `addPriceLine()`. |
| `trading_signal` analysis type | **SQLAlchemy 2.0** + **Alembic 1.18** | New `AnalysisType.TRADING_SIGNAL` enum value. Trading plan details stored in existing `raw_response` JSONB column. |
| Gemini token tracking | **GeminiUsage** model | `analysis_type='trading_signal'` — existing tracking covers it, `String(30)` column is wide enough. |
| Telegram trading alerts | **python-telegram-bot 22.7** | Format trading plan as HTML message. Existing `send_message()` pattern. |
| Batch orchestration | **APScheduler 3.11** + existing `_gemini_lock` | Chain as 5th analysis type after `combined`. Lock serialization prevents rate limit competition. |

---

## Stack Additions: NONE (Zero New Dependencies)

### Backend: No new `pip install`

| Consideration | Decision | Rationale |
|---|---|---|
| `scipy` for peak detection S/R | **NO** | Pivot points + Fibonacci retracements are sufficient. Gemini interprets price structure qualitatively — it doesn't need scipy's `find_peaks()`. Adding scipy (40MB+) for one function is wasteful. |
| `ta-lib` (C wrapper) | **NO** | `ta==0.11.0` already has ATR, ADX, Stochastic. `ta-lib` requires C compilation and platform-specific binaries — unnecessary complexity for 3 extra indicators. |
| `pandas-ta` | **NO** | Overlaps with `ta`. Would add a second TA library with conflicting APIs. |
| `mplfinance` / `plotly` | **NO** | Backend doesn't generate charts. Frontend handles all visualization. |
| New Gemini SDK version | **NO** | `google-genai >=1.73,<2` already supports nested Pydantic schemas, ThinkingConfig, and structured output. Verified with actual code — see verification section below. |

### Frontend: No new `npm install`

| Consideration | Decision | Rationale |
|---|---|---|
| Chart library for trading plan | **NO** | Trading plan is structured data (prices, ratios), not a time series chart. shadcn/ui Card + Badge renders it perfectly. |
| `lightweight-charts` price lines | **Already installed** v5.1.0 | `series.createPriceLine({ price, color, lineWidth })` draws horizontal lines for entry/SL/TP on existing candlestick chart. |
| Progress/gauge component | **NO** | R:R ratio and confidence are numbers, not gauges. Badge with color coding (green/yellow/red) is cleaner UX. |
| Animation library | **NO** | Tailwind CSS 4 transitions + `tw-animate-css` (already installed) cover any subtle UI transitions. |

---

## Existing Stack: Specific Integration Points

### 1. Gemini Structured Output — Nested Pydantic Schema

**Confidence: HIGH** — Verified with actual code execution.

The existing pattern in `ai_analysis_service.py` uses:
```python
config=types.GenerateContentConfig(
    response_schema=TechnicalBatchResponse,  # Pydantic model
    response_mime_type="application/json",
    thinking_config=types.ThinkingConfig(thinking_budget=1024),
)
result = response.parsed  # Returns validated Pydantic instance
```

**Verified**: Nested models work. A schema like:
```python
class TradingPlanDetail(BaseModel):
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    risk_reward_ratio: float
    position_size_pct: float = Field(ge=1, le=100)
    timeframe: Timeframe  # enum

class DirectionAnalysis(BaseModel):
    direction: Direction  # enum
    confidence: int = Field(ge=1, le=10)
    trading_plan: TradingPlanDetail  # nested
    reasoning: str

class TickerTradingSignal(BaseModel):
    ticker: str
    recommended_direction: Direction
    long_analysis: DirectionAnalysis
    short_analysis: DirectionAnalysis

class TradingSignalBatchResponse(BaseModel):
    signals: list[TickerTradingSignal]
```

This serializes to a 1,851-char JSON schema (~462 tokens overhead). `GenerateContentConfig` accepts it via the `response_schema` parameter with type `Union[dict, type, Schema, ...]`. The `response.parsed` returns a fully validated `TradingSignalBatchResponse` instance.

### 2. ATR + ADX + Stochastic — from Existing `ta` Library

**Confidence: HIGH** — Verified function signatures.

Current `indicator_service.py` only uses `close` price. Adding 3 new indicators requires `high`, `low`, `close` from `DailyPrice` (already stored):

```python
# Already importable from ta==0.11.0
from ta.volatility import AverageTrueRange
from ta.trend import ADXIndicator
from ta.momentum import StochasticOscillator

# Signatures (verified):
# AverageTrueRange(high, low, close, window=14, fillna=False)
# ADXIndicator(high, low, close, window=14, fillna=False)
# StochasticOscillator(high, low, close, window=14, smooth_window=3, fillna=False)
```

These 3 indicators add to the `technical_indicators` table (new nullable columns via Alembic migration) and enrich the prompt context sent to Gemini for trading signal generation.

### 3. Pivot Points + Fibonacci — Pure Math

**Confidence: HIGH** — Standard formulas, no library dependency.

```python
# Classic Pivot Points (from daily OHLC)
PP = (high + low + close) / 3
S1 = 2 * PP - high
R1 = 2 * PP - low
S2 = PP - (high - low)
R2 = PP + (high - low)

# Fibonacci Retracement (from N-day swing high/low)
swing_range = swing_high - swing_low
fib_levels = {
    "fib_236": swing_high - 0.236 * swing_range,
    "fib_382": swing_high - 0.382 * swing_range,
    "fib_500": swing_high - 0.500 * swing_range,
    "fib_618": swing_high - 0.618 * swing_range,
}
```

These computed levels are included in the Gemini prompt context to help generate realistic entry/SL/TP targets.

### 4. lightweight-charts Price Lines — for Entry/SL/TP Overlay

**Confidence: HIGH** — `lightweight-charts` v5.1.0 API.

The existing `candlestick-chart.tsx` uses `createChart()` + `addCandlestickSeries()`. Price lines for trading plan overlay:

```typescript
// Already available in lightweight-charts v5.1.0
series.createPriceLine({
    price: tradingPlan.entry_price,
    color: '#2196F3',
    lineWidth: 2,
    lineStyle: LineStyle.Dashed,
    axisLabelVisible: true,
    title: 'Entry',
});
series.createPriceLine({
    price: tradingPlan.stop_loss,
    color: '#ef5350',
    lineWidth: 1,
    lineStyle: LineStyle.Dotted,
    title: 'SL',
});
```

No new package needed — this is a method on the existing series object.

### 5. Database Schema — Extending Existing Models

**Confidence: HIGH** — Standard Alembic migration pattern used 20+ times in project.

Two approaches for storing trading plan data, recommend **Option B**:

**Option A**: New `trading_signals` table (normalized)
- Pros: Clean schema, queryable columns
- Cons: Another table to maintain, JOIN overhead

**Option B**: Extend existing `ai_analyses` table + JSONB (**Recommended**)
- Add `AnalysisType.TRADING_SIGNAL` to the PostgreSQL enum
- Store detailed trading plan in existing `raw_response` JSONB column
- Use `signal` column for recommended direction (`long`/`short`)
- Use `score` column for confidence (1-10)
- Use `reasoning` column for Vietnamese explanation
- Pros: Consistent with existing 4 analysis types, no new table, no new JOINs
- Cons: JSONB not directly queryable for price targets (acceptable — only displayed, not queried)

The existing pattern where `raw_response = analysis.model_dump()` stores the full Pydantic model as JSONB is perfect — the frontend deserializes it for display.

---

## Token Budget Impact Analysis

### Current Daily Pipeline (4 analysis types × 800+ tickers)

| Analysis Type | Batches | Input Tokens/Batch | Output Tokens/Batch | Total/Day |
|---|---|---|---|---|
| Technical | 32 | ~5,000 | ~1,500 | ~208K |
| Fundamental | 32 | ~4,500 | ~1,500 | ~192K |
| Sentiment | 32 | ~3,500 | ~1,500 | ~160K |
| Combined | 32 | ~3,000 | ~1,500 | ~144K |
| **Subtotal** | **128** | | | **~704K** |

### With Trading Signals (5th type)

| Analysis Type | Batches | Input Tokens/Batch | Output Tokens/Batch | Total/Day |
|---|---|---|---|---|
| Trading Signal | 32 | ~10,500 | ~7,500 | **~576K** |
| **New Total** | **160** | | | **~1.28M** |

### Rate Limit Analysis

| Limit | Current | With v3.0 | Status |
|---|---|---|---|
| **RPD** (1,500/day) | ~128 calls | ~160 calls | ✅ 10.7% of limit |
| **RPM** (15/min) | 15 calls/min max | Same (4s delay) | ✅ Same pattern |
| **Tokens/min** (1M) | ~17.6K/min | ~32K/min | ✅ 3.2% of limit |

### Why Output Tokens Increase 5x for Trading Signals

Current `CombinedBatchResponse` per ticker: ~60 tokens
```json
{"ticker":"VNM","recommendation":"mua","confidence":8,"explanation":"...200 words..."}
```

New `TradingSignalBatchResponse` per ticker: ~300 tokens
```json
{"ticker":"VNM","recommended_direction":"long",
 "long_analysis":{"direction":"long","confidence":8,
   "trading_plan":{"entry_price":82000,"stop_loss":79500,"take_profit_1":85000,
     "take_profit_2":88000,"risk_reward_ratio":2.4,"position_size_pct":8,"timeframe":"swing"},
   "reasoning":"...100 words..."},
 "short_analysis":{"direction":"short","confidence":3,
   "trading_plan":{"entry_price":83500,"stop_loss":86000,"take_profit_1":80000,
     "take_profit_2":77000,"risk_reward_ratio":1.4,"position_size_pct":3,"timeframe":"swing"},
   "reasoning":"...100 words..."}}
```

### Mitigation: Reduce Batch Size for Trading Signals

If output token limits cause truncation, reduce `gemini_batch_size` from 25 to 15 for trading signals only:
- 800 ÷ 15 = 54 batches (vs 32)
- At 4s delay: ~216s = ~3.6 min
- Total pipeline time: existing ~34 min + 3.6 min = ~37.6 min
- Still fits within the daily schedule window

### ThinkingConfig Budget

Current: `thinking_budget=1024` for 2.5-flash models. Trading signals are more complex reasoning tasks — consider increasing to `thinking_budget=2048` for this analysis type specifically. Internal thinking tokens don't count against output limits but do count for billing (free tier: no cost).

---

## What NOT to Add (Explicit Anti-Recommendations)

| Don't Add | Why Not | What to Do Instead |
|---|---|---|
| `scipy` / `scikit-learn` | Peak detection S/R is over-engineering. Gemini interprets price structure from context. | Pivot points + Fibonacci (pure math) + let Gemini reason about price levels. |
| `ta-lib` (C wrapper) | Platform-specific binary compilation. `ta` pure Python already has ATR/ADX/Stochastic. | Use `ta==0.11.0` — already installed. |
| `pandas-ta` | Second TA library = conflicting APIs, duplicate computation. | Stick with `ta==0.11.0`. |
| `plotly` / `mplfinance` | Backend shouldn't generate charts. Frontend handles visualization. | `lightweight-charts` price lines + shadcn/ui Cards. |
| `pydantic[email]` or extras | Trading signals don't need email validation or extra Pydantic features. | Plain `pydantic` (already a google-genai dependency). |
| `redis` / `celery` | Trading signal pipeline fits within existing APScheduler + asyncio pattern. No queue needed. | Chain as 5th job after combined analysis. Same `_gemini_lock` serialization. |
| New Gemini model | `gemini-2.5-flash-lite` handles structured output well. Upgrading to `gemini-2.5-pro` wastes RPD budget (lower free limits). | Keep `gemini-2.5-flash-lite`. |
| Separate `response_json_schema` | google-genai supports both `response_schema` (Pydantic) and `response_json_schema` (raw dict). Pydantic is better — validates on both sides. | Continue using `response_schema=PydanticModel`. |

---

## Configuration Additions

New settings for `config.py` (no new dependencies):

```python
# Trading Signals (v3.0)
trading_signal_batch_size: int = 15     # Smaller batches for larger output
trading_signal_thinking_budget: int = 2048  # More thinking for complex reasoning
trading_signal_atr_window: int = 14     # ATR period for stop-loss distance
trading_signal_pivot_lookback: int = 20  # Days for pivot point calculation
trading_signal_swing_lookback: int = 60  # Days for Fibonacci swing detection
```

---

## Database Migration Checklist

All achievable with existing `alembic` + `sqlalchemy`:

1. **Add `TRADING_SIGNAL` to `analysis_type` PostgreSQL ENUM**
   ```sql
   ALTER TYPE analysis_type ADD VALUE 'trading_signal';
   ```

2. **Add new indicator columns to `technical_indicators` table**
   ```sql
   ALTER TABLE technical_indicators ADD COLUMN atr_14 NUMERIC(12,4);
   ALTER TABLE technical_indicators ADD COLUMN adx_14 NUMERIC(8,4);
   ALTER TABLE technical_indicators ADD COLUMN stoch_k NUMERIC(8,4);
   ALTER TABLE technical_indicators ADD COLUMN stoch_d NUMERIC(8,4);
   ```

3. **No new tables needed** — trading plan details go in `ai_analyses.raw_response` JSONB.

---

## Verification Log

All claims verified with actual code execution on the project's installed dependencies:

| Claim | Method | Result |
|---|---|---|
| Nested Pydantic in `response_schema` | Python: Created `TradingSignalBatchResponse` with 3-level nesting, passed to `GenerateContentConfig` | ✅ Config created successfully |
| `ta` has ATR, ADX, Stochastic | Python: Imported all three, checked `__init__` signatures | ✅ All accept `high, low, close, window` |
| `DailyPrice` has OHLCV columns | Inspected `models/daily_price.py` | ✅ `open, high, low, close, volume` all `Numeric(12,2)` |
| `GeminiUsage.analysis_type` fits 'trading_signal' | Checked model: `String(30)` | ✅ 'trading_signal' = 14 chars < 30 |
| Schema JSON size for token estimate | `json.dumps(schema)` | ✅ 1,851 chars ≈ 462 tokens |
| `ThinkingConfig` accepts `thinking_budget` | Instantiated `types.ThinkingConfig(thinking_budget=2048)` | ✅ No error |
| lightweight-charts `createPriceLine` | Training data (library API) | ⚠️ MEDIUM confidence — verify against v5.1.0 docs when implementing |

---

## Sources

- `backend/requirements.txt` — Verified installed versions
- `backend/app/services/ai_analysis_service.py` — Existing Gemini integration pattern
- `backend/app/services/indicator_service.py` — Current ta library usage
- `backend/app/models/daily_price.py` — OHLCV column availability
- `backend/app/models/ai_analysis.py` — AnalysisType enum + JSONB raw_response
- `backend/app/schemas/analysis.py` — Existing Pydantic structured output schemas
- `backend/app/config.py` — Current settings and model configuration
- `frontend/package.json` — Frontend dependency versions
- `frontend/src/components/analysis-card.tsx` — Existing analysis display pattern
- `frontend/src/components/candlestick-chart.tsx` — Existing chart component
- `google-genai==1.73.1` — Installed version, `types.GenerateContentConfig` field inspection
- `ta==0.11.0` — Installed version, `AverageTrueRange`/`ADXIndicator`/`StochasticOscillator` signatures

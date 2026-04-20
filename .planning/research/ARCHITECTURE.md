# Architecture: Smart Trading Signals Integration

**Domain:** Dual-direction trading plan generation for existing AI stock analysis platform
**Researched:** 2026-04-20
**Confidence:** HIGH — based on full codebase analysis of existing pipeline, models, schemas, API, scheduler, and frontend

## Executive Summary

Trading plans integrate as a **5th analysis type** (`trading_plan`) in the existing `ai_analyses` pipeline, running as a **separate Gemini call** chained after `combined` analysis. This approach preserves all existing infrastructure (batching, retry, circuit breaker, usage tracking, storage) while adding richer structured output via the existing `raw_response JSONB` column. The frontend gains a new `TradingPlanPanel` component on the ticker detail page. No new database tables are needed — only a PostgreSQL ENUM value addition and new Pydantic schemas.

## Critical Architecture Decision: Separate Gemini Call

**Decision:** Trading plans are a **separate Gemini call**, NOT an extension of the existing `combined` analysis.

**Why this is the only correct answer:**

| Factor | Extend Combined | Separate Call (✓) |
|--------|----------------|-------------------|
| **Input context** | Combined only sees signal/score summaries | Trading plan needs current price, BB levels, SMA distances, support/resistance — entirely different context |
| **Output size** | Combined: ~100 tokens/ticker | Trading plan: ~400 tokens/ticker (LONG + SHORT plans with 3 targets each) |
| **Prompt purpose** | "What's the recommendation?" | "What are the specific price levels?" — fundamentally different task |
| **Temperature** | Combined: 0.2 (reasoning) | Trading plan: 0.1 (precise numbers) |
| **Failure isolation** | Breaking combined breaks all recommendations | Trading plan failure doesn't affect existing signals |
| **Batch size** | Combined: 25/batch works fine | Trading plan: needs 10-15/batch due to larger output |
| **Selective execution** | Combined runs for all 800+ tickers | Trading plans only for strong-signal tickers (~50-100) |
| **Backward compat** | Changes existing combined schema consumers | Zero impact on existing functionality |

## Recommended Architecture

### Component Map (New vs Modified)

```
NEW COMPONENTS:
├── backend/alembic/versions/010_trading_plan.py    [NEW] — Add 'trading_plan' ENUM value
├── frontend/src/components/trading-plan-panel.tsx   [NEW] — Trading Plan UI component

MODIFIED COMPONENTS:
├── backend/app/schemas/analysis.py                  [MODIFY] — Add TradingPlan Pydantic schemas
├── backend/app/models/ai_analysis.py                [MODIFY] — Add TRADING_PLAN to AnalysisType enum
├── backend/app/services/ai_analysis_service.py      [MODIFY] — Add trading plan methods
├── backend/app/api/analysis.py                      [MODIFY] — Add trading plan endpoints
├── backend/app/scheduler/manager.py                 [MODIFY] — Add trading_plan to job chain
├── backend/app/scheduler/jobs.py                    [MODIFY] — Add trading plan job function
├── backend/app/config.py                            [MODIFY] — Add trading_plan_batch_size setting
├── backend/app/telegram/formatter.py                [MODIFY] — Enhance signal alerts with plan details
├── frontend/src/lib/api.ts                          [MODIFY] — Add TradingPlan types + fetch function
├── frontend/src/lib/hooks.ts                        [MODIFY] — Add useTradingPlan hook
└── frontend/src/app/ticker/[symbol]/page.tsx        [MODIFY] — Mount TradingPlanPanel

NO CHANGES NEEDED (reused as-is):
├── backend/app/services/ai_analysis_service.py::_call_gemini()          — Reused as-is
├── backend/app/services/ai_analysis_service.py::_run_batched_analysis() — Reused as-is
├── backend/app/services/ai_analysis_service.py::_store_analysis()       — Reused as-is
├── backend/app/services/gemini_usage_service.py                         — Works automatically
├── backend/app/resilience.py::gemini_breaker                            — Wraps new calls too
├── backend/app/models/gemini_usage.py                                   — Tracks new analysis_type string
└── frontend/src/components/analysis-card.tsx                            — Existing cards unchanged
```

### Data Flow: Trading Plan Generation

```
EXISTING CHAIN (unchanged up to combined):
  price_crawl_upcom
    → indicator_compute
      → ai_analysis (technical + fundamental)
        → news_crawl
          → sentiment_analysis
            → combined_analysis
              ↓
NEW CHAIN EXTENSION:
              → trading_plan_generation  ←── NEW (filters to strong-signal tickers only)
                → signal_alert_check     ←── MOVED (now after trading_plan, was after combined)
              + hnx_upcom_analysis       ←── unchanged (parallel with trading_plan)
```

**Key: Trading plan runs BEFORE signal alerts** so alerts can include entry/SL/TP in the Telegram message.

### Trading Plan Generation Flow (Detail)

```
1. combined_analysis completes for all tickers
2. trading_plan_generation job starts:
   a. Query ai_analyses for today's combined results
   b. Filter: only tickers where combined.score ≥ 7 (strong buy/mua)
      OR combined.score ≤ 3 (strong sell/bán)
      OR ticker is in user watchlist
   c. For qualifying tickers (~50-100), gather ENRICHED context:
      - Latest close price + 5-day OHLCV
      - All 12 technical indicators (current values)
      - Bollinger Band positions (for support/resistance)
      - SMA levels (for key price levels)
      - Combined recommendation + confidence
   d. Batch 10 tickers per Gemini call (smaller than 25 due to larger output)
   e. Gemini returns dual-direction plan (LONG + SHORT) for each ticker
   f. Store in ai_analyses with analysis_type='trading_plan'
   g. raw_response JSONB contains full structured plan
3. signal_alert_check reads trading_plan from ai_analyses to enrich alerts
```

### Ticker Filtering Strategy (Critical for Rate Limits)

**Problem:** 800+ tickers × trading plan = ~80 Gemini calls at 15 RPM = 5+ minutes + massive token consumption. Free tier has 1500 RPD limit.

**Solution:** Smart filtering — only generate trading plans for high-conviction tickers.

```python
# Filtering logic in _get_trading_plan_qualifying_tickers():
# 1. Strong combined signals (score ≥ 7 or ≤ 3)
strong_signals = query(
    ai_analyses WHERE analysis_type='combined'
    AND analysis_date=today
    AND (score >= 7 OR score <= 3)
)  # Estimated: ~40-80 tickers

# 2. Watchlisted tickers (always get plans regardless of signal)
watchlisted = query(user_watchlist)  # Estimated: ~10-30 tickers

# 3. Deduplicate and cap
qualifying = dedupe(strong_signals + watchlisted)[:settings.max_trading_plans]
```

**Token budget impact (estimated):**

| Analysis Type | Tickers | Batches (batch_size) | Prompt Tokens | Completion Tokens | Total |
|--------------|---------|---------------------|---------------|-------------------|-------|
| Technical | 400 | 16 (×25) | ~32,000 | ~40,000 | ~72,000 |
| Fundamental | 400 | 16 (×25) | ~24,000 | ~32,000 | ~56,000 |
| Sentiment | 400 | 16 (×25) | ~32,000 | ~40,000 | ~72,000 |
| Combined | 400 | 16 (×25) | ~24,000 | ~40,000 | ~64,000 |
| **Trading Plan** | **~80** | **8 (×10)** | **~24,000** | **~32,000** | **~56,000** |
| **Daily Total** | | **72 → 80** | | | **~320,000** |

**RPD impact:** +8 calls/day → 72 to 80 total. Well within 1500 RPD free tier.
**RPM impact:** 8 calls × 4s delay = 32 seconds. Adds ~30s to pipeline. Acceptable.

## Pydantic Schema Design

### New Schemas (in `backend/app/schemas/analysis.py`)

```python
# --- Trading Plan Schemas (v3.0) ---

class TradeDirection(str, Enum):
    """Direction for a trading plan."""
    LONG = "long"
    SHORT = "short"

class Timeframe(str, Enum):
    """Recommended holding timeframe."""
    SCALP = "scalp"          # 1-3 ngày
    SWING = "swing"          # 1-4 tuần
    POSITION = "position"    # 1-3 tháng

class DirectionPlan(BaseModel):
    """Trading plan for a single direction (LONG or SHORT)."""
    direction: TradeDirection
    entry_price: float = Field(description="Recommended entry price in VND")
    stop_loss: float = Field(description="Stop-loss price in VND")
    take_profit_1: float = Field(description="First take-profit target in VND")
    take_profit_2: float = Field(description="Second take-profit target in VND")
    take_profit_3: float | None = Field(None, description="Third take-profit target (optional)")
    risk_reward_ratio: float = Field(description="Risk/reward ratio (e.g., 2.5 means 1:2.5)")
    conviction: int = Field(ge=1, le=10, description="Direction conviction 1-10")
    reasoning: str = Field(description="Why this direction, 2-3 sentences")

class TickerTradingPlan(BaseModel):
    """Complete dual-direction trading plan for a single ticker."""
    ticker: str
    preferred_direction: TradeDirection
    long_plan: DirectionPlan
    short_plan: DirectionPlan
    timeframe: Timeframe
    position_size_pct: float = Field(
        ge=1, le=100,
        description="Suggested position size as % of portfolio"
    )
    key_levels: str = Field(description="Key support/resistance levels summary")
    summary: str = Field(description="Vietnamese trading plan summary, max ~150 words")

class TradingPlanBatchResponse(BaseModel):
    """Batch response for trading plan generation (multiple tickers per Gemini call)."""
    analyses: list[TickerTradingPlan]
```

**Why this schema structure:**

1. **`DirectionPlan` as nested model** — Both LONG and SHORT plans have identical structure. Gemini handles nested Pydantic models well via `response_schema` in google-genai >=1.73.

2. **3 take-profit levels** — TP3 is optional (`None`) for cases where only 2 targets make sense. Gemini can leave it null.

3. **`preferred_direction` at top level** — Tells the user which direction AI favors. Maps to `signal` field in ai_analyses storage.

4. **`position_size_pct`** — Percentage-based, not absolute VND. Works regardless of portfolio size.

5. **`key_levels` as string** — Free-form summary of support/resistance. More flexible than structured levels (Gemini can mention specific MAs, BB bands, etc.).

6. **`summary` in Vietnamese** — Matches existing `combined` analysis pattern. Max ~150 words to keep Telegram messages digestible.

### Schema ↔ Storage Mapping

```python
# In _run_batched_analysis result processing:
if analysis_type == AnalysisType.TRADING_PLAN:
    signal = analysis.preferred_direction.value    # "long" or "short"
    score = max(analysis.long_plan.conviction,     # Higher conviction = score
                analysis.short_plan.conviction)
    reasoning = analysis.summary                   # Vietnamese summary
    raw_response = analysis.model_dump()           # FULL plan in JSONB
```

This maps cleanly to the existing `_store_analysis()` method — **no modification needed** to the storage function.

### API Response Schema Extensions

```python
# New response schema for trading plan endpoint
class DirectionPlanResponse(BaseModel):
    """API response for a single direction plan."""
    direction: str
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float | None
    risk_reward_ratio: float
    conviction: int
    reasoning: str

class TradingPlanResponse(BaseModel):
    """API response for trading plan with full plan details."""
    ticker_symbol: str
    analysis_date: str
    preferred_direction: str          # "long" or "short"
    conviction: int                   # 1-10
    timeframe: str                    # "scalp" / "swing" / "position"
    position_size_pct: float
    key_levels: str
    summary: str
    long_plan: DirectionPlanResponse
    short_plan: DirectionPlanResponse
    model_version: str

# Extend existing SummaryResponse
class SummaryResponse(BaseModel):
    """API response for full analysis summary (all dimensions)."""
    ticker_symbol: str
    technical: AnalysisResultResponse | None = None
    fundamental: AnalysisResultResponse | None = None
    sentiment: AnalysisResultResponse | None = None
    combined: AnalysisResultResponse | None = None
    trading_plan: TradingPlanResponse | None = None    # NEW
```

## Database Schema Changes

### Migration: `010_trading_plan.py`

```python
def upgrade() -> None:
    # Add 'trading_plan' to existing analysis_type PostgreSQL ENUM
    # Same pattern as migration 003 which added 'combined'
    op.execute("ALTER TYPE analysis_type ADD VALUE IF NOT EXISTS 'trading_plan';")

def downgrade() -> None:
    # PostgreSQL does not support removing ENUM values
    # Same limitation documented in migration 003
    pass
```

**That's it.** No new tables. No new columns. The existing `ai_analyses` table handles everything:

| Column | Trading Plan Usage |
|--------|-------------------|
| `ticker_id` | Same FK to tickers |
| `analysis_type` | `'trading_plan'` (new ENUM value) |
| `analysis_date` | Today's date |
| `signal` | `'long'` or `'short'` (preferred direction, fits VARCHAR(20)) |
| `score` | Max conviction of LONG/SHORT plans (1-10, fits CHECK constraint) |
| `reasoning` | Vietnamese summary (fits TEXT) |
| `raw_response` | **Full TickerTradingPlan JSON** — both LONG/SHORT plans with all targets |
| `model_version` | Same model tracking |

**Why JSONB in raw_response is the right storage strategy:**

1. **Existing infrastructure** — `_store_analysis()` already serializes `analysis.model_dump()` to JSONB.
2. **Schema flexibility** — Can add fields to the plan (e.g., trailing stop, partial exits) without migrations.
3. **Query efficiency** — For display, we fetch one row and parse JSONB client-side. No JOINs needed.
4. **Already indexed** — `idx_ai_analyses_ticker_type` covers `(ticker_id, analysis_type, analysis_date DESC)`.
5. **Unique constraint works** — `uq_ai_analyses_ticker_type_date` covers `(ticker_id, 'trading_plan', date)`.

## AI Service Integration

### New Constants and Prompt Architecture

```python
TRADING_PLAN_SYSTEM_INSTRUCTION = (
    "Bạn là chuyên gia giao dịch chứng khoán Việt Nam (HOSE/HNX/UPCOM). "
    "Cho mỗi mã, tạo kế hoạch giao dịch đầy đủ cho CẢ HAI hướng (LONG và SHORT). "
    "Entry/SL/TP phải là giá cụ thể (VND), dựa trên support/resistance thực tế "
    "từ Bollinger Bands, SMA, và cấu trúc giá gần đây. "
    "risk_reward_ratio = |TP1 - Entry| / |Entry - SL|. "
    "position_size_pct: 1-5% cho rủi ro cao, 5-15% cho trung bình, 15-30% cho thấp. "
    "Chọn preferred_direction dựa trên phân tích tổng hợp."
)

TRADING_PLAN_FEW_SHOT = """Ví dụ kế hoạch giao dịch:

--- VNM ---
Giá hiện tại: 82,000 VND
Khuyến nghị: mua (confidence=8)
RSI: 52.1 (neutral), MACD: bullish crossover
SMA(20): 81,000, SMA(50): 79,500, SMA(200): 76,000
BB: Upper=85,000, Middle=81,500, Lower=78,000

Kết quả mẫu:
{"ticker": "VNM", "preferred_direction": "long",
 "long_plan": {"direction": "long", "entry_price": 82000, "stop_loss": 79000,
   "take_profit_1": 85000, "take_profit_2": 88000, "take_profit_3": 92000,
   "risk_reward_ratio": 2.0, "conviction": 8,
   "reasoning": "MACD bullish crossover, price above all MAs. Entry at current, SL below SMA50."},
 "short_plan": {"direction": "short", "entry_price": 85000, "stop_loss": 87500,
   "take_profit_1": 82000, "take_profit_2": 79500, "take_profit_3": null,
   "risk_reward_ratio": 1.2, "conviction": 3,
   "reasoning": "Only if price reaches BB upper resistance. Low conviction in bullish trend."},
 "timeframe": "swing", "position_size_pct": 10,
 "key_levels": "Support: 79,500 (SMA50), 78,000 (BB lower). Resistance: 85,000 (BB upper).",
 "summary": "VNM xu hướng tăng với MACD bullish. LONG entry 82,000, SL 79,000, TP 85-92K. R:R 1:2."}

Tạo kế hoạch giao dịch cho các mã sau:"""

# Temperature: lower than combined for precise price targets
ANALYSIS_TEMPERATURES[AnalysisType.TRADING_PLAN] = 0.1
```

### New Methods in `AIAnalysisService`

**Public method — `run_trading_plan_generation()`:**
- Follows identical pattern to `run_technical_analysis()`, `run_combined_analysis()`, etc.
- Calls `_get_trading_plan_qualifying_tickers()` for filtering (unless `ticker_filter` is provided)
- Calls `_get_trading_plan_context()` per ticker for enriched context
- Passes to `_run_batched_analysis()` with `_analyze_trading_plan_batch` as batch_analyzer

**Qualifying ticker filter — `_get_trading_plan_qualifying_tickers()`:**
- Query today's combined analysis results where score >= 7 or score <= 3
- Union with user watchlist tickers
- Cap at `settings.max_trading_plans` (default 100)
- Returns `dict[str, int]` (symbol → ticker_id) matching existing `ticker_filter` pattern

**Context gathering — `_get_trading_plan_context()`:**
- Reuses `_get_technical_context()` for indicator data (RSI, MACD, MAs, BBs)
- Adds 5-day OHLCV from `daily_prices` for recent price action
- Adds combined recommendation signal/score from `ai_analyses`
- Returns enriched dict with all data Gemini needs for price targets

**Batch analyzer — `_analyze_trading_plan_batch()`:**
- Follows exact same pattern as `_analyze_technical_batch()` (line 665-694)
- Calls `_build_trading_plan_prompt()` then `_call_gemini()` with `TradingPlanBatchResponse` schema
- Includes same fallback chain: `response.parsed` → low-temp retry → manual JSON parse

**Prompt builder — `_build_trading_plan_prompt()`:**
- Per-ticker: latest close, 5-day OHLCV, RSI/zone, MACD/crossover, all SMA/BB levels, combined signal
- More data per ticker than other prompts → justifies smaller batch size

### Batch Size Configuration

Add to `Settings` in `config.py`:
```python
gemini_trading_plan_batch_size: int = 10  # Smaller batches for richer output
max_trading_plans: int = 100  # Cap qualifying tickers per daily run
```

Pass batch_size override to `_run_batched_analysis` by adding optional `batch_size` parameter:
```python
async def _run_batched_analysis(
    self, ..., batch_size: int | None = None
) -> dict:
    effective_batch_size = batch_size or self.batch_size
    # ... use effective_batch_size instead of self.batch_size
```

### analyze_single_ticker Extension

Add trading plan as 5th step in on-demand analysis:
```python
for analysis_type, runner in [
    ("technical", self.run_technical_analysis),
    ("fundamental", self.run_fundamental_analysis),
    ("sentiment", self.run_sentiment_analysis),
    ("combined", self.run_combined_analysis),
    ("trading_plan", self.run_trading_plan_generation),  # NEW
]:
```

## API Endpoint Changes

### New: `GET /analysis/{symbol}/trading-plan`

Returns full structured trading plan with both LONG/SHORT details. Parses `raw_response` JSONB from `ai_analyses` row into `TradingPlanResponse`. Returns 404 if no trading plan exists for this ticker.

### Modified: `GET /analysis/{symbol}/summary`

Add `trading_plan: TradingPlanResponse | None` to `SummaryResponse`. Parsed from `raw_response` JSONB when `analysis_type='trading_plan'` row exists. No impact when plan doesn't exist (field is `None`).

### New: `POST /trigger/trading-plans`

Manual trigger for trading plan generation. Same pattern as existing `/trigger/combined`. Runs `run_trading_plan_generation()` in background task.

### Modified: analysis_type parameter in `POST /trigger/ai`

Extend accepted values to include `'trading_plan'` and ensure `'all'` now runs 5 types.

## Frontend Architecture

### New Component: `TradingPlanPanel`

```
frontend/src/components/trading-plan-panel.tsx
```

**Layout (responsive):**

```
┌──────────────────────────────────────────────────────────────────┐
│  📊 Kế hoạch giao dịch            Timeframe: [SWING]  [10% vốn]│
├──────────────────────────────────────────────────────────────────┤
│  [📈 LONG ⭐ ưu tiên]    [📉 SHORT]           (direction tabs)  │
├──────────────────────────────────────────────────────────────────┤
│  Entry:      82,000 ▸                                            │
│  Stop-Loss:  79,000 ▾ (-3.7%)                                   │
│  TP1:        85,000 ▴ (+3.7%)   R:R 1:1.0                      │
│  TP2:        88,000 ▴ (+7.3%)   R:R 1:2.0                      │
│  TP3:        92,000 ▴ (+12.2%)  R:R 1:3.3                      │
│                                                                  │
│  Conviction: ████████░░ 8/10                                     │
│  "MACD bullish crossover with price above all MAs..."            │
├──────────────────────────────────────────────────────────────────┤
│  Key Levels: Support 79,500 (SMA50), 78,000 (BB lower)          │
│              Resistance 85,000 (BB upper), 88,000 (prior high)   │
├──────────────────────────────────────────────────────────────────┤
│  "VNM đang trong xu hướng tăng với MACD bullish. Ưu tiên LONG   │
│   với entry 82,000, SL 79,000, TP 85,000-92,000. R:R = 1:2."   │
├──────────────────────────────────────────────────────────────────┤
│  2026-04-20                                 gemini-2.5-flash-lite│
└──────────────────────────────────────────────────────────────────┘
```

**Component Hierarchy:**

```
TradingPlanPanel (main Card container)
├── PlanHeader (timeframe Badge, position_size_pct, analysis_date)
├── DirectionTabs (shadcn Tabs — LONG / SHORT toggle)
│   └── DirectionPlanCard (per selected direction)
│       ├── PriceLevel × 5 (entry, SL, TP1, TP2, TP3)
│       │   └── Each: price in VND, % change from entry, color coded
│       ├── RiskRewardBadge (R:R ratio display)
│       ├── ConvictionBar (reuse ScoreBar pattern from analysis-card.tsx)
│       └── DirectionReasoning (reasoning text)
├── KeyLevelsSection (support/resistance summary)
├── PlanSummary (Vietnamese summary text)
└── PlanFooter (analysis_date + model_version — same pattern as AnalysisCard)
```

**Styling:**
- Existing color scheme: `#26a69a` (green/bullish), `#ef5350` (red/bearish)
- LONG tab: green accent border. SHORT tab: red accent border
- Preferred direction tab pre-selected with "⭐ ưu tiên" Badge
- Stop-loss prices in red. Take-profit prices in green. Entry in neutral
- Uses existing shadcn/ui: Card, Badge, Tabs, TabsList, TabsTrigger, TabsContent
- Responsive: on mobile, full-width stacked layout. On desktop, same width as CombinedRecommendationCard

### Placement in Ticker Detail Page

Between `CombinedRecommendationCard` and the analysis cards grid:

```tsx
{/* Combined Recommendation (existing) */}
{analysisSummary?.combined && (
  <CombinedRecommendationCard analysis={analysisSummary.combined} />
)}

{/* NEW: Trading Plan Panel */}
{analysisSummary?.trading_plan && (
  <TradingPlanPanel plan={analysisSummary.trading_plan} />
)}

<Separator />

{/* Analysis Cards Grid (existing, unchanged) */}
```

### Data Fetching

**No new hook needed for summary flow** — `useAnalysisSummary` already fetches `/analysis/{symbol}/summary` and will include `trading_plan` when available.

New TypeScript types in `api.ts`:
```typescript
export interface DirectionPlan {
  direction: "long" | "short";
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  take_profit_3: number | null;
  risk_reward_ratio: number;
  conviction: number;
  reasoning: string;
}

export interface TradingPlan {
  ticker_symbol: string;
  analysis_date: string;
  preferred_direction: "long" | "short";
  conviction: number;
  timeframe: "scalp" | "swing" | "position";
  position_size_pct: number;
  key_levels: string;
  summary: string;
  long_plan: DirectionPlan;
  short_plan: DirectionPlan;
  model_version: string;
}

// Extend existing AnalysisSummary
export interface AnalysisSummary {
  ticker_symbol: string;
  technical?: AnalysisResult;
  fundamental?: AnalysisResult;
  sentiment?: AnalysisResult;
  combined?: AnalysisResult;
  trading_plan?: TradingPlan;  // NEW
}
```

## Telegram Signal Alert Enhancement

### Current Format (signal_alert_check)
```
📊 FPT — MUA MẠNH (9/10)
Cả 3 chiều phân tích đều tích cực...
```

### Enhanced Format with Trading Plan
```
📊 FPT — MUA MẠNH (9/10)

📈 LONG (ưu tiên):
Entry: 125,000 | SL: 121,000 (-3.2%)
TP1: 130,000 | TP2: 135,000 | R:R 1:2.5
Timeframe: Swing | Vốn: 10%

📉 SHORT:
Entry: 130,000 | SL: 133,000 | Conviction: 3/10

💡 FPT xu hướng tăng với MACD bullish...
```

**Implementation:** Modify `MessageFormatter.signal_alert()` to accept optional plan data. When plan exists, format the structured section. When missing, send existing format unchanged.

## Scheduler Chain Changes

### Modified `_on_job_executed` in `manager.py`

```python
# CURRENT (combined → signal_alert + hnx_upcom):
elif event.job_id in ("daily_combined_triggered", "daily_combined_manual"):
    → signal_alert_check
    → hnx_upcom_analysis

# NEW (combined → trading_plan → signal_alert, combined → hnx_upcom):
elif event.job_id in ("daily_combined_triggered", "daily_combined_manual"):
    → trading_plan_generation        # NEW
    → hnx_upcom_analysis             # UNCHANGED (parallel)

# NEW chain link:
elif event.job_id == "daily_trading_plan_triggered":
    → signal_alert_check             # MOVED from combined chain
```

**Full updated pipeline:**
```
price_crawl_upcom
  → indicator_compute
    → ai_analysis (tech + fund)
      → news_crawl
        → sentiment_analysis
          → combined_analysis
            → trading_plan_generation   ← NEW
              → signal_alert_check      ← MOVED (was parallel with combined)
            + hnx_upcom_analysis        ← UNCHANGED (parallel)
```

## Patterns to Follow

### Pattern 1: Reuse `_run_batched_analysis` Infrastructure

**What:** All existing batch orchestration (rate limiting, retry, 429 handling, commit, usage tracking) is in `_run_batched_analysis`. Trading plans use the same method.

**Why:** The method is battle-tested across 4 analysis types with 800+ tickers daily. Zero new retry/rate-limit logic needed.

### Pattern 2: JSONB for Rich Structured Data, Simple Columns for Queries

**What:** `signal` and `score` columns store queryable summary. `raw_response` JSONB stores full structured plan.

**Why:** Enables efficient SQL queries (`WHERE signal = 'long' AND score >= 8`) while preserving rich nested data for API/frontend. No schema changes when adding plan fields.

### Pattern 3: Filtering Before Batching

**What:** Query qualifying tickers BEFORE starting Gemini calls, not after.

**Why:** Critical for rate limit management. 800 tickers × 10/batch = 80 calls. 80 filtered tickers × 10/batch = 8 calls. 10x reduction.

### Pattern 4: Same Few-Shot + System Instruction Architecture

**What:** Dedicated system instruction + few-shot example for trading plans, matching the pattern used by all 4 existing analysis types.

**Why:** Proven pattern for consistent Gemini output quality. Temperature tuned per task type.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Generating Plans for ALL Tickers
**What:** Running trading plans for all 800+ tickers like other analysis types.
**Why bad:** 80+ Gemini calls vs 8. Wastes tokens on neutral-signal tickers where plans are meaningless. Risks hitting daily free tier limits.
**Instead:** Filter to strong-signal + watchlisted tickers. Cap at 100.

### Anti-Pattern 2: Storing Trading Plan in a Separate Table
**What:** Creating a `trading_plans` table with columns for each price level.
**Why bad:** Rigid schema. Every new field requires a migration. JSONB in raw_response is strictly better for this use case.
**Instead:** Use existing ai_analyses table with JSONB raw_response.

### Anti-Pattern 3: Making Trading Plans Part of Combined Analysis
**What:** Running trading plan generation as part of the combined Gemini call.
**Why bad:** Doubles combined prompt token usage. Different temperature needs. Failure in plan generation breaks recommendations. Coupling two different concerns.
**Instead:** Separate call, separate chain step, separate failure handling.

### Anti-Pattern 4: Real-Time Plan Recalculation
**What:** Recalculating plans when price changes intraday.
**Why bad:** Not the system's purpose. Plans are daily strategic views, not real-time signals. Would burn through rate limits.
**Instead:** Generate once daily after combined analysis. On-demand via "Analyze now" button.

### Anti-Pattern 5: Complex Price Level Validation in Backend
**What:** Validating that SL < Entry < TP for LONG (etc.) in Python code.
**Why bad:** Gemini occasionally produces inconsistent levels. Hard validation would reject useful partial results. The prompt + few-shot example guides correct output.
**Instead:** Let Gemini produce plans, display as-is. User applies judgment. Log anomalies for prompt tuning.

## Suggested Build Order

Based on dependency analysis of the existing codebase:

### Phase 1: Schema & DB Foundation
1. Add `TRADING_PLAN` to `AnalysisType` enum in `models/ai_analysis.py`
2. Add all Pydantic schemas to `schemas/analysis.py` (Gemini + API response)
3. Create Alembic migration `010_trading_plan.py`
4. Add config values to `Settings` (`gemini_trading_plan_batch_size`, `max_trading_plans`)

**Why first:** Everything else depends on type and schema definitions.

### Phase 2: AI Pipeline (Core Logic)
1. Add system instruction + few-shot + temperature constants
2. Implement `_get_trading_plan_qualifying_tickers()`
3. Implement `_get_trading_plan_context()`
4. Implement `_build_trading_plan_prompt()`
5. Implement `_analyze_trading_plan_batch()`
6. Implement `run_trading_plan_generation()`
7. Add `batch_size` override parameter to `_run_batched_analysis()`
8. Extend `analyze_single_ticker()` to include trading plans
9. Add result processing for `TRADING_PLAN` in `_run_batched_analysis` switch

**Why second:** Service methods can be tested in isolation. Tests verify Gemini schema, storage, and filtering.

### Phase 3: Scheduler & Job Chain
1. Add `daily_trading_plan_generation` job function in `jobs.py`
2. Modify job chain: combined → trading_plan → signal_alerts
3. Add to `_JOB_NAMES` mapping

**Why third:** Depends on service methods from Phase 2.

### Phase 4: API Endpoints
1. Add `GET /analysis/{symbol}/trading-plan` endpoint
2. Extend `GET /analysis/{symbol}/summary` to include trading plan
3. Add `POST /trigger/trading-plans` manual trigger
4. Extend `POST /trigger/ai` to accept `'trading_plan'` type

**Why fourth:** Endpoints consume service and DB — needs both ready.

### Phase 5: Frontend Trading Plan Panel
1. Add TypeScript types in `api.ts`
2. Add `fetchTradingPlan` function and `useTradingPlan` hook
3. Build `TradingPlanPanel` component with direction tabs
4. Mount in ticker detail page between CombinedCard and AnalysisCards
5. Verify data flow: API → useAnalysisSummary → TradingPlanPanel

**Why fifth:** Frontend is the consumer — needs all backend working.

### Phase 6: Telegram Enhancement
1. Enhance `MessageFormatter` to include plan in signal alerts
2. Modify signal alert check to fetch trading plan data for qualifying tickers
3. Format with entry/SL/TP in Telegram HTML message

**Why last:** Incremental enhancement with lowest risk. Existing alerts continue working without this.

## Sources

- **HIGH confidence:** Full codebase analysis of `ai_analysis_service.py` (1134 lines), `ai_analysis.py` model, `analysis.py` schemas, `analysis.py` API endpoints, `manager.py` scheduler, `page.tsx` ticker detail, `analysis-card.tsx`, `api.ts`, `hooks.ts`
- **HIGH confidence:** Existing patterns verified from 4 working analysis types (technical, fundamental, sentiment, combined) — identical patterns proposed for trading plans
- **HIGH confidence:** PostgreSQL ENUM extension pattern verified from migration `003_sentiment_tables.py` which added 'combined' using identical `ALTER TYPE ... ADD VALUE IF NOT EXISTS` syntax
- **HIGH confidence:** Gemini structured output with nested Pydantic models via `response_schema` verified from existing `_call_gemini_with_retry()` implementation with `google-genai>=1.73`
- **HIGH confidence:** JSONB storage strategy verified from existing `_store_analysis()` which already serializes `model_dump()` to JSONB for all 4 analysis types
- **MEDIUM confidence:** Token estimates based on existing usage patterns and prompt size extrapolation. Actual token counts should be measured during Phase 2 implementation
- **MEDIUM confidence:** Batch size of 10 for trading plans. May need tuning based on actual Gemini output size with nested Pydantic models — test with 5-ticker batches first, scale up

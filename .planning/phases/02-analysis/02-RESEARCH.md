# Phase 2: Technical & Fundamental Analysis - Research

**Researched:** 2026-04-15
**Domain:** Technical indicator computation (`ta` library) + AI analysis (Google Gemini via `google-genai` SDK)
**Confidence:** HIGH

## Summary

Phase 2 adds computed technical indicators and AI-powered scoring on top of Phase 1's OHLCV and financial data. The `ta` library (0.11.0) works correctly with pandas 3.0.2 — verified in the project's own venv. All required indicators (RSI, MACD, SMA, EMA, Bollinger Bands) are available as individual class-based APIs that accept a `close` pandas Series and return a new Series with NaN values for warm-up periods.

The `google-genai` SDK (1.73.1) provides native async support via `client.aio.models.generate_content()` with structured JSON output using Pydantic models passed to `response_schema`. The response object has a `.parsed` attribute that returns the validated Pydantic model directly — no manual JSON parsing needed. Rate limits for Gemini 2.0 Flash free tier (15 RPM) require 4-second minimum delays between requests. With 10 tickers per batch (40 batches for 400 tickers), the full analysis run takes ~3 minutes.

**Primary recommendation:** Use `ta` individual indicator classes (not `add_all_ta_features`), store results with nullable columns (NaN → NULL), chain jobs via APScheduler's `EVENT_JOB_EXECUTED` listener, and use Pydantic models for Gemini structured output with `response.parsed` for type-safe access.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Store indicators in new `technical_indicators` table (one row per ticker per date). Columns: RSI(14), MACD line/signal/histogram, SMA(20/50/200), EMA(12/26), BB upper/middle/lower. Separate from `daily_prices`.
- Compute automatically after daily price crawl completes — scheduler chains: crawl → compute. Also expose API endpoint for on-demand recomputation.
- SMA(200) needs 200 days. Backfill from 2023-07-01 provides ~500 trading days. Compute for most recent 60 days per run. Store all, compute only new/missing dates.
- Standard parameters: RSI(14), MACD(12,26,9), SMA(20/50/200), EMA(12/26), Bollinger(20,2). Hardcoded in v1.
- `gemini-2.0-flash` model — 15 RPM free tier, structured JSON output.
- Batch 5-10 tickers per prompt → ~40-80 calls. 2-second delay between calls. Run async post-crawl, not real-time.
- Feed Gemini pre-computed indicators (not raw OHLCV). Technical: 5-day indicator values, price vs MAs, MACD crossover state, RSI zone. Fundamental: P/E, P/B, ROE, ROA, revenue/profit growth, D/E, current ratio.
- AI output JSON via `response_schema`. Technical: `{signal, strength(1-10), reasoning}`. Fundamental: `{health, score(1-10), reasoning}`. Store in `ai_analyses` table with type, JSONB result, model version.
- New `ai_analyses` table: ticker_id, analysis_type enum (technical/fundamental/sentiment), analysis_date, signal, score(1-10), reasoning text, model_version, raw_response JSONB. One row per ticker per type per date.
- Retry 3x with exponential backoff (tenacity). Failed batches logged and skipped — partial analysis > none.
- `ai_analyses` table uses `analysis_type` enum to accommodate sentiment (Phase 3).
- Use `ta` library (pure Python) for computation.
- Use `google-genai` SDK (new, not legacy).

### Copilot's Discretion
- None specified — all grey areas were resolved with locked decisions.

### Deferred Ideas (OUT OF SCOPE)
- None specified.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AI-01 | Technical analysis scoring — RSI, MACD, MA crossovers → bullish/bearish/neutral signal | `ta` library verified for all indicators; Gemini structured output with `response_schema` for signal/strength/reasoning |
| AI-02 | Fundamental analysis scoring — P/E, growth, financial health → health score | Existing `financials` table has all needed data; Gemini prompt with same structured output pattern |
</phase_requirements>

## Standard Stack

### Core (Phase 2 additions)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| ta | 0.11.0 | Technical indicator computation | Pure Python, zero C deps, 40+ indicators. Verified working with pandas 3.0.2 in project venv. [VERIFIED: pip index + runtime test] |
| google-genai | 1.73.1 | Gemini API SDK (async) | New unified SDK. Native async via `client.aio`. Structured output with Pydantic models. [VERIFIED: pip index versions + API inspection] |

### Supporting (already in project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tenacity | 9.1.4 | Retry with exponential backoff | Gemini API calls — retry on 429/5xx errors |
| pandas | 3.0.2 | DataFrame for indicator input | Feed OHLCV data to `ta` library |
| sqlalchemy | 2.0.49 | ORM for new tables | `technical_indicators` and `ai_analyses` tables |
| alembic | 1.18.4 | Database migrations | Migration 002 for new tables |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| ta 0.11.0 | ta-lib 0.6.8 | Requires C library install — nightmare on Windows. Same indicators. |
| ta 0.11.0 | pandas-ta | Removed from PyPI — dead project. Cannot install. |
| google-genai 1.73 | google-generativeai 0.8.6 | Legacy SDK being phased out. No structured output support. |
| Individual ta classes | `ta.add_all_ta_features()` | Adds 80+ columns, most unused. Individual classes give precise control. |

**Installation (add to requirements.txt):**
```
ta==0.11.0
google-genai>=1.73,<2
```

## Architecture Patterns

### Recommended Project Structure (Phase 2 additions)
```
backend/app/
├── models/
│   ├── technical_indicator.py  # TechnicalIndicator ORM model
│   └── ai_analysis.py          # AIAnalysis ORM model + AnalysisType enum
├── services/
│   ├── indicator_service.py     # ta computation logic
│   └── ai_analysis_service.py   # Gemini integration
├── schemas/
│   ├── analysis.py              # Pydantic response schemas for Gemini
│   └── indicator.py             # API response schemas
├── api/
│   └── analysis.py              # Trigger endpoints
└── scheduler/
    └── jobs.py                  # + daily_indicator_compute, daily_ai_analysis
```

### Pattern 1: ta Library Individual Indicator Classes
**What:** Use per-indicator classes from `ta.momentum`, `ta.trend`, `ta.volatility` — not the all-in-one `add_all_ta_features()` function.
**When to use:** Always for this project — we need exactly 12 indicator values, not 80+.
**Verified:** Runtime tested with pandas 3.0.2 [VERIFIED: venv runtime test]

```python
# Source: [VERIFIED: runtime test with ta 0.11.0 + pandas 3.0.2]
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.volatility import BollingerBands

def compute_indicators(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Compute all technical indicators from OHLCV DataFrame.
    
    Args:
        df: DataFrame with 'close' column. Must have 200+ rows for SMA(200).
    
    Returns: dict of indicator_name → Series (same index as input df)
    """
    close = df["close"].astype(float)
    
    rsi = RSIIndicator(close=close, window=14, fillna=False)
    macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9, fillna=False)
    sma20 = SMAIndicator(close=close, window=20, fillna=False)
    sma50 = SMAIndicator(close=close, window=50, fillna=False)
    sma200 = SMAIndicator(close=close, window=200, fillna=False)
    ema12 = EMAIndicator(close=close, window=12, fillna=False)
    ema26 = EMAIndicator(close=close, window=26, fillna=False)
    bb = BollingerBands(close=close, window=20, window_dev=2, fillna=False)
    
    return {
        "rsi_14": rsi.rsi(),
        "macd_line": macd.macd(),
        "macd_signal": macd.macd_signal(),
        "macd_histogram": macd.macd_diff(),
        "sma_20": sma20.sma_indicator(),
        "sma_50": sma50.sma_indicator(),
        "sma_200": sma200.sma_indicator(),
        "ema_12": ema12.ema_indicator(),
        "ema_26": ema26.ema_indicator(),
        "bb_upper": bb.bollinger_hband(),
        "bb_middle": bb.bollinger_mavg(),
        "bb_lower": bb.bollinger_lband(),
    }
```

### Pattern 2: google-genai Async Structured Output
**What:** Use `client.aio.models.generate_content()` with `response_schema` pointing to a Pydantic model. Response `.parsed` returns the validated model.
**When to use:** All Gemini API calls.
**Verified:** API inspection confirmed async support and Pydantic schema acceptance [VERIFIED: google-genai 1.73.1 API inspection]

```python
# Source: [VERIFIED: google-genai 1.73.1 API inspection]
from pydantic import BaseModel
from enum import Enum
import google.genai as genai
from google.genai import types

class TechnicalSignal(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

class TickerTechnicalAnalysis(BaseModel):
    ticker: str
    signal: TechnicalSignal
    strength: int  # 1-10
    reasoning: str

class TechnicalBatchResponse(BaseModel):
    analyses: list[TickerTechnicalAnalysis]

# Client initialization — uses GOOGLE_API_KEY env var by default
client = genai.Client(api_key="your-key")

# Async call with structured output
response = await client.aio.models.generate_content(
    model="gemini-2.0-flash",
    contents=prompt_text,
    config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=TechnicalBatchResponse,
        temperature=0.2,  # Low for consistent analysis
        max_output_tokens=4096,
    ),
)

# Access parsed response — Pydantic model, not raw JSON
result: TechnicalBatchResponse = response.parsed
for analysis in result.analyses:
    print(f"{analysis.ticker}: {analysis.signal} ({analysis.strength}/10)")

# Token usage
print(f"Tokens: {response.usage_metadata.total_token_count}")
```

### Pattern 3: APScheduler Job Chaining via Event Listener
**What:** Use `scheduler.add_listener(callback, EVENT_JOB_EXECUTED)` to trigger indicator computation after price crawl completes. The callback receives a `JobExecutionEvent` with `job_id` to identify which job finished.
**When to use:** Chain daily_price_crawl → daily_indicator_compute → daily_ai_analysis.
**Verified:** APScheduler 3.11 event API inspected [VERIFIED: APScheduler API inspection in venv]

```python
# Source: [VERIFIED: APScheduler 3.11 event API inspection]
from apscheduler import events

def on_job_executed(event: events.JobExecutionEvent):
    """Chain jobs: price crawl → indicators → AI analysis."""
    if event.exception:
        logger.warning(f"Job {event.job_id} failed, not chaining")
        return
    
    if event.job_id == "daily_price_crawl":
        # Schedule indicator computation to run immediately
        scheduler.add_job(
            daily_indicator_compute,
            id="daily_indicator_compute_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )
    elif event.job_id == "daily_indicator_compute_triggered":
        scheduler.add_job(
            daily_ai_analysis,
            id="daily_ai_analysis_triggered",
            replace_existing=True,
            misfire_grace_time=3600,
        )

# Register in configure_jobs()
scheduler.add_listener(on_job_executed, events.EVENT_JOB_EXECUTED)
```

### Pattern 4: Tenacity Retry for Gemini with Rate Limit Awareness
**What:** Use tenacity's `retry_if_exception_type` to retry on `ClientError` (429 rate limit) and `ServerError` (5xx), but not on schema/prompt errors.
**Verified:** google-genai error hierarchy inspected [VERIFIED: google-genai error source code]

```python
# Source: [VERIFIED: google-genai errors module inspection]
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from google.genai.errors import ClientError, ServerError

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    retry=retry_if_exception_type((ClientError, ServerError)),
    reraise=True,
)
async def call_gemini_with_retry(client, prompt, config):
    """Call Gemini with retry on rate limits and server errors.
    
    ClientError (4xx) includes 429 rate limit.
    ServerError (5xx) includes transient failures.
    """
    return await client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=config,
    )
```

### Pattern 5: Alembic Migration with PostgreSQL ENUM
**What:** Create PostgreSQL ENUM type for `analysis_type` and two new tables in migration 002.
**When to use:** Follow existing `001_initial_schema.py` pattern — raw DDL via `op.execute()`.
**Verified:** Existing migration pattern uses raw SQL DDL [VERIFIED: codebase inspection]

```python
# Source: [VERIFIED: codebase pattern from 001_initial_schema.py]
# alembic/versions/002_analysis_tables.py

def upgrade() -> None:
    # Create ENUM type for analysis categories
    op.execute("""
        CREATE TYPE analysis_type AS ENUM ('technical', 'fundamental', 'sentiment');
    """)
    
    # Technical indicators table
    op.execute("""
        CREATE TABLE technical_indicators (
            id BIGSERIAL PRIMARY KEY,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            date DATE NOT NULL,
            rsi_14 NUMERIC(8,4),
            macd_line NUMERIC(12,6),
            macd_signal NUMERIC(12,6),
            macd_histogram NUMERIC(12,6),
            sma_20 NUMERIC(12,4),
            sma_50 NUMERIC(12,4),
            sma_200 NUMERIC(12,4),
            ema_12 NUMERIC(12,4),
            ema_26 NUMERIC(12,4),
            bb_upper NUMERIC(12,4),
            bb_middle NUMERIC(12,4),
            bb_lower NUMERIC(12,4),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_technical_indicators_ticker_date UNIQUE (ticker_id, date)
        );
        CREATE INDEX idx_technical_indicators_ticker_date 
            ON technical_indicators (ticker_id, date DESC);
    """)
    
    # AI analyses table
    op.execute("""
        CREATE TABLE ai_analyses (
            id BIGSERIAL PRIMARY KEY,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            analysis_type analysis_type NOT NULL,
            analysis_date DATE NOT NULL,
            signal VARCHAR(20) NOT NULL,
            score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 10),
            reasoning TEXT NOT NULL,
            model_version VARCHAR(50) NOT NULL,
            raw_response JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_ai_analyses_ticker_type_date 
                UNIQUE (ticker_id, analysis_type, analysis_date)
        );
        CREATE INDEX idx_ai_analyses_ticker_type 
            ON ai_analyses (ticker_id, analysis_type, analysis_date DESC);
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_analyses CASCADE;")
    op.execute("DROP TABLE IF EXISTS technical_indicators CASCADE;")
    op.execute("DROP TYPE IF EXISTS analysis_type;")
```

### Anti-Patterns to Avoid
- **Using `ta.add_all_ta_features()`:** Adds 80+ columns when we need 12. Wastes computation and makes column mapping unclear.
- **Using `fillna=True` in ta constructors:** Fills warm-up NaN with misleading values (0 or forward-fill). Store NaN as NULL — warm-up rows simply have fewer populated indicators.
- **Sync Gemini calls:** `client.models.generate_content()` is sync. MUST use `client.aio.models.generate_content()` to avoid blocking FastAPI's event loop.
- **Parsing `response.text` manually:** Use `response.parsed` which returns the Pydantic model directly when `response_schema` is set.
- **Single ticker per Gemini call:** 400 calls at 15 RPM = 27 minutes. Batch 10 tickers per call = 40 calls = ~3 minutes.
- **Recomputing all history every day:** Compute only new/missing dates. Query `MAX(date)` from `technical_indicators` per ticker, compute from there forward.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| RSI/MACD/SMA/EMA/BB calculation | Custom math | `ta` library classes | Edge cases in RSI smoothing, MACD signal line EMA, BB standard deviation — all handled correctly |
| JSON schema enforcement on LLM output | String parsing + regex | `response_schema` + Pydantic model | Gemini enforces schema server-side and returns validated JSON |
| Retry with backoff | Custom sleep loops | `tenacity` decorator | Already in project, handles attempt counting, jitter, exception filtering |
| Enum type in PostgreSQL | VARCHAR with CHECK | `CREATE TYPE ... AS ENUM` | Enforced at DB level, extensible for Phase 3 sentiment |

**Key insight:** Both `ta` and `google-genai` have purpose-built APIs that eliminate the need for manual computation or JSON wrangling. The biggest time-saver is `response.parsed` — it returns a typed Pydantic model from Gemini's JSON output.

## Common Pitfalls

### Pitfall 1: NaN Warm-up Period in Indicators
**What goes wrong:** SMA(200) produces NaN for the first 199 rows. If you try to store these as 0.0, it corrupts analysis.
**Why it happens:** Moving averages need N data points before producing a valid value.
**How to avoid:** Use `fillna=False` (default). Store NaN as NULL in PostgreSQL. Query with `WHERE sma_200 IS NOT NULL` when needed.
**Warning signs:** SMA(200) has 199 NaN, MACD signal has 33 NaN, RSI has 13 NaN, BB has 19 NaN. [VERIFIED: runtime test]

**Verified NaN counts per indicator (250 data points):**
| Indicator | NaN Count | First Valid Row |
|-----------|-----------|-----------------|
| RSI(14) | 13 | Row 13 |
| MACD line | 25 | Row 25 |
| MACD signal | 33 | Row 33 |
| MACD histogram | 33 | Row 33 |
| SMA(20) | 19 | Row 19 |
| SMA(50) | 49 | Row 49 |
| SMA(200) | 199 | Row 199 |
| EMA(12) | 11 | Row 11 |
| EMA(26) | 25 | Row 25 |
| BB upper/middle/lower | 19 | Row 19 |

### Pitfall 2: Gemini 15 RPM Free Tier Rate Limit
**What goes wrong:** Sending requests faster than 15 RPM returns 429 errors. With 2-second delays, you'd hit 30 RPM.
**Why it happens:** Free tier has strict per-minute limits.
**How to avoid:** Use 4-second minimum delay between requests (`asyncio.sleep(4)`). With 10 tickers/batch = 40 batches = ~160 seconds (~2.7 min). The tenacity retry with exponential backoff (min=4s) handles occasional 429s.
**Warning signs:** `ClientError` with code 429 in logs.

### Pitfall 3: Blocking Event Loop with Sync Gemini Client
**What goes wrong:** Using `client.models.generate_content()` (sync) blocks FastAPI's event loop for the entire analysis run (~3 minutes).
**Why it happens:** google-genai has both sync and async APIs on the same client.
**How to avoid:** Always use `client.aio.models.generate_content()` — the async version.
**Warning signs:** API endpoints become unresponsive during analysis.

### Pitfall 4: Decimal Precision for Indicator Storage
**What goes wrong:** `ta` returns float64 values. Naive `Decimal(float_value)` creates `Decimal('0.30000000000000004')`.
**Why it happens:** IEEE 754 floating point representation.
**How to avoid:** Use `Decimal(str(round(value, 6)))` or store as `NUMERIC(12,4)` / `NUMERIC(12,6)` and let PostgreSQL truncate. The existing `_safe_decimal` pattern from `FinancialService` works.
**Warning signs:** Database values with 17+ decimal places.

### Pitfall 5: Gemini Structured Output With Enum Values
**What goes wrong:** Gemini might return enum values not in the defined set if the prompt is ambiguous.
**Why it happens:** The model tries to be creative with signal names.
**How to avoid:** `response_schema` with a Python `Enum` class enforces valid values server-side. Gemini will only return values from the enum. [VERIFIED: Pydantic enum schema accepted by GenerateContentConfig]
**Warning signs:** Pydantic validation errors when parsing `response.parsed`.

### Pitfall 6: Computing Indicators Without Enough History
**What goes wrong:** Calling indicator computation on a ticker with < 200 days of data means SMA(200) is always NULL.
**Why it happens:** New tickers or tickers with gaps in daily_prices.
**How to avoid:** Query daily_prices count before computing. Skip tickers with < 200 rows — they won't have meaningful SMA(200). Log a warning. Other indicators (RSI, BB, SMA(20/50)) will still compute fine with fewer rows.
**Warning signs:** `sma_200` is NULL for all rows of a ticker.

## Code Examples

### Complete Indicator Service Pattern
```python
# Source: [VERIFIED: combining ta API + existing service patterns from codebase]
import asyncio
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator, EMAIndicator
from ta.volatility import BollingerBands

from app.models.daily_price import DailyPrice
from app.models.technical_indicator import TechnicalIndicator


class IndicatorService:
    """Compute and store technical indicators for all tickers."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def compute_for_ticker(self, ticker_id: int, symbol: str) -> int:
        """Compute indicators for a single ticker. Returns rows stored."""
        # Fetch price history (need 200+ rows for SMA(200))
        result = await self.session.execute(
            select(DailyPrice.date, DailyPrice.close)
            .where(DailyPrice.ticker_id == ticker_id)
            .order_by(DailyPrice.date)
        )
        rows = result.fetchall()
        
        if len(rows) < 200:
            logger.warning(f"{symbol}: Only {len(rows)} price rows, need 200+ for SMA(200)")
            if len(rows) < 20:
                return 0  # Not enough data for any indicator
        
        df = pd.DataFrame(rows, columns=["date", "close"])
        df["close"] = df["close"].astype(float)
        
        # Compute all indicators
        indicators = self._compute_all(df["close"])
        
        # Find last computed date to only store new rows
        last_computed = await self._get_last_date(ticker_id)
        
        # Store only new dates (most recent 60 days for daily runs)
        stored = 0
        for i, row_date in enumerate(df["date"]):
            if last_computed and row_date <= last_computed:
                continue
            
            values = {col: self._safe_decimal(indicators[col].iloc[i]) 
                      for col in indicators}
            values["ticker_id"] = ticker_id
            values["date"] = row_date
            
            stmt = insert(TechnicalIndicator).values(**values).on_conflict_do_update(
                constraint="uq_technical_indicators_ticker_date",
                set_=values,
            )
            await self.session.execute(stmt)
            stored += 1
        
        return stored

    def _compute_all(self, close: pd.Series) -> dict[str, pd.Series]:
        """Compute all 12 indicator values from close prices."""
        return {
            "rsi_14": RSIIndicator(close=close, window=14).rsi(),
            "macd_line": MACD(close=close, window_slow=26, window_fast=12, window_sign=9).macd(),
            "macd_signal": MACD(close=close, window_slow=26, window_fast=12, window_sign=9).macd_signal(),
            "macd_histogram": MACD(close=close, window_slow=26, window_fast=12, window_sign=9).macd_diff(),
            "sma_20": SMAIndicator(close=close, window=20).sma_indicator(),
            "sma_50": SMAIndicator(close=close, window=50).sma_indicator(),
            "sma_200": SMAIndicator(close=close, window=200).sma_indicator(),
            "ema_12": EMAIndicator(close=close, window=12).ema_indicator(),
            "ema_26": EMAIndicator(close=close, window=26).ema_indicator(),
            "bb_upper": BollingerBands(close=close, window=20, window_dev=2).bollinger_hband(),
            "bb_middle": BollingerBands(close=close, window=20, window_dev=2).bollinger_mavg(),
            "bb_lower": BollingerBands(close=close, window=20, window_dev=2).bollinger_lband(),
        }

    @staticmethod
    def _safe_decimal(value) -> Decimal | None:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return None
        try:
            return Decimal(str(round(value, 6)))
        except (InvalidOperation, ValueError):
            return None

    async def _get_last_date(self, ticker_id: int) -> date | None:
        result = await self.session.execute(
            select(func.max(TechnicalIndicator.date))
            .where(TechnicalIndicator.ticker_id == ticker_id)
        )
        return result.scalar_one_or_none()
```

**Optimization note:** The MACD and BB classes are instantiated multiple times above for clarity. In production, instantiate once and call multiple methods:
```python
macd = MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
macd_line = macd.macd()
macd_signal = macd.macd_signal()
macd_histogram = macd.macd_diff()

bb = BollingerBands(close=close, window=20, window_dev=2)
bb_upper = bb.bollinger_hband()
bb_middle = bb.bollinger_mavg()
bb_lower = bb.bollinger_lband()
```

### Complete AI Analysis Service Pattern
```python
# Source: [VERIFIED: google-genai 1.73.1 API + existing service patterns]
import asyncio
import json
from datetime import date
from enum import Enum

import google.genai as genai
from google.genai import types
from google.genai.errors import ClientError, ServerError
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger


# --- Pydantic schemas for Gemini structured output ---

class TechnicalSignal(str, Enum):
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    NEUTRAL = "neutral"
    SELL = "sell"
    STRONG_SELL = "strong_sell"

class TickerTechnicalAnalysis(BaseModel):
    ticker: str
    signal: TechnicalSignal
    strength: int  # 1-10
    reasoning: str

class TechnicalBatchResponse(BaseModel):
    analyses: list[TickerTechnicalAnalysis]

class FundamentalHealth(str, Enum):
    STRONG = "strong"
    GOOD = "good"
    NEUTRAL = "neutral"
    WEAK = "weak"
    CRITICAL = "critical"

class TickerFundamentalAnalysis(BaseModel):
    ticker: str
    health: FundamentalHealth
    score: int  # 1-10
    reasoning: str

class FundamentalBatchResponse(BaseModel):
    analyses: list[TickerFundamentalAnalysis]


# --- Service ---

class AIAnalysisService:
    BATCH_SIZE = 10
    DELAY_SECONDS = 4  # Minimum for 15 RPM free tier
    MODEL = "gemini-2.0-flash"

    def __init__(self, session, api_key: str):
        self.session = session
        self.client = genai.Client(api_key=api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=30),
        retry=retry_if_exception_type((ClientError, ServerError)),
        reraise=True,
    )
    async def _call_gemini(self, prompt: str, response_schema):
        """Call Gemini with retry. Rate limit (429) triggers exponential backoff."""
        response = await self.client.aio.models.generate_content(
            model=self.MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=response_schema,
                temperature=0.2,
                max_output_tokens=4096,
            ),
        )
        return response

    async def analyze_technical_batch(self, ticker_data: dict[str, dict]) -> TechnicalBatchResponse:
        """Analyze a batch of tickers for technical signals."""
        prompt = self._build_technical_prompt(ticker_data)
        response = await self._call_gemini(prompt, TechnicalBatchResponse)
        logger.debug(f"Gemini tokens: {response.usage_metadata.total_token_count}")
        return response.parsed
```

### Config Extension Pattern
```python
# Source: [VERIFIED: existing config.py pattern]
# Add to app/config.py:
class Settings(BaseSettings):
    # ... existing fields ...
    
    # Gemini AI
    gemini_api_key: str = ""  # Required for Phase 2
    gemini_model: str = "gemini-2.0-flash"
    gemini_batch_size: int = 10
    gemini_delay_seconds: float = 4.0
    gemini_max_retries: int = 3
    
    # Indicator computation
    indicator_compute_days: int = 60  # Compute for most recent N days
```

### ORM Model Patterns
```python
# Source: [VERIFIED: follows existing model patterns from ticker.py, daily_price.py]

# --- models/technical_indicator.py ---
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Integer, BigInteger, Numeric, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP
from app.models import Base

class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    
    # Momentum
    rsi_14: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    
    # Trend
    macd_line: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    macd_signal: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    macd_histogram: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    sma_20: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    sma_50: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    sma_200: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    ema_12: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    ema_26: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    
    # Volatility
    bb_upper: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    bb_middle: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    bb_lower: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ticker_id", "date", name="uq_technical_indicators_ticker_date"),
    )


# --- models/ai_analysis.py ---
import enum
from datetime import date, datetime
from sqlalchemy import Integer, BigInteger, String, Text, Date, ForeignKey, UniqueConstraint, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP
from app.models import Base

class AnalysisType(str, enum.Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"  # Phase 3

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    analysis_type: Mapped[AnalysisType] = mapped_column(
        SAEnum(AnalysisType, name="analysis_type", create_constraint=False, native_enum=False),
        nullable=False
    )
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    signal: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("ticker_id", "analysis_type", "analysis_date", 
                        name="uq_ai_analyses_ticker_type_date"),
    )
```

**Important note on ENUM strategy:** The migration uses raw `CREATE TYPE analysis_type AS ENUM (...)` in PostgreSQL DDL (following the project's migration pattern). The ORM model uses `SAEnum` with `native_enum=False` to avoid SQLAlchemy trying to create the type itself (since migration handles it). Alternatively, use `create_constraint=True, native_enum=True` if you want the ORM to reference the PostgreSQL enum. The safest pattern for this project is to handle ENUM in raw DDL migration and use `native_enum=False` with the string-backed enum in the ORM.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `google-generativeai` (legacy SDK) | `google-genai` (unified SDK) | 2024-2025 | New SDK required for structured output with Pydantic |
| Manual JSON parsing of LLM output | `response_schema` + `response.parsed` | google-genai ~1.x | Eliminates JSON parsing errors, Gemini enforces schema server-side |
| `pandas-ta` for indicators | `ta` library | pandas-ta removed from PyPI 2024 | `ta` is the only actively maintained pure-Python option |
| String-based JSON schemas for Gemini | Pass Pydantic `BaseModel` class directly | google-genai ~1.50+ | SDK handles schema conversion internally |

**Deprecated/outdated:**
- `google-generativeai`: Legacy package. Use `google-genai` instead.
- `pandas-ta`: Removed from PyPI entirely. Cannot be installed.
- `ta.add_all_ta_features()`: Still works but generates 80+ unused columns. Use individual classes.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Gemini 2.0 Flash free tier is 15 RPM | Common Pitfalls | If higher, delays can be reduced. If lower, need longer delays. Rate limit can be verified via API response headers at runtime. |
| A2 | Gemini 2.0 Flash supports structured output with `response_schema` | Architecture Patterns | Critical — if Flash doesn't support it, need to switch to Pro or parse JSON manually. Highly likely since google-genai SDK accepts it. [ASSUMED — needs runtime verification with actual API key] |
| A3 | Gemini 2.0 Flash context window is 1M tokens input / 8K tokens output | Token Estimates | Extremely unlikely to be a constraint — our batches use ~1,300 input + ~400 output tokens. |
| A4 | `native_enum=False` is the correct approach for ORM + raw DDL migration | Code Examples | If wrong, either enum isn't enforced or migration conflicts. Can be tested during implementation. |

## Open Questions

1. **Gemini API Key Configuration**
   - What we know: CLAUDE.md says "user has Gemini API key". Config uses pydantic-settings.
   - What's unclear: Is it stored in `.env` already? What env var name?
   - Recommendation: Add `GEMINI_API_KEY` to `.env.example` and `Settings` class. Check at startup.

2. **10 vs 5 Tickers Per Gemini Batch**
   - What we know: Context says "5-10 tickers per prompt". 10 = 40 batches (~3 min), 5 = 80 batches (~5.3 min).
   - What's unclear: Does Gemini quality degrade with 10 tickers vs 5?
   - Recommendation: Start with 10 per batch. If analysis quality is poor, reduce to 5. Make configurable via settings.

3. **ORM Enum vs Raw PostgreSQL ENUM**
   - What we know: Migration 001 uses raw DDL. SQLAlchemy can use both `native_enum=True` (references PG type) and `native_enum=False` (stores as VARCHAR).
   - What's unclear: Which approach integrates best with Alembic's autogenerate for future migrations?
   - Recommendation: Use raw `CREATE TYPE` in migration DDL + `native_enum=False` in ORM to avoid conflicts.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && .venv/Scripts/python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && .venv/Scripts/python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AI-01a | ta computes RSI/MACD/SMA/EMA/BB from price DataFrame | unit | `pytest tests/test_indicator_service.py -x` | ❌ Wave 0 |
| AI-01b | Indicator service stores computed values to DB | unit | `pytest tests/test_indicator_service.py -x` | ❌ Wave 0 |
| AI-01c | Gemini returns structured technical analysis | unit (mocked) | `pytest tests/test_ai_analysis_service.py -x` | ❌ Wave 0 |
| AI-02a | Gemini returns structured fundamental analysis | unit (mocked) | `pytest tests/test_ai_analysis_service.py -x` | ❌ Wave 0 |
| AI-02b | AI results stored in ai_analyses table | unit | `pytest tests/test_ai_analysis_service.py -x` | ❌ Wave 0 |
| CHAIN | Jobs chain correctly after price crawl | unit | `pytest tests/test_scheduler.py -x` | ✅ exists (extend) |

### Sampling Rate
- **Per task commit:** `cd backend && .venv\Scripts\python -m pytest tests/ -x -q`
- **Per wave merge:** `cd backend && .venv\Scripts\python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_indicator_service.py` — covers AI-01a, AI-01b (indicator computation + storage)
- [ ] `tests/test_ai_analysis_service.py` — covers AI-01c, AI-02a, AI-02b (Gemini mocked calls + storage)
- [ ] Extend `tests/test_scheduler.py` — covers CHAIN (job chaining via events)
- [ ] Framework install: `ta` and `google-genai` already have test-compatible APIs, no additional test frameworks needed

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — personal use, no user auth |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A — single user |
| V5 Input Validation | Yes | Pydantic models for Gemini response validation; `response_schema` enforces output structure |
| V6 Cryptography | No | No custom crypto |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key exposure in logs | Information Disclosure | Never log `GEMINI_API_KEY`. Use `settings.gemini_api_key` via pydantic-settings (not hardcoded). |
| LLM output injection | Tampering | `response_schema` constrains output to defined Pydantic model — no free-form text execution. |
| Rate limit exhaustion | Denial of Service | 4-second delays + tenacity retry with backoff. Don't expose batch analysis to unauthenticated API. |

## Sources

### Primary (HIGH confidence)
- `ta` 0.11.0 — runtime tested all indicators with pandas 3.0.2 in project venv
- `google-genai` 1.73.1 — API inspection (signatures, types, error classes)
- Existing codebase — models, services, scheduler, migration patterns
- pip index — version verification for ta 0.11.0, google-genai 1.73.1, tenacity 9.1.4

### Secondary (MEDIUM confidence)
- Gemini 2.0 Flash model capabilities (structured output, token limits) — inferred from SDK API + training data

### Tertiary (LOW confidence)
- Gemini free tier rate limits (15 RPM) — from training data, needs runtime verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified via pip + runtime tests
- Architecture: HIGH — patterns derived from verified API inspection + existing codebase
- Pitfalls: HIGH — NaN behavior verified via runtime tests; rate limits MEDIUM (assumed)

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable libraries, google-genai releases weekly but API is stable)

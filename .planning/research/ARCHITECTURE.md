# Architecture Patterns

**Domain:** Stock Market Data Crawling + AI Trading Assistant (Vietnam HOSE)
**Researched:** 2025-07-11
**Confidence:** HIGH (well-established patterns for data pipelines, financial schemas, FastAPI monoliths)

---

## Recommended Architecture

### One-Sentence Summary

**Async Python monolith** — a single FastAPI process containing data crawlers, analysis engine, API layer, scheduler, and Telegram bot as internal modules, communicating through PostgreSQL and in-process events.

### Why Monolith, Not Microservices

This is a single-user personal tool crawling 400 tickers. Microservices would add Docker orchestration, service discovery, network serialization, and deployment complexity for zero benefit. A well-structured monolith with clear module boundaries gives the same code organization without operational overhead.

**Rule of thumb:** If you can't name 3 teams that need to deploy independently, you don't need microservices.

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION                       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  SCHEDULER    │  │  CRAWLERS    │  │  TELEGRAM BOT    │  │
│  │  (APScheduler)│─▶│  - VNDirect  │  │  - Webhook/Poll  │  │
│  │              │  │  - SSI       │  │  - Commands      │  │
│  │  Triggers:   │  │  - CafeF     │  │  - Alerts        │  │
│  │  - EOD crawl │  └──────┬───────┘  └────────▲─────────┘  │
│  │  - Intraday  │         │ write                │ read     │
│  │  - News      │         ▼                      │          │
│  │  - Analysis  │  ┌──────────────┐              │          │
│  └──────────────┘  │  PROCESSORS  │              │          │
│                    │  - Cleaners   │              │          │
│                    │  - Validators │              │          │
│                    └──────┬───────┘              │          │
│                           │ write                │          │
│                           ▼                      │          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              POSTGRESQL (Aiven)                         │ │
│  │  tickers │ daily_prices │ financials │ news │ analyses  │ │
│  └────────────────────────▲───────────────────────────────┘ │
│                           │ read                            │
│                           │                                 │
│  ┌──────────────┐  ┌─────┴────────┐  ┌──────────────────┐  │
│  │  INDICATORS  │  │  AI ENGINE   │  │  REST API        │  │
│  │  - RSI, MACD │  │  - Technical │  │  /api/tickers    │  │
│  │  - MA, BB    │──▶  - Fundament.│  │  /api/prices     │  │
│  │  - Computed  │  │  - Sentiment │  │  /api/analysis   │  │
│  │    in Python │  │  - Composite │  │  /api/watchlist   │  │
│  └──────────────┘  │  (Gemini)    │  │  /api/portfolio   │  │
│                    └──────┬───────┘  └────────┬─────────┘  │
│                           │ write             │ JSON        │
│                           ▼                   ▼             │
│                    ┌──────────────┐    ┌────────────────┐   │
│                    │  ai_analyses │    │  NEXT.JS       │   │
│                    │  (stored)    │    │  FRONTEND      │   │
│                    └──────────────┘    │  (separate)    │   │
│                                       └────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Component Boundaries

### Component Map

| Component | Responsibility | Communicates With | Module Path |
|-----------|---------------|-------------------|-------------|
| **Scheduler** | Triggers crawls/analysis on schedule | Crawlers, AI Engine (in-process calls) | `app/scheduler/` |
| **Crawlers** | Fetch raw data from external sources | Processors (passes raw data), DB (writes) | `app/crawlers/` |
| **Processors** | Clean, validate, normalize raw data | Crawlers (receives), DB (writes clean data) | `app/processors/` |
| **Indicators** | Compute technical indicators from OHLCV | DB (reads prices), AI Engine (passes computed values) | `app/indicators/` |
| **AI Engine** | Gemini-powered analysis + synthesis | DB (reads all data), Indicators (receives), DB (writes analyses) | `app/ai/` |
| **REST API** | Serve data to frontend | DB (reads), all modules (status queries) | `app/api/` |
| **Telegram Bot** | Send alerts, respond to commands | DB (reads analyses/alerts), AI Engine (triggers on-demand) | `app/bot/` |
| **Next.js Frontend** | Dashboard UI, charts, interactions | REST API only (HTTP) | `frontend/` |

### Boundary Rules

1. **Crawlers never call AI Engine directly.** They write to DB; scheduler triggers analysis separately. This keeps crawling fast and decoupled from slow AI calls.
2. **Frontend only talks to REST API.** Never directly queries DB or calls Python modules.
3. **Telegram Bot reads from DB**, same as API. It doesn't have special data access.
4. **AI Engine receives pre-computed indicators**, not raw OHLCV. Python computes RSI/MACD/MA; Gemini interprets the values. This saves tokens and produces better analysis.

---

## Data Flow

### Flow 1: Scheduled EOD Data Pipeline (Daily, ~15:15 UTC+7)

```
APScheduler triggers "eod_crawl" job
  │
  ├─▶ VNDirect Crawler: fetch OHLCV for 400 tickers
  │     └─▶ Processor: validate, normalize → INSERT daily_prices
  │
  ├─▶ SSI Crawler: fetch any supplementary data
  │     └─▶ Processor: validate, normalize → INSERT/UPDATE daily_prices
  │
  ├─▶ CafeF Scraper: fetch financial reports (quarterly schedule)
  │     └─▶ Processor: parse HTML, extract numbers → INSERT financials
  │
  └─▶ News Crawler: fetch latest news articles
        └─▶ Processor: clean text, extract ticker mentions → INSERT news

APScheduler triggers "eod_analysis" job (after crawl completes)
  │
  ├─▶ Indicator Engine: compute RSI, MACD, MA, BB for all tickers
  │     └─▶ Store computed indicators in technical_indicators table
  │
  └─▶ AI Analysis Pipeline (for watchlist tickers + triggered tickers):
        ├─▶ Technical Analysis: indicators → Gemini prompt → score
        ├─▶ Fundamental Analysis: financials → Gemini prompt → score
        ├─▶ Sentiment Analysis: recent news → Gemini prompt → score
        └─▶ Composite Synthesis: 3 scores → Gemini prompt → recommendation
              └─▶ INSERT ai_analyses
              └─▶ If signal strength > threshold → Telegram alert
```

### Flow 2: Intraday Real-Time Tracking (Every 1-5 min during trading hours)

```
APScheduler triggers "intraday_update" job (9:00-14:45 UTC+7)
  │
  └─▶ VNDirect/SSI Crawler: fetch current prices for watchlist tickers
        └─▶ UPSERT intraday_prices (latest snapshot)
        └─▶ Check price alerts (% change thresholds)
              └─▶ If alert triggered → Telegram notification
```

### Flow 3: Frontend Dashboard Request

```
User opens dashboard
  │
  ├─▶ Next.js SSR/CSR → GET /api/market/overview
  │     └─▶ FastAPI reads market summary from DB → JSON response
  │
  ├─▶ User clicks ticker → GET /api/tickers/VNM
  │     └─▶ FastAPI reads prices + indicators + latest analysis → JSON
  │
  └─▶ Chart component → GET /api/prices/VNM?period=6m
        └─▶ FastAPI reads daily_prices → JSON array for charting
```

### Flow 4: Telegram Bot Interaction

```
User sends /analyze FPT
  │
  └─▶ Bot receives command
        ├─▶ Check if recent analysis exists in DB (< 4 hours old)
        │     └─▶ YES: Return cached analysis
        └─▶ NO: Trigger on-demand AI analysis
              └─▶ Run analysis pipeline for FPT
              └─▶ Store result → Send formatted response to Telegram
```

---

## Database Schema Design

### Design Principles for Financial Time-Series in PostgreSQL

1. **Partition `daily_prices` by year** — Each year ~100K rows (400 tickers × 250 trading days). Standard PostgreSQL partitioning is sufficient; TimescaleDB is overkill at this scale.
2. **Composite indexes on (ticker_id, date)** — Every query filters by ticker + date range.
3. **Use integer IDs for tickers, not VARCHAR symbols** — Joins are faster on integers.
4. **Store raw and computed data separately** — Never mix OHLCV with computed indicators.
5. **Decimal types for money** — Use `NUMERIC(12,2)` for prices, never `FLOAT`.

### Schema

```sql
-- Master ticker list
CREATE TABLE tickers (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,     -- 'VNM', 'FPT', 'VHM'
    name VARCHAR(200) NOT NULL,              -- 'Vinamilk'
    sector VARCHAR(100),                     -- 'Consumer Goods'
    exchange VARCHAR(10) DEFAULT 'HOSE',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Daily OHLCV price data (partitioned by year)
CREATE TABLE daily_prices (
    id BIGSERIAL,
    ticker_id INTEGER NOT NULL REFERENCES tickers(id),
    date DATE NOT NULL,
    open NUMERIC(12,2) NOT NULL,
    high NUMERIC(12,2) NOT NULL,
    low NUMERIC(12,2) NOT NULL,
    close NUMERIC(12,2) NOT NULL,
    volume BIGINT NOT NULL,
    value NUMERIC(18,2),                     -- Trading value in VND
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, date),
    UNIQUE (ticker_id, date)
) PARTITION BY RANGE (date);

-- Create yearly partitions
CREATE TABLE daily_prices_2024 PARTITION OF daily_prices
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE daily_prices_2025 PARTITION OF daily_prices
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

-- Intraday snapshots (current trading session only, truncated daily)
CREATE TABLE intraday_prices (
    id BIGSERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(id),
    timestamp TIMESTAMPTZ NOT NULL,
    price NUMERIC(12,2) NOT NULL,
    volume BIGINT,
    change_pct NUMERIC(6,3),                 -- % change from previous close
    UNIQUE (ticker_id, timestamp)
);

-- Financial reports (quarterly/yearly)
CREATE TABLE financials (
    id SERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(id),
    period_type VARCHAR(10) NOT NULL,        -- 'Q1', 'Q2', 'Q3', 'Q4', 'YEAR'
    period_year INTEGER NOT NULL,
    revenue NUMERIC(18,2),
    net_income NUMERIC(18,2),
    eps NUMERIC(12,2),
    pe_ratio NUMERIC(8,2),
    pb_ratio NUMERIC(8,2),
    roe NUMERIC(8,4),                        -- as decimal, e.g. 0.1523
    debt_to_equity NUMERIC(8,4),
    current_ratio NUMERIC(8,4),
    raw_data JSONB,                          -- Store full report for flexibility
    source VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker_id, period_type, period_year)
);

-- News articles
CREATE TABLE news (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT,
    summary TEXT,                             -- AI-generated or extracted
    url VARCHAR(500) UNIQUE,
    source VARCHAR(100),                     -- 'cafef', 'vndirect', etc.
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Many-to-many: which tickers are mentioned in which news
CREATE TABLE news_tickers (
    news_id INTEGER REFERENCES news(id) ON DELETE CASCADE,
    ticker_id INTEGER REFERENCES tickers(id) ON DELETE CASCADE,
    relevance_score NUMERIC(3,2),            -- 0.00-1.00 how relevant
    PRIMARY KEY (news_id, ticker_id)
);

-- Pre-computed technical indicators
CREATE TABLE technical_indicators (
    id BIGSERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(id),
    date DATE NOT NULL,
    sma_20 NUMERIC(12,2),
    sma_50 NUMERIC(12,2),
    sma_200 NUMERIC(12,2),
    ema_12 NUMERIC(12,2),
    ema_26 NUMERIC(12,2),
    rsi_14 NUMERIC(6,2),
    macd NUMERIC(12,4),
    macd_signal NUMERIC(12,4),
    macd_histogram NUMERIC(12,4),
    bb_upper NUMERIC(12,2),
    bb_middle NUMERIC(12,2),
    bb_lower NUMERIC(12,2),
    atr_14 NUMERIC(12,2),
    obv BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker_id, date)
);

-- AI analysis results
CREATE TABLE ai_analyses (
    id SERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(id),
    analysis_date DATE NOT NULL,
    -- Individual dimension scores (-100 to +100, negative=bearish, positive=bullish)
    technical_score INTEGER,
    technical_summary TEXT,
    fundamental_score INTEGER,
    fundamental_summary TEXT,
    sentiment_score INTEGER,
    sentiment_summary TEXT,
    -- Composite
    composite_score INTEGER,
    recommendation VARCHAR(20),              -- 'STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL'
    reasoning TEXT,                           -- Full AI reasoning
    confidence NUMERIC(3,2),                 -- 0.00-1.00
    -- Metadata
    model_version VARCHAR(50),               -- 'gemini-1.5-flash' etc.
    prompt_tokens INTEGER,
    response_tokens INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (ticker_id, analysis_date)
);

-- User watchlist
CREATE TABLE watchlist (
    id SERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(id) UNIQUE,
    notes TEXT,
    added_at TIMESTAMPTZ DEFAULT NOW()
);

-- Portfolio positions
CREATE TABLE portfolio (
    id SERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(id),
    quantity INTEGER NOT NULL,
    avg_buy_price NUMERIC(12,2) NOT NULL,
    buy_date DATE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alert configuration
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    ticker_id INTEGER REFERENCES tickers(id), -- NULL = market-wide alert
    alert_type VARCHAR(50) NOT NULL,         -- 'PRICE_ABOVE', 'PRICE_BELOW', 'CHANGE_PCT', 'AI_SIGNAL'
    threshold NUMERIC(12,2),
    is_active BOOLEAN DEFAULT true,
    last_triggered_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alert history
CREATE TABLE alert_history (
    id SERIAL PRIMARY KEY,
    alert_id INTEGER REFERENCES alerts(id),
    ticker_id INTEGER REFERENCES tickers(id),
    message TEXT NOT NULL,
    triggered_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_daily_prices_ticker_date ON daily_prices (ticker_id, date DESC);
CREATE INDEX idx_intraday_ticker_ts ON intraday_prices (ticker_id, timestamp DESC);
CREATE INDEX idx_financials_ticker ON financials (ticker_id, period_year DESC);
CREATE INDEX idx_news_published ON news (published_at DESC);
CREATE INDEX idx_news_tickers_ticker ON news_tickers (ticker_id);
CREATE INDEX idx_indicators_ticker_date ON technical_indicators (ticker_id, date DESC);
CREATE INDEX idx_analyses_ticker_date ON ai_analyses (ticker_id, analysis_date DESC);
CREATE INDEX idx_analyses_recommendation ON ai_analyses (recommendation, analysis_date DESC);
```

### Why This Schema

- **Partitioned `daily_prices`**: Queries always filter by date range. Partitioning lets PostgreSQL skip irrelevant year partitions entirely.
- **Separate `technical_indicators` table**: Indicators are derived data, recomputable from prices. Separating them means you can wipe and recompute without touching raw data.
- **JSONB `raw_data` in `financials`**: Financial reports have varying fields across sources. Store the canonical fields in typed columns for queries, keep raw data in JSONB for flexibility.
- **`news_tickers` junction table**: One news article can mention multiple tickers. A ticker can have many news articles.
- **Scores as integers (-100 to +100)**: Simple, sortable, easy to average. Avoid floating point ambiguity.

---

## API Layer Design (FastAPI)

### Endpoint Structure

```
/api/v1/
├── market/
│   ├── GET /overview           → Market summary, top gainers/losers, index
│   └── GET /heatmap            → Sector heatmap data
│
├── tickers/
│   ├── GET /                   → List all tickers (filterable by sector, watchlist)
│   ├── GET /{symbol}           → Ticker detail (latest price, key metrics)
│   └── GET /{symbol}/prices    → OHLCV history (?period=1m|3m|6m|1y|all)
│
├── analysis/
│   ├── GET /{symbol}           → Latest AI analysis for ticker
│   ├── GET /{symbol}/history   → Analysis history
│   ├── POST /{symbol}/trigger  → Trigger on-demand analysis
│   └── GET /signals            → All active buy/sell signals
│
├── indicators/
│   └── GET /{symbol}           → Technical indicators for ticker
│
├── news/
│   ├── GET /                   → Latest news (filterable by ticker)
│   └── GET /{symbol}           → News for specific ticker
│
├── watchlist/
│   ├── GET /                   → Get watchlist
│   ├── POST /                  → Add ticker to watchlist
│   └── DELETE /{symbol}        → Remove from watchlist
│
├── portfolio/
│   ├── GET /                   → Portfolio positions with current P&L
│   ├── POST /                  → Add position
│   ├── PUT /{id}               → Update position
│   └── DELETE /{id}            → Remove position
│
├── alerts/
│   ├── GET /                   → List alert configs
│   ├── POST /                  → Create alert
│   ├── PUT /{id}               → Update alert
│   └── DELETE /{id}            → Delete alert
│
└── system/
    ├── GET /status             → Scheduler status, last crawl times
    └── POST /crawl/trigger     → Manual crawl trigger
```

### FastAPI Patterns to Follow

```python
# Project structure
app/
├── main.py                     # FastAPI app, lifespan, middleware
├── config.py                   # Settings via pydantic-settings
├── database.py                 # AsyncSession setup (SQLAlchemy async)
├── models/                     # SQLAlchemy ORM models
│   ├── ticker.py
│   ├── price.py
│   ├── financial.py
│   ├── news.py
│   ├── analysis.py
│   └── ...
├── schemas/                    # Pydantic request/response schemas
│   ├── ticker.py
│   ├── price.py
│   └── ...
├── api/                        # Route handlers
│   ├── router.py               # Main router combining sub-routers
│   ├── market.py
│   ├── tickers.py
│   ├── analysis.py
│   └── ...
├── crawlers/                   # Data source connectors
│   ├── base.py                 # Abstract crawler interface
│   ├── vndirect.py
│   ├── ssi.py
│   └── cafef.py
├── processors/                 # Data cleaning/validation
│   ├── price_processor.py
│   ├── financial_processor.py
│   └── news_processor.py
├── indicators/                 # Technical indicator computation
│   └── calculator.py           # Uses pandas + ta library
├── ai/                         # Gemini integration
│   ├── client.py               # Gemini API wrapper
│   ├── prompts.py              # Prompt templates
│   ├── technical.py            # Technical analysis via AI
│   ├── fundamental.py          # Fundamental analysis via AI
│   ├── sentiment.py            # Sentiment analysis via AI
│   └── composite.py            # Synthesize 3 dimensions
├── bot/                        # Telegram integration
│   ├── handlers.py             # Command handlers
│   ├── alerts.py               # Alert sending logic
│   └── formatters.py           # Message formatting
├── scheduler/                  # Job scheduling
│   ├── jobs.py                 # Job definitions
│   └── manager.py              # APScheduler setup
└── services/                   # Business logic layer
    ├── analysis_service.py
    ├── crawler_service.py
    └── alert_service.py
```

### Key Pattern: Async Database with SQLAlchemy 2.0

```python
# database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    pool_size=5,          # Single user, 5 connections is plenty
    max_overflow=5,
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Dependency injection for FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```

### Key Pattern: Lifespan for Scheduler + Bot Startup

```python
# main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    scheduler.start()           # Start APScheduler
    await bot.start_polling()   # Start Telegram bot
    yield
    # Shutdown
    scheduler.shutdown()
    await bot.stop()

app = FastAPI(lifespan=lifespan)
```

---

## AI Analysis Pipeline

### Critical Design Decision: Pre-Compute, Then Interpret

**DO NOT** send raw OHLCV data arrays to Gemini. It wastes tokens and produces worse analysis.

**Instead:**
1. Compute all technical indicators in Python (pandas + `ta` library)
2. Extract key financial ratios from DB
3. Gather recent news headlines
4. Send **structured summaries** to Gemini for interpretation

### Pipeline Architecture

```
┌──────────────────────────────────────────────────────────┐
│                 AI ANALYSIS PIPELINE                       │
│                                                           │
│  Stage 1: Data Gathering (Python, no AI)                  │
│  ├── Read last 200 days of OHLCV from DB                  │
│  ├── Read financial reports from DB                       │
│  └── Read last 30 days of news from DB                    │
│                                                           │
│  Stage 2: Indicator Computation (Python, no AI)           │
│  ├── pandas-ta: RSI(14), MACD(12,26,9), SMA(20,50,200)  │
│  ├── Bollinger Bands, ATR, OBV                            │
│  └── Pattern detection: crossovers, divergences           │
│                                                           │
│  Stage 3: AI Analysis (3 parallel Gemini calls)           │
│  ├── Technical Prompt:                                    │
│  │   "RSI=72, MACD crossing below signal, price above     │
│  │    BB upper. SMA20>SMA50>SMA200. Volume declining.     │
│  │    Analyze the technical outlook..."                    │
│  │   → {score: -30, summary: "Overbought, likely pullback"}│
│  │                                                        │
│  ├── Fundamental Prompt:                                  │
│  │   "P/E=15.2 (sector avg 18), ROE=22%, revenue growth   │
│  │    +12% YoY, D/E=0.3. Analyze..."                      │
│  │   → {score: +45, summary: "Solid fundamentals..."}     │
│  │                                                        │
│  └── Sentiment Prompt:                                    │
│      "Headlines: [list of 10 recent headlines].            │
│       Analyze market sentiment..."                         │
│      → {score: +10, summary: "Mildly positive..."}        │
│                                                           │
│  Stage 4: Composite Synthesis (1 Gemini call)             │
│  ├── Input: 3 dimension scores + summaries                │
│  └── Output: composite recommendation + reasoning          │
│      → {recommendation: "HOLD", score: +8, reasoning: ...} │
│                                                           │
│  Stage 5: Store & Alert                                   │
│  ├── INSERT into ai_analyses                              │
│  └── If recommendation changed or signal strong → alert   │
└──────────────────────────────────────────────────────────┘
```

### Prompt Engineering Pattern: Structured Output

Use Gemini's structured output / JSON mode to get consistent results:

```python
# prompts.py — Example technical analysis prompt template
TECHNICAL_PROMPT = """
You are a Vietnamese stock market technical analyst.

Analyze {symbol} ({name}) with the following indicators:
- Current Price: {close} VND (change: {change_pct}%)
- RSI(14): {rsi} 
- MACD: {macd} (Signal: {macd_signal}, Histogram: {macd_hist})
- SMA20: {sma20}, SMA50: {sma50}, SMA200: {sma200}
- Bollinger Bands: Upper={bb_upper}, Middle={bb_mid}, Lower={bb_lower}
- Volume trend: {volume_trend}
- Key patterns: {patterns}

Respond in JSON:
{{
  "score": <integer -100 to +100>,
  "signal": "<STRONG_BUY|BUY|HOLD|SELL|STRONG_SELL>",
  "summary": "<2-3 sentences in Vietnamese>",
  "key_levels": {{
    "support": <price>,
    "resistance": <price>
  }}
}}
"""
```

### Rate Limiting & Cost Control

- Gemini API has rate limits (RPM and TPM). For 400 tickers, you **cannot** analyze all daily.
- **Strategy:** Full analysis only for watchlist tickers (e.g., 20-30). Scan-mode (lightweight scoring) for the rest.
- Batch with `asyncio.Semaphore(5)` to limit concurrent Gemini calls.
- Cache analysis results; re-analyze only when new data arrives.

---

## Scheduling Architecture

### Decision: APScheduler (not Celery, not cron)

| Criterion | APScheduler | Celery | Cron |
|-----------|-------------|--------|------|
| Extra infrastructure | None | Redis/RabbitMQ required | None |
| Python integration | Native, async-aware | Native | Subprocess only |
| Dynamic scheduling | Yes, runtime add/remove | Yes | Requires crontab edit |
| FastAPI integration | Excellent (same event loop) | OK (separate worker) | None |
| Monitoring | In-process, expose via API | Flower dashboard | Logs only |
| Fit for single user | ✅ Perfect | ❌ Overkill | ⚠️ Too basic |

### APScheduler Setup with FastAPI

```python
# scheduler/manager.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")

def configure_jobs():
    # EOD crawl — after market close + settlement
    scheduler.add_job(
        crawl_eod_data,
        CronTrigger(hour=15, minute=15, day_of_week="mon-fri"),
        id="eod_crawl",
        name="End-of-day data crawl"
    )
    
    # Intraday tracking — every 3 minutes during trading hours
    scheduler.add_job(
        crawl_intraday,
        CronTrigger(
            hour="9-11,13-14", minute="*/3", day_of_week="mon-fri"
        ),
        id="intraday_crawl",
        name="Intraday price update"
    )
    
    # News crawl — every 30 minutes during business hours
    scheduler.add_job(
        crawl_news,
        CronTrigger(hour="8-17", minute="0,30", day_of_week="mon-fri"),
        id="news_crawl",
        name="News crawl"
    )
    
    # AI analysis — after EOD crawl completes
    scheduler.add_job(
        run_ai_analysis,
        CronTrigger(hour=15, minute=45, day_of_week="mon-fri"),
        id="eod_analysis",
        name="End-of-day AI analysis"
    )
    
    # Financial report crawl — weekly (reports don't change daily)
    scheduler.add_job(
        crawl_financials,
        CronTrigger(day_of_week="sat", hour=8),
        id="financial_crawl",
        name="Weekly financial report crawl"
    )
```

### HOSE Trading Hours (UTC+7)

```
Morning session:  09:00 - 11:30 (ATO at 09:00-09:15)
Lunch break:      11:30 - 13:00
Afternoon session: 13:00 - 14:30
ATC:              14:30 - 14:45
Settlement:       ~15:00

→ Intraday crawl: 09:00-11:30, 13:00-14:45
→ EOD crawl: 15:15 (after settlement)
→ AI analysis: 15:45 (after EOD crawl completes)
```

---

## Frontend Architecture (Next.js)

### Page Structure

```
frontend/
├── app/                        # Next.js App Router
│   ├── layout.tsx              # Root layout (sidebar navigation)
│   ├── page.tsx                # Dashboard / Market Overview
│   ├── ticker/
│   │   └── [symbol]/
│   │       └── page.tsx        # Individual stock detail + chart
│   ├── watchlist/
│   │   └── page.tsx            # Watchlist with quick analysis view
│   ├── portfolio/
│   │   └── page.tsx            # Portfolio positions + P&L
│   ├── signals/
│   │   └── page.tsx            # AI signals feed
│   └── alerts/
│       └── page.tsx            # Alert configuration
├── components/
│   ├── charts/
│   │   ├── CandlestickChart.tsx  # Main OHLCV chart (lightweight-charts)
│   │   ├── VolumeChart.tsx
│   │   ├── IndicatorOverlay.tsx  # RSI, MACD sub-charts
│   │   └── MiniChart.tsx         # Sparkline for lists
│   ├── market/
│   │   ├── MarketOverview.tsx
│   │   ├── TopMovers.tsx
│   │   └── SectorHeatmap.tsx
│   ├── analysis/
│   │   ├── AIScoreCard.tsx       # Visual score display
│   │   ├── SignalBadge.tsx       # BUY/SELL/HOLD badge
│   │   └── AnalysisDetail.tsx    # Full AI reasoning
│   ├── ticker/
│   │   ├── TickerCard.tsx
│   │   ├── TickerTable.tsx
│   │   └── PriceDisplay.tsx
│   └── common/
│       ├── DataTable.tsx
│       ├── Sidebar.tsx
│       └── LoadingStates.tsx
├── lib/
│   ├── api.ts                  # API client (fetch wrapper)
│   └── utils.ts                # Formatters (VND currency, %, dates)
└── hooks/
    ├── useTicker.ts            # SWR/React Query hook for ticker data
    ├── usePrices.ts            # Hook for price history
    └── useAnalysis.ts          # Hook for AI analysis
```

### Charting Library: TradingView Lightweight Charts

Use `lightweight-charts` by TradingView (open source, MIT license). It's purpose-built for financial charts with candlesticks, volume bars, and indicator overlays. Much better than general-purpose charting libraries (Recharts, Chart.js) for OHLCV data.

```
npm install lightweight-charts
```

### Data Fetching: SWR or TanStack Query

Use **TanStack Query (React Query)** for:
- Automatic caching and deduplication
- Background refetching (poll every 60s on dashboard)
- Stale-while-revalidate pattern
- Request deduplication across components

### Real-Time Updates Pattern

For a single-user app, **polling is simpler than WebSocket**:
- Dashboard: refetch every 60 seconds
- During trading hours: refetch every 30 seconds for price data
- Use TanStack Query's `refetchInterval` option

WebSocket/SSE is unnecessary complexity for one user watching one dashboard.

---

## Telegram Bot Integration

### Recommended Library: `python-telegram-bot` v20+

Async-first, well-maintained, integrates cleanly with asyncio (same loop as FastAPI + APScheduler).

### Integration Pattern: Shared Application

```python
# bot/setup.py
from telegram.ext import Application, CommandHandler, MessageHandler

async def setup_bot(token: str) -> Application:
    app = Application.builder().token(token).build()
    
    # Command handlers
    app.add_handler(CommandHandler("price", cmd_price))       # /price VNM
    app.add_handler(CommandHandler("analyze", cmd_analyze))   # /analyze FPT
    app.add_handler(CommandHandler("watchlist", cmd_watchlist))# /watchlist
    app.add_handler(CommandHandler("signals", cmd_signals))   # /signals
    app.add_handler(CommandHandler("portfolio", cmd_portfolio))# /portfolio
    
    return app

# Proactive alert sending (called by scheduler/alert system)
async def send_alert(chat_id: int, message: str):
    await bot_app.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode="HTML"
    )
```

### Bot runs alongside FastAPI in the same process:
- Start with `bot_app.start()` in FastAPI lifespan
- Uses polling mode (simpler, no webhook URL needed for personal use)
- Shares the same asyncio event loop
- Shares the same database session factory

---

## Component Communication Strategy

### Decision: Direct In-Process Calls + Database as Integration Point

For a single-user monolith, avoid message queues:

| Communication | Pattern | Why |
|--------------|---------|-----|
| Scheduler → Crawler | Direct async function call | Same process, no serialization needed |
| Crawler → Processor | Function call (pass dataframe) | Data stays in memory |
| Processor → DB | SQLAlchemy async session | Durable storage |
| Scheduler → AI Engine | Direct async function call | Same process |
| AI Engine → Gemini | httpx async HTTP | External API |
| API → DB | SQLAlchemy async session | Read path |
| Bot → DB | SQLAlchemy async session | Read path |
| Bot alert sending | Direct function call from scheduler | Same process |
| Frontend → Backend | HTTP REST (JSON) | Separate processes (Node vs Python) |

### Error Handling & Resilience

```
Crawler fails?
  → Log error, skip ticker, continue with remaining 399
  → Retry failed tickers once after 5-minute delay
  → Alert via Telegram: "Crawl failed for X tickers"

Gemini API fails?
  → Retry with exponential backoff (3 attempts)
  → If still fails, serve stale analysis from DB
  → Log and alert

DB connection drops?
  → SQLAlchemy pool handles reconnection
  → Aiven managed PostgreSQL handles failover

Scheduler job overlaps?
  → APScheduler's max_instances=1 prevents overlap
  → If previous job still running, skip this trigger
```

---

## Patterns to Follow

### Pattern 1: Repository Pattern for Data Access

Decouple data access from business logic:

```python
# services/price_service.py (business logic)
class PriceService:
    def __init__(self, db: AsyncSession):
        self.repo = PriceRepository(db)
    
    async def get_with_indicators(self, symbol: str, days: int):
        prices = await self.repo.get_daily(symbol, days)
        indicators = compute_indicators(prices)  # pandas computation
        return prices, indicators

# repositories/price_repo.py (data access only)
class PriceRepository:
    async def get_daily(self, symbol: str, days: int) -> list[DailyPrice]:
        # SQLAlchemy query only
```

### Pattern 2: Crawler Abstract Base Class

All crawlers implement the same interface:

```python
class BaseCrawler(ABC):
    @abstractmethod
    async def fetch_daily_prices(self, symbol: str, start: date, end: date) -> list[RawPrice]:
        ...
    
    @abstractmethod
    async def fetch_intraday(self, symbol: str) -> RawPrice:
        ...

class VNDirectCrawler(BaseCrawler):
    async def fetch_daily_prices(self, symbol, start, end):
        # VNDirect-specific API calls
```

This lets you swap data sources or add fallbacks transparently.

### Pattern 3: Analysis Pipeline as Chain

```python
async def analyze_ticker(symbol: str) -> AnalysisResult:
    # Stage 1: Gather
    prices = await price_service.get_with_indicators(symbol, 200)
    financials = await financial_service.get_latest(symbol)
    news = await news_service.get_recent(symbol, days=30)
    
    # Stage 2: Parallel AI calls
    tech, fund, sent = await asyncio.gather(
        ai_engine.analyze_technical(symbol, prices),
        ai_engine.analyze_fundamental(symbol, financials),
        ai_engine.analyze_sentiment(symbol, news),
    )
    
    # Stage 3: Synthesize
    composite = await ai_engine.synthesize(symbol, tech, fund, sent)
    
    # Stage 4: Store
    await analysis_repo.save(composite)
    
    return composite
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Sending Raw Data to AI
**What:** Passing 200 rows of OHLCV directly to Gemini.
**Why bad:** Wastes tokens (cost), exceeds context window, produces worse analysis than pre-computed indicators.
**Instead:** Compute indicators in Python, send summary values to Gemini.

### Anti-Pattern 2: Synchronous Crawling
**What:** Crawling tickers one-by-one with `requests`.
**Why bad:** 400 tickers × 2-second API response = 13 minutes.
**Instead:** Use `httpx.AsyncClient` with `asyncio.gather()` + semaphore (limit 10 concurrent).

### Anti-Pattern 3: Storing Everything in One Table
**What:** Single `stock_data` table with all OHLCV, financials, indicators mixed.
**Why bad:** Different update frequencies, different query patterns, impossible to partition effectively.
**Instead:** Separate tables per data type with proper foreign keys.

### Anti-Pattern 4: Real-Time WebSocket for Single User
**What:** Building a WebSocket server for live price streaming.
**Why bad:** Massive complexity (connection management, heartbeats, reconnection) for one browser tab.
**Instead:** HTTP polling every 30-60 seconds using TanStack Query's `refetchInterval`.

### Anti-Pattern 5: Celery for Scheduling
**What:** Adding Redis + Celery worker for background tasks.
**Why bad:** 3 processes to manage instead of 1. Redis dependency. No benefit at single-user scale.
**Instead:** APScheduler AsyncIOScheduler in the same FastAPI process.

---

## Scalability Considerations

| Concern | Current (1 user, 400 tickers) | If Grew to 10 users | If Grew to 1000+ tickers |
|---------|-------------------------------|---------------------|--------------------------|
| **DB size** | ~500MB/year (fine on Aiven free/hobby) | Same DB, add auth | Consider TimescaleDB extension |
| **API load** | Single concurrent request | Add simple auth, same infra | Still fine with connection pooling |
| **Gemini costs** | ~$5-15/month (30 tickers analyzed daily) | Linear cost increase | Need tiered analysis (scan vs deep) |
| **Crawl speed** | ~2-5 min for all tickers | Same | May need to parallelize more aggressively |
| **Architecture change** | Monolith | Monolith + auth | Consider extracting crawler to separate worker |

**Bottom line:** Don't over-engineer. The monolith handles single-user scale trivially. Only add infrastructure when actual scaling pressure appears.

---

## Suggested Build Order (Dependencies)

Build order driven by data dependencies — each layer needs the one below it:

```
Phase 1: Foundation (must be first)
├── Database schema + SQLAlchemy models
├── Configuration management (pydantic-settings)
├── FastAPI app skeleton with health check
└── Reason: Everything depends on data models and DB

Phase 2: Data Ingestion (needs Phase 1)
├── VNDirect crawler (OHLCV prices)
├── Data processors (cleaning/validation)
├── Basic scheduler (EOD crawl)
└── Reason: Can't analyze or display without data

Phase 3: API + Basic Frontend (needs Phase 2)
├── REST API endpoints (tickers, prices)
├── Next.js project setup
├── Candlestick chart + price display
└── Reason: Visual feedback on crawled data, validates pipeline

Phase 4: Analysis Engine (needs Phase 2)
├── Technical indicator computation (pandas-ta)
├── Gemini integration + prompt engineering
├── AI analysis pipeline (3 dimensions + synthesis)
└── Reason: Core value prop, depends on having data in DB

Phase 5: Intelligence Layer (needs Phase 3 + 4)
├── Analysis display in dashboard
├── Signal feed page
├── Telegram bot with alerts
└── Reason: Surfaces analysis to user, full loop

Phase 6: Polish & Expansion (needs Phase 5)
├── CafeF scraper (financial reports)
├── News crawler + sentiment
├── Portfolio tracking
├── Watchlist management
├── Intraday real-time tracking
└── Reason: Enrichment features, not critical path
```

### Critical Path

```
DB Schema → Crawlers → Indicator Engine → AI Analysis → Dashboard + Bot
```

Everything else (news, financials, portfolio, watchlist) enriches the experience but isn't on the critical path to "AI recommends buy/sell based on HOSE data."

---

## Sources

- PostgreSQL partitioning: well-established pattern documented in PostgreSQL official docs, standard for time-series data at moderate scale (< billions of rows)
- APScheduler: mature Python library, AsyncIOScheduler designed for asyncio applications. [MEDIUM confidence — based on established pattern, verify latest API against v3.x docs]
- FastAPI async patterns: standard patterns from FastAPI documentation (Pydantic models, dependency injection, lifespan events)
- TradingView lightweight-charts: open-source MIT licensed library purpose-built for financial charting
- python-telegram-bot v20+: async-first redesign, well-documented. [MEDIUM confidence — verify v20+ async API specifics]
- SQLAlchemy 2.0 async: current recommended pattern for async Python ORMs with PostgreSQL via asyncpg driver
- HOSE trading hours: publicly documented by Ho Chi Minh Stock Exchange

**Overall confidence: HIGH** — These are well-established patterns for data pipeline monoliths. The specific Vietnamese data source APIs (VNDirect, SSI) will need discovery during implementation (not architectural decisions).

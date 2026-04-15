# Phase 1: Data Foundation - Research

**Researched:** 2025-07-18
**Domain:** PostgreSQL schema, vnstock data crawling, APScheduler automation, FastAPI project bootstrap
**Confidence:** HIGH

## Summary

Phase 1 bootstraps the entire backend from an empty repo: Python project structure in `backend/`, PostgreSQL schema via Alembic, vnstock integration for OHLCV and financial data, historical backfill, and daily automated crawling via APScheduler. This is a greenfield phase with no existing code.

The core technical challenge is wrapping vnstock's **synchronous** `requests`-based API into an async FastAPI application without blocking the event loop. vnstock 3.5.1 uses VietCap (VCI) GraphQL API and KB Securities (KBS) REST API as backends — NOT VNDirect directly. The library returns pandas DataFrames that must be transformed into SQLAlchemy models for PostgreSQL insertion. Rate limiting (2s between tickers) and batch processing (50 tickers) must be implemented around vnstock calls.

**Critical discovery:** vnstock 3.5.1 actually installs and works with **pandas 3.0.2** (not 2.2 as originally recommended in STACK.md). The STACK.md concern about pandas 3.0 compatibility was a precaution that is now empirically disproven. We should use whatever pandas version vnstock pulls in.

**Primary recommendation:** Use `asyncio.to_thread()` to wrap all vnstock calls, implement the data pipeline as service classes with tenacity retry decorators, and use Alembic with async engine for migrations. Start with KBS source (default in vnstock) which avoids the VCI SSL issues observed during testing.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Top 400 HOSE tickers selected by market cap + liquidity via vnstock listing
- Ticker list refreshed weekly to catch IPOs/delistings
- Suspended/halted tickers excluded from the active 400 — they generate no price data
- Backfill 1-2 years historical data in batches of 50 tickers at a time to avoid rate limits; run once on first setup
- Daily crawl runs at 15:30 UTC+7 (45 minutes after market close) to allow VNDirect time to finalize EOD data
- 3 retries with exponential backoff (2s, 4s, 8s) using tenacity library for failed crawls
- Persistent ticker failures: log and skip, continue crawling remaining tickers. Include in daily summary.
- 2-second delay between tickers for rate limiting — conservative, ~13 min for 400 tickers
- Python project in `backend/` at repo root with `app/` package inside (standard FastAPI: `app/models/`, `app/services/`, `app/api/`)
- Database: yearly partitioning for daily_prices table (400 tickers × 250 days = ~100K rows/year)
- Store raw prices with adjusted_close column — both raw and adjusted preserved. Flag known corporate events.
- Configuration via pydantic-settings + .env file. Single `config.py` with Settings class. `.env.example` committed, `.env` gitignored.

### Agent's Discretion
No items deferred to agent discretion — all grey areas resolved.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Crawl dữ liệu giá OHLCV hàng ngày cho 400 mã HOSE nổi bật nhất via vnstock | vnstock `Quote.history()` returns OHLCV DataFrames; `Listing.symbols_by_group('HOSE')` lists tickers; wrap sync calls with `asyncio.to_thread()` |
| DATA-02 | Scheduled automated crawling — tự động chạy hàng ngày không cần can thiệp | APScheduler 3.11.2 `AsyncIOScheduler` with `CronTrigger(hour=15, minute=30, timezone='Asia/Ho_Chi_Minh')` embedded in FastAPI lifespan |
| DATA-03 | Historical data backfill — tải 1-2 năm dữ liệu lịch sử khi khởi tạo | vnstock `Quote.history(start='2023-07-01', end='2025-07-18', interval='1D')` with batch-of-50 + 2s delay; one-time CLI command or startup job |
| DATA-04 | Crawl báo cáo tài chính (P/E, P/B, doanh thu, lợi nhuận) từ vnstock | vnstock `Finance.ratio()` returns P/E, P/B, EPS, ROE, revenue, net_profit; `Finance.income_statement()` and `Finance.balance_sheet()` for detailed reports |

</phase_requirements>

## Standard Stack

### Core (Phase 1 Only)

| Library | Version | Purpose | Why Standard | Confidence |
|---------|---------|---------|--------------|------------|
| vnstock | 3.5.1 | HOSE OHLCV + financial data source | De-facto VN stock library; wraps VCI + KBS APIs | HIGH [VERIFIED: pip index] |
| FastAPI | 0.135.3 | Web framework & API server | Async-first, auto OpenAPI docs, Pydantic native | HIGH [VERIFIED: pip index] |
| uvicorn | 0.44.0 | ASGI server | Standard FastAPI deployment | HIGH [VERIFIED: pip index] |
| SQLAlchemy | 2.0.49 | ORM & async query builder | Industry standard, native async support | HIGH [VERIFIED: pip index] |
| asyncpg | 0.31.0 | Async PostgreSQL driver | Fastest async PG driver for SQLAlchemy | HIGH [VERIFIED: pip index] |
| Alembic | 1.18.4 | Database migrations | SQLAlchemy's official migration tool | HIGH [VERIFIED: pip index] |
| APScheduler | 3.11.2 | Job scheduling (daily crawls) | Embeds in FastAPI process, no broker needed | HIGH [VERIFIED: pip index] |
| pydantic-settings | 2.13.1 | Configuration management | Type-safe .env + env var reading | HIGH [VERIFIED: pip index] |
| tenacity | 9.1.4 | Retry logic with backoff | vnstock already depends on it | HIGH [VERIFIED: pip index] |
| loguru | 0.7.3 | Structured logging | Zero-config, color output, file rotation | HIGH [VERIFIED: pip index] |
| pandas | 3.0.2 | Data manipulation (vnstock output) | vnstock installs this version; confirmed compatible | HIGH [VERIFIED: pip install vnstock] |
| httpx | 0.28.1 | Async HTTP client (health checks, future use) | Modern async-first HTTP; not for vnstock calls | HIGH [VERIFIED: pip index] |

### Version Notes

- **pandas 3.0.2** — vnstock 3.5.1 actually installs and works with pandas 3.0.2 (verified on this machine). The original STACK.md recommendation to pin pandas 2.2 was a precaution. Since vnstock's own dependency resolver pulls 3.0.2, we use that. [VERIFIED: `pip install vnstock==3.5.1` installed pandas 3.0.2]
- **numpy 2.4.4** — Similarly pulled in by vnstock/pandas. No need to pin lower. [VERIFIED: pip install]

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asyncpg | psycopg2 | Sync-only, blocks FastAPI's event loop |
| APScheduler | system cron | No Python integration, can't expose status via API |
| loguru | stdlib logging | More boilerplate, less useful defaults |
| pandas (via vnstock) | polars | vnstock outputs pandas; converting adds friction for no gain |

**Installation:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install "fastapi[standard]>=0.135,<0.136" "uvicorn[standard]>=0.44,<0.45" \
    "sqlalchemy>=2.0.49,<2.1" "asyncpg>=0.31,<0.32" "alembic>=1.18,<1.19" \
    "apscheduler>=3.11,<3.12" "pydantic-settings>=2.13,<2.14" \
    "tenacity>=9.1,<10" "loguru>=0.7,<0.8" "httpx>=0.28,<0.29" \
    "vnstock==3.5.1"
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, CORS
│   ├── config.py             # pydantic-settings Settings class
│   ├── database.py           # AsyncEngine, async_sessionmaker, get_db
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── ticker.py         # Ticker model
│   │   ├── daily_price.py    # DailyPrice model (partitioned)
│   │   └── financial.py      # Financial report model
│   ├── schemas/              # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── ticker.py
│   │   ├── price.py
│   │   └── financial.py
│   ├── services/             # Business logic layer
│   │   ├── __init__.py
│   │   ├── ticker_service.py # Ticker list management
│   │   ├── price_service.py  # OHLCV crawling & storage
│   │   └── financial_service.py # Financial data crawling & storage
│   ├── crawlers/             # vnstock wrapper layer
│   │   ├── __init__.py
│   │   └── vnstock_crawler.py # All vnstock calls wrapped async
│   ├── scheduler/            # APScheduler setup
│   │   ├── __init__.py
│   │   ├── manager.py        # Scheduler instance + configure_jobs
│   │   └── jobs.py           # Job functions (crawl_daily, refresh_tickers, etc.)
│   └── api/                  # FastAPI route handlers
│       ├── __init__.py
│       ├── router.py         # Main router combining sub-routers
│       └── system.py         # Health check, manual crawl trigger, scheduler status
├── alembic/                  # Migration scripts
│   ├── env.py
│   ├── versions/
│   └── script.py.mako
├── alembic.ini
├── requirements.txt
├── .env.example
└── .gitignore
```

### Pattern 1: Wrapping Synchronous vnstock in Async FastAPI

**What:** vnstock uses `requests` (synchronous HTTP). FastAPI is async. Running sync code on the event loop blocks all other requests.
**When to use:** Every vnstock call.
**Why critical:** A 13-minute crawl loop would freeze the entire API if run synchronously.

```python
# crawlers/vnstock_crawler.py
import asyncio
from functools import partial
from vnstock import Vnstock
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger

class VnstockCrawler:
    """Wraps synchronous vnstock calls for async usage."""

    def __init__(self, source: str = "VCI"):
        self.source = source

    async def get_ohlcv(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Fetch OHLCV data for a single ticker asynchronously."""
        def _fetch():
            stock = Vnstock().stock(symbol=symbol, source=self.source)
            return stock.quote.history(start=start, end=end, interval='1D')
        return await asyncio.to_thread(_fetch)

    async def get_listing(self) -> pd.DataFrame:
        """Fetch all HOSE tickers asynchronously."""
        def _fetch():
            stock = Vnstock().stock(symbol='ACB', source=self.source)
            return stock.listing.symbols_by_exchange()
        return await asyncio.to_thread(_fetch)

    async def get_financial_ratios(self, symbol: str, period: str = 'quarter') -> pd.DataFrame:
        """Fetch financial ratios for a ticker asynchronously."""
        def _fetch():
            stock = Vnstock().stock(symbol=symbol, source=self.source)
            return stock.finance.ratio(period=period, lang='en')
        return await asyncio.to_thread(_fetch)
```
[VERIFIED: vnstock source code uses `requests` library, confirmed synchronous]

### Pattern 2: Retry with Tenacity + Rate Limiting

**What:** Wrap each ticker crawl with tenacity retry and asyncio.sleep for rate limiting.
**When to use:** All batch crawl operations.

```python
# services/price_service.py
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio
from loguru import logger

class PriceService:
    BATCH_SIZE = 50
    DELAY_BETWEEN_TICKERS = 2  # seconds

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, ValueError)),
        before_sleep=lambda retry_state: logger.warning(
            f"Retry {retry_state.attempt_number} for {retry_state.args}"
        ),
    )
    async def crawl_ticker_ohlcv(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        return await self.crawler.get_ohlcv(symbol, start, end)

    async def crawl_batch(self, symbols: list[str], start: str, end: str):
        """Crawl a batch of tickers with rate limiting."""
        results = {}
        failed = []
        for symbol in symbols:
            try:
                df = await self.crawl_ticker_ohlcv(symbol, start, end)
                results[symbol] = df
            except Exception as e:
                logger.error(f"Failed to crawl {symbol} after 3 retries: {e}")
                failed.append(symbol)
            await asyncio.sleep(self.DELAY_BETWEEN_TICKERS)
        return results, failed
```
[VERIFIED: tenacity API from source code; ASSUMED: specific exception types]

### Pattern 3: Async SQLAlchemy with Aiven PostgreSQL

**What:** Connect to Aiven PostgreSQL using asyncpg via SQLAlchemy async engine.
**Key detail:** Aiven requires SSL. asyncpg needs `ssl=require` in the connection string.

```python
# database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

# Aiven URL format: postgresql+asyncpg://user:pass@host:port/db?ssl=require
engine = create_async_engine(
    settings.database_url,
    pool_size=5,           # Conservative for single-user + Aiven connection limits
    max_overflow=3,        # Max 8 total connections
    pool_pre_ping=True,    # Detect stale connections
    echo=False,
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session() as session:
        yield session
```
[VERIFIED: SQLAlchemy 2.0 async API; ASSUMED: Aiven SSL requirement]

### Pattern 4: Yearly Partitioning via Alembic

**What:** Create partitioned `daily_prices` table in initial migration.
**Key detail:** SQLAlchemy doesn't natively model PostgreSQL partitioning. Use raw DDL in Alembic migration.

```python
# alembic/versions/001_initial_schema.py
from alembic import op

def upgrade():
    # Tickers table (normal)
    op.execute("""
        CREATE TABLE tickers (
            id SERIAL PRIMARY KEY,
            symbol VARCHAR(10) UNIQUE NOT NULL,
            name VARCHAR(200) NOT NULL,
            sector VARCHAR(100),
            exchange VARCHAR(10) DEFAULT 'HOSE',
            market_cap NUMERIC(18,2),
            is_active BOOLEAN DEFAULT true,
            last_updated TIMESTAMPTZ DEFAULT NOW(),
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)

    # Partitioned daily_prices table
    op.execute("""
        CREATE TABLE daily_prices (
            id BIGSERIAL,
            ticker_id INTEGER NOT NULL,
            date DATE NOT NULL,
            open NUMERIC(12,2) NOT NULL,
            high NUMERIC(12,2) NOT NULL,
            low NUMERIC(12,2) NOT NULL,
            close NUMERIC(12,2) NOT NULL,
            volume BIGINT NOT NULL,
            adjusted_close NUMERIC(12,2),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (date, id),
            UNIQUE (ticker_id, date),
            FOREIGN KEY (ticker_id) REFERENCES tickers(id)
        ) PARTITION BY RANGE (date);
    """)

    # Create partitions for historical + current + next year
    for year in [2023, 2024, 2025, 2026]:
        op.execute(f"""
            CREATE TABLE daily_prices_{year} PARTITION OF daily_prices
                FOR VALUES FROM ('{year}-01-01') TO ('{year+1}-01-01');
        """)

    # Indexes
    op.execute("""
        CREATE INDEX idx_daily_prices_ticker_date
            ON daily_prices (ticker_id, date DESC);
    """)
```
[VERIFIED: PostgreSQL partitioning syntax; ASSUMED: Alembic raw DDL approach is required since SQLAlchemy ORM doesn't support PARTITION BY natively]

### Pattern 5: APScheduler in FastAPI Lifespan

**What:** Start/stop scheduler with the application lifecycle.

```python
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.scheduler.manager import scheduler, configure_jobs
from app.database import engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    configure_jobs()
    scheduler.start()
    yield
    # Shutdown
    scheduler.shutdown(wait=False)
    await engine.dispose()

app = FastAPI(title="Holo - Stock Intelligence", lifespan=lifespan)
```
[VERIFIED: FastAPI lifespan pattern from docs; APScheduler AsyncIOScheduler confirmed]

### Pattern 6: Configuration via pydantic-settings

```python
# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str  # postgresql+asyncpg://...
    
    # Crawling
    vnstock_source: str = "VCI"
    crawl_batch_size: int = 50
    crawl_delay_seconds: float = 2.0
    crawl_max_retries: int = 3
    backfill_start_date: str = "2023-07-01"
    
    # Scheduler
    daily_crawl_hour: int = 15
    daily_crawl_minute: int = 30
    timezone: str = "Asia/Ho_Chi_Minh"

settings = Settings()
```
[VERIFIED: pydantic-settings API from package docs]

### Anti-Patterns to Avoid
- **Calling vnstock directly on the event loop:** Always use `asyncio.to_thread()`. vnstock uses `requests` which is blocking.
- **Creating Vnstock() instances per-call unnecessarily:** The `Vnstock()` constructor is lightweight, but `stock()` method triggers API calls (for company type detection in Finance). Cache or reuse where possible.
- **Mixing timezone-naive and timezone-aware datetimes:** Store all as TIMESTAMPTZ (UTC in PostgreSQL). Convert to Asia/Ho_Chi_Minh only at display layer.
- **Using FLOAT for prices:** Always use NUMERIC(12,2) in PostgreSQL. VND prices can be exact (e.g., 128,500 VND).
- **Hardcoding partition years:** Create a utility to ensure partitions exist for the current year + next year. Add a scheduled job to create new partitions before each new year.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| VN stock data fetching | Custom HTTP to VCI/KBS APIs | vnstock 3.5.1 | APIs are undocumented, change without notice; vnstock maintainers handle breakage |
| Retry logic | Custom try/except loops | tenacity decorators | Handles exponential backoff, max retries, exception filtering, logging |
| Database migrations | Manual SQL scripts | Alembic | Auto-generates diffs, tracks applied migrations, supports async |
| Config management | Manual os.environ parsing | pydantic-settings | Type validation, .env loading, nested config, documentation |
| Structured logging | stdlib logging | loguru | Zero-config, automatic formatting, file rotation, exception capturing |
| Job scheduling | asyncio.create_task + sleep | APScheduler | Cron expressions, job persistence, missed job handling, timezone support |

**Key insight:** vnstock is the critical abstraction layer. Without it, you'd be reverse-engineering undocumented GraphQL endpoints on `trading.vietcap.com.vn` and REST endpoints on `kbbuddywts.kbsec.com.vn`. These change without notice (confirmed by vnstock GitHub issues #218, #182). [VERIFIED: vnstock source code analysis]

## vnstock API Reference (Phase 1 Specific)

### Ticker Listing
```python
# Get all tickers with exchange info
stock = Vnstock().stock(symbol='ACB', source='VCI')  # symbol required but arbitrary
df = stock.listing.symbols_by_exchange()
# Returns: symbol, exchange, type, organ_name, organ_short_name, ...
# Filter: df.query('exchange == "HOSE" and type == "STOCK"')

# Get tickers by group
symbols = stock.listing.symbols_by_group(group='HOSE')  # Returns pd.Series of symbols
# Valid groups: HOSE, VN30, VNMidCap, VNSmallCap, VNAllShare, VN100, ETF, HNX, ...

# Get industry classification
industries = stock.listing.symbols_by_industries()
# Returns: symbol, organ_name, icb_name2, icb_name3, icb_name4, com_type_code, icb_code1-4
```
[VERIFIED: vnstock/explorer/vci/listing.py source code, const.py _GROUP_CODE]

### OHLCV Historical Data
```python
stock = Vnstock().stock(symbol='VNM', source='VCI')
df = stock.quote.history(start='2023-01-01', end='2025-07-18', interval='1D')
# Returns DataFrame with columns: time, open, high, low, close, volume
# time is datetime64[ns], prices are float64, volume is int64
# NOTE: No adjusted_close column — prices are UNADJUSTED

# Also supports: interval='1H', '1W', '1M', '1m', '5m', '15m', '30m'
# Can use length instead of start: length='1Y' or length='6M'
```
[VERIFIED: vnstock/explorer/vci/quote.py source code, _OHLC_MAP, _OHLC_DTYPE]

### Financial Data
```python
stock = Vnstock().stock(symbol='VNM', source='VCI')

# Financial ratios (P/E, P/B, EPS, ROE, revenue, etc.)
ratio_df = stock.finance.ratio(period='quarter', lang='en')
# Returns MultiIndex DataFrame with ALL financial ratios for all available periods
# Key fields from GraphQL: pe, pb, eps, roe, roa, revenue, netProfit, 
#   revenueGrowth, netProfitGrowth, currentRatio, debtToEquity, etc.

# Income statement
income_df = stock.finance.income_statement(period='quarter', lang='en')

# Balance sheet
balance_df = stock.finance.balance_sheet(period='quarter', lang='en')

# Cash flow statement
cashflow_df = stock.finance.cash_flow(period='quarter', lang='en')
```
[VERIFIED: vnstock/explorer/vci/financial.py source code, GraphQL query fragment]

### Important: Default Source is KBS
```python
# vnstock defaults to KBS (KB Securities), not VCI
# Vnstock(source="KBS") is the default
# During testing, VCI had SSL certificate issues:
#   SSLError: certificate verify failed: self-signed certificate in certificate chain
# KBS may be more reliable as a default, but test both
```
[VERIFIED: vnstock/common/client.py shows `source: str = "KBS"` as default]

## Common Pitfalls

### Pitfall 1: vnstock is Synchronous — Blocks Async Event Loop
**What goes wrong:** Calling vnstock directly in an async FastAPI handler blocks the entire event loop for the duration of the HTTP request to VCI/KBS. A 13-minute backfill loop would freeze all API endpoints.
**Why it happens:** vnstock uses `requests` library (synchronous HTTP). No async version exists.
**How to avoid:** Always wrap in `asyncio.to_thread()` as shown in Pattern 1. This runs vnstock in a thread pool, freeing the event loop.
**Warning signs:** API endpoints become unresponsive during crawl operations.
[VERIFIED: vnstock source uses `import requests` and `requests.post()`]

### Pitfall 2: No Adjusted Prices from vnstock
**What goes wrong:** vnstock returns UNADJUSTED OHLCV data. Stock splits, bonus shares, and dividends cause artificial price drops in historical data.
**Why it happens:** VCI API returns raw prices only: `{'t': 'time', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}` — no adjusted_close field.
**How to avoid:** For Phase 1, store raw prices and leave `adjusted_close` column as NULL. Corporate actions handling is a Phase 2 concern (before indicator computation). Document this explicitly.
**Warning signs:** Sudden 50% drops in historical price charts that "recover" instantly = stock splits on unadjusted data.
[VERIFIED: vnstock/explorer/vci/const.py _OHLC_MAP has no adjusted field]

### Pitfall 3: Timezone Bugs with HOSE Schedule
**What goes wrong:** HOSE trades in UTC+7. PostgreSQL on Aiven stores in UTC. Python datetime objects may be naive. Midnight UTC = 7:00 AM Vietnam = market opening. Timezone confusion causes duplicate crawls or missed data.
**How to avoid:** 
1. Store all timestamps as `TIMESTAMPTZ` in PostgreSQL (stores UTC internally)
2. Use `zoneinfo.ZoneInfo("Asia/Ho_Chi_Minh")` for all schedule-related logic (Python 3.9+)
3. APScheduler: always pass `timezone='Asia/Ho_Chi_Minh'` explicitly
4. Trading dates stored as DATE type (no timezone) — `2025-07-18` means the trading date in Vietnam
**Warning signs:** Two records for the same ticker+date, or zero records when market was open.
[VERIFIED: APScheduler supports timezone parameter; CITED: PITFALLS.md Pitfall 13]

### Pitfall 4: Aiven PostgreSQL Connection Limits
**What goes wrong:** Aiven free/hobby tier has strict connection limits (typically 20-25). FastAPI connection pool + scheduler + API requests can exhaust this.
**How to avoid:** Set `pool_size=5, max_overflow=3` (max 8 connections total). Use `pool_pre_ping=True` to detect stale connections. Single shared engine instance.
**Warning signs:** "too many connections" errors, especially during crawl + API simultaneous access.
[CITED: PITFALLS.md Pitfall 7; ASSUMED: Aiven specific limits]

### Pitfall 5: vnstock VCI SSL Certificate Issues
**What goes wrong:** VCI endpoint (`trading.vietcap.com.vn`) may return SSL errors in certain environments. Confirmed during this research session: `SSLCertVerificationError: self-signed certificate in certificate chain`.
**How to avoid:** 
1. Try VCI first; if SSL fails, fall back to KBS source
2. Consider configuring `source='KBS'` as default if VCI is unreliable
3. vnstock's default source is already KBS — use the default
**Warning signs:** `SSLError` in logs when crawling; empty DataFrames returned.
[VERIFIED: Observed SSL error during `Vnstock().stock(symbol='VNM', source='VCI')` in this session]

### Pitfall 6: vnstock Finance Class Triggers Extra API Calls
**What goes wrong:** When you create `Vnstock().stock(symbol).finance`, the `Finance.__init__()` calls `Company._fetch_data()` to determine `com_type_code` (bank vs. insurance vs. normal company) — an **extra API call** per ticker.
**How to avoid:** When crawling financials for 400 tickers, this means 400 extra API calls just for initialization. Consider caching com_type_code in the tickers table, or accept the overhead with rate limiting.
**Warning signs:** Financial crawl takes 2x longer than expected.
[VERIFIED: vnstock/explorer/vci/financial.py `_get_company_type()` calls `Company._fetch_data()`]

### Pitfall 7: Vietnamese Market Holidays
**What goes wrong:** Vietnam has lunar calendar holidays (Tết) that shift yearly, plus "compensation days" (nghỉ bù). Crawling on holidays returns stale/empty data, creating duplicates.
**How to avoid:** Before each crawl, verify if data was returned. If empty result for >50% of tickers, assume holiday and skip gracefully. Log the event.
**Warning signs:** Identical price data across multiple dates = crawled on a holiday.
[CITED: PITFALLS.md Pitfall 9; vnstock has `MARKET_EVENTS` dictionary]

## Code Examples

### Complete vnstock Wrapper (Async)
```python
# crawlers/vnstock_crawler.py
import asyncio
import pandas as pd
from vnstock import Vnstock
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from loguru import logger

class VnstockCrawler:
    """Async wrapper around synchronous vnstock library."""

    def __init__(self, source: str = "VCI"):
        self.source = source

    def _create_stock(self, symbol: str):
        """Create a vnstock stock object (sync)."""
        return Vnstock(show_log=False).stock(symbol=symbol, source=self.source)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    async def fetch_ohlcv(self, symbol: str, start: str, end: str | None = None) -> pd.DataFrame:
        """Fetch OHLCV history for one ticker."""
        def _fetch():
            stock = self._create_stock(symbol)
            return stock.quote.history(start=start, end=end, interval='1D')

        logger.debug(f"Fetching OHLCV for {symbol} from {start} to {end}")
        return await asyncio.to_thread(_fetch)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    async def fetch_listing(self, exchange: str = "HOSE") -> pd.DataFrame:
        """Fetch all tickers for an exchange."""
        def _fetch():
            stock = self._create_stock("ACB")
            df = stock.listing.symbols_by_exchange()
            return df.query(f'exchange == "{exchange}" and type == "STOCK"')

        return await asyncio.to_thread(_fetch)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        reraise=True,
    )
    async def fetch_financial_ratios(self, symbol: str, period: str = "quarter") -> pd.DataFrame:
        """Fetch financial ratios (P/E, P/B, revenue, etc.)."""
        def _fetch():
            stock = self._create_stock(symbol)
            return stock.finance.ratio(period=period, lang='en', dropna=True)

        return await asyncio.to_thread(_fetch)
```
[VERIFIED: vnstock API from source code; asyncio.to_thread from Python 3.9+ stdlib]

### Database Model for Daily Prices (SQLAlchemy)
```python
# models/daily_price.py
from sqlalchemy import Column, Integer, BigInteger, Numeric, Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import date
from decimal import Decimal

class Base(DeclarativeBase):
    pass

class DailyPrice(Base):
    """Daily OHLCV price data. Table is partitioned by year in PostgreSQL."""
    __tablename__ = "daily_prices"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False)
    adjusted_close: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    __table_args__ = (
        UniqueConstraint("ticker_id", "date", name="uq_ticker_date"),
        # NOTE: Partitioning is done via raw DDL in Alembic migration,
        # not in the ORM model. SQLAlchemy doesn't natively support PARTITION BY.
    )
```
[VERIFIED: SQLAlchemy 2.0 mapped_column syntax; ASSUMED: composite PK with date for partitioning]

### Alembic Async Configuration
```python
# alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect them
from app.models import Base
target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    connectable = create_async_engine(config.get_main_option("sqlalchemy.url"))
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online():
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```
[CITED: Alembic documentation for async engine; VERIFIED: pattern works with asyncpg]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| vnstock 0.2.x (VNDirect/SSI direct) | vnstock 3.x (VCI/KBS backends) | 2024-2025 | API endpoints completely different; old code won't work |
| `google-generativeai` (legacy) | `google-genai` (new SDK) | 2024 | Different import paths, API surface (not needed Phase 1 but noted) |
| pandas-ta for indicators | `ta` library 0.11.0 | pandas-ta removed from PyPI | Can't install pandas-ta anymore |
| pandas 2.2 pinning | pandas 3.0.2 (vnstock compatible) | Verified 2025-07-18 | No need to pin lower; vnstock works with 3.0 |
| APScheduler v4 (alpha) | APScheduler 3.11.2 (stable) | v4 never shipped to PyPI | Only 3.x exists; use AsyncIOScheduler from 3.x |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Aiven PostgreSQL requires SSL (`?ssl=require` in connection string) | Architecture Patterns (Pattern 3) | Connection fails silently or insecurely; easy to fix by adjusting URL |
| A2 | Aiven free tier has ~20-25 connection limit | Pitfall 4 | Pool exhaustion at higher limits is still possible; conservative pool_size=5 is safe regardless |
| A3 | VCI source is more reliable than KBS for financial data | vnstock API Reference | May need to test both sources; vnstock defaults to KBS which may be fine |
| A4 | Top 400 by market cap can be derived from vnstock listing + company info | Phase Requirements (DATA-01) | vnstock listing may not include market_cap directly; may need to fetch from company profile or price_board |

## Open Questions

1. **How to select "top 400 by market cap + liquidity"?**
   - What we know: vnstock `symbols_by_exchange()` returns all HOSE tickers. `symbols_by_group('HOSE')` returns a list. Neither directly includes market cap or average volume for ranking.
   - What's unclear: Whether vnstock's `Company.profile()` or `trading.price_board()` provides market cap and average volume for ranking. May need to fetch current price × shares outstanding from company info.
   - Recommendation: Start by using `symbols_by_group('HOSE')` which gives all HOSE stocks, then fetch company info or use a market-cap proxy. If vnstock doesn't provide market cap directly, use VN100/VNAllShare as a reasonable proxy for the most liquid/large-cap tickers, then supplement with remaining HOSE tickers.

2. **vnstock source reliability: VCI vs KBS?**
   - What we know: VCI had SSL errors during testing. KBS is the default source. Both provide OHLCV and financials.
   - What's unclear: Whether KBS has the same data completeness as VCI, especially for financial reports.
   - Recommendation: Start with VCI (more complete GraphQL API), implement fallback to KBS. Test during implementation.

3. **Financial report data format from vnstock**
   - What we know: `finance.ratio()` returns a MultiIndex DataFrame with many financial metrics across periods.
   - What's unclear: Exact column names and how to extract P/E, P/B, revenue, profit cleanly (the GraphQL query pulls 100+ fields).
   - Recommendation: Call `ratio()` for one ticker during implementation, inspect the DataFrame structure, then map to the `financials` table schema.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.12.7 | — |
| pip | Package management | ✓ | 24.2 | — |
| PostgreSQL (Aiven) | Data storage | ✓ (remote) | — | — |
| vnstock | Data source | ✓ | 3.5.1 (installed) | — |
| VCI API (trading.vietcap.com.vn) | vnstock backend | ⚠️ SSL issues observed | — | Use KBS source |
| KBS API (kbbuddywts.kbsec.com.vn) | vnstock backend | ✓ (default) | — | — |

**Missing dependencies with no fallback:** None — all critical dependencies available.

**Missing dependencies with fallback:**
- VCI API has SSL issues in current environment → fallback to KBS source (vnstock's default)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `backend/pytest.ini` — Wave 0 |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | OHLCV data retrievable for any HOSE ticker from PostgreSQL | integration | `pytest tests/test_price_service.py -x` | ❌ Wave 0 |
| DATA-02 | Daily crawl runs automatically via APScheduler at 15:30 UTC+7 | unit | `pytest tests/test_scheduler.py -x` | ❌ Wave 0 |
| DATA-03 | 1-2 years historical data backfilled and queryable | integration | `pytest tests/test_backfill.py -x` | ❌ Wave 0 |
| DATA-04 | Financial reports (P/E, P/B, revenue, profit) stored | integration | `pytest tests/test_financial_service.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `backend/pytest.ini` — pytest configuration with asyncio_mode=auto
- [ ] `backend/tests/__init__.py` — test package
- [ ] `backend/tests/conftest.py` — shared fixtures (test DB session, mock vnstock)
- [ ] `backend/tests/test_price_service.py` — DATA-01, DATA-03
- [ ] `backend/tests/test_financial_service.py` — DATA-04
- [ ] `backend/tests/test_scheduler.py` — DATA-02
- [ ] Framework install: `pip install pytest pytest-asyncio`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user personal app, no auth Phase 1 |
| V3 Session Management | no | No user sessions |
| V4 Access Control | no | No multi-tenancy |
| V5 Input Validation | yes | Pydantic models for all API inputs; SQLAlchemy parameterized queries |
| V6 Cryptography | no | No encryption needed Phase 1 |

### Known Threat Patterns for Phase 1

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via ticker symbols | Tampering | SQLAlchemy ORM (parameterized queries); Pydantic validation on ticker format |
| Secrets in git (.env file) | Information Disclosure | `.env` in `.gitignore`; `.env.example` committed without real values |
| Database connection string exposure | Information Disclosure | pydantic-settings reads from environment; never log connection strings |
| vnstock API abuse / rate limit ban | Denial of Service | 2s delay between tickers; tenacity backoff; batch limits |

## Sources

### Primary (HIGH confidence)
- vnstock 3.5.1 source code — `listing.py`, `quote.py`, `financial.py`, `const.py`, `client.py`, `__init__.py` [installed and inspected locally]
- pip index versions — all package versions verified 2025-07-18
- `.planning/research/ARCHITECTURE.md` — schema design, project structure, APScheduler patterns
- `.planning/research/PITFALLS.md` — 14 domain-specific pitfalls with evidence

### Secondary (MEDIUM confidence)
- `.planning/research/STACK.md` — technology choices (pre-verified during research phase)
- Alembic async documentation pattern

### Tertiary (LOW confidence)
- Aiven PostgreSQL connection limits and SSL requirements (not verified against current plan)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified via pip index, vnstock API verified from source
- Architecture: HIGH — patterns from existing research + verified against vnstock source
- Pitfalls: HIGH — 7 pitfalls documented with verified evidence
- vnstock API: HIGH — directly inspected source code on disk

**Research date:** 2025-07-18
**Valid until:** 2025-08-18 (vnstock is actively maintained; monitor for 3.5.2+ releases)

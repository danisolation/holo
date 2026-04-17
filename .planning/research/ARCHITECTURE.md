# Architecture Patterns — v2.0 Feature Integration

**Domain:** Stock Intelligence Platform — multi-market expansion, real-time, portfolio & health enhancements
**Researched:** 2026-04-17
**Confidence:** HIGH (all recommendations based on direct source code analysis)

## Executive Summary

The v2.0 features integrate cleanly into the existing monolith architecture. The codebase is well-structured with clear separation (crawlers → services → API → frontend) and consistent patterns (async sessions, circuit breakers, job chaining). Most v2.0 features are extensions of existing components, not architectural changes. The two genuinely new architectural elements are: (1) a WebSocket server endpoint in FastAPI for real-time streaming, and (2) a CSV file upload/parsing pipeline. Everything else extends existing patterns.

---

## Current Architecture (v1.1)

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Process                         │
│                                                               │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐          │
│  │ API      │  │ APScheduler  │  │ Telegram Bot   │          │
│  │ Routes   │  │ (in-process) │  │ (long-poll)    │          │
│  │ tickers  │  │ cron jobs    │  │ /buy /sell     │          │
│  │ analysis │  │ job chaining │  │ /portfolio     │          │
│  │ portfolio│  │ EVENT_JOB_*  │  │ /pnl /check    │          │
│  │ health   │  │              │  │ daily summary  │          │
│  └────┬─────┘  └──────┬───────┘  └───────┬───────┘          │
│       │               │                  │                    │
│  ┌────┴───────────────┴──────────────────┴──────────────┐   │
│  │              Services Layer                            │   │
│  │  price_service  ticker_service  ai_analysis_service   │   │
│  │  indicator_service  financial_service  health_service  │   │
│  │  corporate_action_service  portfolio_service           │   │
│  │  job_execution_service  dead_letter_service            │   │
│  └────────────────────┬─────────────────────────────────┘   │
│       │               │                                       │
│  ┌────┴──────┐  ┌─────┴──────────────────────────────────┐  │
│  │ Crawlers  │  │ Resilience: CircuitBreaker + tenacity   │  │
│  │ vnstock   │  │ vnstock / gemini / cafef / vndirect     │  │
│  │ cafef     │  └────────────────────────────────────────┘  │
│  │ vndirect  │                                               │
│  └───────────┘                                               │
│                       │                                       │
│  ┌────────────────────┴─────────────────────────────────┐   │
│  │  Models: tickers, daily_prices (yearly partitioned),  │   │
│  │  financials, technical_indicators, ai_analyses,       │   │
│  │  news_articles, corporate_events, trades, lots,       │   │
│  │  job_executions, failed_jobs, user_watchlists,        │   │
│  │  price_alerts                                         │   │
│  └────────────────────┬─────────────────────────────────┘   │
└───────────────────────┼───────────────────────────────────────┘
                        │
              ┌─────────┴──────────┐
              │  PostgreSQL (Aiven) │
              │  pool_size=5+3      │
              └────────────────────┘

Frontend: Next.js 16 + lightweight-charts + recharts + @tanstack/react-query + zustand
```

---

## Component Integration Map

### Overview: New vs Modified Components

| Feature | New Components | Modified Components |
|---------|---------------|-------------------|
| HNX/UPCOM | None | `ticker_service.py`, `scheduler/jobs.py`, `scheduler/manager.py`, frontend market-overview, heatmap |
| WebSocket streaming | `app/api/websocket.py`, `app/services/realtime_service.py` | `main.py` (lifespan), `scheduler/manager.py`, frontend candlestick-chart |
| Dividend tracking | `app/models/dividend_income.py` | `portfolio_service.py`, `corporate_action_service.py`, portfolio schemas, frontend portfolio page |
| Performance chart | `performance-chart.tsx` | `portfolio_service.py` (new method), `api/portfolio.py`, `lib/api.ts`, `lib/hooks.ts` |
| Allocation chart | `allocation-chart.tsx` | Frontend portfolio page (compose existing holdings data) |
| Trade edit/delete | None | `portfolio_service.py`, `api/portfolio.py`, portfolio schemas, trade-history.tsx, trade-form.tsx |
| Broker CSV import | `app/services/csv_import_service.py` | `api/portfolio.py`, frontend portfolio page (new upload component) |
| Gemini usage tracking | `app/models/api_usage.py`, `app/services/api_usage_service.py` | `ai_analysis_service.py`, `health_service.py`, `api/health.py`, health dashboard |
| Pipeline timeline | `pipeline-timeline.tsx` | `health_service.py` (new method), `api/health.py` |
| Telegram health alerts | None | `scheduler/manager.py`, `telegram/services.py`, `telegram/formatter.py` |
| Rights issues | None | `corporate_event_crawler.py`, `corporate_action_service.py`, CorporateEvent model (add type) |
| Ex-date alerts | None | `telegram/services.py`, `scheduler/jobs.py`, `scheduler/manager.py` |
| Event calendar | `event-calendar.tsx` | `api/tickers.py` or new `api/corporate.py`, `lib/api.ts` |
| Adjusted/raw toggle | None | `candlestick-chart.tsx`, `lib/api.ts` (PriceData type already served with adjusted_close) |

---

## Detailed Integration Architecture

### 1. Multi-Market Coverage (HNX/UPCOM)

**Integration point:** The architecture already supports this. `VnstockCrawler._EXCHANGE_MAP` already maps `"HNX": "HNX"` and `"UPCOM": "UPCOM"`. The `Ticker` model already has an `exchange` column with `server_default="HOSE"`. vnstock's `Quote(symbol)` resolves across all exchanges — no exchange parameter needed for OHLCV.

**Changes needed:**

```
Backend:
  app/services/ticker_service.py
    - Change fetch_and_sync_tickers() to loop over ["HOSE", "HNX", "UPCOM"]
    - Adjust MAX_TICKERS per exchange: HOSE=400, HNX=~200, UPCOM=~200
    - Set exchange correctly per listing (currently hardcoded "HOSE" on line 78)
    
  app/scheduler/jobs.py
    - daily_price_crawl already uses get_ticker_id_map() for ALL active tickers
    - No change needed — new HNX/UPCOM tickers automatically included after sync
    
  app/api/tickers.py
    - Add exchange filter: Query param ?exchange=HOSE|HNX|UPCOM
    - market_overview: add exchange filter or include exchange in response
    
Frontend:
  components/heatmap.tsx — add exchange filter tabs/dropdown
  app/dashboard/page.tsx — exchange selector state
  lib/api.ts — add exchange param to fetchTickers, fetchMarketOverview
```

**Critical detail:** VCI API's `symbols_by_exchange()` returns ALL tickers across exchanges with a `board`/`exchange` column. The existing code filters by exchange in Python (`df.query(f'exchange == "{vci_exchange}" and type == "STOCK"')`). One API call can get everything.

**Data volume impact:**
- HOSE: ~400 tickers → HNX: ~350 → UPCOM: ~800+ (many illiquid)
- Recommendation: Cap UPCOM at 200-300 most active. Total ~950 tickers.
- Daily crawl time: ~13min → ~33min at 2s/ticker delay
- Consider reducing delay to 1.5s (still within 20 req/min VCI free tier = 3s minimum)

**Migration:** No schema migration needed — `exchange` column already exists. Just logic changes.

### 2. WebSocket Real-Time Price Streaming

**Architecture decision:** FastAPI WebSocket endpoint with in-process price polling. Single-user, no need for Redis pub/sub.

**New components:**

```python
# app/api/websocket.py — NEW FILE
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.realtime_service import realtime_manager

router = APIRouter()

@router.websocket("/ws/prices")
async def price_stream(websocket: WebSocket):
    await realtime_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await realtime_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        realtime_manager.disconnect(websocket)
```

```python
# app/services/realtime_service.py — NEW FILE
class RealtimeManager:
    """Manages WebSocket connections and price broadcasting."""
    
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self.subscriptions: dict[WebSocket, set[str]] = {}
    
    async def connect(self, websocket: WebSocket): ...
    def disconnect(self, websocket: WebSocket): ...
    async def broadcast_prices(self, prices: dict[str, dict]):
        """Called by the sub-minute polling job."""
        for conn in self.active_connections:
            subs = self.subscriptions.get(conn, set())
            filtered = {s: p for s, p in prices.items() if s in subs or not subs}
            if filtered:
                await conn.send_json({"type": "price_update", "data": filtered})

realtime_manager = RealtimeManager()
```

**Scheduler integration:**

```python
# In scheduler/manager.py — new interval job during market hours
from apscheduler.triggers.interval import IntervalTrigger

scheduler.add_job(
    realtime_price_poll,
    trigger=IntervalTrigger(seconds=30),
    id="realtime_price_poll",
    name="Real-Time Price Poll",
    # Market hours guard: checked inside job function
)
```

**Data source:** vnstock `Quote(symbol).history(interval='1D', count_back=1)` for latest bar. For sub-minute, vnstock VCI supports intervals via `_INTERVAL_MAP` — need to verify `1m`/`5m` support. Fallback: poll last close, compute change from yesterday.

**Frontend integration:**

```typescript
// lib/websocket.ts — NEW FILE
// Single WebSocket connection with JSON subscription messages
// On message: update react-query cache via queryClient.setQueryData()
// Reconnect with exponential backoff
```

**Mount in main.py:** `app.include_router(ws_router, prefix="/api")`

**Connection pool impact:** 30-second poll = 1 DB read/cycle. Current pool (5+3=8) is sufficient.

### 3. Dividend Tracking in Portfolio

**Integration point:** `CorporateEvent` already stores CASH_DIVIDEND with `dividend_amount`. Portfolio `Lot` tracks holdings. Need: for each CASH_DIVIDEND, `income = dividend_amount × shares_held_at_record_date`.

**New model:**

```python
# app/models/dividend_income.py — NEW FILE
class DividendIncome(Base):
    __tablename__ = "dividend_incomes"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    corporate_event_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("corporate_events.id"), nullable=False
    )
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
    shares_held: Mapped[int] = mapped_column(Integer, nullable=False)
    dividend_per_share: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total_income: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint("corporate_event_id", name="uq_dividend_income_event"),
    )
```

**Service extension in `portfolio_service.py`:**

```python
async def compute_dividend_income(self) -> list[dict]:
    """For each CASH_DIVIDEND event, compute income from shares held at ex_date."""
    # 1. Query all CASH_DIVIDEND events
    # 2. For each: count remaining_quantity in lots where buy_date < ex_date
    # 3. total_income = dividend_amount × shares_held
    # 4. Upsert into dividend_incomes

async def get_dividend_summary(self) -> dict:
    """Total dividend income, by ticker, by year."""
```

**Schema extension:** Add `total_dividend_income: float | None = None` to `PortfolioSummaryResponse`.

**Computation trigger:** Chain after `daily_corporate_action_check` in the job pipeline.

### 4. Performance Chart (Portfolio Value Over Time)

**Backend — computed on-demand, not stored:**

```python
# In portfolio_service.py — add method
async def get_performance_history(self, days: int = 365) -> list[dict]:
    """Daily portfolio value over time.
    
    1. Get all trades ordered by trade_date
    2. For each day: compute holdings from FIFO lots active that day
    3. portfolio_value = sum(shares × close) for each day
    
    Returns: [{"date": "2025-01-01", "value": 50000000, "invested": 45000000}]
    """
```

**Why on-demand:** Single user, <20 tickers. Query joins trades + daily_prices for 365 days × 20 tickers = ~7,300 rows — fast.

**API:** `GET /api/portfolio/performance?days=365`

**Frontend:** `performance-chart.tsx` using recharts `AreaChart` (already installed v3.8.1). Time range buttons matching candlestick chart pattern.

### 5. Allocation Pie Chart

**No backend changes.** Frontend-only from existing `GET /api/portfolio/holdings` data.

```typescript
// components/allocation-chart.tsx — NEW FILE
// recharts PieChart with data: holdings.map(h => ({ name: h.symbol, value: h.market_value }))
```

### 6. Trade Edit/Delete

**Backend:**

```python
# In portfolio_service.py
async def update_trade(self, trade_id: int, updates: dict) -> dict:
    """Update price, fees, date. Recalculate lot if BUY."""

async def delete_trade(self, trade_id: int) -> dict:
    """Delete trade and reverse FIFO effects."""
```

**API endpoints:**

```python
@router.put("/trades/{trade_id}")    # TradeUpdateRequest
@router.delete("/trades/{trade_id}") # 204 No Content
```

**Critical pitfall:** Editing a BUY trade partially consumed by SELLs requires FIFO chain recalculation. **Recommendation:** Allow edit of price/fees/date freely (these don't affect FIFO). Quantity changes and deletes only if the trade hasn't been consumed by a SELL. Validate this constraint in the service.

### 7. Broker CSV Import

**New service:**

```python
# app/services/csv_import_service.py — NEW FILE
class CSVImportService:
    BROKER_FORMATS = {
        "vnds": {"date_col": "Ngày GD", "symbol_col": "Mã CK", "side_col": "Loại GD", ...},
        "ssi": {...},
        "generic": {...},
    }
    
    async def parse_csv(self, file_content: bytes, broker: str = "auto") -> list[dict]:
        """Parse CSV into normalized trade records."""
    
    async def import_trades(self, session, trades: list[dict]) -> dict:
        """Import trades chronologically for FIFO integrity."""
```

**API endpoint:**

```python
from fastapi import UploadFile, File

@router.post("/trades/import")
async def import_csv(
    file: UploadFile = File(...),
    broker: str = Query("auto"),
): ...
```

**Critical:** Must process trades in chronological order (oldest first) to maintain FIFO lot integrity.

### 8. Gemini API Usage Tracking

**Integration point:** `google-genai` responses include `usage_metadata` with `prompt_token_count`, `candidates_token_count`, `total_token_count`.

**New model:**

```python
# app/models/api_usage.py — NEW FILE
class ApiUsage(Base):
    __tablename__ = "api_usage"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(String(50), nullable=False)  # "gemini"
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    analysis_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
```

**Integration in `ai_analysis_service.py`:** After each Gemini call, extract `response.usage_metadata` and store.

**Health extension:** `GET /api/health/api-usage?days=30` with daily token usage aggregation.

### 9. Pipeline Execution Timeline

**Data source:** Already in `job_executions` table with `started_at`, `completed_at`, `status`.

**Backend:** New method in `health_service.py`:

```python
async def get_pipeline_timeline(self, date_str: str | None = None) -> list[dict]:
    """All job executions for a date, ordered by started_at."""
```

**API:** `GET /api/health/pipeline-timeline?date=2026-04-17`

**Frontend:** `pipeline-timeline.tsx` — horizontal bar chart (Gantt-style). X-axis: time of day. Y-axis: job names. Color: green/yellow/red.

### 10. Telegram Health Notifications

**Extend existing patterns:**

```python
# In scheduler/jobs.py — new job
async def daily_health_check():
    """Run at 16:30. Check freshness + pipeline completion."""
    async with async_session() as session:
        health_svc = HealthService(session)
        freshness = await health_svc.get_data_freshness()
        stale = [f for f in freshness if f["is_stale"]]
        jobs = await health_svc.get_job_statuses()
        failed = [j for j in jobs if j["color"] == "red"]
        if stale or failed:
            msg = MessageFormatter.health_alert(stale, failed)
            await telegram_bot.send_message(msg)
```

**Schedule:** Cron at 16:30 UTC+7 Mon-Fri (30min after daily summary).

### 11. Rights Issues in Corporate Actions

**Model change:** Add `exercise_price` column to `CorporateEvent`, add `"RIGHTS_ISSUE"` type.

**Crawler extension:** Add `"RIGHTS"` to `RELEVANT_TYPES`, map to `"RIGHTS_ISSUE"`.

**Adjustment formula:**

```python
# factor = (close_before × 100 + exercise_price × ratio) / (close_before × (100 + ratio))
```

### 12. Ex-Date Telegram Alerts

**In `telegram/services.py`:** Query upcoming ex-dates for watched/held tickers within 3 days. Chain after `daily_corporate_action_check`.

### 13. Event Calendar View

**API:** `GET /api/corporate-events?start_date=...&end_date=...&exchange=...`

**Frontend:** `event-calendar.tsx` — monthly grid with event dots. Uses `date-fns` (already installed).

### 14. Adjusted/Raw Price Toggle

**API already serves `adjusted_close`** in `GET /tickers/{symbol}/prices` (tickers.py line 107). Frontend `PriceData` type just needs to include it.

**Candlestick chart:** Add toggle button. When "adjusted" on, scale OHLC by ratio:

```typescript
const ratio = d.adjusted_close != null ? d.adjusted_close / d.close : 1;
// adjustedCandle = { open: d.open * ratio, high: d.high * ratio, ... }
```

This is the standard approach used by all major charting platforms — ratio-based scaling preserves intraday structure.

---

## Data Flow Changes

### Extended Job Chain

```
Current:
  daily_price_crawl → [indicators → AI → news → sentiment → combined → signal_alerts]
                     → [price_alerts]
                     → [corporate_action_check]
  daily_summary_send (cron 16:00)

v2.0:
  daily_price_crawl → [indicators → AI → news → sentiment → combined → signal_alerts]
                     → [price_alerts]
                     → [corporate_action_check → dividend_income_compute → ex_date_alerts]
  daily_summary_send (cron 16:00)
  daily_health_check (cron 16:30)                     ← NEW
  realtime_price_poll (interval 30s, market hours)     ← NEW
```

### New Database Tables

| Table | Purpose | Migration |
|-------|---------|-----------|
| `dividend_incomes` | Track dividend income per event × holding | 008 |
| `api_usage` | Track Gemini token/request usage | 008 |

### Modified Tables

| Table | Change | Migration |
|-------|--------|-----------|
| `corporate_events` | Add `exercise_price` column for RIGHTS_ISSUE | 008 |

---

## Frontend Page Structure Changes

```
Current:                              v2.0:
/dashboard                            /dashboard + exchange filter tabs
/dashboard/portfolio                  /dashboard/portfolio + allocation pie + perf chart
/dashboard/health                     /dashboard/health + pipeline timeline + API usage
/ticker/[symbol]                      /ticker/[symbol] + adjusted/raw toggle
                                      /dashboard/calendar (NEW — corporate events)
```

---

## Suggested Build Order

### Phase 1: Multi-Market Foundation
**Build first** — everything else benefits from having HNX/UPCOM tickers available.

### Phase 2: Portfolio Enhancements (Core)
**Build second** — trade edit/delete, CSV import, performance chart, allocation pie.

### Phase 3: Corporate Actions Enhancements
**Build third** — rights issues, dividend tracking, ex-date alerts, event calendar, adjusted/raw toggle.

### Phase 4: Health & Monitoring Enhancements
**Build fourth** — Gemini API usage, pipeline timeline, Telegram health alerts.

### Phase 5: Real-Time WebSocket
**Build last** — most architecturally novel, highest risk (vnstock intraday support uncertain).

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Storing Computed Portfolio Snapshots
**What:** Daily `portfolio_snapshots` table
**Why bad:** Write amplification, stale data, complex invalidation on trade edits
**Instead:** Compute on-demand from trades + daily_prices (single user = fast)

### Anti-Pattern 2: WebSocket Connection Per Ticker
**What:** Separate WS connections per subscribed ticker
**Why bad:** Connection overhead, unnecessary complexity
**Instead:** Single connection with JSON subscription messages

### Anti-Pattern 3: Full Adjusted OHLC in Backend
**What:** Storing `adjusted_open`, `adjusted_high`, `adjusted_low`, `adjusted_close`
**Why bad:** 4× storage, complex maintenance
**Instead:** Store only `adjusted_close`, compute adjusted O/H/L frontend-side via ratio

### Anti-Pattern 4: Separate Crawler Per Exchange
**What:** `hnx_crawler.py`, `upcom_crawler.py`
**Why bad:** vnstock handles all exchanges already. Code duplication.
**Instead:** Parameterize existing `VnstockCrawler` and `TickerService`

### Anti-Pattern 5: Real-Time as Separate Service
**What:** WebSocket server as separate process/microservice
**Why bad:** Single user, deployment complexity, IPC overhead
**Instead:** WebSocket endpoint embedded in FastAPI process

---

## Scalability Considerations

| Concern | Current (400 tickers) | v2.0 (~950 tickers) | Mitigation |
|---------|----------------------|---------------------|------------|
| Daily crawl time | ~13 min | ~33 min | Reduce delay to 1.5s, or parallel batch crawlers |
| DB rows (daily_prices) | ~150K/year | ~350K/year | Already partitioned by year — scales fine |
| AI analysis time | ~30 min | ~60 min | May need API key upgrade, or analyze only top tickers per exchange |
| WebSocket memory | N/A | ~1 client | Negligible for single user |
| Connection pool | 5+3=8 max | Same + 1 for realtime | Still under limit |

---

## Sources

- Direct source code analysis: all backend/frontend files (HIGH confidence)
- vnstock 3.5.1 source: `Listing.symbols_by_exchange()` returns all exchanges, `Quote(symbol)` is exchange-agnostic (HIGH confidence)
- FastAPI WebSocket: built-in support since v0.65+, no additional deps (HIGH confidence)
- google-genai SDK: `response.usage_metadata` with token counts (HIGH confidence)
- lightweight-charts v5.1.0: `CandlestickSeries` + `LineSeries` (HIGH confidence)
- recharts v3.8.1: `PieChart`, `AreaChart` (HIGH confidence)

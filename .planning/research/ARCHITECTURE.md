# Architecture Patterns — v1.1 Reliability & Portfolio

**Domain:** Stock intelligence platform — reliability hardening & portfolio tracking
**Researched:** 2026-04-16

## Current Architecture (v1.0)

```
┌─────────────────────────────────────────────────────┐
│                    FastAPI Process                    │
│                                                       │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ API      │  │ APScheduler  │  │ Telegram Bot   │  │
│  │ Routes   │  │ (in-process) │  │ (long-poll)    │  │
│  └────┬─────┘  └──────┬───────┘  └───────┬───────┘  │
│       │               │                  │           │
│  ┌────┴───────────────┴──────────────────┴─────┐    │
│  │              Services Layer                   │    │
│  │  price_service  ticker_service  ai_service   │    │
│  │  indicator_service  financial_service         │    │
│  └────────────────────┬──────────────────────────┘   │
│                       │                               │
│  ┌────────────────────┴──────────────────────────┐   │
│  │              Models / SQLAlchemy               │   │
│  └────────────────────┬──────────────────────────┘   │
│                       │                               │
└───────────────────────┼───────────────────────────────┘
                        │
              ┌─────────┴──────────┐
              │  PostgreSQL (Aiven) │
              └────────────────────┘

External APIs: vnstock/VCI ←→ CafeF ←→ Google Gemini
```

## v1.1 Architecture Additions

```
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Process                         │
│                                                               │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐          │
│  │ API      │  │ APScheduler  │  │ Telegram Bot   │          │
│  │ Routes   │  │ (in-process) │  │ (long-poll)    │          │
│  │ + health │  │ + retry job  │  │ + /portfolio   │          │
│  │ + trades │  │ + corp crawl │  │ + daily P&L    │          │
│  └────┬─────┘  └──────┬───────┘  └───────┬───────┘          │
│       │               │                  │                    │
│  ┌────┴───────────────┴──────────────────┴──────────────┐   │
│  │              Services Layer                            │   │
│  │  [existing services]                                   │   │
│  │  + corporate_action_service  (NEW)                     │   │
│  │  + portfolio_service         (NEW)                     │   │
│  │  + job_run_service           (NEW)                     │   │
│  │  + dead_letter_service       (NEW)                     │   │
│  └────────────────────┬─────────────────────────────────┘   │
│                       │                                       │
│  ┌────────────────────┴─────────────────────────────────┐   │
│  │          Resilience Layer (NEW)                        │   │
│  │  ┌────────────────┐  ┌──────────────────────────┐    │   │
│  │  │ CircuitBreaker │  │ tenacity @retry           │    │   │
│  │  │ vci / gemini / │  │ (extended to all external │    │   │
│  │  │ cafef          │  │  calls)                   │    │   │
│  │  └────────────────┘  └──────────────────────────┘    │   │
│  └──────────────────────────────────────────────────────┘   │
│                       │                                       │
│  ┌────────────────────┴─────────────────────────────────┐   │
│  │              Models / SQLAlchemy                       │   │
│  │  [existing models]                                     │   │
│  │  + CorporateAction  Trade  TradeLot  (NEW)            │   │
│  │  + DividendIncome  JobRun  DeadLetter (NEW)           │   │
│  └────────────────────┬─────────────────────────────────┘   │
│                       │                                       │
└───────────────────────┼───────────────────────────────────────┘
                        │
              ┌─────────┴──────────┐
              │  PostgreSQL (Aiven) │
              │  + 6 new tables     │
              └────────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `CorporateActionService` | Crawl events via vnstock, store, compute adjustment factors, apply to prices | VnstockCrawler, DailyPrice model, IndicatorService (recalc trigger) |
| `PortfolioService` | Trade CRUD, FIFO cost basis, P&L calculation, holdings aggregation | Trade/TradeLot models, DailyPrice (current price), DividendIncome |
| `JobRunService` | Record job start/end/failure, query history, compute health metrics | JobRun model, used by all scheduler jobs as a wrapper |
| `DeadLetterService` | Store failed operations, query pending retries, mark completed | DeadLetterOperation model, used by scheduler retry job |
| `AsyncCircuitBreaker` | Track failure counts per service, open/close circuit | Used by crawlers and AI service, reports state to health endpoint |
| `ResilienceLayer` | Combine circuit breaker + tenacity retry into reusable decorators | Wraps all external API calls |

### Data Flow — Corporate Actions

```
1. APScheduler triggers corp_action_crawl (weekly, after ticker refresh)
2. CorporateActionService calls vnstock Company.events() for each ticker
   └─ via asyncio.to_thread() (vnstock is sync)
   └─ wrapped in circuit breaker (vci_breaker)
3. New events detected → stored in corporate_actions table
4. For events with exright_date ≤ today:
   └─ Compute adjustment factor from ratio/value
   └─ UPDATE daily_prices SET adjusted_close = close × factor
      WHERE ticker_id = X AND date < exright_date
5. Chain: trigger indicator recalculation for affected tickers
```

### Data Flow — Portfolio P&L

```
1. User enters trade via POST /api/trades (or Telegram)
2. PortfolioService validates + stores in trades table
3. If BUY: create TradeLot with remaining_quantity = quantity
4. If SELL: FIFO dequeue from oldest TradeLots
   └─ Calculate realized P&L per lot
   └─ Update lot remaining_quantity
5. Holdings view: aggregate open TradeLots per ticker
   └─ Join with latest daily_prices.close for current value
   └─ Unrealized P&L = (current - avg_cost) × remaining
6. Portfolio summary: sum all positions
```

### Data Flow — Error Recovery

```
1. External call fails (vnstock/Gemini/CafeF)
2. tenacity retries N times with exponential backoff
3. If still failing → circuit breaker increments failure count
4. If circuit opens → subsequent calls fail fast (CircuitOpenError)
5. Failed operation → DeadLetterService stores in dead_letter_operations
   └─ payload = {operation_type, ticker_ids, params}
   └─ next_retry_at = now + backoff
6. APScheduler periodic job (every 30 min) checks dead_letter_operations
   └─ If circuit is closed → retry pending operations
   └─ If succeeds → mark completed
   └─ If still fails → increment retry_count, update next_retry_at
   └─ If retry_count > max_retries → mark abandoned
```

### Data Flow — Job Health Monitoring

```
1. Every scheduler job wrapped in JobRunService context:
   job_run = await job_run_service.start("daily_price_crawl")
   try:
       result = await actual_job()
       await job_run_service.complete(job_run, records=result.count)
   except Exception as e:
       await job_run_service.fail(job_run, error=str(e))
       raise

2. GET /api/system/health returns:
   └─ last_successful: {job_name: timestamp} for each job
   └─ error_count_24h: int
   └─ data_freshness: {daily_prices: date, ai_analyses: date, ...}
   └─ circuit_states: {vci: open/closed, gemini: open/closed, cafef: open/closed}

3. Frontend /dashboard/health renders:
   └─ Status cards: green/yellow/red per job
   └─ Error rate chart: recharts bar chart (last 7 days)
   └─ Job history table: last 20 runs with duration/status
```

## Patterns to Follow

### Pattern 1: Service-per-Domain (existing pattern)
**What:** Each domain concern gets its own service class with its own DB session.
**When:** Adding corporate actions, portfolio, health monitoring.
**Example:**
```python
class PortfolioService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_trade(self, trade: TradeCreate) -> Trade: ...
    async def get_holdings(self) -> list[Holding]: ...
    async def calculate_pnl(self, ticker_id: int) -> PnL: ...
```

### Pattern 2: Job Wrapping for Health Tracking
**What:** Wrap all scheduler jobs with JobRunService for automatic tracking.
**When:** Every job in `scheduler/jobs.py`.
**Example:**
```python
async def daily_price_crawl():
    async with async_session() as session:
        job_service = JobRunService(session)
        run = await job_service.start("daily_price_crawl")
        try:
            crawler = VnstockCrawler()
            service = PriceService(session, crawler)
            result = await service.crawl_daily()
            await job_service.complete(run, records_processed=result["inserted"])
        except Exception as e:
            await job_service.fail(run, error_message=str(e))
            raise
```

### Pattern 3: Circuit Breaker as Module-Level Singletons
**What:** One circuit breaker instance per external service, shared across all callers.
**When:** VCI API, Gemini API, CafeF scraping.
**Example:**
```python
# app/resilience.py
vci_breaker = AsyncCircuitBreaker("vci", fail_max=5, reset_timeout=300)
gemini_breaker = AsyncCircuitBreaker("gemini", fail_max=3, reset_timeout=120)
cafef_breaker = AsyncCircuitBreaker("cafef", fail_max=5, reset_timeout=300)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Adjusting Raw Prices
**What:** Modifying the `close` column when applying corporate action adjustments.
**Why bad:** Destroys original data. Can't reverse incorrect adjustments. Breaks data integrity.
**Instead:** Only modify `adjusted_close`. Keep `open/high/low/close` as original market values.

### Anti-Pattern 2: Computing P&L in Frontend
**What:** Sending all trades to frontend and computing FIFO/P&L in JavaScript.
**Why bad:** FIFO logic is complex, error-prone in JS, and leaks business logic to frontend.
**Instead:** Compute in backend `PortfolioService`. Frontend receives pre-computed P&L values.

### Anti-Pattern 3: Circuit Breaker Per Request
**What:** Creating new circuit breaker instances per HTTP request or job run.
**Why bad:** No state sharing — can't track failures across requests. Circuit never opens.
**Instead:** Module-level singletons (see Pattern 3).

### Anti-Pattern 4: Blocking vnstock Calls in Async Context
**What:** Calling `Company.events()` directly in async function without `to_thread()`.
**Why bad:** vnstock is sync (uses `requests`). Blocks the event loop, stalling all other tasks.
**Instead:** Always use `await asyncio.to_thread(stock.company.events)` — existing pattern from v1.0.

## Scalability Considerations

| Concern | Current (400 tickers) | At 1000 tickers | Notes |
|---------|----------------------|------------------|-------|
| Corporate action crawl | ~400 API calls (one per ticker) | ~1000 calls | Batch by crawling only tickers with recent events (check `public_date` > last crawl) |
| Trade storage | <1000 trades/year personal | <1000 | Single user — not a concern |
| Job runs table | ~15 runs/day × 365 = ~5,500/year | Same | Partition by year or just VACUUM |
| Dead letter table | <100/year ideally | Same | Completed items can be archived/deleted |
| Price adjustment | One-time per corporate action | Same | Only recalculate affected ticker's history |

# Phase 12: Multi-Market Foundation - Research

**Researched:** 2026-04-17
**Domain:** Multi-exchange stock data pipeline scaling (HOSE → HOSE+HNX+UPCOM)
**Confidence:** HIGH

## Summary

Phase 12 expands the Holo platform from HOSE-only (400 tickers) to all three Vietnamese stock exchanges: HOSE (400), HNX (200), and UPCOM (200) — 800 total tickers. The codebase is well-prepared: the `Ticker.exchange` column already exists with `server_default="HOSE"`, the `VnstockCrawler._EXCHANGE_MAP` already maps all three exchanges, and `fetch_listing(exchange=)` already accepts an exchange parameter. The core work is parameterizing the currently hardcoded HOSE logic, adding staggered scheduled jobs, building the exchange filter UI, and implementing tiered AI analysis.

The primary risk area is the **deactivation logic in `TickerService.fetch_and_sync_tickers()`** — the current deactivation query (`Ticker.symbol.notin_(symbols)`) has no exchange filter, so syncing HNX tickers would incorrectly deactivate all HOSE tickers. This must be scoped per-exchange. The secondary risk is **DB pool pressure** — the pool is capped at 8 connections (5+3 overflow) for Aiven, and three staggered crawl jobs plus the analysis pipeline plus API requests could compete for connections.

**Primary recommendation:** Parameterize existing code with `exchange` parameter throughout the stack (service → jobs → API → frontend), add staggered cron jobs per exchange, scope the ticker deactivation to per-exchange, and build tiered AI analysis using the existing watchlist + a new on-demand endpoint.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Top 200 HNX + top 200 UPCOM tickers (matches personal scope, keeps pipeline under 35 min total)
- One parameterized job per exchange — reuses existing crawl logic, stagger via cron offsets
- Stagger timing: HOSE at 15:30, HNX at 16:00, UPCOM at 16:30 — 30-min gaps prevent DB pool contention
- Ticker selection via VCI listing default order (pre-sorted by relevance) — consistent with HOSE approach
- Exchange filter as segmented tabs (HOSE / HNX / UPCOM / All) — always visible, one-click switching, consistent with shadcn Tabs
- Default filter: All — shows complete market view, user narrows as needed
- Single merged heatmap with exchange-colored borders — unified view, exchange filter applies
- Add exchange badge column to stock list — color-coded (HOSE=blue, HNX=green, UPCOM=orange), sortable & filterable
- "Watchlisted" = tickers in user's watchlist (localStorage + Telegram /watch) — consistent with existing watchlist
- On-demand analysis via button on ticker detail page ("Analyze now") — explicit user action, clear UX
- Gemini budget: HOSE full daily (400), watchlisted HNX/UPCOM daily, cap at 50 extra/day — stays within 1500 RPD
- HNX/UPCOM analysis runs after HOSE analysis completes via job chain (EVENT_JOB_EXECUTED pattern)

### the agent's Discretion
None — all decisions captured above.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MKT-01 | User can view OHLCV data for HNX and UPCOM tickers alongside existing HOSE tickers | Parameterize `TickerService`, `PriceService`, scheduler jobs; add exchange to API & frontend — all integration points documented below |
| MKT-02 | User can filter market overview, stock lists, and heatmap by exchange (HOSE/HNX/UPCOM/All) | shadcn Tabs already installed; add `exchange` query param to API; store filter in zustand or URL state |
| MKT-03 | System crawls HNX and UPCOM tickers on the same daily schedule as HOSE with staggered execution | Three cron-triggered jobs at 15:30/16:00/16:30 using `CronTrigger`; parameterize `daily_price_crawl(exchange)` |
| MKT-04 | AI analysis runs on tiered schedule — HOSE fully daily, HNX/UPCOM for watchlisted tickers daily, rest on-demand | New `analyze_exchange_watchlist()` method; on-demand POST endpoint per ticker; cap at 50 extra/day |
</phase_requirements>

## Standard Stack

No new packages required. This phase uses exclusively the existing stack.

### Core (Already Installed)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| APScheduler | 3.11.2 | Staggered cron jobs per exchange | Already installed — add 2 new cron triggers [VERIFIED: codebase] |
| SQLAlchemy | ~2.0 | Exchange-filtered queries | Already installed — add `.where(Ticker.exchange == ...)` [VERIFIED: codebase] |
| shadcn/ui Tabs | 4.x | Exchange filter UI component | Already installed at `frontend/src/components/ui/tabs.tsx` [VERIFIED: codebase] |
| zustand | ~5.x | Exchange filter state management | Already installed with persist middleware [VERIFIED: codebase] |
| @tanstack/react-query | ~5.x | Exchange-parameterized query keys | Already installed [VERIFIED: codebase] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Zustand for exchange filter | URL search params | URL params are shareable but more complex; zustand is consistent with existing watchlist pattern. Either works — prefer zustand for consistency. |
| Three cron triggers | Single job with exchange iteration | Single job creates serial dependency; staggered crons allow independent failure and 30-min gaps for DB pool recovery |

## Architecture Patterns

### Recommended Change Structure
```
backend/
├── app/
│   ├── config.py                   # Add per-exchange MAX_TICKERS settings
│   ├── services/
│   │   ├── ticker_service.py       # Parameterize with exchange, per-exchange deactivation
│   │   └── ai_analysis_service.py  # Add tiered analysis method
│   ├── scheduler/
│   │   ├── jobs.py                 # Exchange-parameterized job functions
│   │   └── manager.py             # Three staggered cron triggers + chain updates
│   └── api/
│       ├── tickers.py             # Add exchange query param to list/overview
│       └── analysis.py            # Add on-demand single-ticker endpoint
├── alembic/
│   └── versions/
│       └── 008_*.py               # (No schema migration needed — exchange column exists)
frontend/
├── src/
│   ├── lib/
│   │   ├── api.ts                 # Add exchange param to fetch functions
│   │   ├── hooks.ts               # Exchange-aware query hooks
│   │   └── store.ts               # Add exchange filter store
│   ├── app/
│   │   └── page.tsx               # Exchange tabs, update HOSE-specific text
│   └── components/
│       ├── heatmap.tsx            # Exchange-colored borders, filter support
│       ├── exchange-filter.tsx    # New: reusable exchange tabs component
│       └── watchlist-table.tsx    # Add exchange badge column
```

### Pattern 1: Exchange-Parameterized Services
**What:** Pass `exchange` parameter through service → crawler → DB layer instead of hardcoding "HOSE"
**When to use:** Every service method that currently assumes HOSE-only

**Example (TickerService):**
```python
# Source: Codebase analysis — backend/app/services/ticker_service.py
class TickerService:
    # Per-exchange limits per CONTEXT.md decision
    EXCHANGE_MAX_TICKERS = {
        "HOSE": 400,
        "HNX": 200,
        "UPCOM": 200,
    }

    async def fetch_and_sync_tickers(self, exchange: str = "HOSE") -> dict:
        max_tickers = self.EXCHANGE_MAX_TICKERS.get(exchange, 200)
        listing_df = await self.crawler.fetch_listing(exchange=exchange)
        symbols = listing_df["symbol"].tolist()[:max_tickers]
        
        # CRITICAL: Scope deactivation to THIS exchange only
        deactivate_stmt = (
            update(Ticker)
            .where(
                Ticker.symbol.notin_(symbols),
                Ticker.exchange == exchange,  # <-- Must add this
                Ticker.is_active == True,
            )
            .values(is_active=False, last_updated=datetime.now(timezone.utc))
        )
```

### Pattern 2: Staggered Cron Jobs via Closures
**What:** Create exchange-parameterized job functions using closures, register each with its own cron trigger
**When to use:** The three staggered daily crawl schedules

**Example (scheduler):**
```python
# Source: Codebase analysis — backend/app/scheduler/manager.py + jobs.py

# In jobs.py — factory function that returns an exchange-specific coroutine
async def daily_price_crawl_for_exchange(exchange: str):
    """Exchange-parameterized daily OHLCV crawl."""
    logger.info(f"=== DAILY PRICE CRAWL ({exchange}) START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start(f"daily_price_crawl_{exchange.lower()}")
        try:
            crawler = VnstockCrawler()
            service = PriceService(session, crawler)
            # PriceService.crawl_daily() needs exchange param too
            result = await service.crawl_daily(exchange=exchange)
            # ... same resilience pattern as current daily_price_crawl ...

# In manager.py — register three staggered cron triggers
EXCHANGE_CRAWL_SCHEDULE = {
    "HOSE":  {"hour": 15, "minute": 30},
    "HNX":   {"hour": 16, "minute": 0},
    "UPCOM": {"hour": 16, "minute": 30},
}

for exchange, schedule in EXCHANGE_CRAWL_SCHEDULE.items():
    scheduler.add_job(
        lambda ex=exchange: daily_price_crawl_for_exchange(ex),
        trigger=CronTrigger(
            hour=schedule["hour"],
            minute=schedule["minute"],
            day_of_week="mon-fri",
            timezone=settings.timezone,
        ),
        id=f"daily_price_crawl_{exchange.lower()}",
        name=f"Daily OHLCV Price Crawl ({exchange})",
        replace_existing=True,
        misfire_grace_time=3600,
    )
```

### Pattern 3: Tiered AI Analysis Chain
**What:** After HOSE analysis completes, chain HNX/UPCOM analysis for watchlisted tickers only, capped at 50 extra/day
**When to use:** MKT-04 — tiered Gemini budget management

**Example:**
```python
# In ai_analysis_service.py — new method
async def analyze_watchlisted_tickers(self, exchanges: list[str], max_extra: int = 50) -> dict:
    """Analyze only watchlisted tickers from given exchanges.
    
    Reads watchlist from both UserWatchlist (Telegram) table 
    and considers tickers that are in the localStorage watchlist
    (synced via an API endpoint or passed as parameter).
    """
    # Query active tickers in target exchanges that are in watchlist
    stmt = (
        select(Ticker.symbol, Ticker.id)
        .join(UserWatchlist, UserWatchlist.ticker_id == Ticker.id)
        .where(Ticker.exchange.in_(exchanges), Ticker.is_active == True)
    )
    result = await self.session.execute(stmt)
    watchlisted = {row[0]: row[1] for row in result.fetchall()}
    
    # Cap at max_extra per day
    symbols_to_analyze = list(watchlisted.keys())[:max_extra]
    # ... run analysis only for these symbols ...

# In manager.py _on_job_executed — chain after HOSE pipeline completes
elif event.job_id in ("daily_combined_triggered", "daily_combined_manual"):
    # Existing chain: signal alert check
    scheduler.add_job(daily_signal_alert_check, ...)
    # NEW: chain HNX/UPCOM watchlist analysis
    scheduler.add_job(daily_hnx_upcom_analysis, ...)
```

### Pattern 4: On-Demand Single-Ticker Analysis Endpoint
**What:** POST endpoint to trigger AI analysis for a single ticker immediately
**When to use:** "Analyze now" button on ticker detail page for non-HOSE tickers

**Example:**
```python
# In analysis.py router
@router.post("/{symbol}/analyze-now", response_model=AnalysisTriggerResponse)
async def trigger_on_demand_analysis(symbol: str, background_tasks: BackgroundTasks):
    """On-demand AI analysis for a single ticker."""
    async def _run():
        async with async_session() as session:
            # Verify ticker exists
            ticker = await _get_ticker_by_symbol(session, symbol.upper())
            service = AIAnalysisService(session)
            await service.analyze_single_ticker(ticker.id, symbol.upper())
    
    background_tasks.add_task(_run)
    return AnalysisTriggerResponse(
        message=f"AI analysis for {symbol.upper()} triggered",
        triggered=True,
    )
```

### Pattern 5: Exchange Filter UI Component
**What:** Reusable exchange tabs component with shadcn Tabs, connected to zustand store
**When to use:** Home page (heatmap), stock list, market overview, dashboard

**Example:**
```typescript
// frontend/src/components/exchange-filter.tsx
"use client";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useExchangeStore } from "@/lib/store";

const EXCHANGES = [
  { value: "all", label: "Tất cả" },
  { value: "HOSE", label: "HOSE" },
  { value: "HNX", label: "HNX" },
  { value: "UPCOM", label: "UPCOM" },
] as const;

export function ExchangeFilter() {
  const { exchange, setExchange } = useExchangeStore();
  return (
    <Tabs value={exchange} onValueChange={(v) => setExchange(v as Exchange)}>
      <TabsList>
        {EXCHANGES.map((ex) => (
          <TabsTrigger key={ex.value} value={ex.value}>
            {ex.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}
```

### Pattern 6: Exchange-Colored Heatmap Borders
**What:** Add subtle colored border to heatmap cells indicating exchange
**When to use:** The merged heatmap view

**Example:**
```typescript
// In heatmap.tsx — modify the button style
const EXCHANGE_BORDER_COLORS: Record<string, string> = {
  HOSE: "border-blue-500",    // blue
  HNX: "border-green-500",    // green
  UPCOM: "border-orange-500", // orange
};

// On the heatmap cell:
<button
  className={`... border-2 ${EXCHANGE_BORDER_COLORS[ticker.exchange] ?? ""}`}
  style={{ backgroundColor: getChangeColor(ticker.change_pct) }}
>
```

### Anti-Patterns to Avoid
- **Hardcoding exchange in multiple places:** Use a single `EXCHANGE_CONFIG` dict/constant that all services reference. Don't duplicate "HOSE"/"HNX"/"UPCOM" strings across 15 files.
- **Single massive crawl job for all exchanges:** This defeats the staggering purpose. Each exchange must have its own scheduled job with independent failure handling.
- **Deactivating tickers across exchanges:** The `fetch_and_sync_tickers` deactivation MUST be scoped to the exchange being synced. This is the #1 data corruption risk.
- **Fetching all 800 tickers for AI analysis:** The tiered approach means HNX/UPCOM only get analyzed on-demand or if watchlisted. Never batch-analyze all 800 daily — this would blow the Gemini budget (1500 RPD).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Exchange filter state | Custom context provider | `zustand` with persist middleware | Already used for watchlist, proven pattern in codebase |
| Segmented tabs UI | Custom segmented control | shadcn `Tabs` component | Already installed, consistent with design system |
| Staggered scheduling | Custom setTimeout chains | APScheduler `CronTrigger` with offset times | APScheduler handles misfire grace, timezone, day-of-week filtering |
| Watchlist-based ticker filtering | New watchlist table | Existing `UserWatchlist` model + `useWatchlistStore` | Both already exist — combine DB (Telegram) + localStorage (frontend) |

## Common Pitfalls

### Pitfall 1: Deactivation Query Without Exchange Scope
**What goes wrong:** Syncing HNX tickers deactivates all HOSE tickers because the deactivation query only checks `symbol.notin_(new_symbols)` without filtering by exchange.
**Why it happens:** Current code was written for single-exchange (HOSE) and deactivation implicitly meant "not in the HOSE list."
**How to avoid:** Always add `.where(Ticker.exchange == exchange)` to the deactivation query. Test with a unit test that syncs HNX while HOSE tickers exist.
**Warning signs:** After running HNX ticker sync, HOSE tickers disappear from the dashboard.

### Pitfall 2: Ticker Symbol Collisions Across Exchanges
**What goes wrong:** Some ticker symbols might exist on multiple exchanges (e.g., "AAA" on both HOSE and HNX).
**Why it happens:** The `Ticker.symbol` column has a `unique=True` constraint. If the same symbol exists on HNX, the upsert would overwrite the HOSE ticker.
**How to avoid:** Verify whether VN stock symbols are unique across exchanges (they are — each company lists on exactly one exchange). Add a defensive check: if a symbol already exists with a different exchange, log a warning and skip. Consider changing the unique constraint to `(symbol, exchange)` as a safety measure if collisions are possible.
**Warning signs:** Ticker exchange values flip unexpectedly after sync.

### Pitfall 3: DB Pool Exhaustion During Staggered Crawls
**What goes wrong:** If HOSE crawl runs long (>30 min), HNX crawl starts while HOSE is still holding connections, exceeding the 8-connection pool limit.
**Why it happens:** Pool size is 5 + 3 overflow = 8 max. Each crawl job holds a session for its entire duration. Concurrent crawls + API requests can exhaust the pool.
**How to avoid:** 30-minute gaps should be sufficient (current HOSE crawl takes ~13 min for 400 tickers). Monitor via the health dashboard's DB pool endpoint. If needed, reduce batch sizes or increase delays for HNX/UPCOM.
**Warning signs:** `TimeoutError` from asyncpg, health dashboard showing pool checked_out at max.

### Pitfall 4: Job Chaining Confusion With Multiple Exchange Crawls
**What goes wrong:** The `_on_job_executed` listener chains indicators and AI analysis after `daily_price_crawl`. With three exchange-specific crawls, the chain fires three times — tripling indicator computation and AI analysis.
**Why it happens:** The listener matches on `event.job_id == "daily_price_crawl"` — if exchange crawls use different IDs, the chain logic needs updating.
**How to avoid:** Only chain indicator computation and AI analysis after the LAST exchange crawl completes (UPCOM at 16:30). Use distinct job IDs (`daily_price_crawl_hose`, `daily_price_crawl_hnx`, `daily_price_crawl_upcom`) and only chain from the UPCOM job (or use a sentinel/counter pattern).
**Warning signs:** Indicators and AI analysis run 3x, Gemini RPD budget exceeded.

### Pitfall 5: Gemini RPD Budget Exceeded
**What goes wrong:** With 800 tickers, batch analysis would require ~128 Gemini API calls per analysis type (800/25 per batch × 4 types = 128 calls). At 1500 RPD free tier, this leaves almost no headroom.
**Why it happens:** Naive approach of analyzing all tickers regardless of exchange.
**How to avoid:** Strict tiering: HOSE (400) gets full daily analysis = ~64 calls. Watchlisted HNX/UPCOM (cap 50) = ~8 calls. Total ~72 calls per analysis type × 4 types = ~288 RPD. Well within 1500.
**Warning signs:** `429 Too Many Requests` from Gemini, analysis jobs failing with rate limit errors.

### Pitfall 6: Frontend Query Cache Invalidation
**What goes wrong:** Switching exchange filter doesn't refetch data because react-query uses the same query key.
**Why it happens:** If `exchange` isn't included in the query key, cached data from "HOSE" is served when user switches to "HNX".
**How to avoid:** Include exchange in all query keys: `["market-overview", exchange]`, `["tickers", exchange, sector]`.
**Warning signs:** Data doesn't change when switching exchange tabs.

### Pitfall 7: Lambda Closure Bug in APScheduler Job Registration
**What goes wrong:** When registering jobs in a loop with `lambda: daily_price_crawl_for_exchange(exchange)`, all lambdas capture the same variable reference and all crawl the same exchange (the last one in the loop).
**Why it happens:** Python's late-binding closures. The `exchange` variable is evaluated when the lambda is called, not when it's defined.
**How to avoid:** Use default argument binding: `lambda ex=exchange: daily_price_crawl_for_exchange(ex)` or use `functools.partial`.
**Warning signs:** All three crawl jobs crawl the same exchange (UPCOM).

## Code Examples

### Backend: TickerService with Exchange Parameter
```python
# Source: Codebase analysis — backend/app/services/ticker_service.py
class TickerService:
    EXCHANGE_MAX_TICKERS = {"HOSE": 400, "HNX": 200, "UPCOM": 200}

    async def fetch_and_sync_tickers(self, exchange: str = "HOSE") -> dict:
        max_tickers = self.EXCHANGE_MAX_TICKERS.get(exchange, 200)
        listing_df = await self.crawler.fetch_listing(exchange=exchange)
        symbols = listing_df["symbol"].tolist()[:max_tickers]
        
        # Upsert with correct exchange
        for _, row in listing_df.iterrows():
            sym = row["symbol"]
            if sym not in symbols:
                continue
            stmt = insert(Ticker).values(
                symbol=sym, name=str(name), exchange=exchange,
                sector=sector_map.get(sym), industry=industry_map.get(sym),
                is_active=True, last_updated=datetime.now(timezone.utc),
            ).on_conflict_do_update(
                index_elements=["symbol"],
                set_={"name": str(name), "exchange": exchange, ...}
            )
        
        # Deactivate ONLY within this exchange
        deactivate_stmt = (
            update(Ticker)
            .where(Ticker.symbol.notin_(symbols), Ticker.exchange == exchange, Ticker.is_active == True)
            .values(is_active=False)
        )

    async def get_active_symbols(self, exchange: str | None = None) -> list[str]:
        stmt = select(Ticker.symbol).where(Ticker.is_active == True)
        if exchange:
            stmt = stmt.where(Ticker.exchange == exchange)
        return [row[0] for row in (await self.session.execute(stmt.order_by(Ticker.symbol))).fetchall()]

    async def get_ticker_id_map(self, exchange: str | None = None) -> dict[str, int]:
        stmt = select(Ticker.symbol, Ticker.id).where(Ticker.is_active == True)
        if exchange:
            stmt = stmt.where(Ticker.exchange == exchange)
        return {row[0]: row[1] for row in (await self.session.execute(stmt)).fetchall()}
```

### Backend: API Exchange Filter
```python
# Source: Codebase analysis — backend/app/api/tickers.py
@router.get("/", response_model=list[TickerResponse])
async def list_tickers(
    sector: str | None = Query(None),
    exchange: str | None = Query(None, description="Filter by exchange: HOSE, HNX, UPCOM"),
):
    async with async_session() as session:
        stmt = select(Ticker).where(Ticker.is_active.is_(True))
        if sector:
            stmt = stmt.where(Ticker.sector == sector)
        if exchange:
            stmt = stmt.where(Ticker.exchange == exchange)
        stmt = stmt.order_by(Ticker.symbol)
        # ...

# MarketOverview also needs exchange filter
@router.get("/market-overview", response_model=list[MarketTickerResponse])
async def market_overview(
    exchange: str | None = Query(None, description="Filter by exchange"),
):
    # Add exchange to MarketTickerResponse schema
    # Add Ticker.exchange to the select
    # Add .where(Ticker.exchange == exchange) if provided
```

### Backend: Scheduler Staggered Jobs
```python
# Source: Codebase analysis — backend/app/scheduler/manager.py
EXCHANGE_CRAWL_SCHEDULE = {
    "HOSE":  {"hour": 15, "minute": 30},
    "HNX":   {"hour": 16, "minute": 0},
    "UPCOM": {"hour": 16, "minute": 30},
}

def configure_jobs():
    from app.scheduler.jobs import daily_price_crawl_for_exchange, ...

    for exchange, schedule in EXCHANGE_CRAWL_SCHEDULE.items():
        scheduler.add_job(
            functools.partial(daily_price_crawl_for_exchange, exchange),
            trigger=CronTrigger(
                hour=schedule["hour"], minute=schedule["minute"],
                day_of_week="mon-fri", timezone=settings.timezone,
            ),
            id=f"daily_price_crawl_{exchange.lower()}",
            name=f"Daily OHLCV Price Crawl ({exchange})",
            replace_existing=True,
            misfire_grace_time=3600,
        )
```

### Frontend: Exchange-Aware API Client
```typescript
// Source: Codebase analysis — frontend/src/lib/api.ts
export interface MarketTicker {
  symbol: string;
  name: string;
  sector: string | null;
  exchange: string;  // NEW: "HOSE" | "HNX" | "UPCOM"
  market_cap: number | null;
  last_price: number | null;
  change_pct: number | null;
}

export async function fetchMarketOverview(exchange?: string): Promise<MarketTicker[]> {
  const params = exchange && exchange !== "all" ? `?exchange=${exchange}` : "";
  return apiFetch<MarketTicker[]>(`/tickers/market-overview${params}`);
}

export async function fetchTickers(sector?: string, exchange?: string): Promise<Ticker[]> {
  const params = new URLSearchParams();
  if (sector) params.set("sector", sector);
  if (exchange && exchange !== "all") params.set("exchange", exchange);
  const qs = params.toString();
  return apiFetch<Ticker[]>(`/tickers/${qs ? `?${qs}` : ""}`);
}
```

### Frontend: Exchange Store
```typescript
// Source: Codebase analysis — frontend/src/lib/store.ts
export type Exchange = "all" | "HOSE" | "HNX" | "UPCOM";

interface ExchangeFilterState {
  exchange: Exchange;
  setExchange: (exchange: Exchange) => void;
}

export const useExchangeStore = create<ExchangeFilterState>()(
  persist(
    (set) => ({
      exchange: "all",
      setExchange: (exchange) => set({ exchange }),
    }),
    { name: "holo-exchange-filter" },
  ),
);
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with asyncio_mode=auto |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/ -x --tb=short -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MKT-01 | HNX/UPCOM tickers synced and prices crawled | unit | `pytest tests/test_ticker_service_multi.py -x` | ❌ Wave 0 |
| MKT-02 | API endpoints filter by exchange param | unit | `pytest tests/test_api.py -x -k exchange` | ❌ Wave 0 (add to existing) |
| MKT-03 | Staggered crawl jobs registered with correct timing | unit | `pytest tests/test_scheduler.py -x -k exchange` | ❌ Wave 0 (add to existing) |
| MKT-04 | Tiered analysis: HOSE all, HNX/UPCOM watchlist only | unit | `pytest tests/test_ai_analysis_tiered.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/ -x --tb=short -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_ticker_service_multi.py` — covers MKT-01, MKT-03 (exchange-parameterized sync, deactivation scoping)
- [ ] `tests/test_ai_analysis_tiered.py` — covers MKT-04 (tiered analysis, on-demand, budget cap)
- [ ] Add exchange filter tests to existing `tests/test_api.py` — covers MKT-02
- [ ] Add exchange-parameterized job tests to existing `tests/test_scheduler.py` — covers MKT-03

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HOSE-only hardcoded | Exchange-parameterized | Phase 12 | All services, jobs, API, frontend affected |
| Single `MAX_TICKERS = 400` | Per-exchange config dict | Phase 12 | TickerService, config.py |
| Single daily_price_crawl cron | Three staggered crons | Phase 12 | scheduler/manager.py, jobs.py |
| All tickers get daily AI | Tiered: HOSE daily, HNX/UPCOM watchlist | Phase 12 | ai_analysis_service.py, jobs.py |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | VN stock ticker symbols are unique across exchanges (no symbol exists on both HOSE and HNX) | Pitfall 2 | If symbols collide, the `unique(symbol)` constraint will cause upsert to overwrite cross-exchange. Would need composite unique on `(symbol, exchange)` and an Alembic migration. |
| A2 | HNX/UPCOM crawl via vnstock VCI API works identically to HOSE crawl | Architecture | vnstock `fetch_listing(exchange="HNX")` and OHLCV fetching for HNX symbols is untested in this session. STATE.md flags this: "vnstock HNX/UPCOM compatibility needs live validation." |
| A3 | HOSE daily crawl completes within 15 minutes (leaving 15-min buffer before HNX starts) | Pitfall 3 | If HOSE crawl takes >30 min, it overlaps with HNX. Current timing: ~13 min for 400 tickers at 3.5s delay. Should be safe. |
| A4 | Gemini 1500 RPD budget is sufficient for 400 HOSE + 50 watchlisted HNX/UPCOM per analysis type | Pitfall 5 | If user watchlists >50 HNX/UPCOM tickers, analysis will be capped. User-facing: some tickers won't get daily analysis. |
| A5 | The `UserWatchlist` table (Telegram watchlist) and `useWatchlistStore` (localStorage) are the authoritative sources for "watchlisted" status | Architecture | If they diverge (e.g., user adds via Telegram but not frontend), tiered analysis may miss some tickers. Consider syncing or using union of both sources. |

## Open Questions

1. **VN Stock Symbol Uniqueness Across Exchanges**
   - What we know: In practice, VN companies list on exactly one exchange. HNX companies that "graduate" to HOSE are delisted from HNX first. [ASSUMED]
   - What's unclear: Whether there's a transition period where a symbol exists on both exchanges
   - Recommendation: Add defensive logging in TickerService — if a symbol is being upserted with a different exchange than what's in DB, log a warning. This catches the edge case without blocking.

2. **Watchlist Synchronization for Tiered Analysis**
   - What we know: Frontend watchlist is in localStorage (zustand persist). Telegram watchlist is in `UserWatchlist` table. These are independent.
   - What's unclear: Should tiered AI analysis use the union of both, or only the DB-based Telegram watchlist?
   - Recommendation: Use `UserWatchlist` (DB) as the authoritative source for scheduled analysis since it's server-accessible. The "Analyze now" button handles the frontend-only watchlist case via on-demand analysis.

3. **Weekly Ticker Refresh for HNX/UPCOM**
   - What we know: `weekly_ticker_refresh` currently only syncs HOSE tickers (Sunday 10:00 AM)
   - What's unclear: Should HNX/UPCOM also get weekly refreshes, or is the daily crawl's implicit discovery enough?
   - Recommendation: Yes, extend `weekly_ticker_refresh` to all three exchanges with staggered timing (Sunday 10:00, 10:30, 11:00). This catches IPOs/delistings.

4. **Financial Crawl Scope for HNX/UPCOM**
   - What we know: `weekly_financial_crawl` crawls financial ratios for all active tickers. With 800 tickers, this takes proportionally longer.
   - What's unclear: Should financials be crawled for all 800 tickers or only HOSE + watchlisted HNX/UPCOM?
   - Recommendation: Crawl financials for all active tickers (800). The financial crawl runs on Saturday with no competing jobs, and financial data is needed for any ticker the user might click on.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user app, no auth |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | No multi-tenancy |
| V5 Input Validation | Yes | Validate `exchange` query param against allowed enum (HOSE/HNX/UPCOM) |
| V6 Cryptography | No | No crypto in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Invalid exchange param injection | Tampering | Validate exchange against allowlist `{"HOSE", "HNX", "UPCOM"}` in API layer |
| Gemini API rate limit abuse via "Analyze now" spam | Denial of Service | Rate-limit the on-demand endpoint (e.g., 1 request per ticker per 10 minutes) |

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `backend/app/crawlers/vnstock_crawler.py` — `_EXCHANGE_MAP`, `fetch_listing(exchange=)` [VERIFIED: codebase]
- Codebase analysis: `backend/app/models/ticker.py` — `exchange` column with `server_default="HOSE"` [VERIFIED: codebase]
- Codebase analysis: `backend/app/services/ticker_service.py` — `MAX_TICKERS = 400`, deactivation logic [VERIFIED: codebase]
- Codebase analysis: `backend/app/scheduler/manager.py` — job registration, `_on_job_executed` chain [VERIFIED: codebase]
- Codebase analysis: `backend/app/scheduler/jobs.py` — all job functions, resilience pattern [VERIFIED: codebase]
- Codebase analysis: `backend/app/services/ai_analysis_service.py` — `analyze_all_tickers`, `get_ticker_id_map` [VERIFIED: codebase]
- Codebase analysis: `frontend/src/components/ui/tabs.tsx` — shadcn Tabs already installed [VERIFIED: codebase]
- Codebase analysis: `frontend/src/lib/store.ts` — zustand with persist pattern [VERIFIED: codebase]
- Codebase analysis: `backend/app/database.py` — pool_size=5, max_overflow=3 [VERIFIED: codebase]

### Tertiary (LOW confidence)
- VN stock symbol uniqueness across exchanges — based on domain knowledge, not verified against official exchange data [ASSUMED]
- vnstock HNX/UPCOM API compatibility — not live-tested in this session [ASSUMED, flagged in STATE.md]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages, purely extending existing codebase patterns
- Architecture: HIGH — all integration points identified in code, patterns well-understood
- Pitfalls: HIGH — deactivation bug and chaining issue identified through code analysis
- vnstock HNX/UPCOM compatibility: LOW — needs live validation (flagged in STATE.md)

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (30 days — stable codebase, no fast-moving external dependencies)

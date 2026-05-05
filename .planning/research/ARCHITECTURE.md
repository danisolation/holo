# Architecture Patterns

**Domain:** Stock Intelligence Platform — v11.0 UX & Reliability Overhaul
**Researched:** 2026-05-06
**Overall confidence:** HIGH (based on direct codebase analysis)

## Current Architecture (As-Is)

```
┌─────────────────────────────────────────────────────────────────┐
│  Vercel (Frontend)                                              │
│  Next.js 16 + React + TanStack Query                           │
│  ┌───────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │ Navbar    │  │ TickerSearch │  │ Pages: /, /ticker/X,   │   │
│  │ + Search  │  │ (CommandDialog│  │ /discovery, /watchlist,│   │
│  │           │  │  shouldFilter)│  │ /coach, /journal       │   │
│  └───────────┘  └──────────────┘  └────────────────────────┘   │
│         │              │                      │                  │
│         └──────────────┴──────────────────────┘                  │
│                        │ HTTP + WebSocket                        │
└────────────────────────┼────────────────────────────────────────┘
                         │
┌────────────────────────┼────────────────────────────────────────┐
│  Render.com Free Tier (Backend)                                 │
│  FastAPI + APScheduler (in-process)                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ API Routes   │  │ Scheduler    │  │ WebSocket /ws/prices  │  │
│  │ /api/*       │  │ (AsyncIO)    │  │ (30s VCI polling)     │  │
│  │ 10 routers   │  │ Cron+Chain   │  │                       │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘  │
│         │                 │                                      │
│  ┌──────┴─────────────────┴──────────────────────────────────┐  │
│  │ Services Layer                                             │  │
│  │ AIAnalysisService, PriceService, DiscoveryService,        │  │
│  │ TickerService, etc. (12 services)                          │  │
│  └──────────────────────────┬────────────────────────────────┘  │
│                              │                                   │
│  ┌──────────────────────────┴────────────────────────────────┐  │
│  │ SQLAlchemy Async + asyncpg                                 │  │
│  │ pool_size=5, max_overflow=3 (8 max connections)            │  │
│  └──────────────────────────┬────────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────┘
                              │ SSL
┌─────────────────────────────┼───────────────────────────────────┐
│  Aiven PostgreSQL                                               │
│  ~20-25 max connections, yearly partitioned daily_prices        │
│  20+ tables: tickers, daily_prices, technical_indicators,       │
│  ai_analyses, discovery_results, news_articles, etc.            │
└─────────────────────────────────────────────────────────────────┘
```

### Job Chain (Current — 1x daily at 15:30)

```
15:30 Mon-Fri (cron)
    │
    ▼
daily_price_crawl_hose
    │ (EVENT_JOB_EXECUTED chain)
    ▼
daily_indicator_compute
    │
    ▼
daily_discovery_scoring
    │
    ▼
daily_ai_analysis  ← WATCHLIST ONLY (~15-20 tickers)
    │
    ▼
daily_news_crawl
    │
    ▼
daily_sentiment_analysis
    │
    ▼
daily_combined_analysis
    │
    ▼
daily_trading_signal_analysis
    │
    ▼
daily_pick_generation
    │
    ▼
daily_pick_outcome_check
    │
    ▼
daily_consecutive_loss_check
```

## Problems & Root Causes

### Problem 1: Cold Start (~3 min API response on production)

**Root cause:** Render.com free tier spins down after 15 minutes of inactivity. Cold start = Python process restart + uvicorn init + SQLAlchemy engine creation + APScheduler startup + first DB connection through Aiven SSL.

**Why ~3 minutes:** Cold boot (~30-60s) + first query establishing asyncpg connection pool through Aiven SSL (~5-10s) + potentially heavy market-overview query (ROW_NUMBER over entire daily_prices table, no date filtering).

**Architectural impact:** The `market-overview` endpoint (line 147 of `tickers.py`) runs `ROW_NUMBER()` over the ENTIRE `daily_prices` table to find the latest 2 prices per ticker. With 400 tickers × 2+ years of data = 200K+ rows being ranked. This is the likely cause of sustained slowness beyond cold start.

### Problem 2: Search Misses Tickers

**Root cause identified in code:** `ticker-search.tsx` line 54 — `tickers?.slice(0, 50)` hard-caps rendered CommandItems to 50. The `useTickers()` hook calls `fetchTickers()` with default `limit=100` (backend default). So:
1. API returns max 100 tickers (backend default limit parameter)
2. Frontend renders only the first 50 in the Command list
3. `shouldFilter={true}` on `<Command>` only filters within the 50 rendered items
4. Any ticker beyond the first 50 alphabetically is invisible to search

**This is purely a frontend issue** — the API supports `limit=500` and the Command component can filter client-side over a larger set.

### Problem 3: AI Analysis Staleness

**Root cause:** The entire 11-step job chain runs once daily at 15:30. AI analysis runs mid-chain after price crawl + indicators + discovery scoring. By next morning, analysis is ~18 hours old. No mechanism for intraday refresh.

**Constraint:** Gemini free tier = 15 RPM, 4s delay between batches. With ~15-20 watchlist tickers at batch_size=8, a full AI cycle (technical + fundamental + sentiment + combined + trading_signal) takes ~15-20 minutes.

### Problem 4: UX Confusion for New Users

**Root cause:** Landing page shows a heatmap that's empty until user adds watchlist items. No onboarding flow. Navigation labels are abbreviated Vietnamese. No "what does this do?" context for features.

## Recommended Architecture Changes (To-Be)

### Component Map: New vs Modified

| Component | Status | What Changes |
|-----------|--------|--------------|
| **External keep-alive pinger** | 🆕 NEW | cron-job.org or UptimeRobot (zero code) |
| **TickerSearch component** | 🔧 MODIFY | Remove `.slice(0, 50)`, fetch all 400 |
| **`GET /api/tickers/market-overview`** | 🔧 MODIFY | Add date filter to ROW_NUMBER query |
| **Database indexes** | 🆕 NEW | Alembic migration for composite index |
| **In-memory response cache** | 🆕 NEW | Simple TTL cache utility |
| **Scheduler manager** | 🔧 MODIFY | Add morning AI refresh cron trigger |
| **`_on_job_executed` chain handler** | 🔧 MODIFY | Add morning chain path |
| **Home page (`page.tsx`)** | 🔧 MODIFY | Onboarding state when watchlist empty |
| **Navbar component** | 🔧 MODIFY | Feature descriptions/tooltips |

---

### Change 1: Keep-Alive Service (External Pinger)

**Architecture decision:** Use an external free cron service, NOT an in-process keep-alive.

**Why external:** The backend IS the thing that sleeps. An in-process timer dies when Render spins down the process. You need something outside Render to keep hitting it.

**Recommended approach: UptimeRobot or cron-job.org**
- Configure to ping `https://holo-api.onrender.com/` every 5 minutes
- Both are free, no code changes needed
- The existing `GET /` endpoint returns `{"status": "ok"}` — perfect health target

**Why NOT Vercel Cron:** Vercel Hobby plan only supports daily cron frequency. Not sufficient for keep-alive.

**Integration impact:** Zero backend/frontend code changes. Purely external configuration.

---

### Change 2: Search Fix

**Files modified:**
```
frontend/src/components/ticker-search.tsx  ← MODIFY (2 lines)
```

**What to change:**
1. Remove `.slice(0, 50)` from line 54
2. Change `useTickers()` to `useTickers(undefined, undefined, 500)` to fetch all 400 HOSE tickers
3. cmdk's `shouldFilter={true}` handles client-side fuzzy matching over the full set

**Why NOT a backend search endpoint:** 400 tickers × ~50 bytes = ~20KB. Already fetched and cached by TanStack Query (5-min staleTime). Client-side filtering over 400 items is instant. A backend endpoint adds network latency + cold start risk for zero benefit.

**Architecture impact:** None. Pure presentation fix.

---

### Change 3: API Performance Optimization

**Files modified:**
```
backend/app/api/tickers.py                ← MODIFY market-overview query
backend/alembic/versions/xxx_indexes.py   ← NEW migration
backend/app/cache.py                      ← NEW utility (optional)
```

#### 3a. Market-Overview Query Fix (Critical)

The current query runs `ROW_NUMBER()` over the ENTIRE `daily_prices` table. Fix by adding a date filter:

```python
# BEFORE (scans entire daily_prices — 200K+ rows):
ranked = select(
    DailyPrice.ticker_id, DailyPrice.close,
    func.row_number().over(
        partition_by=DailyPrice.ticker_id,
        order_by=DailyPrice.date.desc(),
    ).label("rn"),
).subquery("ranked")

# AFTER (scans last 7 days only — ~2,800 rows):
since = date.today() - timedelta(days=7)
ranked = select(
    DailyPrice.ticker_id, DailyPrice.close,
    func.row_number().over(
        partition_by=DailyPrice.ticker_id,
        order_by=DailyPrice.date.desc(),
    ).label("rn"),
).where(DailyPrice.date >= since).subquery("ranked")
```

**Expected improvement:** ~100x reduction in rows processed.

#### 3b. Composite Database Index

```sql
-- Alembic migration
CREATE INDEX ix_daily_prices_ticker_date_close
ON daily_prices (ticker_id, date DESC, close);
```

This covers the market-overview query's access pattern (ticker_id partition, date ordering, close column) without touching the heap.

#### 3c. In-Memory Response Cache (Optional)

Simple TTL cache for the market-overview response. Single user = no stale data concerns.

```python
import time
from typing import Any

_cache: dict[str, tuple[float, Any]] = {}

def get_cached(key: str, ttl: float = 60.0):
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < ttl:
            return data
    return None

def set_cached(key: str, data: Any):
    _cache[key] = (time.time(), data)
```

**Architecture decision: NOT adding Redis.** Single-user app. Python `dict` with TTL is equivalent. Redis adds infrastructure complexity for zero benefit.

---

### Change 4: More Frequent AI Analysis

**Files modified:**
```
backend/app/scheduler/manager.py  ← MODIFY: add morning cron + chain
```

**Strategy: Add a morning AI refresh at 8:30 AM for watchlist tickers.**

The morning chain is a subset of the daily chain — only the steps needed for fresh AI signals:

```
08:30 Mon-Fri (NEW cron trigger)
    │
    ▼
morning_price_crawl_hose  ← Crawl pre-market/opening prices
    │ (chain via _on_job_executed)
    ▼
morning_indicator_compute  ← Recompute with fresh data
    │
    ▼
morning_ai_analysis  ← Technical + combined only (watchlist)
    │
    ▼
morning_trading_signal  ← Fresh trading plans for the day
```

**Why 8:30:** HOSE opens at 9:00. VCI provides pre-market data by ~8:15. Running at 8:30 gives fresh signals before market open.

**Why skip discovery/news/sentiment in morning:** Discovery scores all 400 tickers (slow). News/sentiment are supplementary and don't change dramatically intraday. The afternoon run covers these.

**Implementation approach:** Add a new cron trigger and chain path in `manager.py`. Reuse the same job functions (`daily_price_crawl_for_exchange`, `daily_indicator_compute`, `daily_ai_analysis`, `daily_trading_signal_analysis`) but with different job IDs for the morning chain (e.g., `morning_price_crawl_hose`, `morning_indicator_compute`, etc.).

**Gemini budget check:** ~15-20 watchlist tickers × 5 analysis types × 2 runs/day ≈ ~150-200 API calls/day. At 15 RPM with 4s delay, each run takes ~15 min. Well under Gemini free tier (1,500 RPD).

**Idempotency:** AI analysis uses `INSERT ... ON CONFLICT (ticker_id, analysis_type, analysis_date) DO UPDATE` — already idempotent. Running twice per day safely overwrites the earlier result.

**Critical dependency on Phase 1:** The keep-alive pinger MUST be active before this works. Otherwise the 8:30 AM cron fires on a sleeping Render process. While `misfire_grace_time=3600` provides a 1-hour recovery window, the pinger ensures reliable scheduling.

---

### Change 5: UX/Onboarding Improvements

**Files modified:**
```
frontend/src/app/page.tsx           ← MODIFY: onboarding state
frontend/src/components/navbar.tsx  ← MODIFY: descriptions
```

**Onboarding strategy for empty-watchlist users:**

Current: empty heatmap + "Chưa có mã trong danh mục" message.

Proposed:
1. **Hero card:** "Holo — AI phân tích chứng khoán HOSE" with brief feature summary
2. **Quick-start:** Show top 5 tickers from discovery (by total_score) with one-click add buttons
3. **Feature cards:** 4 cards explaining Discovery → Watchlist → Coach → Journal workflow
4. **Nav descriptions:** Brief subtitle text under navigation labels

**Architecture impact:** Frontend-only. Uses existing `/api/discovery` endpoint for the quick-start tickers — no new backend code.

---

## Data Flow Changes Summary

### Current (1x daily)
```
15:30 → price → indicators → discovery → AI(all) → news → sentiment → combined → signal → picks
```

### Proposed (2x daily)
```
08:30 → price → indicators → AI(tech+combined) → signal  [MORNING — fast, watchlist]
15:30 → price → indicators → discovery → AI(all) → news → sentiment → combined → signal → picks  [AFTERNOON — full]
```

### API Response Flow (Optimized)
```
Request → In-memory cache check (60s TTL)
  ├── HIT  → Return cached (< 1ms)
  └── MISS → Date-filtered query (7 days, ~2800 rows)
             → Cache result → Return (~50-100ms)
```

## Patterns to Follow

### Pattern 1: Date-Bounded Window Queries
**What:** Always add a date filter BEFORE window functions on time-series tables
**When:** Any query using ROW_NUMBER/RANK over daily_prices or similar
**Why:** Prevents full table scans as historical data accumulates

### Pattern 2: External Health Pinging
**What:** Use external free services for keep-alive instead of in-process timers
**When:** Render.com free tier or any sleeping infrastructure
**Why:** In-process solutions die with the sleeping process

### Pattern 3: Client-Side Filtering for Small Datasets
**What:** Fetch complete dataset, cache in TanStack Query, filter in browser
**When:** Dataset < 1000 items and < 100KB
**Why:** Eliminates network round-trips, works offline, instant UX

### Pattern 4: Subset Job Chains for Freshness
**What:** Run a shorter version of the full pipeline at additional times
**When:** Full pipeline too slow/expensive to run multiple times daily
**Why:** Gets 80% of freshness benefit at 30% of the computational cost

## Anti-Patterns to Avoid

### Anti-Pattern 1: Backend Search for 400 Items
**What:** Creating `/api/search?q=X` for the ticker list
**Why bad:** Adds network latency + cold start risk for zero benefit
**Instead:** Fetch all tickers, cache with TanStack Query, filter with cmdk

### Anti-Pattern 2: Redis for Single-User Caching
**What:** Adding Redis infrastructure for response caching
**Why bad:** Adds cost, connection management, failure points. Python `dict` with TTL is equivalent.
**Instead:** In-memory dict cache with timestamp-based TTL

### Anti-Pattern 3: Premature Render Paid Tier
**What:** Upgrading to $7/month Render to avoid cold starts
**Why bad:** External pinger + query optimization solves 95% for free
**Instead:** External pinger first. Evaluate paid tier only if still insufficient.

### Anti-Pattern 4: Celery/Worker for Morning AI
**What:** Adding Celery + Redis broker for a second daily AI run
**Why bad:** APScheduler already handles multiple cron triggers and chaining in-process
**Instead:** Add another cron trigger + chain path in existing scheduler manager

## Suggested Build Order (Dependency-Aware)

### Phase 1: Keep-Alive + API Performance
**Rationale:** Eliminates the most visible user pain (~3 min load). All other improvements are useless if the app doesn't respond.

| Step | Component | Type | Risk |
|------|-----------|------|------|
| 1a | External pinger setup (UptimeRobot/cron-job.org) | Config only | None |
| 1b | Market-overview date filter | Modify `tickers.py` | LOW |
| 1c | Composite index migration | New Alembic migration | LOW |
| 1d | In-memory response cache | New `cache.py` utility | LOW |

**Dependencies:** None. Start immediately.

### Phase 2: Search Fix
**Rationale:** Smallest change, highest UX impact. 2-line fix.

| Step | Component | Type | Risk |
|------|-----------|------|------|
| 2a | Remove `.slice(0, 50)` | Modify `ticker-search.tsx` | None |
| 2b | Fetch all tickers (limit=500) | Modify `useTickers()` call | None |

**Dependencies:** Independent of Phase 1. Can run in parallel.

### Phase 3: AI Analysis Refresh
**Rationale:** Requires keep-alive (Phase 1) for reliable 8:30 AM scheduling.

| Step | Component | Type | Risk |
|------|-----------|------|------|
| 3a | Morning cron trigger | Modify `manager.py` | LOW |
| 3b | Morning chain in `_on_job_executed` | Modify `manager.py` | MEDIUM |
| 3c | Verify idempotency in production | Testing | LOW |

**Dependencies:** Phase 1 (keep-alive must be active).

### Phase 4: UX/Onboarding
**Rationale:** Polish layer. Best done after functional fixes.

| Step | Component | Type | Risk |
|------|-----------|------|------|
| 4a | Home page onboarding redesign | Modify `page.tsx` | LOW |
| 4b | Quick-add popular tickers | Modify `page.tsx` | LOW |
| 4c | Navigation descriptions | Modify `navbar.tsx` | None |

**Dependencies:** Phase 2 (search must work for onboarding).

## Scalability Considerations

| Concern | Now (1 user) | At 10 users | At 100 users |
|---------|-------------|-------------|--------------|
| DB connections | pool_size=5 sufficient | pool_size=10 | PgBouncer needed |
| Gemini rate limit | 15 RPM covers 2x/day | Paid tier required | Queue + paid tier |
| Cold start | External pinger | Paid Render ($7/mo) | Paid + autoscaling |
| Market-overview | Date filter + cache | Same approach | Materialized view |
| Search | Client-side (400 items) | Same approach | Server-side ILIKE |

**For v11.0:** No scaling changes needed. Architecture is fully adequate for single-user.

## Sources

- Direct codebase analysis: `backend/app/scheduler/manager.py`, `backend/app/api/tickers.py`, `frontend/src/components/ticker-search.tsx` — **HIGH confidence**
- Render.com free tier sleep behavior: well-documented, 15-min inactivity timeout — **HIGH confidence**
- Vercel Hobby cron limitations (daily only): **MEDIUM confidence** (verify current docs)
- PostgreSQL window function performance characteristics: standard DB knowledge — **HIGH confidence**
- UptimeRobot/cron-job.org free tier availability: established services — **HIGH confidence**
- Gemini free tier limits (15 RPM, 1500 RPD): per project constraints doc — **HIGH confidence**

# Architecture Patterns

**Domain:** Watchlist-centric stock discovery integration into existing Holo platform
**Researched:** 2025-07-23
**Confidence:** HIGH — based on direct codebase analysis of all integration points

## Executive Summary

The v10.0 architecture challenge is **narrowing a 400-ticker firehose to a watchlist-gated pipeline** while adding a new Discovery engine that scans the full market to suggest additions. This requires surgical modifications to the existing scheduler chain, two new database entities (sector grouping + discovery results), a new API router, and a new frontend route — all without breaking the existing daily pipeline.

The key architectural insight: the current system runs ALL analysis on ALL ~400 active tickers. v10.0 splits this into two distinct pipelines: (1) a **lightweight discovery scan** across all tickers (cheap, technical-only), and (2) the **deep analysis pipeline** (AI-heavy, multi-dimensional) gated to only watchlist tickers. This dramatically reduces Gemini API usage from ~400 tickers x 5 analysis types to ~15-30 watchlist tickers x 5 types + ~400 tickers x 1 lightweight scan.

## Current Architecture (As-Is)

### Scheduler Chain (daily, Mon-Fri)

```
15:30 CRON: daily_price_crawl_hose (ALL ~400 HOSE tickers)
  | EVENT_JOB_EXECUTED chain
daily_indicator_compute (ALL tickers)
  |
daily_ai_analysis (ALL tickers -- technical + fundamental)
  |
daily_news_crawl (ALL tickers -- CafeF)
  |
daily_sentiment_analysis (ALL tickers)
  |
daily_combined_analysis (ALL tickers)
  |
daily_trading_signal_analysis (ALL tickers)
  |
daily_pick_generation (top 3-5 from ALL)
  |
daily_pick_outcome_check
  |
daily_consecutive_loss_check
```

### Key Integration Points Identified

| Component | File | Current Scope | v10.0 Impact |
|-----------|------|---------------|-------------|
| `TickerService.get_ticker_id_map()` | `ticker_service.py` | Returns ALL active tickers | Discovery uses this; AI pipeline needs watchlist-filtered version |
| `AIAnalysisService.analyze_all_tickers()` | `ai_analysis_service.py` | Accepts optional `ticker_filter` dict | Already supports filtering! Key enabler for watchlist gating |
| `_on_job_executed()` | `scheduler/manager.py` | Linear chain, no branching | Needs fork point for discovery vs deep analysis |
| `UserWatchlist` model | `models/user_watchlist.py` | Simple `(id, symbol, created_at)` | Needs `sector_group` column |
| `Ticker` model | `models/ticker.py` | Has `sector`, `industry` from vnstock | Source for default sector suggestions |
| Heatmap component | `components/heatmap.tsx` | Groups by `ticker.sector` from market-overview API | Needs to group by user-assigned sector from watchlist |
| Market overview API | `api/tickers.py` `/market-overview` | Returns ALL active tickers with price/change | Heatmap needs watchlist-only variant |

## Recommended Architecture (To-Be)

### Revised Scheduler Chain

```
15:30 CRON: daily_price_crawl_hose (ALL ~400 tickers -- unchanged)
  |
daily_indicator_compute (ALL tickers -- unchanged, needed for discovery)
  |
daily_discovery_scan (NEW -- lightweight scoring of ALL tickers)
  |   Runs AFTER indicators. Pure computation, no Gemini calls.
  |   Scores tickers on technical signals only (RSI, MACD, volume spike, etc.)
  |   Stores results in discovery_results table.
  |
daily_ai_analysis (MODIFIED -- watchlist tickers ONLY)
  |
daily_news_crawl (watchlist tickers ONLY)
  |
daily_sentiment_analysis (watchlist tickers ONLY)
  |
daily_combined_analysis (watchlist tickers ONLY)
  |
daily_trading_signal_analysis (watchlist tickers ONLY)
  |
daily_pick_generation (from watchlist tickers ONLY)
  |
daily_pick_outcome_check (unchanged)
  |
daily_consecutive_loss_check (unchanged)
```

### Chain Fork Strategy

The insertion after `daily_indicator_compute` is the critical design decision. Two approaches:

**Option A: Sequential (recommended)** — Discovery runs first, then AI pipeline. Simple, no concurrency issues with DB pool or Gemini rate limits.

```python
# In manager.py _on_job_executed:
elif event.job_id in ("daily_indicator_compute_triggered", "daily_indicator_compute_manual"):
    # Discovery first (no Gemini, fast), then AI pipeline
    scheduler.add_job(daily_discovery_scan, id="daily_discovery_scan_triggered", ...)

elif event.job_id in ("daily_discovery_scan_triggered",):
    # After discovery completes, start AI pipeline (watchlist-only)
    scheduler.add_job(daily_ai_analysis, id="daily_ai_analysis_triggered", ...)
```

**Option B: Parallel** — Both run concurrently. Faster but risks DB pool exhaustion (pool_size=5, max_overflow=3) and adds complexity. **Not recommended** given the tight DB pool.

### Component Boundaries

| Component | Responsibility | New/Modified | Communicates With |
|-----------|---------------|-------------|-------------------|
| `DiscoveryService` | Score all tickers on technical signals, rank, persist | **NEW** | IndicatorService (reads), DB (writes discovery_results) |
| `DiscoveryScoringEngine` | Pure computation: RSI zones, MACD crossovers, volume spikes, breakout detection | **NEW** | None (pure functions, no I/O) |
| `AIAnalysisService` | Gemini multi-dimensional analysis | **MODIFIED** — add watchlist-filter helper | TickerService, WatchlistService |
| `WatchlistService` | Extract watchlist logic from API into service layer | **NEW** | DB (user_watchlist), TickerService |
| Scheduler jobs | Chain orchestration | **MODIFIED** — add discovery job, gate AI jobs | All services |
| Discovery API | `/api/discovery` endpoints | **NEW** | DiscoveryService |
| Watchlist API | `/api/watchlist` | **MODIFIED** — add sector_group CRUD | WatchlistService |

### New Database Entities

#### 1. `discovery_results` table

```sql
CREATE TABLE discovery_results (
    id BIGSERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(id),
    scan_date DATE NOT NULL,
    discovery_score NUMERIC(5,2) NOT NULL,  -- 0-100
    score_breakdown JSONB NOT NULL,          -- {rsi: 8, macd: 7, volume: 9, breakout: 6}
    signal_summary VARCHAR(50) NOT NULL,     -- 'strong_buy', 'buy', 'neutral', 'avoid'
    highlights TEXT,                          -- Vietnamese 1-line reason
    is_in_watchlist BOOLEAN DEFAULT FALSE,   -- Denormalized for fast filtering
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(ticker_id, scan_date)
);
CREATE INDEX idx_discovery_date_score ON discovery_results(scan_date, discovery_score DESC);
```

**Why a dedicated table instead of reusing `ai_analyses`:**
- Discovery scoring is pure computation (no Gemini), different from AI analysis
- Different schema: composite score + breakdown, not signal/reasoning
- Allows independent retention policy (keep 7 days of discovery vs years of AI analysis)
- Avoids bloating `ai_analyses` with ~400 rows/day of non-AI data

#### 2. `user_watchlist.sector_group` column

```sql
ALTER TABLE user_watchlist ADD COLUMN sector_group VARCHAR(50);
```

**Why a column on `user_watchlist` instead of a separate table:**
- Single-user system — no complex group management needed
- One ticker belongs to one user-assigned group
- Simple `GROUP BY sector_group` for heatmap
- `Ticker.sector` from vnstock provides a sensible default suggestion
- No need for a full `watchlist_groups` table with ordering, colors, etc.

### Data Flow

#### Discovery Flow (daily, automatic)

```
1. Indicators computed for ALL tickers (existing)
2. DiscoveryService reads latest indicators + prices for ALL tickers
3. DiscoveryScoringEngine scores each ticker:
   - RSI zone score (oversold=high, overbought=low)
   - MACD momentum score (bullish crossover=high)
   - Volume spike detection (unusual volume=high)
   - Breakout score (price vs S/R levels)
   - ADX trend strength
4. Results stored in discovery_results (UPSERT on ticker_id+scan_date)
5. Discovery page reads top N results, filtered by NOT in watchlist
```

#### Watchlist-Gated AI Flow (daily, automatic)

```
1. Jobs.py queries user_watchlist to get symbols list
2. TickerService.get_ticker_id_map() filtered to only those symbols
3. Passes ticker_filter dict to AIAnalysisService.analyze_all_tickers()
4. analyze_all_tickers() already supports ticker_filter parameter!
   (See ai_analysis_service.py line 87-98)
5. Downstream chain (news, sentiment, combined, signals) all receive
   same watchlist-gated ticker set
```

#### Heatmap Rework Flow

```
1. Frontend calls GET /api/watchlist (already returns all watchlist items)
2. Response enriched with sector_group field
3. Frontend calls GET /api/tickers/market-overview (existing)
4. Frontend filters market-overview to only watchlist symbols
5. Groups by sector_group instead of ticker.sector
6. Heatmap renders watchlist-only, user-grouped data
```

## Patterns to Follow

### Pattern 1: Watchlist-Filter Helper

The `AIAnalysisService.analyze_all_tickers()` already accepts `ticker_filter: dict[str, int] | None`. Create a reusable helper to build this from watchlist.

```python
# services/watchlist_service.py (NEW)
class WatchlistService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_watchlist_ticker_map(self) -> dict[str, int]:
        """Return {symbol: ticker_id} for all watchlist tickers.
        Used to gate AI analysis pipeline to watchlist-only.
        """
        stmt = (
            select(UserWatchlist.symbol, Ticker.id)
            .join(Ticker, UserWatchlist.symbol == Ticker.symbol)
            .where(Ticker.is_active == True)
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
```

**Why this pattern:** Single source of truth for "which tickers to analyze." Used by all chained jobs. Avoids N+1 queries across the chain.

### Pattern 2: Discovery Score as Pure Functions

Keep discovery scoring as stateless pure functions (like `pick_service.py` already does with `compute_composite_score`, `compute_safety_score`).

```python
# services/discovery/scoring.py (NEW)
def compute_rsi_score(rsi_14: float | None) -> float:
    """Score RSI for discovery. Oversold (< 30) = high score."""
    if rsi_14 is None:
        return 5.0
    if rsi_14 < 30:
        return 10.0 - (rsi_14 / 30) * 2  # 8-10 range
    if rsi_14 > 70:
        return max(0, 3.0 - (rsi_14 - 70) / 10)
    return 5.0 + (50 - abs(rsi_14 - 50)) / 10

def compute_discovery_score(indicators: dict) -> tuple[float, dict]:
    """Returns (total_score, breakdown_dict)."""
    rsi = compute_rsi_score(indicators.get("rsi_14"))
    macd = compute_macd_score(indicators.get("macd_histogram"))
    volume = compute_volume_score(indicators.get("volume"), indicators.get("avg_volume"))
    breakout = compute_breakout_score(indicators.get("close"), indicators.get("resistance_1"))
    trend = compute_trend_score(indicators.get("adx_14"))

    breakdown = {"rsi": rsi, "macd": macd, "volume": volume, "breakout": breakout, "trend": trend}
    total = sum(breakdown.values()) / len(breakdown) * 10  # Normalize to 0-100
    return total, breakdown
```

**Why pure functions:** Testable without DB, composable, mirrors existing `pick_service.py` pattern.

### Pattern 3: Chain Gate with Fallback

If watchlist is empty, the AI pipeline should gracefully skip rather than crash.

```python
async def daily_ai_analysis():
    async with async_session() as session:
        # Gate: only analyze watchlist tickers
        watchlist_svc = WatchlistService(session)
        ticker_filter = await watchlist_svc.get_watchlist_ticker_map()

        if not ticker_filter:
            logger.warning("Watchlist is empty -- skipping AI analysis")
            # Still return normally so chain continues
            return

        service = AIAnalysisService(session)
        results = await service.analyze_all_tickers(
            analysis_type="both",
            ticker_filter=ticker_filter,  # Already supported!
        )
```

### Pattern 4: Frontend Data Composition (No New API for Heatmap)

For the heatmap rework, avoid creating a new dedicated API endpoint. Compose existing data on the frontend:

```typescript
// Compose watchlist + market data on frontend
const watchlistSymbols = new Set(watchlistData.map(w => w.symbol));
const watchlistMarketData = marketData.filter(t => watchlistSymbols.has(t.symbol));

// Group by user sector instead of ticker sector
const sectorMap = new Map(watchlistData.map(w => [w.symbol, w.sector_group]));
const grouped = watchlistMarketData.reduce((acc, ticker) => {
  const group = sectorMap.get(ticker.symbol) ?? ticker.sector ?? "Khac";
  if (!acc[group]) acc[group] = [];
  acc[group].push(ticker);
  return acc;
}, {});
```

**Why frontend composition:** Both APIs already exist. Adding a third "watchlist-market-overview" API duplicates logic. React Query caches both responses, so composition is fast.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Gemini for Discovery Scoring
**What:** Using Gemini API to score all 400 tickers for discovery
**Why bad:** 15 RPM rate limit x batch 8 = ~50 batches x 4s delay = 200s minimum. Plus unnecessary API cost for scores that pure computation handles better.
**Instead:** Use indicator-based scoring (RSI zones, MACD crossovers, volume spikes, S/R breakouts). All data already exists in `technical_indicators` table.

### Anti-Pattern 2: Separate Watchlist Scheduler
**What:** Creating a separate cron-triggered scheduler for watchlist analysis
**Why bad:** Two competing scheduler chains create race conditions, duplicate DB sessions, and make the pipeline order unpredictable.
**Instead:** Single chain with a fork point after indicators. Sequential, deterministic.

### Anti-Pattern 3: Denormalizing Sector Group on Ticker Table
**What:** Adding `user_sector_group` column to `tickers` table
**Why bad:** Mixes system data (ticker metadata from vnstock) with user preferences. Confuses `weekly_ticker_refresh` which upserts ticker data. Gets overwritten on sync.
**Instead:** Store on `user_watchlist` table — user data stays on user table.

### Anti-Pattern 4: Over-Engineering Discovery with ML
**What:** Building a recommendation engine with collaborative filtering or ML scoring
**Why bad:** Single-user system. No collaborative data. ML adds complexity, training pipeline, and false precision.
**Instead:** Weighted composite score from 5 indicator dimensions. User can understand why a ticker was recommended.

### Anti-Pattern 5: Creating a New Market Overview API for Heatmap
**What:** Adding `GET /api/tickers/watchlist-overview` endpoint
**Why bad:** Duplicates 90% of `/api/tickers/market-overview` logic. Two endpoints to maintain. Frontend already has both watchlist and market data via React Query.
**Instead:** Frontend composes the intersection.

## New Components Inventory

### Backend — New Files

| File | Type | Purpose |
|------|------|---------|
| `services/watchlist_service.py` | Service | Watchlist query helpers (ticker_map, sector groups) |
| `services/discovery/scoring.py` | Module | Pure discovery scoring functions |
| `services/discovery/discovery_service.py` | Service | Orchestrate scoring for all tickers, persist results |
| `models/discovery_result.py` | Model | SQLAlchemy model for discovery_results table |
| `schemas/discovery.py` | Schema | Pydantic schemas for discovery API |
| `api/discovery.py` | Router | Discovery API endpoints |
| `alembic/versions/xxx_add_discovery.py` | Migration | discovery_results table + sector_group column |

### Backend — Modified Files

| File | Change |
|------|--------|
| `scheduler/manager.py` | Add discovery chain link after indicators |
| `scheduler/jobs.py` | Add `daily_discovery_scan()` job, modify AI jobs to use watchlist filter |
| `api/router.py` | Register discovery router |
| `models/user_watchlist.py` | Add `sector_group` column |
| `schemas/watchlist.py` | Add `sector_group` to response/request schemas |
| `api/watchlist.py` | Add sector_group CRUD, update enrichment query |

### Frontend — New Files

| File | Type | Purpose |
|------|------|---------|
| `src/app/discovery/page.tsx` | Page | Discovery page showing recommended tickers |
| `src/components/discovery-card.tsx` | Component | Individual discovery result card |

### Frontend — Modified Files

| File | Change |
|------|--------|
| `src/components/navbar.tsx` | Add "Kham pha" nav link |
| `src/components/heatmap.tsx` | Support watchlist-only mode with user sector groups |
| `src/app/page.tsx` | Switch from all-market to watchlist-only heatmap |
| `src/lib/api.ts` | Add discovery API types and fetch functions |
| `src/lib/hooks.ts` | Add `useDiscoveryResults()` hook |
| `src/components/watchlist-table.tsx` | Add sector_group column with inline edit |

## Scalability Considerations

| Concern | Current (400 tickers) | With Watchlist (15-30 tickers) | Impact |
|---------|----------------------|-------------------------------|--------|
| Daily Gemini API calls | ~400 x 5 types = ~250 API calls | ~25 x 5 = ~80 calls | **70% reduction** in API usage |
| Pipeline duration | ~25-30 min (250 calls x 4s delay) | ~8-10 min | **3x faster** pipeline |
| DB writes (ai_analyses) | ~2,000 rows/day | ~125 rows/day | **16x less** DB load |
| Discovery scan | N/A | ~400 tickers, pure computation | <5 seconds, no API calls |
| Discovery storage | N/A | 400 rows/day, 7-day retention | 2,800 rows max |

## Suggested Build Order

### Phase A: Database & Discovery Foundation
1. Alembic migration -- `discovery_results` table + `sector_group` column on `user_watchlist`
2. Discovery models -- SQLAlchemy model for `discovery_results`
3. Discovery scoring engine -- Pure functions for technical scoring
4. Discovery service -- Orchestration: read indicators, score, persist
5. Discovery scheduler job -- `daily_discovery_scan()` + chain link

### Phase B: Watchlist-Gated AI Pipeline
1. WatchlistService -- `get_watchlist_ticker_map()` helper
2. Modify AI jobs -- Gate all 5 AI scheduler jobs to use watchlist filter
3. Scheduler chain rewire -- Insert discovery between indicators and AI analysis
4. Verify pick generation only processes watchlist tickers

### Phase C: Sector Grouping & Heatmap Rework
1. Watchlist API -- Add `sector_group` to schemas, CRUD, auto-suggest from `Ticker.sector`
2. Watchlist table -- Add inline sector_group editing
3. Heatmap rework -- Filter to watchlist-only, group by `sector_group`
4. Home page -- Switch from all-market to watchlist heatmap

### Phase D: Discovery Frontend
1. Discovery API -- Endpoints for discovery results (today's scan, filters)
2. Discovery page -- New `/discovery` route with result cards
3. Add-to-watchlist flow -- One-click from discovery card to watchlist
4. Navigation -- Add nav link

## Sources

- Direct codebase analysis of `scheduler/manager.py` (chain logic, lines 58-162)
- Direct codebase analysis of `ai_analysis_service.py` (ticker_filter support, line 87)
- Direct codebase analysis of `models/user_watchlist.py` (current schema)
- Direct codebase analysis of `models/ticker.py` (sector/industry fields)
- Direct codebase analysis of `components/heatmap.tsx` (grouping logic)
- Direct codebase analysis of `api/watchlist.py` (enrichment query pattern)
- Direct codebase analysis of `services/pick_service.py` (pure function pattern)
- Direct codebase analysis of `config.py` (Gemini settings: batch_size=8, delay=4s)

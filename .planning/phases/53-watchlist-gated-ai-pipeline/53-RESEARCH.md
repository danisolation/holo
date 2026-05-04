# Phase 53: Watchlist-Gated AI Pipeline - Research

**Researched:** 2025-07-18
**Domain:** Backend pipeline filtering (Python/FastAPI/SQLAlchemy)
**Confidence:** HIGH

## Summary

This phase gates all Gemini-powered AI analysis and daily pick generation to only process tickers on the user's watchlist (~15-30 tickers) instead of the entire HOSE exchange (~400 tickers). The infrastructure is remarkably well-prepared: `AIAnalysisService.analyze_all_tickers()` already accepts a `ticker_filter: dict[str, int]` parameter that all 5 analysis sub-methods honor. The change is primarily plumbing: build a watchlist→ticker_id map, pass it to existing methods, and add empty-watchlist guard rails.

The scheduler chain (`price_crawl → indicators → discovery_scoring → ai_analysis → news → sentiment → combined → trading_signal → pick_generation`) needs gating at 5 job functions: `daily_ai_analysis`, `daily_sentiment_analysis`, `daily_combined_analysis`, `daily_trading_signal_analysis`, and `daily_pick_generation`. The first 4 are near-identical changes (fetch watchlist map, pass as `ticker_filter`). The pick service needs an additional WHERE clause to constrain signal queries to watchlist tickers.

**Primary recommendation:** Create a single helper function `get_watchlist_ticker_map(session) -> dict[str, int]` that JOINs `UserWatchlist.symbol` → `Ticker.symbol` → `Ticker.id`, then call it in each gated job function and pass the result as `ticker_filter`. Guard empty watchlist with early return + `status="skipped"`.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- All decisions at agent's discretion (no locked choices from discuss-phase)

### Agent's Discretion
- Full discretion on implementation approach

### Deferred Ideas (OUT OF SCOPE)
- None specified

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WL-01 | AI analysis (Gemini) runs only on watchlist tickers | `ticker_filter` param already exists on all 5 analysis methods; need to build watchlist→ticker_id map and pass it in 4 job functions |
| WL-02 | Daily picks selected exclusively from watchlist tickers | `generate_daily_picks()` signal query needs explicit `.where(Ticker.symbol.in_(watchlist_symbols))` filter |

</phase_requirements>

## Standard Stack

No new libraries needed. This phase modifies existing code only.

### Existing Libraries Used
| Library | Version | Purpose | Role in This Phase |
|---------|---------|---------|-------------------|
| SQLAlchemy | ~2.0 | ORM & query builder | JOIN UserWatchlist → Ticker for ticker_id map |
| loguru | 0.7.3 | Structured logging | Warning logs for empty watchlist |
| APScheduler | 3.11 | Job scheduling | Job functions being modified |

## Architecture Patterns

### Pattern 1: Watchlist Ticker Map Helper
**What:** A reusable async function that resolves watchlist symbols to `{symbol: ticker_id}` dict.
**When to use:** At the start of every gated job function.
**Why:** The UserWatchlist model stores `symbol` (String), not `ticker_id` (FK). The `ticker_filter` parameter expects `dict[str, int]` mapping `{symbol: ticker_id}`. A JOIN resolves this. [VERIFIED: codebase inspection of `UserWatchlist` model and `ticker_filter` type signature]

**Current UserWatchlist model** (no `ticker_id` column):
```python
# Source: backend/app/models/user_watchlist.py
class UserWatchlist(Base):
    __tablename__ = "user_watchlist"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
```

**Correct JOIN pattern** (from `app/api/watchlist.py` line 49):
```python
# Source: backend/app/api/watchlist.py
.outerjoin(Ticker, UserWatchlist.symbol == Ticker.symbol)
```

**Helper function location:** `backend/app/scheduler/jobs.py` (module-level, since all consumers are in this file).

```python
async def _get_watchlist_ticker_map(session) -> dict[str, int]:
    """Resolve watchlist symbols to {symbol: ticker_id} for ticker_filter.
    
    Returns empty dict if watchlist is empty or no symbols match active tickers.
    """
    from app.models.user_watchlist import UserWatchlist
    from app.models.ticker import Ticker
    
    stmt = (
        select(Ticker.symbol, Ticker.id)
        .join(UserWatchlist, UserWatchlist.symbol == Ticker.symbol)
        .where(Ticker.is_active == True)
    )
    result = await session.execute(stmt)
    return {row[0]: row[1] for row in result.fetchall()}
```

### Pattern 2: Empty Watchlist Guard
**What:** Early return with `status="skipped"` when watchlist is empty, preventing crashes and continuing the scheduler chain.
**When to use:** After fetching watchlist map, before calling analysis service.

```python
# In each gated job function:
ticker_filter = await _get_watchlist_ticker_map(session)
if not ticker_filter:
    logger.warning("Watchlist empty — skipping daily_ai_analysis")
    await job_svc.complete(execution, status="skipped", 
                          result_summary={"reason": "empty_watchlist", "tickers": 0})
    await session.commit()
    return  # Normal return → chain continues via EVENT_JOB_EXECUTED
```

**Critical detail:** Return normally (don't raise) so the scheduler chain continues. The `_on_job_executed` handler in `manager.py` only skips chaining when `event.exception` is set. A normal return with "skipped" status will still chain to the next job. [VERIFIED: manager.py lines 66-68]

### Pattern 3: Gated Job Function Modification
**What:** Minimal modification to existing job functions — add 5-8 lines at the start.
**When to use:** For all 4 Gemini-calling job functions.

**Current pattern** (e.g., `daily_ai_analysis`):
```python
async def daily_ai_analysis():
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_ai_analysis")
        try:
            service = AIAnalysisService(session)
            results = await service.analyze_all_tickers(analysis_type="both")
            # ... result handling
```

**Modified pattern:**
```python
async def daily_ai_analysis():
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_ai_analysis")
        try:
            # Phase 53: Gate to watchlist tickers only
            ticker_filter = await _get_watchlist_ticker_map(session)
            if not ticker_filter:
                logger.warning("Watchlist empty — skipping daily_ai_analysis")
                await job_svc.complete(execution, status="skipped",
                                      result_summary={"reason": "empty_watchlist"})
                await session.commit()
                return
            logger.info(f"Watchlist gating: {len(ticker_filter)} tickers")
            
            service = AIAnalysisService(session)
            results = await service.analyze_all_tickers(
                analysis_type="both", ticker_filter=ticker_filter
            )
            # ... rest unchanged
```

### Pattern 4: Pick Service Watchlist Filter
**What:** Add explicit watchlist filter to `generate_daily_picks()` signal query.
**Why needed:** Even though AI analysis is gated (so only watchlist tickers will have today's trading signals), an explicit filter is a safety net against stale data from pre-gating runs. [ASSUMED]

**Current signal query** (pick_service.py line 304-320):
```python
signal_query = (
    select(AIAnalysis.ticker_id, AIAnalysis.score, AIAnalysis.raw_response,
           Ticker.symbol, Ticker.name, Ticker.sector)
    .join(Ticker, Ticker.id == AIAnalysis.ticker_id)
    .where(
        AIAnalysis.analysis_type == AnalysisType.TRADING_SIGNAL,
        AIAnalysis.signal == "long",
        AIAnalysis.analysis_date == today,
        AIAnalysis.score > 0,
    )
)
```

**Two approaches:**

*Approach A: Filter at query level (recommended)*
Add a `.where(Ticker.symbol.in_(watchlist_symbols))` to the signal query.

```python
async def generate_daily_picks(self, watchlist_symbols: set[str] | None = None) -> dict:
    # ... existing code ...
    signal_query = (
        select(...)
        .join(Ticker, Ticker.id == AIAnalysis.ticker_id)
        .where(
            AIAnalysis.analysis_type == AnalysisType.TRADING_SIGNAL,
            AIAnalysis.signal == "long",
            AIAnalysis.analysis_date == today,
            AIAnalysis.score > 0,
        )
    )
    # Phase 53: Gate picks to watchlist only
    if watchlist_symbols is not None:
        signal_query = signal_query.where(Ticker.symbol.in_(watchlist_symbols))
    
    signal_rows = (await self.session.execute(signal_query)).all()
```

*Approach B: Use ticker_filter dict directly*
Accept `ticker_filter: dict[str, int] | None = None` like the AI analysis service, and filter with `AIAnalysis.ticker_id.in_(ticker_filter.values())`.

**Recommendation: Approach A** — accepts just the symbol set (lighter API), and the `IN` clause on `Ticker.symbol` is already indexed (unique constraint on `user_watchlist.symbol`). Approach B would also work.

### Jobs Requiring Modification

| Job Function | File | Line | Gemini API? | Gate? | Change |
|-------------|------|------|-------------|-------|--------|
| `daily_ai_analysis` | jobs.py | 289 | ✅ tech+fund | ✅ YES | Pass `ticker_filter` to `analyze_all_tickers("both")` |
| `daily_news_crawl` | jobs.py | 329 | ❌ HTTP scraping | ❌ NO | No Gemini calls — keep crawling all tickers |
| `daily_sentiment_analysis` | jobs.py | 363 | ✅ sentiment | ✅ YES | Pass `ticker_filter` to `analyze_all_tickers("sentiment")` |
| `daily_combined_analysis` | jobs.py | 403 | ✅ combined | ✅ YES | Pass `ticker_filter` to `analyze_all_tickers("combined")` |
| `daily_trading_signal_analysis` | jobs.py | 443 | ✅ trading signal | ✅ YES | Pass `ticker_filter` to `analyze_all_tickers("trading_signal")` |
| `daily_pick_generation` | jobs.py | 486 | ✅ explanations | ✅ YES | Pass watchlist symbols to `generate_daily_picks()` |

**News crawl decision:** `daily_news_crawl` calls CafeF HTTP scraping (no Gemini). Gating it would save ~5-10 minutes of crawl time but is NOT required by WL-01. The sentiment analysis that follows uses Gemini and IS gated. Recommendation: leave news crawl ungated to keep discovery data fresh. The speed gain from gating 4 Gemini jobs is already ~70%+ API reduction. [ASSUMED]

### Anti-Patterns to Avoid

- **Modifying `analyze_all_tickers()` signature:** Don't add watchlist logic inside the AI service. The service already accepts `ticker_filter` — the gating belongs in the jobs layer. Services should remain filter-agnostic.
- **Using `analyze_watchlisted_tickers()` method:** This existing method (line 326) has a bug — it JOINs on `UserWatchlist.ticker_id` which doesn't exist in the current model (model only has `symbol`). Don't use or fix this method; it was designed for the old Telegram/HNX/UPCOM flow. The `ticker_filter` approach is cleaner. [VERIFIED: model has no `ticker_id` column]
- **Raising on empty watchlist:** Don't raise exceptions for empty watchlist. This would break the scheduler chain via `EVENT_JOB_ERROR`. Return normally with "skipped" status so downstream jobs still execute (they'll also skip gracefully).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Ticker filtering | Custom WHERE clause per analysis type | `ticker_filter` parameter already on `analyze_all_tickers()` | 5 sub-methods already respect this param — zero analysis code changes needed |
| Watchlist→ticker_id resolution | Direct SQL queries in each job | Single `_get_watchlist_ticker_map()` helper | DRY — called from 5 job functions |
| Empty watchlist handling | Try/catch around each call | Guard clause with early return at job level | Consistent behavior across all gated jobs |

## Common Pitfalls

### Pitfall 1: Empty Watchlist Crash
**What goes wrong:** Empty watchlist causes `ticker_filter={}` which might produce `WHERE ticker_id IN ()` (empty IN clause) — syntax error in some SQL dialects.
**Why it happens:** SQLAlchemy handles empty IN gracefully (generates `WHERE 1!=1`), but the bigger issue is that Gemini would be called with 0 tickers, wasting a job execution cycle.
**How to avoid:** Check `if not ticker_filter:` before calling analysis service. Return "skipped" status.
**Warning signs:** Job completes with 0 success, 0 failed.

### Pitfall 2: Stale Trading Signals in Picks
**What goes wrong:** `generate_daily_picks()` finds trading signals from a pre-gating run (when all 400 tickers had signals) and generates picks for non-watchlist tickers.
**Why it happens:** Trading signals are stored in `ai_analysis` table with `analysis_date`. If the code was deployed mid-day after signals were already generated for all tickers, today's signals include non-watchlist tickers.
**How to avoid:** Explicitly filter the signal query in `generate_daily_picks()` by watchlist symbols. Don't rely solely on "only watchlist tickers will have signals."
**Warning signs:** Picks include tickers not in the watchlist.

### Pitfall 3: Watchlist Query Hit on Every Job
**What goes wrong:** The watchlist ticker map is fetched 5 times (once per gated job) during a single pipeline run, generating 5 identical DB queries.
**Why it happens:** Each job function creates its own session and runs independently.
**How to avoid:** This is acceptable — the query is trivial (JOIN of ~20 rows to ~400 rows, both indexed). The alternative (passing the map through the chain) would require modifying the APScheduler chaining mechanism, which is far more complex. [ASSUMED]
**Warning signs:** None — this is a non-issue for this scale.

### Pitfall 4: Breaking the Scheduler Chain
**What goes wrong:** A gated job raises an exception (instead of returning normally), causing `EVENT_JOB_ERROR` which prevents the next job from being chained.
**Why it happens:** Developer puts the watchlist guard in a `try` block that re-raises, or forgets to commit the session before returning.
**How to avoid:** The empty-watchlist guard must: (1) `await job_svc.complete(...)`, (2) `await session.commit()`, (3) `return` (not raise). This matches the existing `ValueError` catch pattern in the AI jobs (lines 317-320).
**Warning signs:** Downstream jobs never execute after a "skipped" job.

### Pitfall 5: Broken `analyze_watchlisted_tickers()` Method
**What goes wrong:** Someone calls the existing `analyze_watchlisted_tickers()` method which references `UserWatchlist.ticker_id` — a column that doesn't exist.
**Why it happens:** This method was written for an older watchlist model (likely with a ticker_id FK). The model was later simplified to symbol-only.
**How to avoid:** Don't use this method. Optionally fix or remove it in this phase to prevent future confusion.
**Warning signs:** `AttributeError: type object 'UserWatchlist' has no attribute 'ticker_id'` at runtime.

## Code Examples

### Example 1: Watchlist Ticker Map Helper

```python
# Source: Pattern derived from app/api/watchlist.py JOIN pattern (line 49)
# Location: backend/app/scheduler/jobs.py (new function)

async def _get_watchlist_ticker_map(session) -> dict[str, int]:
    """Resolve watchlist symbols to {symbol: ticker_id} for ticker_filter.
    
    JOINs UserWatchlist.symbol → Ticker.symbol → returns {symbol: Ticker.id}.
    Returns empty dict if watchlist is empty or no symbols match active tickers.
    """
    from app.models.user_watchlist import UserWatchlist
    from app.models.ticker import Ticker
    from sqlalchemy import select
    
    stmt = (
        select(Ticker.symbol, Ticker.id)
        .join(UserWatchlist, UserWatchlist.symbol == Ticker.symbol)
        .where(Ticker.is_active == True)
    )
    result = await session.execute(stmt)
    return {row[0]: row[1] for row in result.fetchall()}
```

### Example 2: Gated AI Analysis Job

```python
# Source: Modification of backend/app/scheduler/jobs.py daily_ai_analysis() (line 289)

async def daily_ai_analysis():
    """Run Gemini AI analysis for watchlist tickers only (Phase 53)."""
    logger.info("=== DAILY AI ANALYSIS START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_ai_analysis")
        try:
            # Phase 53: Watchlist gating
            ticker_filter = await _get_watchlist_ticker_map(session)
            if not ticker_filter:
                logger.warning("Watchlist empty — skipping daily AI analysis")
                await job_svc.complete(
                    execution, status="skipped",
                    result_summary={"reason": "empty_watchlist", "tickers": 0},
                )
                await session.commit()
                return
            
            logger.info(f"Watchlist gating: analyzing {len(ticker_filter)} tickers")
            from app.services.ai_analysis_service import AIAnalysisService
            service = AIAnalysisService(session)
            results = await service.analyze_all_tickers(
                analysis_type="both", ticker_filter=ticker_filter
            )
            # ... rest of existing result handling unchanged ...
```

### Example 3: Gated Pick Generation Job

```python
# Source: Modification of backend/app/scheduler/jobs.py daily_pick_generation() (line 486)

async def daily_pick_generation():
    """Generate daily stock picks from watchlist tickers only (Phase 53)."""
    logger.info("=== DAILY PICK GENERATION START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_pick_generation")
        try:
            # Phase 53: Get watchlist symbols for pick filtering
            ticker_filter = await _get_watchlist_ticker_map(session)
            if not ticker_filter:
                logger.warning("Watchlist empty — skipping daily pick generation")
                await job_svc.complete(
                    execution, status="skipped",
                    result_summary={"reason": "empty_watchlist", "picked": 0, "almost": 0},
                )
                await session.commit()
                return
            
            watchlist_symbols = set(ticker_filter.keys())
            logger.info(f"Watchlist gating: picking from {len(watchlist_symbols)} tickers")
            
            from app.services.pick_service import PickService
            service = PickService(session)
            result = await service.generate_daily_picks(watchlist_symbols=watchlist_symbols)
            # ... rest unchanged ...
```

### Example 4: Pick Service Signal Query Filter

```python
# Source: Modification of backend/app/services/pick_service.py generate_daily_picks() (line 285)

async def generate_daily_picks(self, watchlist_symbols: set[str] | None = None) -> dict:
    """Generate daily picks, optionally restricted to watchlist symbols."""
    today = date.today()
    profile = await self.get_or_create_profile()
    capital = int(profile.capital)

    signal_query = (
        select(
            AIAnalysis.ticker_id, AIAnalysis.score, AIAnalysis.raw_response,
            Ticker.symbol, Ticker.name, Ticker.sector,
        )
        .join(Ticker, Ticker.id == AIAnalysis.ticker_id)
        .where(
            AIAnalysis.analysis_type == AnalysisType.TRADING_SIGNAL,
            AIAnalysis.signal == "long",
            AIAnalysis.analysis_date == today,
            AIAnalysis.score > 0,
        )
    )
    # Phase 53: Restrict picks to watchlist tickers
    if watchlist_symbols is not None:
        signal_query = signal_query.where(Ticker.symbol.in_(watchlist_symbols))
    
    signal_rows = (await self.session.execute(signal_query)).all()
    # ... rest unchanged ...
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | No pyproject.toml — uses defaults |
| Quick run command | `cd backend && python -m pytest tests/ -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WL-01 | AI analysis jobs pass watchlist ticker_filter | unit | `python -m pytest tests/test_watchlist_gating.py::TestAIAnalysisGating -x` | ❌ Wave 0 |
| WL-01 | Empty watchlist skips AI analysis gracefully | unit | `python -m pytest tests/test_watchlist_gating.py::TestEmptyWatchlistGuard -x` | ❌ Wave 0 |
| WL-02 | Pick generation filters by watchlist symbols | unit | `python -m pytest tests/test_watchlist_gating.py::TestPickServiceGating -x` | ❌ Wave 0 |
| WL-02 | Empty watchlist skips pick generation | unit | `python -m pytest tests/test_watchlist_gating.py::TestEmptyWatchlistGuard -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_watchlist_gating.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_watchlist_gating.py` — covers WL-01, WL-02, empty watchlist edge cases
- [ ] Test helper function `_get_watchlist_ticker_map` returns correct dict and handles empty case

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | News crawl should remain ungated (not required by WL-01, and doesn't call Gemini) | Architecture Patterns - Jobs table | Low — if user wants news gated too, it's trivial to add later |
| A2 | Pick service explicit filter is needed as safety net against stale signals | Pitfall 2 | Low — worst case, an extra WHERE clause that has no effect if signals are already gated |
| A3 | 5 watchlist queries per pipeline run is acceptable performance | Pitfall 3 | Very low — query is trivial (~20 rows JOIN ~400 rows on indexed columns) |

## Open Questions

1. **Should news crawl be gated too?**
   - What we know: News crawl doesn't use Gemini, but takes time crawling all ~400 tickers
   - What's unclear: Whether the user wants news data only for watchlist tickers or all tickers (for potential discovery use)
   - Recommendation: Leave ungated. If speed is needed later, the same `ticker_filter` pattern can be applied to CafeF crawler

2. **Should `analyze_watchlisted_tickers()` be fixed or removed?**
   - What we know: This method (ai_analysis_service.py line 326) has a broken JOIN on `UserWatchlist.ticker_id` which doesn't exist
   - What's unclear: Whether any code path still calls it (grep shows no callers outside its definition)
   - Recommendation: Remove or fix in this phase to prevent confusion. It was designed for the Telegram/HNX/UPCOM flow that no longer exists

## Sources

### Primary (HIGH confidence)
- `backend/app/services/ai_analysis_service.py` — verified `ticker_filter` param on all 5 analysis methods
- `backend/app/models/user_watchlist.py` — verified model has `symbol` only (no `ticker_id`)
- `backend/app/api/watchlist.py` — verified correct JOIN pattern: `UserWatchlist.symbol == Ticker.symbol`
- `backend/app/scheduler/jobs.py` — verified 4 Gemini-calling jobs + pick generation job structure
- `backend/app/scheduler/manager.py` — verified chain continues on normal return, breaks only on exception
- `backend/app/services/pick_service.py` — verified signal query has no existing ticker filter

### Secondary (MEDIUM confidence)
- `backend/app/services/ai_analysis_service.py:326` — identified broken `analyze_watchlisted_tickers()` method with invalid `UserWatchlist.ticker_id` reference

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, all existing patterns verified in codebase
- Architecture: HIGH — `ticker_filter` param already exists and is battle-tested, change is pure plumbing
- Pitfalls: HIGH — all identified from direct code inspection of actual execution paths

**Research date:** 2025-07-18
**Valid until:** 2025-08-18 (stable — no external dependencies)

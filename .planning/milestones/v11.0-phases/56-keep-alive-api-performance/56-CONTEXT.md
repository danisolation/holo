# Phase 56: Keep-Alive & API Performance - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure/performance phase — root causes identified in research)

<domain>
## Phase Boundary

Eliminate the ~3 minute production load time caused by two compounding issues:
1. Render.com free tier cold start (~30-60s sleep after 15 min inactivity)
2. Unfiltered `ROW_NUMBER()` scan over entire `daily_prices` table (~200K+ rows)

Deliver: external keep-alive ping setup, query optimization with date filter, and in-memory TTL caching for frequently-accessed endpoints.

</domain>

<decisions>
## Implementation Decisions

### Query Optimization
- Add `WHERE date >= CURRENT_DATE - INTERVAL '7 days'` filter to the ranked subquery in `tickers.py:176-188` to reduce scan from 200K+ to ~2K rows
- Keep existing ROW_NUMBER() window function pattern — just bound the date range
- Add composite index on `(ticker_id, date DESC)` via Alembic migration if not already present

### Caching Strategy
- Use `cachetools.TTLCache` with 60-second TTL for market overview endpoint
- Cache key: combination of query parameters (exchange, sort, order, top)
- Cache invalidated by TTL only — no manual invalidation needed for personal use
- Install `cachetools>=5.5,<6` as new dependency

### Keep-Alive
- Document UptimeRobot/cron-job.org setup (external, zero code changes)
- Ensure `/` or `/api/health` endpoint is lightweight for ping checks
- No in-process keep-alive (anti-pattern — can't keep itself awake)

### the agent's Discretion
- Exact cache implementation pattern (decorator vs inline)
- Whether to cache additional endpoints beyond market overview
- Alembic migration numbering

</decisions>

<code_context>
## Existing Code Insights

### Root Cause Files
- `backend/app/api/tickers.py:150-230` — market_overview endpoint with unfiltered ROW_NUMBER()
- `backend/app/database.py` — pool_size=5, max_overflow=3 (8 total connections)
- `backend/app/api/health.py` — health endpoint exists, suitable for keep-alive ping

### Established Patterns
- SQLAlchemy 2.0 async with `async_session()` context manager
- Alembic migrations in `backend/alembic/versions/`
- FastAPI dependency injection for DB sessions

### Integration Points
- `requirements.txt` — add cachetools
- New Alembic migration for index
- tickers.py market_overview function — primary optimization target

</code_context>

<specifics>
## Specific Ideas

- Research identified the exact query bottleneck: `tickers.py:176-188` ranked subquery scans all daily_prices without date filter
- cachetools is the only new package needed — no Redis, no infrastructure changes
- UptimeRobot free tier pings every 5 min — sufficient to prevent Render sleep

</specifics>

<deferred>
## Deferred Ideas

- WebSocket connection pooling optimization (not needed for v11.0)
- PostgreSQL materialized views for market overview (overkill for 400 tickers)
- Paid Render tier upgrade (external pinger solves it for free)

</deferred>

# Domain Pitfalls — v11.0 UX & Reliability Overhaul

**Domain:** UX & Reliability improvements on free-tier FastAPI + PostgreSQL + Gemini stock platform
**Researched:** 2025-07-27
**Overall confidence:** HIGH (pitfalls derived from direct codebase analysis + known platform constraints)

---

## Critical Pitfalls

Mistakes that cause outages, data loss, or require rework.

### Pitfall 1: Keep-Alive Ping Consuming the App's Own Connection Pool

**What goes wrong:** A naive keep-alive (e.g., APScheduler job hitting `/` every 10 min) uses the same in-process event loop AND database pool. If the keep-alive endpoint touches the DB (health check, not just `{"status": "ok"}`), it competes for the pool_size=5 connections alongside scheduled jobs, API requests, and WebSocket polling. During the daily pipeline chain (price crawl → indicators → discovery → AI → news → sentiment → combined → trading signals → picks → outcome check — **10 chained jobs**), every connection matters.

**Why it happens:** Developers think "just add a ping" without considering that in-process APScheduler means ping jobs share resources with everything else. Render free tier also has 750 hours/month — a ping every 5 min keeps the service running 24/7 = 720 hours, leaving only 30 hours of headroom.

**Consequences:**
- Connection pool exhaustion during peak pipeline runs causing API request timeouts
- Exceeding 750 free hours causes service to stop for the rest of the month
- If keep-alive pings a heavy endpoint (like `/api/health`), it triggers DB queries every N minutes forever

**Prevention:**
- Keep-alive should ping the root `/` endpoint which returns `{"status": "ok"}` with **zero DB access** (already exists in `main.py`)
- Use an EXTERNAL pinger (UptimeRobot, cron-job.org, or GitHub Action cron) — NOT an in-process APScheduler job. External pinger doesn't consume your app's resources
- Calculate hours: 24h x 31 days = 744 hours. Ping interval of 14 min keeps it just under. But consider: ping only during 8:00-22:00 ICT = ~420 hours/month, well within limits
- Never let the keep-alive endpoint query the database

**Detection:** Monitor Render dashboard for hours consumed. If approaching 700 hours by mid-month, you're over-pinging.

**Confidence:** HIGH — derived from render.yaml (`plan: free`), database.py (`pool_size=5`), and main.py root endpoint.

---

### Pitfall 2: Intraday AI Analysis Blowing Through Gemini Rate Limits

**What goes wrong:** Moving from EOD-only to intraday AI analysis multiplies Gemini API calls by 3-4x. With 15 RPM free tier, batch_size=8, and 4s delay between batches, a single full pipeline run for ~10-20 watchlist tickers takes ~3-8 batches across 5 analysis types (technical, fundamental, sentiment, combined, trading signals). That's potentially 40+ API calls per run. Three runs per day = 120+ calls, competing with the existing daily chain.

**Why it happens:** The existing pipeline is designed for one full run per day. Adding intraday runs without reducing scope means the same heavy pipeline runs multiple times. The `_gemini_lock` serializes access but doesn't prevent rate limit exhaustion.

**Consequences:**
- 429 rate limit errors from Gemini with exponential backoff making pipeline take 30+ minutes
- Intraday run collides with daily chain if timing overlaps (e.g., 14:00 intraday vs 15:30 daily)
- Dead letter queue fills with "rate limit exceeded" failures
- Circuit breaker trips blocking all Gemini calls for 2 minutes

**Prevention:**
- Intraday runs should ONLY refresh `combined` analysis, NOT re-run all 5 types. Fundamental doesn't change intraday. Sentiment only when new news arrives
- Scope intraday to watchlist tickers only (already gated in v10.0)
- Budget: 10 watchlist tickers x 1 combined call = 2 batches = 2 RPM. That's safe
- Add a "last_analyzed" check: skip tickers analyzed within the last 2 hours
- NEVER run full 5-type pipeline intraday

**Detection:** Check `gemini_usage` table for calls-per-hour trending up.

**Confidence:** HIGH — config.py shows exact batch/delay settings; rate limit is 15 RPM per PROJECT.md.

---

### Pitfall 3: Connection Pool Exhaustion from Concurrent Jobs + API + WebSocket

**What goes wrong:** The system has exactly 8 DB connections (pool_size=5 + max_overflow=3). Currently running simultaneously: real-time price polling (every 30s), heartbeat (every 15s), API requests, AND the daily pipeline chain. Adding intraday AI analysis adds more concurrent DB access. If all 8 are in use, new requests block waiting for a connection.

**Why it happens:** Every scheduled job creates its own session. WebSocket polling runs on an interval timer in parallel with everything else. The pool has no priority system.

**Consequences:**
- `TimeoutError: QueuePool limit of 5 overflow 3 reached` in logs
- API endpoints return 500 errors during pipeline runs
- WebSocket disconnects when it can't get a connection

**Prevention:**
- Add `pool_recycle=300` to prevent Aiven from closing idle connections
- Add `pool_timeout=10` explicitly (default 30s is too long for API requests)
- During pipeline runs, pause WebSocket polling (market is closed at 15:30 when pipeline runs)
- **Do NOT increase pool_size** — Aiven free tier has ~20-25 max connections total

**Detection:** Monitor `/api/health/db-pool` during pipeline runs. Watch for overflow approaching max.

**Confidence:** HIGH — database.py shows exact pool config; scheduler/manager.py shows concurrent interval jobs.

---

### Pitfall 4: Ticker Search Only Shows First 50 of 400+ Tickers

**What goes wrong:** `ticker-search.tsx` line 54: `tickers?.slice(0, 50).map(...)` renders only 50 tickers. The API defaults to `limit=100`. cmdk's `shouldFilter={true}` filters **rendered** items, not the full dataset. Searching for ticker #300 alphabetically returns "not found" even though it exists.

**Why it happens:** Performance cap that prevents search from working. The API also caps at 100, so even removing the slice won't show all 400.

**Consequences:**
- Users can't find ~300+ tickers via search
- Reported as "search is broken" when it's data truncation

**Prevention:**
- Remove `.slice(0, 50)` — cmdk handles filtering fine
- Increase API `limit` to 500 for the ticker list fetch (400 items x ~100 bytes = 40KB — trivially small)
- Cache with `staleTime: 5 * 60 * 1000` (already set), let cmdk filter locally
- Alternative: add server-side `/api/tickers/search?q=VNM` with `ILIKE` on symbol and name

**Detection:** Test by searching for tickers starting with letters T-Z (beyond position 50).

**Confidence:** HIGH — directly observed in `ticker-search.tsx:54` and `tickers.py:57`.

---

## Moderate Pitfalls

### Pitfall 5: Cold Start Triggers APScheduler Misfire Storm

**What goes wrong:** When Render wakes from sleep, APScheduler recalculates run times. Weekly jobs (`weekly_behavior_analysis`, `weekly_financial_crawl`, `weekly_ticker_refresh`) could all misfire simultaneously if service was asleep during their Sat/Sun scheduled times = 3 concurrent DB-heavy operations.

**Why it happens:** APScheduler 3.x in-process scheduler doesn't persist job state. Jobs with `misfire_grace_time=3600` fire immediately if their scheduled time was within the last hour.

**Prevention:**
- Daily chain is safe — only the trigger job fires on misfire; rest chain sequentially
- IntervalTrigger jobs recalculate from "now" — no storm
- For weekly jobs: consider `misfire_grace_time=None` (coalesce) — skip if missed
- Add startup guard: check current time before running misfired jobs

**Detection:** Check logs after wake for multiple "Running job..." entries in the same second.

**Confidence:** HIGH — manager.py shows all misfire_grace_time values.

---

### Pitfall 6: Market Overview Query Scanning Entire daily_prices Table

**What goes wrong:** The `market-overview` endpoint uses `ROW_NUMBER() OVER (PARTITION BY ticker_id ORDER BY date DESC)` across the ENTIRE `daily_prices` table. With ~400 tickers x ~500 days = 200,000+ rows scanned, this is the likely cause of the 3-minute load time on Aiven free tier.

**Why it happens:** No date filter on the window function. PostgreSQL must sort all rows per partition.

**Consequences:**
- First page load takes 3+ minutes (the reported performance issue)
- Connection held for entire duration adding pool pressure
- Gets worse over time as data grows

**Prevention:**
- Add `WHERE date >= CURRENT_DATE - INTERVAL '7 days'` to ranked subquery — ~2,800 rows instead of 200,000+
- Create `latest_prices` cache table updated by daily pipeline — O(1) lookup
- Add composite index: `(ticker_id, date DESC)` for index-only scans
- In-memory TTL cache (60s) for the result — single-user app

**Detection:** `EXPLAIN ANALYZE` the query. `Seq Scan on daily_prices` = scanning everything.

**Confidence:** HIGH — tickers.py:176-228 shows the query; no date filter exists.

---

### Pitfall 7: Keep-Alive Creating Self-Referential Dependency Loop

**What goes wrong:** An APScheduler interval job pinging the app's own endpoint creates circular dependency: app must be awake to run the scheduler that keeps it awake. When Render sleeps the process, the scheduler stops too.

**Prevention:**
- Keep-alive MUST be external: UptimeRobot (free, 5-min intervals), cron-job.org, GitHub Actions cron, or Vercel cron (frontend already on Vercel with `vercel.json`)
- Vercel cron is easiest — add a cron hitting the Render backend URL every 10 minutes

**Detection:** Service still sleeps despite "having keep-alive" = pinger is internal.

**Confidence:** HIGH — fundamental Render free tier constraint.

---

### Pitfall 8: Intraday Analysis Running When Market Is Closed

**What goes wrong:** Fixed-interval intraday AI analysis runs on weekends, holidays, and after market close. Data hasn't changed but Gemini API calls and DB connections are consumed.

**Prevention:**
- Use `CronTrigger(day_of_week="mon-fri", hour="9,11,13", timezone=settings.timezone)`
- Skip analysis if latest price timestamp hasn't changed since last analysis
- Maintain simple Vietnamese holiday list (Tet, April 30, May 1, September 2, January 1)

**Detection:** Check `gemini_usage` for weekend/holiday API calls.

**Confidence:** HIGH — existing CronTrigger patterns in scheduler/manager.py to follow.

---

### Pitfall 9: UX Onboarding Overcomplicating a Single-User App

**What goes wrong:** Building full onboarding (tooltips, wizards, feature tours) for a personal single-user app.

**Prevention:**
- Focus on: clear homepage layout, sensible defaults, empty states with actionable CTAs
- Show immediately useful data (watchlist summary, today's signals, market status)
- Skip: tooltip tours, multi-step wizards, progress bars, feature flags

**Detection:** If you're building auth/user-state tracking for onboarding, you've gone too far.

**Confidence:** HIGH — PROJECT.md: "single-user personal app."

---

## Minor Pitfalls

### Pitfall 10: cachetools TTLCache Not Async-Safe

**What goes wrong:** `cachetools.TTLCache` isn't async-safe. Interleaving between check and write possible if `await` occurs between them.

**Prevention:** Use sync check then async DB then sync write pattern. `asyncio.Lock()` if paranoid. Single-user makes races extremely unlikely.

**Confidence:** MEDIUM.

### Pitfall 11: Adding Redis/External Cache for a Single-User App

**What goes wrong:** Redis adds a service to manage and a failure point. Render free tier doesn't include Redis.

**Prevention:** In-memory `cachetools.TTLCache`. Single-user = no cache invalidation complexity.

**Confidence:** HIGH.

### Pitfall 12: SSL Patches Interfering with New HTTP Clients

**What goes wrong:** `config.py` globally disables SSL verification. New HTTP clients inherit this behavior silently.

**Prevention:** Keep-alive should be external (Pitfall 7). Be aware of the patch if adding internal HTTP clients.

**Confidence:** MEDIUM.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Severity | Mitigation |
|-------------|---------------|----------|------------|
| Keep-alive service | Internal pinger (7) + hour budget (1) | CRITICAL | External pinger, limit to market hours |
| Ticker search fix | Only fixing slice without API limit (4) | CRITICAL | Remove `.slice(0,50)` AND increase API limit to 500+ |
| Intraday AI analysis | Full pipeline re-run (2) + weekend runs (8) | CRITICAL | Watchlist-only combined, CronTrigger with market hours |
| UX/Onboarding | Over-engineering for single user (9) | MODERATE | Homepage layout + empty states, skip tutorials |
| API performance | Market overview query bottleneck (6) | CRITICAL | Date filter + in-memory TTL cache |
| All phases | Connection pool exhaustion (3) | CRITICAL | Audit concurrent DB usage, pool_timeout=10 |

## Integration Risk Matrix

| Combination | Risk | Why |
|---|---|---|
| Keep-alive + Intraday AI | Pool exhaustion | Both add concurrent DB load |
| Intraday AI + API optimization | Conflicting freshness | Caching stale data vs. wanting fresh analysis |
| Search fix + API performance | False victory | 400 tickers load but API still slow = different broken |
| Keep-alive + Cold start | Misfire on failure | If pinger fails once, next real request triggers cold start + misfires |

## Recommended Implementation Order (Pitfall-Informed)

1. **API Performance (Pitfall 6)** — Fix root cause. Everything feels broken with 3-min loads
2. **Ticker Search (Pitfall 4)** — Surgical fix, low risk, immediate UX win
3. **Keep-Alive (Pitfalls 1, 7)** — External pinger, 10 min setup, prevents cold starts
4. **Intraday AI (Pitfalls 2, 3, 8)** — Highest complexity, needs stable base from 1-3
5. **UX/Onboarding (Pitfall 9)** — Lowest risk, iterate freely once platform is stable

## Sources

- Direct codebase analysis: `main.py`, `database.py`, `config.py`, `scheduler/manager.py`, `ticker-search.tsx`, `tickers.py`, `watchlist.py`, `ai_analysis_service.py`, `jobs.py`
- Render.com free tier: 750 hours/month, 15-min sleep — per `render.yaml` and PROJECT.md
- Gemini free tier: 15 RPM — per `config.py` and PROJECT.md
- Aiven PostgreSQL: pool_size=5, max_overflow=3 — per `database.py`
- APScheduler 3.x misfire behavior — well-documented upstream

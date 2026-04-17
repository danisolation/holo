# Project Research Summary

**Project:** Holo — Stock Intelligence Platform
**Domain:** VN Stock Intelligence Platform — v2.0 Multi-Market, Real-Time, Portfolio & Health Expansion
**Researched:** 2026-04-17
**Confidence:** HIGH

## Executive Summary

Holo v2.0 is a feature expansion of a well-structured monolith (FastAPI + PostgreSQL + Next.js) that already has strong foundations from v1.0/v1.1. The critical finding across all research is that **the existing stack covers every v2.0 backend feature with zero new Python packages** — only 3 frontend packages are needed (react-day-picker, papaparse, @types/papaparse). vnstock 3.5.1 already supports HNX/UPCOM exchanges, FastAPI already has WebSocket support via Starlette, and google-genai already exposes usage metadata. This is purely an engineering expansion, not a technology pivot. The codebase's existing patterns (async sessions, circuit breakers, job chaining, FIFO lot tracking) are extensible to all v2.0 features.

The recommended approach is a 5-phase build order driven by dependency chains: (1) Multi-market foundation first — expanding from 400 to ~950 active tickers is prerequisite for everything else; (2) Portfolio enhancements — trade edit/delete with FIFO-safe lot replay, dividend tracking, performance/allocation charts; (3) Corporate action enhancements — rights issues, ex-date alerts, event calendar, adjusted price toggle; (4) Health & monitoring — Gemini usage tracking, pipeline timeline, Telegram health notifications; (5) WebSocket real-time streaming last — highest complexity, lowest dependency on other features. This order respects both data dependencies and risk gradients.

The top risks are: **crawl pipeline explosion** (3.75× ticker growth without architectural redesign will starve DB pool and blow the 30-minute pipeline window), **FIFO lot corruption** on trade edit/delete (current append-only model has no audit trail for lot consumption reversals), and **WebSocket complexity being underestimated** (no free VN market WebSocket exists — "real-time" is actually 30-second polling dressed as push). All three have concrete prevention strategies documented in PITFALLS.md and must be addressed in the phase where they first appear, not deferred.

## Key Findings

### Recommended Stack

The v2.0 stack is the v1.1 stack with 3 frontend additions. Zero backend changes to `requirements.txt`. This restraint is the strongest signal from research — every feature was validated against existing dependencies before considering alternatives.

**Core technologies (unchanged, extended use):**
- **vnstock 3.5.1**: Multi-market crawling — `Listing.symbols_by_exchange()` returns all exchanges; `Quote(symbol)` is exchange-agnostic for OHLCV; supports 1m/5m/15m/30m intraday intervals via VCI
- **FastAPI + Starlette**: WebSocket server — native `@app.websocket()` decorator, zero additional deps; `python-multipart` already installed for file uploads
- **google-genai 1.73**: Usage tracking — `response.usage_metadata` returns `prompt_token_count`, `candidates_token_count`, `total_token_count`
- **APScheduler 3.11**: New interval trigger for market-hours realtime polling (30s); new cron for health checks (16:30) and ex-date alerts
- **SQLAlchemy 2.0 + Alembic 1.18**: 2 new tables (`dividend_incomes`, `api_usage`), 3-4 column additions, 2 new indexes
- **Recharts 3.x**: Performance area chart, allocation pie chart, pipeline timeline bar chart — all already installed
- **Python stdlib csv**: Backend broker CSV parsing — no pandas needed

**New frontend dependencies (3 total):**
- **react-day-picker ^9.14.0**: Calendar component via shadcn's `<Calendar>` — for corporate event calendar view
- **papaparse ^5.5.3**: Client-side CSV parsing for broker import preview with column mapping
- **@types/papaparse ^5.5.2**: TypeScript definitions for papaparse

**Explicitly rejected:** Redis/message broker, Celery, Socket.IO, FullCalendar, D3.js, pandas for CSV, react-hook-form (add only when needed), separate crawlers per exchange, portfolio snapshot tables.

### Expected Features

**Must have (table stakes):**
- Exchange filter on dashboard (MKT-02) — 1700 tickers unfiltered is unusable
- Trade edit/delete (PORT-11) — no edit for manual entry errors = user frustration
- Adjusted/raw price toggle (CORP-09) — platform computes `adjusted_close` but never shows it
- Telegram health alerts on errors (HEALTH-10) — stale data silently degrades without proactive alerting
- Ex-date alerts for held positions (CORP-07) — platform tracks events + portfolio but doesn't connect them

**Should have (differentiators):**
- Multi-market HNX/UPCOM crawling (MKT-01) — ~1300 additional tickers; covers entire VN stock market
- WebSocket real-time streaming (RT-01/02) — intraday visibility during market hours via polling-to-push
- Dividend income tracking (PORT-08) — actual cash returns, not just capital gains
- Portfolio performance chart (PORT-09) — visual P&L over time; most compelling portfolio view
- Broker CSV import (PORT-12) — bulk import from VN broker exports (SSI, VNDirect, TCBS, VCBS)
- Gemini API usage tracking (HEALTH-08) — free-tier visibility to avoid surprise throttling at 3× ticker count
- Pipeline execution timeline (HEALTH-09) — Gantt-style visualization of daily job chain

**Defer to v3+:**
- Stock dividend lot adjustment (STOCK_DIVIDEND increasing lot share count) — complex FIFO impact
- Historical WebSocket data replay — low value for personal use
- More than 4 broker CSV formats — start with 1, expand later
- VN-Index benchmark overlay on performance chart — nice-to-have
- Automatic rights issue exercise recording — requires user intent modeling
- Real-time portfolio P&L recalculation from WebSocket prices — complexity/value ratio too high

### Architecture Approach

v2.0 features integrate into the existing monolith without architectural changes. The codebase has clear separation (crawlers → services → API → frontend) and the two genuinely new architectural elements are: (1) a WebSocket endpoint in FastAPI with an in-memory `ConnectionManager` for price broadcasting, and (2) a CSV file upload/parsing pipeline. Everything else extends existing service methods, adds new models, or chains new jobs onto the existing scheduler pipeline. The job chain extends from `daily_price_crawl → [indicators → AI → ...]` to include `→ [corporate_action_check → dividend_income_compute → ex_date_alerts]` plus new standalone jobs: `daily_health_check` (cron 16:30) and `realtime_price_poll` (interval 30s, market hours only).

**Major components:**
1. **Ticker/Crawl Pipeline** — Extended to loop over HOSE/HNX/UPCOM; split per-exchange jobs for parallelism; cap at ~950 active tickers
2. **Portfolio Service** — Extended with `sell_allocations` audit table, lot replay, dividend income computation, performance history, CSV import service
3. **WebSocket Layer** — New `realtime_service.py` + `api/websocket.py`; in-memory `ConnectionManager`; APScheduler interval trigger polls vnstock every 30s during market hours for watchlist tickers only
4. **Health/Monitoring** — New `api_usage` model + service; pipeline timeline from `job_executions` with `pipeline_run_id`; Telegram notification aggregation with cooldowns
5. **Corporate Actions** — Extended with `RIGHTS_ISSUE` type, alert-driven (not auto-exercise), ex-date alert scheduler, event calendar API with indexed queries

### Critical Pitfalls

1. **Crawl pipeline explosion (Pitfall 1)** — 3.75× ticker growth = ~87 min daily crawl; DB pool starvation; pipeline won't finish before daily summary. **Avoid by:** Split crawl jobs per exchange, cap at top N per exchange (~950 total), per-exchange circuit breakers, session-per-batch (not per-crawl), push daily summary to 17:00+.

2. **FIFO lot corruption on trade edit/delete (Pitfall 2)** — Current append-only model has no `sell_allocations` audit trail; editing consumed BUY trades corrupts all downstream P&L. **Avoid by:** Add `sell_allocations` table recording lot consumption, implement `replay_lots(ticker_id)` function, soft-delete trades, validate after replay.

3. **WebSocket misconception (Pitfall 3)** — No free VN market WebSocket exists; "real-time" is 30-second HTTP polling via vnstock wrapped in WS push. Event loop contention with APScheduler + Telegram polling. **Avoid by:** Watchlist-only scope (max 10-20 tickers), separate market-hours poller from EOD pipeline, explicit thread pool cap, heartbeat with timeout for connection cleanup.

4. **Dividend tracking on historical holdings (Pitfall 4)** — `Lot.remaining_quantity` is current state only; can't query "what did I hold on date X?" **Avoid by:** Build `get_holdings_at_date()` function replaying trades to target date; separate `dividend_payments` table (NOT in trades table); never model dividends as trades.

5. **Broker CSV format chaos (Pitfall 5)** — VN brokers have wildly different date formats, number formats, column names, side encoding, symbol variations. **Avoid by:** Start with ONE broker, per-broker parser pattern, dry-run preview before commit, import batch tracking for undo, symbol normalization (strip .HM/.VN suffixes).

## Implications for Roadmap

Based on combined research, suggested 5-phase structure:

### Phase 1: Multi-Market Foundation
**Rationale:** Expanding the ticker universe from 400 to ~950 is the prerequisite for everything downstream — exchange filters, WebSocket scope, AI budget management, and CSV import all depend on multi-exchange data being available. This phase must redesign the crawl pipeline architecture BEFORE adding exchanges.
**Delivers:** HNX/UPCOM tickers in database, exchange filter on all API endpoints and dashboard UI, per-exchange crawl jobs with independent circuit breakers, exchange-indexed queries.
**Addresses:** MKT-01 (Multi-market crawling), MKT-02 (Exchange filter UI)
**Avoids:** Pitfall 1 (crawl time explosion) — split crawl jobs per exchange, cap UPCOM at top 200-300; Pitfall 11 (backend filtering needed) — add SQL-level exchange filter; Pitfall 16 (vnstock compatibility) — validate HNX/UPCOM data source first.
**Migration:** Add index on `tickers.exchange` column.

### Phase 2: Portfolio Enhancements
**Rationale:** Portfolio features are the highest user-facing value and have the most intricate data model changes. Trade edit/delete requires `sell_allocations` audit infrastructure that CSV import and dividend tracking both depend on. Build the FIFO replay foundation first, then layer features on top.
**Delivers:** Trade edit/delete with FIFO-safe lot replay, portfolio allocation pie chart (by ticker/sector), portfolio performance line chart, broker CSV import (1 broker format initially), dividend income tracking with historical holdings computation.
**Addresses:** PORT-11 (Trade edit/delete), PORT-10 (Allocation chart), PORT-09 (Performance chart), PORT-12 (CSV import), PORT-08 (Dividend tracking)
**Avoids:** Pitfall 2 (FIFO corruption) — build sell_allocations + replay before edit/delete; Pitfall 4 (record-date holdings) — build get_holdings_at_date() before dividend logic; Pitfall 5 (CSV chaos) — one broker format, dry-run preview, batch tracking; Pitfall 12 (retroactive computation) — compute on-demand for single user; Pitfall 13 (missing sector) — refactor holdings query to JOIN Ticker.
**Migration:** Add `sell_allocations` table, `dividend_incomes` table, `trades.notes` column, `trades.source` column.

### Phase 3: Corporate Actions Enhancements
**Rationale:** Independent of multi-market data — builds on existing v1.1 corporate action infrastructure. Low-to-medium complexity features that connect existing data in new ways (events → portfolio → alerts).
**Delivers:** Rights issue tracking (alert-driven, no auto-exercise), ex-date Telegram alerts for held positions, event calendar view (list grouped by week), adjusted/raw price toggle on candlestick chart.
**Addresses:** CORP-06 (Rights issues), CORP-07 (Ex-date alerts), CORP-08 (Event calendar), CORP-09 (Adjusted/raw toggle)
**Avoids:** Pitfall 6 (rights exercise modeling) — keep simple: track event + alert, user manually /buy; Pitfall 7 (indicator mismatch) — hide indicators in adjusted mode; Pitfall 14 (late ex-date alerts) — morning alert check + post-crawl check; Pitfall 15 (unindexed ex_date) — add index in migration.
**Migration:** Add `exercise_price`, `subscription_deadline` to `corporate_events`; add `RIGHTS_ISSUE` event type; add index on `corporate_events.ex_date`.

### Phase 4: Health & Monitoring Enhancements
**Rationale:** With 3× ticker count and extended pipeline, observability becomes critical. Gemini usage tracking prevents surprise throttling. Pipeline timeline provides debugging visibility. Health notifications close the loop on proactive monitoring. Best built after the expanded system is running to observe real behavior.
**Delivers:** Gemini API usage tracking dashboard (tokens, RPM, daily budget), pipeline execution timeline (Gantt-style), Telegram health notifications with dedup and cooldowns.
**Addresses:** HEALTH-08 (Gemini usage tracking), HEALTH-09 (Pipeline timeline), HEALTH-10 (Telegram health alerts)
**Avoids:** Pitfall 8 (no pipeline run ID) — add `pipeline_run_id` to job_executions schema, pass through chain; Pitfall 9 (notification spam) — cooldown per category, aggregate pipeline failures, priority levels; Pitfall 10 (request counting vs token tracking) — intercept `usage_metadata` from Gemini SDK responses.
**Migration:** Add `api_usage` table; add `pipeline_run_id` column to `job_executions`.

### Phase 5: Real-Time WebSocket Streaming
**Rationale:** Highest complexity, most architecturally novel, lowest dependency on other v2.0 features. Build last when the rest of the system is stable. This is the only feature introducing a fundamentally new data flow (polling → in-memory broadcast → persistent connections).
**Delivers:** FastAPI WebSocket endpoint for price streaming, APScheduler market-hours polling (30s interval), frontend WebSocket client with auto-reconnect, lightweight-charts real-time candle updates.
**Addresses:** RT-01 (WebSocket server), RT-02 (Frontend real-time chart)
**Avoids:** Pitfall 3 (event loop contention) — watchlist-only scope (max 10-20 tickers), separate poller from EOD pipeline, thread pool cap, heartbeat cleanup; VCI rate limit — max 20 req/min guest, register for 60 RPM key.
**Migration:** Add `intraday_prices` table (or use in-memory only).

### Phase Ordering Rationale

- **Dependency chain:** MKT-01 is foundational → Portfolio features need all tickers → Corp actions are independent but benefit from multi-market → Health monitors the expanded system → WebSocket is standalone
- **Risk gradient:** Phase 1 has moderate risk (vnstock compatibility unknown for HNX/UPCOM). Phase 2 has highest data-model risk (FIFO replay). Phase 5 has highest architectural risk (new data flow pattern). Ordering by ascending architectural novelty.
- **Value delivery:** Each phase delivers usable features independently. Phase 1 alone makes the dashboard cover all VN exchanges. Phase 2 alone makes portfolio management robust.
- **Pitfall avoidance:** The most dangerous compound effect (Pitfall 1 + 3 + DB pool exhaustion) is mitigated by never building multi-market and WebSocket in the same phase.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Multi-Market):** Needs live validation that vnstock VCI source returns data for HNX/UPCOM tickers before committing to architecture. Test `Quote("PVS").history()` and `Quote("BSR").history()` against VCI.
- **Phase 2 (Portfolio — CSV Import):** Broker CSV format details are MEDIUM confidence based on domain knowledge, not verified exports. Need actual CSV samples from at least 1 broker before building parsers.
- **Phase 5 (WebSocket):** VCI rate limits for sub-minute polling need live verification. vnstock's freemium model may impose new restrictions.

Phases with standard patterns (skip research-phase):
- **Phase 3 (Corporate Actions):** Rights issue modeling, ex-date alerts, and adjusted price toggle are well-documented VN market concepts. Standard CRUD + scheduler patterns.
- **Phase 4 (Health/Monitoring):** Gemini usage extraction is well-documented in SDK. Pipeline timeline is standard query + frontend rendering. Telegram notification patterns are already proven in codebase.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommendations verified against installed packages, source code, and SDK documentation. Zero speculative dependencies. |
| Features | HIGH | All features mapped to existing codebase components with verified API/model support. VN broker CSV formats are MEDIUM (need actual samples). VNDirect rights issue API type is LOW (needs live verification). |
| Architecture | HIGH | All integration points verified via direct source code analysis. 14 features mapped to specific files to modify/create. Build order validated against dependency graph. |
| Pitfalls | HIGH | 16 pitfalls identified from actual code patterns — FIFO model limitations, DB pool constraints, pipeline timing, vnstock rate limits. All grounded in 9,400+ LOC analysis, not theoretical. |

**Overall confidence:** HIGH

### Gaps to Address

- **vnstock HNX/UPCOM compatibility:** Must be validated with live API calls before Phase 1 implementation begins. If VCI doesn't support HNX/UPCOM, may need SSI source (different rate limits, response format).
- **VN broker CSV samples:** Need actual export files from at least SSI or VNDirect to validate parser assumptions. Current format knowledge is domain inference (MEDIUM confidence).
- **VNDirect rights issue API type:** The event type for rights issues (`RIGHTS` vs `STOCKRIGHTS`) is unknown. Needs live API inspection. Fallback: CafeF scraping.
- **Gemini free-tier limits post-expansion:** 1500 RPD is documented but may change. With ~950 tickers × 4 analysis types, budget is tight. Need monitoring from Phase 1 onward.
- **Performance chart computation approach:** Architecture research recommends on-demand computation (single user, <20 holdings = fast). Pitfalls research suggests snapshot table for reliability. **Recommendation:** Start on-demand; add snapshot only if response time exceeds 3 seconds.
- **vnstock freemium model evolution:** Pinned at 3.5.1 but future versions may add authentication or restrict volume. Monitor changelog.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis — all backend/frontend files (models, services, crawlers, scheduler, API, components)
- vnstock 3.5.1 source — `Listing.symbols_by_exchange()`, `Quote(symbol)`, `_EXCHANGE_MAP`, `_TIMEFRAME_MAP`, `_INTERVAL_MAP`
- google-genai SDK — `response.usage_metadata` with `prompt_token_count`, `candidates_token_count`, `total_token_count`
- FastAPI/Starlette — native WebSocket support, `python-multipart` for file uploads
- Database schema — all models inspected: `ticker.py`, `daily_price.py`, `trade.py`, `lot.py`, `corporate_event.py`, `job_execution.py`
- Frontend packages — `package.json` verified: recharts 3.8.1, lightweight-charts 5.1.0, @tanstack/react-query, zustand, date-fns 4.x

### Secondary (MEDIUM confidence)
- Gemini free tier limits (15 RPM, 1500 RPD) — from AI Studio docs, may change
- VN broker CSV formats (SSI, VNDirect, TCBS, VCBS) — domain knowledge, not verified with actual exports
- react-day-picker 9.14.0 / papaparse 5.5.3 — npm registry version check

### Tertiary (LOW confidence)
- VNDirect API rights issue event type — inferred from existing crawl types, needs live verification
- vnstock VCI support for HNX/UPCOM intraday intervals — code suggests support but untested
- VCI rate limits for sustained high-volume polling — 20 req/min guest documented, enforcement behavior unknown

---
*Research completed: 2026-04-17*
*Ready for roadmap: yes*

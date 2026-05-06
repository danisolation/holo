# Roadmap: Holo — Stock Intelligence Platform

## Overview

Holo delivers AI-powered multi-dimensional stock analysis for Vietnamese stock exchanges (HOSE, HNX, UPCOM) through a data pipeline that feeds technical indicators, fundamental metrics, and news sentiment into Google Gemini — surfacing buy/sell/hold recommendations via Telegram bot and real-time web dashboard.

## Milestones

- ✅ **v1.0 Holo Stock Intelligence Platform** — Phases 1-5 (shipped 2026-04-15)
- ✅ **v1.1 Reliability & Portfolio** — Phases 6-11 (shipped 2026-04-17)
- ✅ **v2.0 Full Coverage & Real-Time** — Phases 12-16 (shipped 2026-04-17)
- ✅ **v3.0 Smart Trading Signals** — Phases 17-21 (shipped 2026-04-20)
- ✅ **v4.0 Paper Trading & Signal Verification** — Phases 22-26 (shipped 2025-07-20)
- ✅ **v5.0 E2E Testing & Quality Assurance** — Phases 27-31 (shipped 2025-07-21)
- ✅ **v6.0 AI Backtesting Engine** — Phases 32-34 (shipped 2026-04-22)
- ✅ **v7.0 Consolidation & Quality Upgrade** — Phases 35-42 (shipped 2025-07-22)
- ✅ **v8.0 AI Trading Coach** — Phases 43-47 (shipped 2026-04-23)
- ✅ **v9.0 UX Rework & Simplification** — Phases 48-51 (shipped 2026-05-04)
- ✅ **v10.0 Watchlist-Centric & Stock Discovery** — Phases 52-55 (shipped 2026-05-05)
- ✅ **v11.0 UX & Reliability Overhaul** — Phases 56-59 (shipped 2026-05-05)
- ✅ **v12.0 Rumor Intelligence** — Phases 60-63 (shipped 2026-05-05)
- ✅ **v13.0 AI Context & Accuracy** — Phases 64-67 (shipped 2026-05-05)
- ✅ **v14.0 Multi-Source Rumor & Quota Fix** — Phases 68-70 (shipped 2026-05-06)
- ✅ **v15.0 Performance Optimization** — Phases 71-75 (shipped 2026-05-06)
- ✅ **v16.0 Real-Time Price** — Phases 76-79 (shipped 2026-05-06)
- ✅ **v17.0 AI Consistency & UX** — Phases 80-82 (shipped)
- 🔄 **v18.0 Multi-Source Community Rumors** — Phases 83-87 (active)

## Phases

<details>
<summary>✅ v1.0 (Phases 1-5) — SHIPPED 2026-04-15</summary>

- [x] Phase 1: Data Foundation (3/3 plans) — PostgreSQL, vnstock, OHLCV + financials, APScheduler
- [x] Phase 2: Technical & Fundamental Analysis (3/3 plans) — ta indicators, Gemini AI scoring
- [x] Phase 3: Sentiment & Combined Intelligence (3/3 plans) — CafeF news, sentiment, combined recommendations
- [x] Phase 4: Telegram Bot (3/3 plans) — 7 commands, signal/price alerts, daily summary
- [x] Phase 5: Dashboard & Visualization (3/3 plans) — Next.js, candlestick charts, heatmap, watchlist

Full details: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)

</details>

<details>
<summary>✅ v1.1 Reliability & Portfolio (Phases 6-11) — SHIPPED 2026-04-17</summary>

- [x] Phase 6: Resilience Foundation (4 plans) — Circuit breakers, job tracking, dead-letter queue, auto-retry
- [x] Phase 7: Corporate Actions (3 plans) — VNDirect events, adjusted prices, cascade indicator recompute
- [x] Phase 8: Portfolio Core (4 plans) — Trade entry, FIFO lots, realized/unrealized P&L, summary
- [x] Phase 9: AI Prompt Improvements (3 plans) — System instruction, few-shot, scoring rubric, temperature tuning
- [x] Phase 10: System Health Dashboard (3 plans) — Health API + frontend page with job status, error rates, triggers
- [x] Phase 11: Telegram Portfolio (3 plans) — /buy, /sell, /portfolio, /pnl, daily P&L notification

Full details: [milestones/v1.1-ROADMAP.md](milestones/v1.1-ROADMAP.md)

</details>

<details>
<summary>✅ v2.0 Full Coverage & Real-Time (Phases 12-16) — SHIPPED 2026-04-17</summary>

- [x] Phase 12: Multi-Market Foundation (4 plans) — HNX/UPCOM crawling, exchange filters, tiered AI analysis
- [x] Phase 13: Portfolio Enhancements (5 plans) — Dividend tracking, performance/allocation charts, trade edit/delete, CSV import
- [x] Phase 14: Corporate Actions Enhancements (4 plans) — Rights issues, ex-date alerts, event calendar, adjusted/raw toggle
- [x] Phase 15: Health & Monitoring (3 plans) — Gemini usage tracking, pipeline timeline, Telegram health alerts
- [x] Phase 16: Real-Time WebSocket (2 plans) — WebSocket price streaming, 30s polling, market-hours auto-connect

Full details: [milestones/v2.0-ROADMAP.md](milestones/v2.0-ROADMAP.md)

</details>

<details>
<summary>✅ v3.0 Smart Trading Signals (Phases 17-21) — SHIPPED 2026-04-20</summary>

- [x] Phase 17: Enhanced Technical Indicators (2/2 plans) — ATR, ADX, Stochastic computation + display
- [x] Phase 18: Support & Resistance Levels (2/2 plans) — Pivot points, Fibonacci retracements
- [x] Phase 19: AI Trading Signal Pipeline (3/3 plans) — Dual-direction schema, Gemini prompt, batch processing
- [x] Phase 20: Trading Plan Dashboard Panel (2/2 plans) — Trading plan component on ticker detail page
- [x] Phase 21: Chart Price Line Overlays (1/1 plan) — Entry/SL/TP lines on candlestick chart

Full details: [milestones/v3.0-ROADMAP.md](milestones/v3.0-ROADMAP.md)

</details>

<details>
<summary>✅ v4.0 Paper Trading & Signal Verification (Phases 22-26) — SHIPPED 2025-07-20</summary>

- [x] Phase 22: Paper Trade Foundation (2 plans) — PaperTrade model, state machine, P&L, SimulationConfig
- [x] Phase 23: Position Monitoring & Auto-Track (2 plans) — Auto-track signals, daily SL/TP/timeout monitor
- [x] Phase 24: API & Analytics Engine (2 plans) — 18 REST endpoints, 12 analytics, manual follow
- [x] Phase 25: Dashboard Structure & Trade Management (2 plans) — 5-tab dashboard, trade table, settings, signal outcomes
- [x] Phase 26: Analytics Visualization & Calendar (2 plans) — Equity chart, streaks, calendar heatmap, periodic tables

Full details: [milestones/v4.0-ROADMAP.md](milestones/v4.0-ROADMAP.md)

</details>

<details>
<summary>✅ v5.0 E2E Testing & Quality Assurance (Phases 27-31) — SHIPPED 2025-07-21</summary>

- [x] Phase 27: Test Infrastructure & Foundation (4 plans) — Playwright dual webServer, test mode guard, data-testid, fixtures
- [x] Phase 28: Page Smoke Tests & API Health Checks (3 plans) — 66 tests: all 8 routes, all API endpoints
- [x] Phase 29: User Interaction Tests (2 plans) — 23 tests: forms, tables, tabs, interactive controls
- [x] Phase 30: Visual Regression Testing (2 plans) — 14 tests: screenshots, chart canvas, responsive checks
- [x] Phase 31: Critical User Flows (2 plans) — 8 tests: multi-page journeys end-to-end

Full details: [milestones/v5.0-ROADMAP.md](milestones/v5.0-ROADMAP.md)

</details>

<details>
<summary>✅ v6.0 AI Backtesting Engine (Phases 32-34) — SHIPPED 2026-04-22</summary>

- [x] Phase 32: Backtest Engine & Portfolio Simulation (3/3 plans) — Historical session replay, Gemini AI calls, position management, checkpoint/resume
- [x] Phase 33: Analytics & Benchmark Computation (2/2 plans) — AI equity vs VN-Index, win rate, drawdown, Sharpe, breakdowns
- [x] Phase 34: Backtest Dashboard (2/2 plans) — /backtest page, config form, progress bar, equity chart, trade log

Full details: [milestones/v6.0-ROADMAP.md](milestones/v6.0-ROADMAP.md)

</details>

<details>
<summary>✅ v7.0 Consolidation & Quality Upgrade (Phases 35-42) — SHIPPED 2025-07-22</summary>

- [x] Phase 35: Database & Model Cleanup (2 plans) — Remove dead tables, unused columns via Alembic migrations
- [x] Phase 36: Frontend Cleanup & Utility Extraction (1 plan) — Remove dead components, consolidate format/config utilities
- [x] Phase 37: Backend Analytics Consolidation (1 plan) — Extract shared analytics logic, composition pattern, merge schemas
- [x] Phase 38: Backend Architecture Refactor (1 plan) — Split AIAnalysisService and BacktestEngine into focused modules
- [x] Phase 39: AI Quality Upgrade (1 plan) — Anti-hallucination validation for scores, prices, and prompt input
- [x] Phase 40: Frontend Component Consolidation (1 plan) — Shared trade table, equity chart, watchlist & page role cleanup
- [x] Phase 41: Performance Optimization (1 plan) — WebSocket off-hours scheduling, chart lazy-loading
- [x] Phase 42: Test Maintenance (1 plan) — Update all unit tests and E2E tests after refactoring

Full details: [milestones/v7.0-ROADMAP.md](milestones/v7.0-ROADMAP.md)

</details>

<details>
<summary>✅ v8.0 AI Trading Coach (Phases 43-47) — SHIPPED 2026-04-23</summary>

- [x] Phase 43: Daily Picks Engine (3/3 plans) — AI selects 3-5 daily stock picks with entry/SL/TP, position sizing, safety scoring
- [x] Phase 44: Trade Journal & P&L (3/3 plans) — User logs real trades with auto-calculated P&L including VN fees/tax
- [x] Phase 45: Coach Dashboard & Pick Performance (2/2 plans) — Single-page coach view with picks, performance cards, outcome tracking
- [x] Phase 46: Behavior Tracking & Adaptive Strategy (3/3 plans) — Viewing habits, trading patterns, risk adjustments, sector preferences
- [x] Phase 47: Goals & Weekly Reviews (3/3 plans) — Monthly profit targets, weekly risk tolerance prompt, AI coaching reviews

Full details: [milestones/v8.0-ROADMAP.md](milestones/v8.0-ROADMAP.md)

</details>

<details>
<summary>✅ v9.0 UX Rework & Simplification (Phases 48-51) — SHIPPED 2026-05-04</summary>

- [x] Phase 48: Backend Cleanup & Scheduler Simplification (2/2 plans) — Remove corporate events, HNX/UPCOM, telegram; HOSE-only pipeline
- [x] Phase 49: Navigation & Watchlist Migration (2/2 plans) — 5-item nav, watchlist localStorage→PostgreSQL, AI signal enrichment
- [x] Phase 50: Coach Page Restructure & Trade Flow (2/2 plans) — Tab layout, one-click trade recording, post-trade guidance
- [x] Phase 51: AI Analysis Improvement (2/2 plans) — Structured AI output sections, visual hierarchy rendering

Full details: [milestones/v9.0-ROADMAP.md](milestones/v9.0-ROADMAP.md)

</details>

<details>
<summary>✅ v10.0 Watchlist-Centric & Stock Discovery (Phases 52-55) — SHIPPED 2026-05-05</summary>

- [x] Phase 52: Discovery Engine & Schema (2/2 plans) — Daily scoring of ~400 HOSE tickers on 6 dimensions
- [x] Phase 53: Watchlist-Gated AI Pipeline (1/1 plan) — AI analysis gated to watchlist only, ~70% API reduction
- [x] Phase 54: Sector Grouping & Heatmap Rework (2/2 plans) — Sector assignment, combobox, watchlist-only heatmap
- [x] Phase 55: Discovery Frontend (2/2 plans) — Discovery page with scored tickers, filters, add-to-watchlist

Full details: [milestones/v10.0-ROADMAP.md](milestones/v10.0-ROADMAP.md)

</details>

<details>
<summary>✅ v11.0 UX & Reliability Overhaul (Phases 56-59) — SHIPPED 2026-05-05</summary>

- [x] Phase 56: Keep-Alive & API Performance (2/2 plans) — Date-bounded query, composite index, TTL cache, keep-alive docs
- [x] Phase 57: Search Fix (1/1 plan) — Removed .slice(0,50) truncation, limit=500, recent searches
- [x] Phase 58: AI Analysis Freshness (2/2 plans) — Morning CronTrigger 8:30 AM, shortened chain, freshness badges
- [x] Phase 59: UX & Onboarding (1/1 plan) — VN30 preset, empty states, nav descriptions

Full details: [milestones/v11.0-ROADMAP.md](milestones/v11.0-ROADMAP.md)

</details>

<details>
<summary>✅ v12.0 Rumor Intelligence (Phases 60-63) — SHIPPED 2026-05-05</summary>

- [x] Phase 60: Database & Fireant Crawler (2/2 plans) — Rumor model, Fireant REST API crawler, dedup
- [x] Phase 61: AI Rumor Scoring (2/2 plans) — Gemini credibility/impact scoring, Vietnamese prompts
- [x] Phase 62: API Endpoints & Frontend Display (2/2 plans) — Rumor score panel, watchlist badges
- [x] Phase 63: Scheduler Integration (1/1 plan) — Chain wiring, manual triggers

Full details: [milestones/v12.0-ROADMAP.md](milestones/v12.0-ROADMAP.md)

</details>

<details>
<summary><b>v13.0 AI Context & Accuracy (Phases 64-67) ✅ SHIPPED</b></summary>

- [x] Phase 64: Rumor-to-Signal Integration — Rumor data in combined/trading signal prompts + pick scoring
- [x] Phase 65: AI Accuracy Tracking Backend — ai_accuracy table, daily backfill job, verdict logic
- [x] Phase 66: Accuracy Dashboard & Feedback Loop — AccuracyCard component, accuracy-based pick boost
- [x] Phase 67: Enhanced Gemini Context — Volume profile, sector peer comparison, 52w percentile

Full details: [milestones/v13.0-ROADMAP.md](milestones/v13.0-ROADMAP.md)

</details>

<details>
<summary>✅ v14.0 Multi-Source Rumor & Quota Fix (Phases 68-70) — SHIPPED 2026-05-06</summary>

- [x] Phase 68: Gemini Quota Fix & Scoring Repair (1/1 plan) — Switch to gemini-2.5-flash, verify scoring
- [x] Phase 69: Multi-Source Crawlers (1/1 plan) — VnExpress, Vietstock, Stockbiz crawlers
- [x] Phase 70: Pipeline Integration (1/1 plan) — Wire all sources into scoring, scheduler, prompts

</details>

### v15.0 Performance Optimization (Phases 71-75)

- [x] **Phase 71: Database Indexes & Pool Tuning** — Composite indexes on 7 hot tables + connection pool optimization (completed 2026-05-06)
- [x] **Phase 72: N+1 Query Fixes & Pagination** — Batch queries for rumor/AI context + paginated list endpoints (completed 2026-05-06)
- [x] **Phase 73: API Response Caching** — TTLCache for expensive endpoints + dashboard payload caching (completed 2026-05-06)
- [x] **Phase 74: Crawler Efficiency** — Parallel fetch with bounded concurrency + bulk inserts + ticker map reuse (completed 2026-05-06)
- [x] **Phase 75: Async Patterns & Bulk Operations** — CPU parsing offloaded to thread pool + financial bulk upsert (completed 2026-05-06)

## Phase Details

### Phase 71: Database Indexes & Pool Tuning
**Goal**: Database queries hit indexes on hot paths and connection pool handles concurrent load without exhaustion
**Depends on**: Phase 70 (v14.0 complete)
**Requirements**: DB-IDX-01, DB-POOL-01
**Success Criteria** (what must be TRUE):
  1. Queries on daily_prices, technical_indicators, ai_analyses, daily_picks, weekly_reviews, job_executions, and community_posts use composite indexes (verified via EXPLAIN ANALYZE)
  2. API endpoints that query these tables show measurably lower latency under normal load
  3. Connection pool settings (pool_size, max_overflow, pool_recycle) are tuned so concurrent scheduler jobs + API requests don't produce "pool exhausted" errors
**Plans:** 1/1 plans complete

Plans:
- [x] 71-01-PLAN.md — Alembic migration for 5 composite indexes + pool tuning

### Phase 72: N+1 Query Fixes & Pagination
**Goal**: List and summary endpoints use batch queries instead of per-item loops, and return paginated results with stable ordering
**Depends on**: Phase 71
**Requirements**: DB-N1-01, DB-N1-02, DB-PAGE-01
**Success Criteria** (what must be TRUE):
  1. Rumor watchlist summary endpoint returns aggregated data via a single batch query instead of issuing one query per ticker
  2. AI context builder fetches all dimension data (technical, fundamental, sentiment) in batch queries per dimension rather than sequential per-ticker queries
  3. Watchlist, rumor list, and analysis list endpoints return paginated responses with page/limit parameters and consistent sort order
  4. Total query count for summary endpoints scales O(1) with ticker count, not O(N)
**Plans:** 2/2 plans complete

Plans:
- [x] 72-01-PLAN.md — Batch aggregate queries for rumor summary + AI context builder
- [x] 72-02-PLAN.md — Pagination with stable ordering on list endpoints

### Phase 73: API Response Caching
**Goal**: Expensive read endpoints return cached responses, eliminating redundant computation within TTL windows
**Depends on**: Phase 72
**Requirements**: CACHE-01, CACHE-02
**Success Criteria** (what must be TRUE):
  1. Sectors, discovery, goals, analysis summary, and rumor summary endpoints serve cached responses within TTL (repeated calls within window don't hit DB)
  2. Dashboard overview endpoint (latest prices, SMA deltas, volume stats) returns a pre-computed cached payload
  3. Cache invalidation occurs naturally via TTL expiry — no stale data persists beyond configured window
**Plans:** 1/1 plans complete

Plans:
- [x] 73-01-PLAN.md — TTLCache for 5 expensive endpoints (sectors, discovery, weekly-review, analysis/summary, rumor/watchlist/summary)

### Phase 74: Crawler Efficiency
**Goal**: Crawlers fetch data in parallel with controlled concurrency, insert in bulk, and share a single ticker map per job run
**Depends on**: Phase 71
**Requirements**: CRAWL-01, CRAWL-02, CRAWL-03
**Success Criteria** (what must be TRUE):
  1. Crawler fetch phase runs requests in parallel with asyncio.Semaphore bounding max concurrent connections
  2. Rumor/news crawlers use multi-row INSERT ON CONFLICT instead of single-row inserts (fewer round-trips to DB)
  3. Ticker symbol-to-ID map is loaded once per job run and reused across all crawlers — no redundant ticker queries
  4. Total crawler job duration is measurably shorter than sequential baseline
**Plans:** 2 plans

Plans:
- [ ] 74-01-PLAN.md — Centralize ticker map + bulk inserts (CRAWL-02, CRAWL-03)
- [ ] 74-02-PLAN.md — Semaphore parallel fetch + concurrent RSS crawlers (CRAWL-01)

### Phase 75: Async Patterns & Bulk Operations
**Goal**: CPU-heavy sync work runs in thread pool without blocking the event loop, and financial data uses bulk upsert
**Depends on**: Phase 72
**Requirements**: PERF-01, PERF-02
**Success Criteria** (what must be TRUE):
  1. BeautifulSoup HTML parsing and DataFrame iterrows operations run inside asyncio.to_thread() — event loop stays responsive during parsing
  2. Financial service upserts quarterly/annual data via bulk INSERT ON CONFLICT instead of row-by-row saves
  3. No async event loop blocking warnings appear in logs during crawler or financial data processing
**Plans**: TBD

</details>

### v16.0: Real-Time Price (Phases 76-79)

### Phase 76: VNDirect WebSocket Client
**Goal**: Connect to VNDirect WebSocket, parse SP/BA messages, manage lifecycle with auto-reconnect
**Requirements**: WS-01, WS-02, WS-03, WS-04
**Success Criteria** (what must be TRUE):
  1. WebSocket client connects to `wss://price-cmc-04.vndirect.com.vn/realtime/websocket` and receives SP messages
  2. BA (Bid/Ask) messages are parsed into structured data for subscribed tickers
  3. Client auto-reconnects with exponential backoff (1s, 2s, 4s, 8s... max 60s) on disconnect
  4. Client only connects during market hours (9:00-11:30, 13:00-14:45 UTC+7) and sleeps outside
  5. Unit tests verify message parsing for SP and BA message types
**Plans:** 2 plans

Plans:
- [ ] 76-01-PLAN.md — VNDirect WS client class with SP/BA message parsing + unit tests
- [ ] 76-02-PLAN.md — Integration with RealtimePriceService + app startup lifecycle

### Phase 77: Backend WebSocket Broadcasting
**Goal**: Backend server broadcasts real-time price updates to connected frontend clients
**Depends on**: Phase 76
**Requirements**: BC-01, BC-02, BC-03
**Success Criteria** (what must be TRUE):
  1. FastAPI WebSocket endpoint accepts frontend connections and pushes price updates
  2. New clients receive latest price snapshot for all subscribed tickers immediately on connect
  3. Subscription is filtered to user's watchlist tickers only (no wasted bandwidth)
  4. Multiple concurrent frontend clients can connect and receive updates independently
**Plans**: TBD

### Phase 78: Frontend Real-Time Price Display
**Goal**: Dashboard shows live price updates with visual feedback
**Depends on**: Phase 77
**Requirements**: FE-01, FE-02
**Success Criteria** (what must be TRUE):
  1. Watchlist prices update in real-time without page refresh during market hours
  2. Price changes show flash animation (green for up, red for down) lasting ~1 second
  3. Candlestick chart on ticker page updates the current intraday bar in real-time
  4. Price display gracefully falls back to last known price when WebSocket disconnects
**Plans**: TBD

### Phase 79: Bid/Ask Depth Display
**Goal**: Show bid/ask depth data on ticker detail page
**Depends on**: Phase 77
**Requirements**: FE-03
**Success Criteria** (what must be TRUE):
  1. Ticker detail page shows top 3 bid/ask levels with volume
  2. Bid/Ask display updates in real-time during market hours
  3. Visual indicator shows spread between best bid and best ask
**Plans**: TBD

### v17.0: AI Consistency & UX (Phases 80-82)

- [x] **Phase 80: AI Prompt Consistency** — Fix combined/trading signal prompts to output coherent, single-direction recommendations
- [x] **Phase 81: Frontend Signal Display** — Simplify trading plan panel to show recommended direction only with consistent badges
- [x] **Phase 82: VNDirect WS Render Fix** — Fix WebSocket DNS/connectivity on Render production deployment

## Phase Details — v17.0

### Phase 80: AI Prompt Consistency
**Goal**: AI analysis outputs are internally consistent — combined recommendation aligns with technical/fundamental signals, and trading signal outputs exactly one recommended direction
**Depends on**: Phase 79 (v16.0 complete)
**Requirements**: APC-01, APC-02, APC-03
**Success Criteria** (what must be TRUE):
  1. Combined analysis recommendation explicitly references and aligns with technical/fundamental/sentiment scores — no silent contradictions between "Technical = SELL" and "Combined = BUY" without explanation
  2. Combined prompt receives technical, fundamental, and sentiment scores as structured input and the AI reasoning text references these scores by name
  3. Trading signal endpoint returns exactly 1 recommended direction per ticker (not dual LONG+BEARISH), with a single trading plan containing entry/SL/TP
  4. Existing unit tests and API contract remain stable (no breaking schema changes to consumers)
**Plans**: TBD

### Phase 81: Frontend Signal Display
**Goal**: Trading plan panel shows only the recommended direction with visual consistency across all analysis cards
**Depends on**: Phase 80
**Requirements**: FED-01, FED-02
**Success Criteria** (what must be TRUE):
  1. Trading Plan panel on ticker detail page displays only the recommended direction's plan (no secondary/alternative direction panel visible)
  2. Analysis cards (technical, fundamental, sentiment, combined) show direction badges/icons that are visually consistent with the final recommendation
  3. When AI recommends HOLD/neutral, trading plan panel shows appropriate empty/neutral state instead of stale directional data
**Plans**: TBD
**UI hint**: yes

### Phase 82: VNDirect WS Render Fix
**Goal**: VNDirect WebSocket connects successfully from Render production environment and streams live prices
**Depends on**: Phase 80 (independent of Phase 81, but sequenced after for deployment clarity)
**Requirements**: RTC-01
**Success Criteria** (what must be TRUE):
  1. VNDirect WebSocket client establishes connection from Render deployment and receives SP messages during market hours
  2. If direct DNS resolution fails on Render, a fallback mechanism (proxy, alternative endpoint, or VCI polling) activates automatically
  3. Frontend receives real-time price updates on production (not just localhost) during market hours
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 80. AI Prompt Consistency | done | Complete | 2026-05-06 |
| 81. Frontend Signal Display | done | Complete | 2026-05-06 |
| 82. VNDirect WS Render Fix | done | Complete | 2026-05-06 |

---

### v18.0: Multi-Source Community Rumors (Phases 83-87)

- [ ] **Phase 83: Telegram Channel Crawler** — Telethon MTProto client to read public VN stock Telegram channels
- [ ] **Phase 84: News Source Expansion** — tinnhanhchungkhoan.vn scraper + F319 second feed + nhadautu.vn
- [ ] **Phase 85: AI Rumor Scoring Enhancement** — Source weighting, credibility scoring, cross-source corroboration
- [ ] **Phase 86: Frontend Source Tags** — Rumor panel shows source icons and tags per post
- [ ] **Phase 87: Integration & Testing** — End-to-end rumor pipeline test, scheduler integration, monitoring

## Phase Details — v18.0

### Phase 83: Telegram Channel Crawler
**Goal**: Crawl public Vietnamese stock Telegram channels via Telethon and store ticker-matched posts in rumors table
**Depends on**: None (new feature)
**Requirements**: TGM-01, TGM-02, TGM-03
**Success Criteria** (what must be TRUE):
  1. TelegramCrawler class connects via Telethon StringSession and fetches messages from configured channels
  2. Ticker mentions extracted from messages and matched against known ticker list
  3. Posts stored in rumors table with `author_name` prefixed `tg:` for source identification
  4. APScheduler job runs every 30 min during market hours (configurable)
  5. Feature flag `telegram_enabled` controls activation; graceful skip when disabled
**Plans**: TBD

### Phase 84: News Source Expansion
**Goal**: Add tinnhanhchungkhoan.vn crawler, expand F319 to second feed, add nhadautu.vn
**Depends on**: None (independent of Phase 83)
**Requirements**: NSE-01, NSE-02, NSE-03
**Success Criteria** (what must be TRUE):
  1. tinnhanhchungkhoan.vn crawler fetches article listings, extracts tickers from titles/body, stores in news/rumors table
  2. F319 crawler processes both main forum RSS and giao-lưu feed
  3. nhadautu.vn crawler works (or documented as not feasible with fallback plan)
  4. All new crawlers use existing patterns: ON CONFLICT dedup, tenacity retry, rate limiting
**Plans**: TBD

### Phase 85: AI Rumor Scoring Enhancement
**Goal**: Upgrade rumor scoring to weight sources, detect credibility, and corroborate across sources
**Depends on**: Phase 83, Phase 84 (needs multiple sources active)
**Requirements**: ARI-01, ARI-02, ARI-03
**Success Criteria** (what must be TRUE):
  1. Rumor scoring prompt receives source metadata and applies different weight per source type
  2. Pump-and-dump patterns detected (repeated ticker spam from same author, exaggerated claims) → lower credibility
  3. Cross-source corroboration: when ≥2 different sources mention same ticker+direction within 24h → confidence boost
  4. Final rumor score integrates all sources into single weighted score per ticker
**Plans**: TBD

### Phase 86: Frontend Source Tags
**Goal**: Dashboard rumor panel displays source origin for each rumor post
**Depends on**: Phase 83, Phase 84 (needs posts from new sources)
**Requirements**: FRD-01
**Success Criteria** (what must be TRUE):
  1. Each rumor post shows source badge (Fireant / F319 / Telegram / TNCK / NĐT)
  2. Source-specific icon or color distinguishes origins visually
  3. Filter by source available in rumor list view
**Plans**: TBD
**UI hint**: yes

### Phase 87: Integration & Testing
**Goal**: End-to-end validation of multi-source rumor pipeline
**Depends on**: Phase 85, Phase 86
**Requirements**: All (integration)
**Success Criteria** (what must be TRUE):
  1. Scheduler orchestrates all crawlers (Fireant + F319 + Telegram + TNCK) in correct sequence
  2. AI scoring processes posts from all sources without errors
  3. Frontend displays mixed-source rumors correctly with proper tagging
  4. Graceful degradation: if one source fails, others continue working
**Plans**: TBD
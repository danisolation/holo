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
- 🔄 **v12.0 Rumor Intelligence** — Phases 60-63

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

### v12.0 Rumor Intelligence (Phases 60-63)

- [x] **Phase 60: Database & Fireant Crawler** — `community_posts` table, Fireant REST API crawler, post deduplication (completed 2026-05-05)
- [x] **Phase 61: AI Rumor Scoring** — Gemini credibility/impact scoring, direction classification, key claims extraction (completed 2026-05-05)
- [x] **Phase 62: API Endpoints & Frontend Display** — Rumor score panel, feed timeline, watchlist badges (completed 2026-05-05)
- [ ] **Phase 63: Scheduler Integration** — Wire crawler + scoring into daily APScheduler job chain

## Phase Details

### Phase 60: Database & Fireant Crawler
**Goal**: System can ingest and store community posts from Fireant.vn for watchlist tickers
**Depends on**: Nothing (first phase of v12.0)
**Requirements**: RUMOR-01, RUMOR-02
**Success Criteria** (what must be TRUE):
  1. Running the crawler for a watchlist ticker fetches posts from Fireant.vn and stores them in the database
  2. Re-running the crawler for the same ticker does not create duplicate posts (ON CONFLICT dedup)
  3. Stored posts contain content, author info, engagement metrics (likes, replies), and verified user status
  4. Crawler handles Vietnamese content encoding correctly (no HTML entities in stored text)
**Plans:** 2/2 plans complete
Plans:
- [x] 60-01-PLAN.md — Schema foundation: Rumor model, Alembic migration, config, circuit breaker, types
- [x] 60-02-PLAN.md — FireantCrawler implementation + unit tests

### Phase 61: AI Rumor Scoring
**Goal**: Each crawled rumor receives AI-generated credibility, impact, and directional assessment
**Depends on**: Phase 60
**Requirements**: RUMOR-04, RUMOR-05, RUMOR-06, RUMOR-07, RUMOR-08
**Success Criteria** (what must be TRUE):
  1. Each scored rumor has a credibility score (1-10) and an impact score (1-10) stored in `rumor_scores` table
  2. Each scored rumor has a bullish/bearish/neutral classification
  3. Scoring output includes extracted key factual claims as a structured list
  4. All AI assessments include Vietnamese explanations for the scores
  5. Posts with higher engagement (likes, replies) and verified authors receive appropriately weighted credibility signals
**Plans:** 2/2 plans complete
Plans:
- [x] 61-01-PLAN.md — Schema foundation: RumorScore model, migration, Pydantic schemas, Vietnamese prompts
- [x] 61-02-PLAN.md — RumorScoringService implementation + unit tests

### Phase 62: API Endpoints & Frontend Display
**Goal**: User can view rumor intelligence on the ticker detail page and watchlist
**Depends on**: Phase 61
**Requirements**: RUMOR-09, RUMOR-10, RUMOR-11
**Success Criteria** (what must be TRUE):
  1. Ticker detail page shows a rumor score panel with latest credibility and impact scores
  2. Ticker detail page shows a chronological feed of scored rumor posts with their assessments
  3. Watchlist table rows show a badge indicating recent rumor count and overall sentiment for each ticker
**Plans:** 2/2 plans complete
Plans:
- [x] 62-01-PLAN.md — Backend FastAPI rumor router (2 GET endpoints + Pydantic schemas)
- [x] 62-02-PLAN.md — Frontend components, hooks, ticker page + watchlist integration
**UI hint**: yes

### Phase 63: Scheduler Integration
**Goal**: Rumor crawling and scoring run automatically as part of the daily pipeline
**Depends on**: Phase 62
**Requirements**: RUMOR-03
**Success Criteria** (what must be TRUE):
  1. Fireant crawl + rumor scoring execute automatically in the daily APScheduler job chain
  2. Rumor jobs run after `trading_signal` and before `pick_generation` in the chain
  3. A scheduler failure in rumor jobs does not break the rest of the pipeline
**Plans:** 1 plan
Plans:
- [x] 63-01-PLAN.md — Job functions, chain wiring, manual triggers

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 60. Database & Fireant Crawler | 2/2 | Complete   | 2026-05-05 |
| 61. AI Rumor Scoring | 2/2 | Complete   | 2026-05-05 |
| 62. API Endpoints & Frontend Display | 2/2 | Complete   | 2026-05-05 |
| 63. Scheduler Integration | 1/1 | Complete   | 2026-05-05 |
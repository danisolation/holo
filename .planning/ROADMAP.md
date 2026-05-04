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
- 🚧 **v10.0 Watchlist-Centric & Stock Discovery** — Phases 52-55 (in progress)

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

### 🚧 v10.0 Watchlist-Centric & Stock Discovery (In Progress)

**Milestone Goal:** Chuyển Holo từ "hiển thị 400 mã cố định" sang "watchlist là trung tâm" — AI scan toàn sàn gợi ý mã tiềm năng hàng ngày, user tự chọn thêm vào watchlist, mọi thứ (AI analysis, daily picks, heatmap) chỉ chạy trên watchlist.

- [x] **Phase 52: Discovery Engine & Schema** - Alembic migration + pure-indicator scoring engine scanning ~400 HOSE tickers daily (completed 2026-05-04)
- [x] **Phase 53: Watchlist-Gated AI Pipeline** - Gate AI analysis and daily picks to run exclusively on watchlist tickers (completed 2026-05-04)
- [ ] **Phase 54: Sector Grouping & Heatmap Rework** - User-assigned sector tags on watchlist, heatmap filtered and grouped by sector
- [ ] **Phase 55: Discovery Frontend** - Discovery page with scored recommendations, add-to-watchlist flow, signal/sector filters

## Phase Details

### Phase 52: Discovery Engine & Schema
**Goal**: A pure-computation discovery engine scores all ~400 HOSE tickers daily on technical and fundamental indicators, persisting results with 14-day retention
**Depends on**: Phase 51 (v9.0 shipped)
**Requirements**: DISC-01, DISC-02
**Success Criteria** (what must be TRUE):
  1. After the daily pipeline runs, `discovery_results` table contains scored entries for all active HOSE tickers with breakdown by indicator dimension (RSI, MACD, ADX, volume, P/E, ROE)
  2. Discovery job executes sequentially after indicators complete in the scheduler chain, without breaking any existing downstream jobs (AI analysis, picks, etc.)
  3. Results older than 14 days are automatically cleaned up during each run, keeping the table bounded
  4. `sector_group` column exists on `user_watchlist` table (Alembic migration), ready for Phase 54
**Plans:** 2/2 plans complete
Plans:
- [x] 52-01-PLAN.md — Schema, model & DiscoveryService implementation
- [x] 52-02-PLAN.md — Scheduler integration & unit tests

### Phase 53: Watchlist-Gated AI Pipeline
**Goal**: AI analysis and daily picks run exclusively on watchlist tickers, reducing Gemini API usage by ~70% and pipeline time by ~3x
**Depends on**: Phase 52
**Requirements**: WL-01, WL-02
**Success Criteria** (what must be TRUE):
  1. AI analysis (Gemini calls) runs only on tickers present in the user's watchlist — non-watchlist tickers receive no AI analysis
  2. Daily picks are selected exclusively from watchlist tickers — no picks appear for tickers outside the watchlist
  3. An empty watchlist causes the AI pipeline to skip gracefully with a logged warning and the scheduler chain continues — no crashes or stuck jobs
  4. Full pipeline completes noticeably faster, proportional to watchlist size (~15-30 tickers) versus the previous ~400-ticker run
**Plans:** 1/1 plans complete
Plans:
- [x] 53-01-PLAN.md — Watchlist gating for AI analysis jobs, pick service, and tests

### Phase 54: Sector Grouping & Heatmap Rework
**Goal**: User can organize watchlist tickers by sector and the home page heatmap reflects only their curated, sector-grouped watchlist
**Depends on**: Phase 52
**Requirements**: TAG-01, TAG-02, TAG-03
**Success Criteria** (what must be TRUE):
  1. User can assign a sector/industry group to each ticker in their watchlist via inline editing on the watchlist table
  2. When adding a new ticker, the sector field auto-suggests a value based on vnstock ICB classification data
  3. Home page heatmap displays only tickers from the user's watchlist, grouped visually by their assigned sector
  4. Changing watchlist membership or sector assignment immediately reflects in the heatmap without full page refresh
**Plans:** 2 plans
Plans:
- [ ] 54-01-PLAN.md — Backend: sector_group model fix, PATCH endpoint, auto-populate on add, sectors list endpoint, unit tests
- [ ] 54-02-PLAN.md — Frontend: sector combobox, inline editing in watchlist table, heatmap rework to watchlist-only with sector grouping
**UI hint**: yes

### Phase 55: Discovery Frontend
**Goal**: User can browse daily AI-scored stock recommendations on a dedicated Discovery page and add promising tickers to their watchlist with one click
**Depends on**: Phase 53, Phase 54
**Requirements**: DPAGE-01, DPAGE-02, DPAGE-03
**Success Criteria** (what must be TRUE):
  1. Discovery page shows top-scored tickers with their composite score and signal breakdown (e.g., RSI oversold, MACD cross, volume spike, strong ADX trend)
  2. User can add any discovery ticker to their watchlist with a single button click, with sector auto-suggested from ICB data
  3. User can filter discovery results by sector and by signal type (e.g., show only MACD crossover signals, or only Banking sector)
  4. Discovery page updates daily after the pipeline runs, showing fresh scores each trading day
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:** 52 → 53 → 54 → 55

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 52. Discovery Engine & Schema | 2/2 | Complete    | 2026-05-04 |
| 53. Watchlist-Gated AI Pipeline | 1/1 | Complete    | 2026-05-04 |
| 54. Sector Grouping & Heatmap Rework | 0/0 | Not started | - |
| 55. Discovery Frontend | 0/0 | Not started | - |
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
- 🚧 **v11.0 UX & Reliability Overhaul** — Phases 56-59 (in progress)

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

### 🚧 v11.0 UX & Reliability Overhaul (In Progress)

**Milestone Goal:** Sửa các thiếu sót thực tế về trải nghiệm người dùng, data freshness, AI timeliness, và performance trên production — app load < 3s, search tìm tất cả mã, AI analysis fresh trước giờ mở cửa, UX rõ ràng cho người mới.

- [ ] **Phase 56: Keep-Alive & API Performance** - External pinger, query optimization, in-memory cache, date-bounded queries
- [ ] **Phase 57: Search Fix** - Remove ticker search truncation, add recent searches
- [ ] **Phase 58: AI Analysis Freshness** - Morning AI refresh chain, freshness indicator in dashboard
- [ ] **Phase 59: UX & Onboarding** - Preset watchlist, empty state guidance, navigation descriptions

## Phase Details

### Phase 56: Keep-Alive & API Performance
**Goal**: App loads in under 3 seconds on production — no cold start delay, no slow queries
**Depends on**: Phase 55 (v10.0 shipped)
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04
**Success Criteria** (what must be TRUE):
  1. Opening the app in a browser after 30+ minutes of inactivity returns the home page within 5 seconds (no cold start)
  2. Market overview API responds in under 3 seconds with current-day price data for all ~400 HOSE tickers
  3. Repeated requests to the same API endpoint within 60 seconds return instantly from cache without hitting the database
  4. Daily prices queries scan only the last 7 days of data, not the entire table history
**Plans**: TBD

### Phase 57: Search Fix
**Goal**: User can find and select any of the ~400 HOSE tickers through the search dialog
**Depends on**: Phase 56
**Requirements**: SRCH-01, SRCH-02
**Success Criteria** (what must be TRUE):
  1. Typing any valid HOSE ticker symbol (including tickers beyond position 50 alphabetically, e.g., VNM, VPB, TCB) into the search dialog shows and selects that ticker
  2. After searching for a ticker, the search dialog shows up to 5 recent searches on next open (persisted across browser sessions via localStorage)
**Plans**: TBD
**UI hint**: yes

### Phase 58: AI Analysis Freshness
**Goal**: AI analysis is fresh before market opens each trading day, and user can see how recent each analysis is
**Depends on**: Phase 56 (keep-alive must be active for morning cron to fire)
**Requirements**: AI-01, AI-02, AI-03
**Success Criteria** (what must be TRUE):
  1. On weekday mornings by 9:00 AM ICT, watchlist tickers have AI analysis updated after 8:30 AM (not stale from previous day's 15:30 run)
  2. Morning refresh completes within Gemini free tier limits (15 RPM) by running a shortened chain (price → indicators → AI analysis → signals only, skipping discovery/news/sentiment)
  3. Dashboard shows a freshness indicator per ticker displaying the age of the last AI analysis (e.g., "2h ago", "18h ago") with visual distinction for stale (>12h) vs fresh
**Plans**: TBD
**UI hint**: yes

### Phase 59: UX & Onboarding
**Goal**: First-time users immediately understand what each section does and have data to explore within 30 seconds
**Depends on**: Phase 57 (search must work for onboarding guidance)
**Requirements**: UX-01, UX-02, UX-03
**Success Criteria** (what must be TRUE):
  1. A user with an empty watchlist sees a one-click option to add VN30 blue-chip tickers as a preset watchlist
  2. Empty states on heatmap, watchlist, and discovery pages show helpful guidance text with a clear call-to-action (not blank screens)
  3. Navigation items include short descriptions or tooltips explaining what each section does (e.g., "Discovery — AI-scored stock recommendations updated daily")
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:** 56 → 57 → 58 → 59

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 52. Discovery Engine & Schema | v10.0 | 2/2 | Complete | 2026-05-04 |
| 53. Watchlist-Gated AI Pipeline | v10.0 | 1/1 | Complete | 2026-05-04 |
| 54. Sector Grouping & Heatmap Rework | v10.0 | 2/2 | Complete | 2026-05-04 |
| 55. Discovery Frontend | v10.0 | 2/2 | Complete | 2026-05-04 |
| 56. Keep-Alive & API Performance | v11.0 | 0/? | Not started | - |
| 57. Search Fix | v11.0 | 0/? | Not started | - |
| 58. AI Analysis Freshness | v11.0 | 0/? | Not started | - |
| 59. UX & Onboarding | v11.0 | 0/? | Not started | - |
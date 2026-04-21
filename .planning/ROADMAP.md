# Roadmap: Holo — Stock Intelligence Platform

## Overview

Holo delivers AI-powered multi-dimensional stock analysis for Vietnamese stock exchanges (HOSE, HNX, UPCOM) through a data pipeline that feeds technical indicators, fundamental metrics, and news sentiment into Google Gemini — surfacing buy/sell/hold recommendations via Telegram bot and real-time web dashboard.

## Milestones

- ✅ **v1.0 Holo Stock Intelligence Platform** — Phases 1-5 (shipped 2026-04-15)
- ✅ **v1.1 Reliability & Portfolio** — Phases 6-11 (shipped 2026-04-17)
- ✅ **v2.0 Full Coverage & Real-Time** — Phases 12-16 (shipped 2026-04-17)
- ✅ **v3.0 Smart Trading Signals** — Phases 17-21 (shipped 2026-04-20)
- ✅ **v4.0 Paper Trading & Signal Verification** — Phases 22-26 (shipped 2025-07-20)
- 🚧 **v5.0 E2E Testing & Quality Assurance** — Phases 27-31 (in progress)

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

### 🚧 v5.0 E2E Testing & Quality Assurance (In Progress)

**Milestone Goal:** Playwright E2E test suite covering all pages, API endpoints, user interactions, visual regression, and critical flows — catching bugs automatically and verifying the entire application works end-to-end.

- [x] **Phase 27: Test Infrastructure & Foundation** - Playwright configured with dual webServer, test mode guard, data-testid attributes, seed fixtures (completed 2026-04-21)
- [ ] **Phase 28: Page Smoke Tests & API Health Checks** - Every route loads, every API endpoint responds correctly
- [ ] **Phase 29: User Interaction Tests** - Forms, tables, tabs, and interactive controls verified
- [ ] **Phase 30: Visual Regression Testing** - Screenshot baselines, chart verification, dynamic masking, responsive checks
- [ ] **Phase 31: Critical User Flows** - Multi-page journeys proving the app works end-to-end

## Phase Details

### Phase 27: Test Infrastructure & Foundation
**Goal**: E2E test infrastructure is fully operational — Playwright configured, both servers auto-start/stop, test selectors stable, seed fixtures ready
**Depends on**: Phase 26 (v4.0 shipped — all features exist to test)
**Requirements**: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05
**Success Criteria** (what must be TRUE):
  1. `npx playwright test` executes with both FastAPI (:8001) and Next.js (:3000) auto-starting via `webServer` config and stopping after completion
  2. HOLO_TEST_MODE=true prevents APScheduler jobs and Telegram bot from starting during test runs
  3. Key UI components (navbar, tabs, forms, tables, chart containers) have stable `data-testid` attributes for reliable selection
  4. Test fixture utilities can seed necessary data (tickers, prices, analysis, paper trades) for test scenarios
  5. Test artifacts (test-results/, playwright-report/, screenshot baselines) are properly git-ignored
**Plans:** 4/3 plans complete

Plans:
- [ ] 27-01-PLAN.md — Playwright install + backend HOLO_TEST_MODE guard + dual webServer config + smoke test
- [x] 27-02-PLAN.md — data-testid attributes on all key UI components (pages, navbar, tabs, forms, tables, charts)
- [ ] 27-03-PLAN.md — Test fixture utilities (base fixture, API helpers, test data constants)

### Phase 28: Page Smoke Tests & API Health Checks
**Goal**: Every application route loads without crashing and every API endpoint responds with correct status codes and response shapes
**Depends on**: Phase 27
**Requirements**: SMOKE-01, SMOKE-02, SMOKE-03, SMOKE-04, API-01, API-02, API-03, API-04
**Success Criteria** (what must be TRUE):
  1. All 8 routes (/, /dashboard, /watchlist, /dashboard/paper-trading, /dashboard/portfolio, /dashboard/health, /dashboard/corporate-events, /ticker/[symbol]) load without errors
  2. Navbar navigation between all pages works correctly
  3. Key components (chart containers, data tables, stat cards, tab panels) render on their respective pages
  4. Dark/light theme toggle preserves layout integrity on all pages
  5. All API endpoints (price, analysis, trading signals, paper trading CRUD, health) return correct status codes and response structures, with 404 for invalid tickers and 422 for invalid request bodies
**Plans**: TBD

### Phase 29: User Interaction Tests
**Goal**: Forms, tables, tabs, and interactive UI controls respond correctly to user input and persist state where expected
**Depends on**: Phase 28
**Requirements**: INTERACT-01, INTERACT-02, INTERACT-03, INTERACT-04, INTERACT-05
**Success Criteria** (what must be TRUE):
  1. Paper trading settings form submits successfully and persisted values survive page reload
  2. Trade table sorting (by P&L, status, date) and filtering (by direction, status) produce correctly ordered/filtered results
  3. Watchlist add/remove operations work and persist across page reloads
  4. Tab switching on paper trading dashboard (Overview → Trades → Analytics → Calendar → Settings) renders correct content for each tab
  5. Ticker detail page tabs and interactive chart controls respond to user input
**Plans**: TBD

### Phase 30: Visual Regression Testing
**Goal**: Screenshot baselines capture key page states, chart rendering is verified via canvas checks, and layout holds on mobile viewports
**Depends on**: Phase 28
**Requirements**: VIS-01, VIS-02, VIS-03, VIS-04
**Success Criteria** (what must be TRUE):
  1. Screenshot baselines exist for 5 key pages (Dashboard, Ticker detail, Paper Trading, Portfolio, Watchlist) and `toHaveScreenshot()` comparisons pass
  2. Candlestick chart canvas elements are verified to exist with non-zero dimensions on pages that display charts
  3. Dynamic data areas (prices, timestamps, percentages) are masked in screenshot comparisons to prevent false positives from live data changes
  4. Key pages render correctly at mobile viewport (375px) without layout breakage or content overflow
**Plans**: TBD

### Phase 31: Critical User Flows
**Goal**: Multi-page end-to-end user journeys complete successfully — proving the application works as a cohesive whole
**Depends on**: Phase 29
**Requirements**: FLOW-01, FLOW-02, FLOW-03, FLOW-04
**Success Criteria** (what must be TRUE):
  1. User can navigate: open ticker → view analysis → view trading plan → click Follow → verify paper trade is created successfully
  2. User can navigate paper trading dashboard: view trades → sort/filter table → switch to analytics tab → switch to calendar tab — all content loads correctly
  3. User can add ticker to watchlist → verify it appears on watchlist page → remove it → verify removal persists
  4. User can change paper trading settings → verify settings persist after reload → verify settings affect overview display
**Plans**: TBD

## Progress

**Execution Order:** 27 → 28 → 29 → 30 → 31

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 27. Test Infrastructure & Foundation | 4/3 | Complete   | 2026-04-21 |
| 28. Page Smoke Tests & API Health Checks | 0/0 | Not started | - |
| 29. User Interaction Tests | 0/0 | Not started | - |
| 30. Visual Regression Testing | 0/0 | Not started | - |
| 31. Critical User Flows | 0/0 | Not started | - |
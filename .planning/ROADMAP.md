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
- 🚧 **v8.0 AI Trading Coach** — Phases 43-47 (in progress)

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

### 🚧 v8.0 AI Trading Coach (In Progress)

**Milestone Goal:** Biến Holo thành huấn luyện viên trading cá nhân — mỗi ngày gợi ý cụ thể mua mã nào, ghi nhận kết quả, học từ thói quen, và điều chỉnh chiến lược theo thời gian.

- [ ] **Phase 43: Daily Picks Engine** - AI selects 3-5 daily stock picks with entry/SL/TP, position sizing, safety scoring, and Vietnamese explanations
- [ ] **Phase 44: Trade Journal & P&L** - User logs real trades with auto-calculated P&L including VN fees/tax, optionally linked to AI picks
- [ ] **Phase 45: Coach Dashboard & Pick Performance** - Single-page coach view with today's picks, open trades, performance cards, and full pick history with outcome tracking
- [ ] **Phase 46: Behavior Tracking & Adaptive Strategy** - Track viewing habits and trading patterns, maintain risk level with suggest-then-confirm adjustments and sector preference learning
- [ ] **Phase 47: Goals & Weekly Reviews** - Monthly profit targets with progress tracking, weekly risk tolerance prompt, and AI-generated coaching reviews

## Phase Details

### Phase 43: Daily Picks Engine
**Goal**: Each trading day, the app selects and displays 3-5 specific stock picks with entry/SL/TP, position sizing, and Vietnamese explanations — filtered for the user's capital and scored for safety
**Depends on**: Phase 42 (v7.0 shipped)
**Requirements**: PICK-01, PICK-02, PICK-03, PICK-04, PICK-05, PICK-06, PICK-07
**Success Criteria** (what must be TRUE):
  1. User sees 3-5 daily stock picks on the /coach page, each with a Vietnamese explanation (200-300 words) combining technical, fundamental, and sentiment reasoning for why it was selected
  2. Every pick displays a specific entry price, stop-loss, and take-profit level inherited from the existing trading signal pipeline
  3. Every pick shows position sizing in absolute terms: "Mua X cổ × Y đồng = Z VND (N% vốn)" — based on the user's capital (<50M VND) and 100-share lot sizes
  4. Picks are filtered by affordability (user can buy at least 1 lot of 100 shares) and scored with safety bias — high-ATR, low-ADX, and low-volume tickers are penalized in ranking
  5. Below the main picks, 5-10 "almost selected" tickers are shown with a one-line explanation of why they weren't chosen
**Plans**: TBD
**UI hint**: yes

### Phase 44: Trade Journal & P&L
**Goal**: User can log real buy/sell trades and see accurate profit/loss calculations with VN market fees and taxes, optionally linking trades to daily AI picks
**Depends on**: Phase 43
**Requirements**: JRNL-01, JRNL-02, JRNL-03
**Success Criteria** (what must be TRUE):
  1. User can enter a buy or sell trade (ticker, price, quantity, date, fees) through a validated form on the journal page
  2. The app automatically calculates realized P&L using FIFO matching, including broker fees (0.15% each side) and mandatory sell tax (0.1%) per VN regulations — showing both gross and net P&L
  3. When logging a trade, user can optionally link it to a specific daily pick to track whether they followed the AI recommendation
**Plans**: TBD
**UI hint**: yes

### Phase 45: Coach Dashboard & Pick Performance
**Goal**: The /coach page becomes the daily landing page — displaying today's picks, open trades, performance metrics, and full pick history with actual outcome tracking for every pick
**Depends on**: Phase 44
**Requirements**: CDSH-01, CDSH-02, CDSH-03
**Success Criteria** (what must be TRUE):
  1. The /coach page displays today's picks, currently open trades, and a performance summary all on a single page
  2. Pick history shows actual outcomes for every pick — whether entry was hit, SL was hit, TP was hit, and return after N days — including picks the user didn't trade
  3. Performance cards display win rate, total P&L, average risk-to-reward ratio, and current winning/losing streak
**Plans**: TBD
**UI hint**: yes

### Phase 46: Behavior Tracking & Adaptive Strategy
**Goal**: The app observes the user's trading habits and viewing patterns, then suggests personalized risk adjustments and sector preferences based on actual trade performance
**Depends on**: Phase 45
**Requirements**: BEHV-01, BEHV-02, ADPT-01, ADPT-02
**Success Criteria** (what must be TRUE):
  1. The app records which tickers the user views most frequently, when they view them, and how often — surfacing unconscious biases on the coach dashboard
  2. The app detects trading habit patterns: selling too early when in profit, holding too long when in loss, and impulsive trading after news events
  3. A risk level (1-5) is maintained — after 3 consecutive losses, the app suggests reducing risk level and requires explicit user confirmation before applying the change
  4. The app learns sector preferences from trade results — biasing future picks toward sectors where the user typically profits and away from sectors with consistent losses
**Plans**: TBD
**UI hint**: yes

### Phase 47: Goals & Weekly Reviews
**Goal**: User sets monthly profit targets, tracks progress visually, and receives AI-generated weekly coaching reviews with risk tolerance adjustments
**Depends on**: Phase 46
**Requirements**: GOAL-01, GOAL-02, GOAL-03
**Success Criteria** (what must be TRUE):
  1. User can set a monthly profit target, and a progress bar on the coach dashboard shows real-time tracking of actual P&L toward that goal
  2. Each week the app prompts: "Bạn muốn thận trọng hơn hay mạo hiểm hơn?" — the user's response adjusts the risk level for the following week
  3. Every Sunday, an AI-generated weekly performance review summarizes the week in Vietnamese, highlights good and bad trading habits, and suggests specific improvements
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:** 43 → 44 → 45 → 46 → 47

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 43. Daily Picks Engine | 0/TBD | Not started | - |
| 44. Trade Journal & P&L | 0/TBD | Not started | - |
| 45. Coach Dashboard & Pick Performance | 0/TBD | Not started | - |
| 46. Behavior Tracking & Adaptive Strategy | 0/TBD | Not started | - |
| 47. Goals & Weekly Reviews | 0/TBD | Not started | - |
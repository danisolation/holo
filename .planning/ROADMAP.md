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
- 🚧 **v6.0 AI Backtesting Engine** — Phases 32-34 (in progress)

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

### 🚧 v6.0 AI Backtesting Engine (In Progress)

**Milestone Goal:** Backtest hệ thống AI trên dữ liệu lịch sử 6 tháng (120 phiên) cho 400+ mã, gọi Gemini phân tích thật tại mỗi phiên, mô phỏng mở/đóng lệnh, tổng kết P&L so sánh với VN-Index — delivered via dedicated /backtest dashboard.

- [x] **Phase 32: Backtest Engine & Portfolio Simulation** - Historical session replay with Gemini AI calls, virtual position management, checkpoint/resume, smart batching
- [x] **Phase 33: Analytics & Benchmark Computation** - Post-backtest metrics: AI equity vs VN-Index, win rate, drawdown, Sharpe, sector/confidence/timeframe breakdowns (completed 2026-04-22)
- [ ] **Phase 34: Backtest Dashboard** - /backtest page with config form, real-time progress, equity chart, stats tables, breakdown charts

## Phase Details

### Phase 32: Backtest Engine & Portfolio Simulation
**Goal**: Complete backtest engine can replay historical sessions, call Gemini AI at each session, open/close virtual positions with position sizing and slippage, and track portfolio equity — with checkpoint/resume for the ~53-hour compute workload
**Depends on**: Phase 31 (v5.0 shipped); reuses v4.0 paper trading logic (position sizing, SL/TP monitoring)
**Requirements**: BT-01, BT-02, BT-03, BT-04, BT-05, BT-06, SIM-01, SIM-02, SIM-03, SIM-04
**Success Criteria** (what must be TRUE):
  1. User can configure a backtest specifying time period (1-6 months), initial capital, and slippage percentage — configuration is persisted and validated before engine starts
  2. Engine replays historical sessions sequentially, calling Gemini for technical + combined + trading signal analysis at each session, and opens virtual positions when signals meet entry criteria (using v4.0 position sizing logic with configurable slippage)
  3. Open positions are monitored at each subsequent session for SL hit, TP hit, or timeout expiry — exits reflect configured slippage and P&L is computed per trade
  4. Backtest progress is checkpointed to database — if interrupted (crash, rate limit, restart), user can resume from the last completed session without re-processing prior sessions
  5. All 400+ tickers are processed with smart batching that respects 15 RPM Gemini rate limit, and per-session equity (cash balance, open positions value, cumulative P&L, % return) is tracked
**Plans**: 3 plans

Plans:
- [x] 32-01-PLAN.md — Database models + Alembic migration + API layer
- [x] 32-02-PLAN.md — Backtest engine core (analysis service + engine loop)
- [x] 32-03-PLAN.md — Comprehensive tests + human verification

### Phase 33: Analytics & Benchmark Computation
**Goal**: After backtest completion, system computes comprehensive performance metrics and multi-dimensional breakdowns comparing AI strategy returns vs VN-Index buy-and-hold
**Depends on**: Phase 32
**Requirements**: BENCH-01, BENCH-02, BENCH-03, BENCH-04, BENCH-05
**Success Criteria** (what must be TRUE):
  1. System computes AI strategy equity curve and VN-Index buy-and-hold equity curve over the same backtest period, stored as time-series data ready for charting
  2. Core performance metrics are calculated and persisted: win rate, total P&L (absolute + %), max drawdown (absolute + %), Sharpe ratio, total trade count
  3. Performance breakdown by sector shows win rate and average P&L per industry — revealing which sectors the AI analyzes most accurately
  4. Performance breakdown by confidence level (buckets: 1-3, 4-6, 7-10) shows whether higher-confidence signals produce higher win rates
  5. Performance breakdown by timeframe (short-term vs medium-term) shows which signal durations the AI predicts most accurately
**Plans**: 2 plans

Plans:
- [x] 33-01-PLAN.md — BacktestAnalyticsService + schemas + API endpoints
- [x] 33-02-PLAN.md — Comprehensive tests for analytics service

### Phase 34: Backtest Dashboard
**Goal**: Users can configure, launch, monitor progress, and review full backtest results through a dedicated /backtest page with interactive visualizations
**Depends on**: Phase 32, Phase 33
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06
**Success Criteria** (what must be TRUE):
  1. User can navigate to /backtest page and fill in a configuration form (time period, initial capital, slippage) then click "Run Backtest" to start the engine
  2. While backtest is running, a real-time progress bar displays percentage completion, current session/ticker being processed, and estimated time remaining
  3. After completion, an equity curve area chart (Recharts) overlays AI strategy returns vs VN-Index buy-and-hold returns for visual comparison
  4. A summary statistics panel displays win rate, total P&L, max drawdown, Sharpe ratio, and total trade count in a clear card/table layout
  5. User can browse a detailed trade log table (symbol, direction, entry/exit price, P&L, holding time) and view breakdown charts (bar/pie) by sector, confidence level, and timeframe
**Plans**: 2 plans

Plans:
- [ ] 34-01-PLAN.md — Page + API layer + Config tab + Progress + Results tab (equity chart + stats)
- [ ] 34-02-PLAN.md — Trade log table + Analytics breakdown charts

## Progress

**Execution Order:** 32 → 33 → 34

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 32. Backtest Engine & Portfolio Simulation | 3/3 | ✅ Complete |  |
| 33. Analytics & Benchmark Computation | 2/2 | Complete   | 2026-04-22 |
| 34. Backtest Dashboard | 0/2 | Not started | - |
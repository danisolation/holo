# Roadmap: Holo — Stock Intelligence Platform

## Overview

Holo delivers AI-powered multi-dimensional stock analysis for Vietnamese stock exchanges (HOSE, HNX, UPCOM) through a data pipeline that feeds technical indicators, fundamental metrics, and news sentiment into Google Gemini — surfacing buy/sell/hold recommendations via Telegram bot and real-time web dashboard.

## Milestones

- ✅ **v1.0 Holo Stock Intelligence Platform** — Phases 1-5 (shipped 2026-04-15)
- ✅ **v1.1 Reliability & Portfolio** — Phases 6-11 (shipped 2026-04-17)
- ✅ **v2.0 Full Coverage & Real-Time** — Phases 12-16 (shipped 2026-04-17)
- ✅ **v3.0 Smart Trading Signals** — Phases 17-21 (shipped 2026-04-20)
- 🚧 **v4.0 Paper Trading & Signal Verification** — Phases 22-26 (in progress)

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

### 🚧 v4.0 Paper Trading & Signal Verification (In Progress)

**Milestone Goal:** Kiểm chứng chất lượng tư vấn AI bằng giả lập trading — mọi signal thành lệnh ảo có thể đo lường.

- [x] **Phase 22: Paper Trade Foundation** - PaperTrade model, state machine, P&L calculation, SimulationConfig
- [x] **Phase 23: Position Monitoring & Auto-Track** - Scheduler jobs for auto-tracking signals and daily TP/SL/timeout checks (completed 2026-04-20)
- [x] **Phase 24: API & Analytics Engine** - REST API with full analytics computation and manual follow (completed 2026-04-20)
- [x] **Phase 25: Dashboard Structure & Trade Management** - Paper trading page, trade list, settings, signal outcome history (completed 2026-04-20)
- [x] **Phase 26: Analytics Visualization & Calendar** - Calendar heatmap, streaks, timeframe comparison, performance summaries (completed 2025-07-20)

## Phase Details

### Phase 22: Paper Trade Foundation
**Goal**: Paper trade data model with correct state machine and P&L calculation exists and is verified by unit tests
**Depends on**: Phase 21 (v3.0 trading signals must exist to track)
**Requirements**: PT-02, PT-03, PT-05, PT-07
**Success Criteria** (what must be TRUE):
  1. PaperTrade records can be created with all required fields (symbol, direction, entry, SL, TP1, TP2, status, sizing) and persisted via Alembic migration
  2. State transitions follow correct lifecycle: PENDING → ACTIVE → PARTIAL_TP → CLOSED with no invalid transitions possible
  3. P&L calculation correctly handles partial TP scenarios (50% closed at TP1, remaining 50% at TP2/SL/timeout) in both VND and percentage
  4. Position sizing rounds to 100-share lots based on configurable virtual capital and AI-recommended allocation
  5. SimulationConfig allows setting initial capital, auto-track toggle, and minimum confidence threshold
**Plans:** 2 plans
Plans:
- [ ] 22-01-PLAN.md — Data layer: PaperTrade + SimulationConfig models, Alembic migration 013, model tests
- [ ] 22-02-PLAN.md — Business logic: state machine, P&L calculation, position sizing service + TDD tests

### Phase 23: Position Monitoring & Auto-Track
**Goal**: System automatically creates paper trades from valid signals and monitors positions daily for TP/SL/timeout hits
**Depends on**: Phase 22
**Requirements**: PT-01, PT-04, PT-06, PT-08
**Success Criteria** (what must be TRUE):
  1. Every valid AI signal (score > 0) automatically generates a corresponding paper trade within the same scheduler cycle
  2. Scheduler checks all open positions against daily OHLCV after price crawl completes — SL takes priority on ambiguous bars where both SL and TP breach
  3. Trades exceeding their timeframe (swing: 15 trading days, position: 60 trading days) auto-close at market close price
  4. PENDING trades activate at next trading day's open price (D+1 open entry) — no lookahead bias
  5. Score=0 invalid signals are excluded from auto-tracking with deduplication preventing retries
**Plans:** 2/2 plans complete
Plans:
- [x] 23-01-PLAN.md — Auto-track signals job: creates PENDING paper trades from valid AI signals with dedup
- [x] 23-02-PLAN.md — Position monitor job: daily SL/TP/timeout evaluation, PENDING activation, BEARISH support

### Phase 24: API & Analytics Engine
**Goal**: Users can query paper trading data and analytics through a complete REST API that measures AI signal quality
**Depends on**: Phase 23
**Requirements**: PT-09, AN-01, AN-02, AN-03, AN-04, AN-05, AN-06, AN-07, AN-08, AN-09
**Success Criteria** (what must be TRUE):
  1. User can retrieve overall win rate, total realized P&L (VND + % vs initial capital), and equity curve time-series data
  2. User can compare signal performance by direction (LONG vs BEARISH), AI confidence bracket (LOW/MEDIUM/HIGH), and sector
  3. User can see R:R achieved vs predicted, profit factor (gross profit / gross loss), and expected value per trade
  4. User can manually follow a signal with customized entry/SL/TP to create a new paper trade via API
  5. Max drawdown (% and VND) is computed from equity curve with drawdown periods identified
**Plans:** 2/2 plans complete
Plans:
- [x] 24-01-PLAN.md — Trade CRUD API + manual follow (PT-09) + config endpoints with Pydantic schemas and service layer
- [x] 24-02-PLAN.md — Analytics engine: summary, equity curve, drawdown, direction, confidence, R:R, profit factor, sector (AN-01–AN-09)

### Phase 25: Dashboard Structure & Trade Management
**Goal**: Users can view and manage paper trades through a dedicated dashboard with trade listing, settings, and signal outcome history
**Depends on**: Phase 24
**Requirements**: UI-01, UI-05, UI-07, UI-08
**Success Criteria** (what must be TRUE):
  1. A dedicated paper trading page exists at `/dashboard/paper-trading` with organized tabs (Overview, Trades, Analytics, Calendar, Settings)
  2. User can view a sortable/filterable trade list showing symbol, direction, entry, exit, P&L, status, and AI score
  3. User can configure simulation settings (initial capital, auto-track on/off, min confidence threshold) via a form that persists to backend
  4. User can see the 10 most recent signal outcomes (✅/❌) on each ticker's detail page
**Plans:** 2/2 plans complete
Plans:
- [x] 25-01-PLAN.md — Backend symbol filter + frontend types/hooks/API + dashboard page with tabs + overview tab
- [x] 25-02-PLAN.md — Trade table (UI-07) + settings form (UI-08) + signal outcome history on ticker page (UI-05)
**UI hint**: yes

### Phase 26: Analytics Visualization & Calendar
**Goal**: Users can visualize trading performance patterns through charts, calendar heatmap, streak indicators, and periodic summaries
**Depends on**: Phase 25
**Requirements**: UI-02, UI-03, UI-04, UI-06
**Success Criteria** (what must be TRUE):
  1. GitHub-style calendar heatmap displays daily P&L with green (win) / red (loss) coloring, intensity proportional to magnitude
  2. Current and longest win/loss streaks are prominently displayed, with visual warning when loss streak exceeds 5
  3. Swing vs position timeframe performance can be compared side-by-side (win rate, avg P&L per timeframe)
  4. Weekly and monthly performance summary tables show win rate, P&L, trade count, and average R:R for each period
**Plans**: 2 plans
Plans:
- [x] 26-01-PLAN.md — Backend analytics endpoints (streaks, timeframe, periodic, calendar) + frontend types/hooks/API
- [x] 26-02-PLAN.md — Analytics tab (equity chart, streaks, comparisons) + Calendar tab (heatmap, periodic tables)
**UI hint**: yes

## Progress

**Execution Order:** Phases 22 → 23 → 24 → 25 → 26

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 22. Paper Trade Foundation | 2/2 | ✅ Complete | 2025-07-18 |
| 23. Position Monitoring & Auto-Track | 2/2 | Complete   | 2026-04-20 |
| 24. API & Analytics Engine | 2/2 | Complete   | 2026-04-20 |
| 25. Dashboard Structure & Trade Management | 2/2 | Complete   | 2026-04-20 |
| 26. Analytics Visualization & Calendar | 2/2 | ✅ Complete | 2025-07-20 |
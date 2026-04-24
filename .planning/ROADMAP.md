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
- 🚧 **v9.0 UX Rework & Simplification** — Phases 48-51 (in progress)

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

### 🚧 v9.0 UX Rework & Simplification (In Progress)

**Milestone Goal:** Đơn giản hóa Holo — bỏ features không cần (corporate events, HNX/UPCOM), redesign luồng sử dụng cho rõ ràng, cải thiện AI output dài và hữu ích hơn.

- [x] **Phase 48: Backend Cleanup & Scheduler Simplification** - Remove corporate events, HNX/UPCOM, dead telegram dependency; simplify scheduler to HOSE-only pipeline (2 plans) (completed 2026-04-24)
- [x] **Phase 49: Navigation & Watchlist Migration** - Reduce nav to 5 items, migrate watchlist from localStorage to PostgreSQL, show AI signals on watchlist (2 plans) (completed 2026-04-24)
- [x] **Phase 50: Coach Page Restructure & Trade Flow** - Tab-based Coach layout, pick card trade recording, post-trade next steps (2 plans) (completed 2026-04-24)
- [ ] **Phase 51: AI Analysis Improvement** - Longer structured AI output, reduced batch sizes, frontend structured rendering

## Phase Details

### Phase 48: Backend Cleanup & Scheduler Simplification
**Goal**: All dead features are fully removed — corporate events, HNX/UPCOM support, and telegram dependency — and the scheduler pipeline is simplified to a reliable HOSE-only chain
**Depends on**: Phase 47 (v8.0 shipped)
**Requirements**: CLN-01, CLN-02, CLN-03
**Success Criteria** (what must be TRUE):
  1. The daily scheduler pipeline (price crawl → indicators → AI analysis → picks) runs end-to-end on HOSE tickers only, with the chain trigger rewired from UPCOM to HOSE completion
  2. Corporate events are fully removed: DB table dropped via Alembic migration, API endpoints return 404, scheduler jobs removed, frontend page and nav link gone
  3. All HNX/UPCOM references removed: exchange filter component, exchange badge, exchange store, tickers deactivated in DB, no frontend traces remain
  4. `python-telegram-bot` is removed from requirements.txt and the backend starts cleanly without it
**Plans**: 2 plans

Plans:
- [x] 48-01-PLAN.md — Scheduler rewire (HOSE-only chain) + backend dead code removal (corporate events, deps, tests)
- [x] 48-02-PLAN.md — Frontend dead feature removal (corporate events page, exchange components, HNX/UPCOM references)
**UI hint**: yes

### Phase 49: Navigation & Watchlist Migration
**Goal**: User has a clean, simplified navigation and a server-backed watchlist that persists across devices and shows AI signal data alongside each ticker
**Depends on**: Phase 48
**Requirements**: NAV-01, NAV-02, NAV-03
**Success Criteria** (what must be TRUE):
  1. Navigation shows 4-5 items (reduced from 7), with overlapping pages merged or removed and redirects in place for old routes
  2. User's watchlist is stored in PostgreSQL — adding/removing tickers persists across browsers and devices without data loss
  3. Existing localStorage watchlist data is automatically migrated to the database on first visit, with localStorage cleared after successful migration
  4. Each ticker in the watchlist displays the latest AI signal score and buy/sell/hold recommendation alongside the ticker name
**Plans**: 2 plans

Plans:
- [x] 49-01-PLAN.md — Backend watchlist DB migration + REST API with AI signal enrichment
- [x] 49-02-PLAN.md — Frontend navigation simplification + watchlist server migration
**UI hint**: yes

### Phase 50: Coach Page Restructure & Trade Flow
**Goal**: The Coach page is interactive and action-oriented — user can record trades directly from AI picks with one click and sees clear next steps after every trade
**Depends on**: Phase 49
**Requirements**: FLOW-01, FLOW-02, FLOW-03
**Success Criteria** (what must be TRUE):
  1. Each pick card displays a "Ghi nhận giao dịch" button that opens a trade entry dialog pre-filled with the pick's ticker, entry price, SL, and TP
  2. The Coach page uses a tab-based layout (Picks / Nhật ký / Mục tiêu) instead of a single long scroll — each tab loads its own content
  3. After recording a trade, the app immediately shows the open position with SL/TP monitoring status and clear guidance on what to do next
**Plans**: 2 plans

Plans:
- [x] 50-01-PLAN.md — Trade flow components: dialog prefill, pick card button, post-trade guidance
- [x] 50-02-PLAN.md — Coach page tab restructure (Picks / Nhật ký / Mục tiêu) + trade flow wiring
**UI hint**: yes

### Phase 51: AI Analysis Improvement
**Goal**: AI analysis output is longer, structured into clear sections, and rendered on the frontend with visual hierarchy — not a plain text block
**Depends on**: Phase 48
**Requirements**: AI-01, AI-02, AI-03
**Success Criteria** (what must be TRUE):
  1. AI analysis output includes distinct sections (tóm tắt, mức giá quan trọng, rủi ro, hành động cụ thể) — each clearly labeled and separated
  2. Batch sizes are reduced and token/thinking limits increased, producing multi-paragraph analysis for every ticker without output truncation
  3. The frontend renders AI analysis as structured sections with headings and visual separation, replacing the previous plain text block display
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:** 48 → 49 → 50 → 51

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 48. Backend Cleanup & Scheduler Simplification | 2/2 | Complete    | 2026-04-24 |
| 49. Navigation & Watchlist Migration | 2/2 | Complete    | 2026-04-24 |
| 50. Coach Page Restructure & Trade Flow | 2/2 | Complete    | 2026-04-24 |
| 51. AI Analysis Improvement | 0/0 | Not started | - |
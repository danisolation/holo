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
- 🚧 **v7.0 Consolidation & Quality Upgrade** — Phases 35-42 (in progress)

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

### 🚧 v7.0 Consolidation & Quality Upgrade (In Progress)

**Milestone Goal:** Audit toàn diện → xóa code dư thừa, gộp logic chồng chéo, nâng cấp AI validation và UX — giảm LOC, tăng maintainability và trải nghiệm dùng.

- [x] **Phase 35: Database & Model Cleanup** - Remove dead tables, unused columns via Alembic migrations
- [x] **Phase 36: Frontend Cleanup & Utility Extraction** - Remove dead components, consolidate format/config utilities
- [x] **Phase 37: Backend Analytics Consolidation** - Extract shared analytics logic, composition pattern, merge schemas
- [x] **Phase 38: Backend Architecture Refactor** - Split AIAnalysisService and BacktestEngine into focused modules
- [x] **Phase 39: AI Quality Upgrade** - Anti-hallucination validation for scores, prices, and prompt input
- [ ] **Phase 40: Frontend Component Consolidation** - Shared trade table, equity chart, watchlist & page role cleanup
- [ ] **Phase 41: Performance Optimization** - WebSocket off-hours scheduling, chart lazy-loading
- [ ] **Phase 42: Test Maintenance** - Update all unit tests and E2E tests after refactoring

## Phase Details

### Phase 35: Database & Model Cleanup
**Goal**: All dead database columns and unused tables are removed — the data model reflects only what the system actually uses
**Depends on**: Phase 34 (v6.0 shipped)
**Requirements**: CLN-01, CLN-02, CLN-03, CLN-04
**Success Criteria** (what must be TRUE):
  1. The price_alert table no longer exists in the database, and no backend code references PriceAlert model, service methods, or handler imports
  2. The daily_price table no longer has an adjusted_close column — all queries, models, and schemas that referenced it are updated
  3. The financial table no longer has revenue or net_profit columns — the Financial model and any API schemas reflect only actual columns
  4. The news_article table no longer has a source column — model and schemas are consistent with the migration
**Plans:** 2/2 plans executed ✅
Plans:
- [x] 35-01-PLAN.md — Remove price_alerts table and news_article.source column (CLN-01, CLN-04)
- [x] 35-02-PLAN.md — Remove adjusted_close and Financial revenue/net_profit columns (CLN-02, CLN-03)

### Phase 36: Frontend Cleanup & Utility Extraction
**Goal**: Dead frontend components are removed and duplicated utility functions/config objects are consolidated into shared modules
**Depends on**: Phase 35
**Requirements**: CLN-05, CLN-06, FRN-03
**Success Criteria** (what must be TRUE):
  1. The DilutionBadge component file no longer exists and no imports reference it anywhere in the codebase
  2. A single `src/lib/format.ts` module exports formatVND, formatCompactVND, formatDateVN — all components import from this shared module instead of local duplicates
  3. STATUS_CONFIG and SIGNAL_CONFIG are defined once in `src/lib/constants.ts` — all components that used inline copies now import from the shared file
**Plans**: 1/1 plans executed ✅
Plans:
- [x] 36-01-PLAN.md — Remove DilutionBadge, extract format utilities, consolidate config constants
**UI hint**: yes

### Phase 37: Backend Analytics Consolidation
**Goal**: Duplicated analytics logic between paper trading and backtesting is consolidated into shared abstractions with clean separation of concerns
**Depends on**: Phase 36
**Requirements**: BCK-01, BCK-02, BCK-03
**Success Criteria** (what must be TRUE):
  1. An AnalyticsBase class provides shared computation methods (win rate, P&L, drawdown, sector breakdown, confidence breakdown, timeframe breakdown) — both BacktestAnalyticsService and PaperTradeAnalyticsService use it instead of duplicating logic
  2. BacktestAnalysisService uses composition pattern with AnalysisContextStrategy (Live vs Backtest) instead of inheritance — context switching is explicit and testable
  3. A TradeBaseResponse schema provides common fields (symbol, direction, entry/exit price, P&L, dates) — BacktestTradeResponse and PaperTradeResponse extend it with context-specific fields only
**Plans**: 1/1 plans executed ✅
Plans:
- [x] 37-01-PLAN.md — Extract TradeBaseResponse, AnalyticsBase shared utilities (BCK-02 deferred to Phase 38)

### Phase 38: Backend Architecture Refactor
**Goal**: The two largest service files are broken into focused, single-responsibility modules — easier to test, maintain, and extend
**Depends on**: Phase 37
**Requirements**: BCK-04, BCK-05
**Success Criteria** (what must be TRUE):
  1. AIAnalysisService (400+ LOC) is replaced by 4 focused classes: ContextBuilder (assembles data for prompts), GeminiClient (handles API calls), AnalysisStorage (persists results), AnalysisOrchestrator (coordinates the pipeline)
  2. BacktestEngine (300+ LOC) is replaced by 4 focused modules: BacktestRunner (orchestrates session replay), TradeActivator (opens positions from signals), PositionEvaluator (checks SL/TP/timeout), EquitySnapshot (tracks portfolio value)
  3. All existing API endpoints that used AIAnalysisService and BacktestEngine continue to work identically after the refactor — no behavior changes
**Plans**: 1/1 plans executed ✅
Plans:
- [x] 38-01-PLAN.md — Split AIAnalysisService into analysis/ package + BacktestEngine into backtest/ package

### Phase 39: AI Quality Upgrade
**Goal**: AI analysis output is validated more rigorously — preventing hallucinated prices, inconsistent score-signal pairs, and malformed prompt inputs
**Depends on**: Phase 38 (AIAnalysisService refactored into modules)
**Requirements**: AIQ-01, AIQ-02, AIQ-03
**Success Criteria** (what must be TRUE):
  1. When AI returns a score < 5, the signal cannot be buy or strong_buy — the system rejects or corrects inconsistent score-signal pairs automatically
  2. Trading signal entry prices are validated against the ticker's 52-week high/low range — prices outside this range are flagged as invalid (score=0)
  3. News titles are sanitized (control characters stripped, length enforced) before being sent to Gemini — preventing prompt corruption from malformed source data
**Plans**: 1/1 plans executed ✅
Plans:
- [x] 39-01-PLAN.md — Score-signal consistency, 52-week bounds, news sanitization

### Phase 40: Frontend Component Consolidation
**Goal**: Duplicated frontend components are replaced with shared, reusable components — and page roles are clearly differentiated so users know where to find what
**Depends on**: Phase 36
**Requirements**: FRN-01, FRN-02, FRN-04, FRN-05
**Success Criteria** (what must be TRUE):
  1. A single GenericTradesTable component renders trades for portfolio, paper-trading, and backtest pages — with context-specific columns configured via props, not three separate table implementations
  2. A shared EquityCurveChart component renders equity curves on both paper-trading and backtest pages — replacing two separate chart implementations
  3. Watchlist management happens exclusively on the /watchlist page — the /dashboard page no longer shows watchlist cards
  4. The "/" route shows Market Overview (heatmap-focused) and "/dashboard" shows Portfolio Dashboard (portfolio-focused) — with no duplicated market stats between them
**Plans**: TBD
**UI hint**: yes

### Phase 41: Performance Optimization
**Goal**: System resources are used efficiently — no unnecessary WebSocket polling off-hours, no heavy chart library loaded on pages that don't need it
**Depends on**: Phase 40
**Requirements**: PRF-01, PRF-02
**Success Criteria** (what must be TRUE):
  1. WebSocket real-time price streaming automatically deactivates outside trading hours (9:00-15:00 VN weekdays) and reactivates when market opens — no manual intervention needed
  2. The lightweight-charts library (~150KB) is loaded only when the user navigates to /ticker/[symbol] — other pages do not include this bundle in their JavaScript payload
**Plans**: TBD
**UI hint**: yes

### Phase 42: Test Maintenance
**Goal**: All tests pass after the refactoring and consolidation changes — confirming zero regressions across the entire codebase
**Depends on**: Phase 41 (all code changes complete)
**Requirements**: TST-01, TST-02
**Success Criteria** (what must be TRUE):
  1. All 560+ backend unit tests pass after the service refactoring — tests updated for new class/module structure (AnalyticsBase, composition pattern, split AIAnalysisService, split BacktestEngine)
  2. All 119+ E2E tests pass after the frontend consolidation — tests updated for removed components (DilutionBadge, watchlist cards on dashboard), renamed imports, and page role changes
**Plans**: TBD

## Progress

**Execution Order:** 35 → 36 → 37 → 38 → 39 → 40 → 41 → 42

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 35. Database & Model Cleanup | 2/2 | ✅ Complete | 2025-07-22 |
| 36. Frontend Cleanup & Utility Extraction | 1/1 | ✅ Complete | 2025-07-22 |
| 37. Backend Analytics Consolidation | 1/1 | ✅ Complete | 2025-07-22 |
| 38. Backend Architecture Refactor | 1/1 | ✅ Complete | 2025-07-22 |
| 39. AI Quality Upgrade | 1/1 | ✅ Complete | 2025-07-22 |
| 40. Frontend Component Consolidation | 0/0 | Not started | - |
| 41. Performance Optimization | 0/0 | Not started | - |
| 42. Test Maintenance | 0/0 | Not started | - |
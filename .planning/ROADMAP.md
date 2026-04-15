# Roadmap: Holo — Stock Intelligence Platform

## Overview

Holo delivers AI-powered multi-dimensional stock analysis for 400 HOSE tickers through a data pipeline that feeds technical indicators, fundamental metrics, and news sentiment into Google Gemini — surfacing buy/sell/hold recommendations via Telegram bot and web dashboard. The build follows the data flow: reliable data first, then deterministic analysis, then AI synthesis, then delivery channels (bot before dashboard for immediate personal utility).

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Data Foundation** - PostgreSQL schema, vnstock integration, OHLCV + financial crawling with automated scheduling
- [x] **Phase 2: Technical & Fundamental Analysis** - Indicator computation with `ta` library + Gemini scoring for technical signals and fundamental health
- [x] **Phase 3: Sentiment & Combined Intelligence** - News sentiment analysis + unified 3-dimensional buy/sell/hold recommendations with confidence and explanation
- [ ] **Phase 4: Telegram Bot** - Trading signal alerts, price triggers, and daily market summaries delivered to phone
- [ ] **Phase 5: Dashboard & Visualization** - Next.js web dashboard with candlestick charts, indicator overlays, watchlist, ticker details, and market heatmap

## Phase Details

### Phase 1: Data Foundation
**Goal**: 400 HOSE tickers' price and financial data flowing reliably into PostgreSQL on a daily automated schedule
**Depends on**: Nothing (first phase)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04
**Success Criteria** (what must be TRUE):
  1. User can query OHLCV data for any of the 400 HOSE tickers from PostgreSQL
  2. 1-2 years of historical price data is backfilled and queryable by ticker + date range
  3. Financial reports (P/E, P/B, revenue, profit) are stored for all tickers
  4. Daily crawl runs automatically after market close (~15:15 UTC+7) without manual intervention
**Plans:** 3 plans
Plans:
- [x] 01-01-PLAN.md — Project bootstrap, database schema & Alembic migration with yearly partitioning
- [x] 01-02-PLAN.md — vnstock async crawler, ticker management, price & financial data services
- [x] 01-03-PLAN.md — APScheduler automation, API endpoints for health/status/triggers/backfill

### Phase 2: Technical & Fundamental Analysis
**Goal**: Every ticker has computed technical indicators and AI-powered scoring for technical signals and fundamental health
**Depends on**: Phase 1
**Requirements**: AI-01, AI-02
**Success Criteria** (what must be TRUE):
  1. Each ticker has RSI, MACD, MA, and Bollinger Bands computed and stored after each daily crawl
  2. Gemini produces a bullish/bearish/neutral technical signal with reasoning for any ticker
  3. Gemini produces a fundamental health score based on actual financial metrics for any ticker
**Plans:** 3 plans
Plans:
- [x] 02-01-PLAN.md — Models, migration, schemas, dependencies & config (TechnicalIndicator + AIAnalysis tables, Pydantic Gemini schemas)
- [x] 02-02-PLAN.md — IndicatorService (ta library computation) + AIAnalysisService (Gemini integration)
- [x] 02-03-PLAN.md — Scheduler job chaining, API endpoints, unit tests

### Phase 3: Sentiment & Combined Intelligence
**Goal**: AI delivers a unified buy/sell/hold recommendation combining technical, fundamental, and sentiment dimensions with confidence level and Vietnamese explanation
**Depends on**: Phase 2
**Requirements**: AI-03, AI-04, AI-05, AI-06
**Success Criteria** (what must be TRUE):
  1. Gemini analyzes Vietnamese news articles and produces a sentiment score per ticker
  2. Combined recommendation (mua/bán/giữ) integrates all three analysis dimensions
  3. Each recommendation includes a confidence level (1-10) reflecting data quality and signal alignment
  4. Each recommendation includes a natural language explanation in Vietnamese
**Plans:** 3 plans
Plans:
- [x] 03-01-PLAN.md — NewsArticle model, migration 003, Pydantic schemas, deps & config
- [x] 03-02-PLAN.md — CafeF crawler + AIAnalysisService sentiment & combined methods
- [x] 03-03-PLAN.md — Scheduler chain extension, API endpoints, unit tests

### Phase 4: Telegram Bot
**Goal**: User receives timely trading intelligence and market summaries on their phone via Telegram without opening a browser
**Depends on**: Phase 3
**Requirements**: BOT-01, BOT-02, BOT-03
**Success Criteria** (what must be TRUE):
  1. Telegram bot sends an alert when AI detects a notable trading signal for watched tickers
  2. User receives a notification when a ticker crosses a price threshold they configured
  3. User receives a daily market summary (top movers, signal changes, watchlist status) via Telegram
**Plans:** 3 plans
Plans:
- [ ] 04-01-PLAN.md — Models (UserWatchlist, PriceAlert), migration 004, python-telegram-bot dep, Telegram config
- [ ] 04-02-PLAN.md — Bot module: TelegramBot lifecycle, 7 command handlers, HTML message formatter
- [ ] 04-03-PLAN.md — AlertService, scheduler jobs (signal/price/summary), FastAPI lifespan integration, tests

### Phase 5: Dashboard & Visualization
**Goal**: User can visually explore market data, AI insights, and manage their watchlist through a responsive web dashboard
**Depends on**: Phase 3
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06
**Success Criteria** (what must be TRUE):
  1. User can view interactive candlestick charts with technical indicator overlays (MA, RSI, MACD, BB) for any ticker
  2. User can add/remove tickers to a watchlist for quick monitoring
  3. Clicking a ticker shows a detail page combining chart, key financial metrics, and AI verdict
  4. Market overview page shows a sector-based heatmap of all 400 tickers
  5. All dashboard pages are usable on mobile browser with responsive layout
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5
Note: Phase 4 and Phase 5 are independent after Phase 3 — could execute in either order.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Foundation | 3/3 | ✅ Complete | 2026-04-15 |
| 2. Technical & Fundamental Analysis | 3/3 | ✅ Complete | 2026-04-15 |
| 3. Sentiment & Combined Intelligence | 3/3 | ✅ Complete | 2026-04-15 |
| 4. Telegram Bot | 0/3 | Not started | - |
| 5. Dashboard & Visualization | 0/? | Not started | - |

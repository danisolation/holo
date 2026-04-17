# Roadmap: Holo — Stock Intelligence Platform

## Overview

Holo delivers AI-powered multi-dimensional stock analysis for 400 HOSE tickers through a data pipeline that feeds technical indicators, fundamental metrics, and news sentiment into Google Gemini — surfacing buy/sell/hold recommendations via Telegram bot and web dashboard.

## Milestones

- ✅ **v1.0 Holo Stock Intelligence Platform** — Phases 1-5 (shipped 2026-04-15)
- 🔄 **v1.1 Reliability & Portfolio** — Phases 6-11

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

### v1.1 Reliability & Portfolio

- [ ] **Phase 6: Resilience Foundation** — Circuit breakers, job tracking, dead-letter queue, auto-retry (4 plans)
- [ ] **Phase 7: Corporate Actions** — Crawl VCI events, adjust historical prices, cascade indicator recompute
- [ ] **Phase 8: Portfolio Core** — Trade entry, FIFO lots, realized/unrealized P&L, portfolio summary
- [ ] **Phase 9: AI Prompt Improvements** — System instruction, few-shot, scoring rubric, temperature tuning
- [ ] **Phase 10: System Health Dashboard** — Health API + frontend page with job status, error rates, manual triggers
- [ ] **Phase 11: Telegram Portfolio** — /buy, /sell, /portfolio, /pnl, daily P&L notification

## Phase Details

### Phase 6: Resilience Foundation
**Goal**: System recovers gracefully from failures, tracks all job execution, and prevents cascade failures via circuit breakers
**Depends on**: Phase 5 (v1.0 complete)
**Requirements**: ERR-01, ERR-02, ERR-03, ERR-04, ERR-05, ERR-06, ERR-07
**Success Criteria** (what must be TRUE):
  1. Failed tickers in AI analysis batches are automatically retried once, and remaining tickers proceed regardless of individual failures
  2. Permanently failed operations appear in a dead letter table with error details, retry count, and timestamps
  3. External API calls (VCI, Gemini, CafeF) stop after N consecutive failures and auto-resume after cooldown period
  4. Every scheduled job logs execution start/end, status (success/partial/fail), and result summary to job_executions table
  5. Complete crawler failure triggers a Telegram notification to the user within minutes
**Plans**: 4 plans

Plans:
- [x] 06-01-PLAN.md — Resilience foundation: DB models, migration, circuit breaker, config
- [x] 06-02-PLAN.md — Services + Telegram failure notifications
- [x] 06-03-PLAN.md — Circuit breaker integration into crawlers
- [x] 06-04-PLAN.md — Job function refactoring + resilience test suite

### Phase 7: Corporate Actions
**Goal**: Historical prices accurately reflect stock splits, dividends, and bonus shares so charts and analysis use correct data
**Depends on**: Phase 6
**Requirements**: CORP-01, CORP-02, CORP-03, CORP-04, CORP-05
**Success Criteria** (what must be TRUE):
  1. User views historical price charts with adjusted_close values that account for splits, dividends, and bonus shares
  2. Corporate events are crawled from VCI and stored in database with classified event types (cash dividend, stock dividend, bonus, split)
  3. New corporate events detected in the daily check trigger automatic price adjustment and indicator recompute for affected tickers
  4. Each event type (cash dividend, stock dividend, bonus shares, stock split) produces correct adjusted_close values using VN market formulas
**Plans**: TBD

### Phase 8: Portfolio Core
**Goal**: User can track personal trades and see accurate FIFO-based P&L on all positions
**Depends on**: Phase 7
**Requirements**: PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, PORT-07
**Success Criteria** (what must be TRUE):
  1. User can enter buy and sell trades specifying ticker, quantity, price, date, and fees
  2. User can view current holdings with quantity, average cost, market value, and per-position P&L
  3. Cost basis is calculated using FIFO method with explicit lot tracking (first bought = first sold)
  4. User can see both realized P&L on closed positions and unrealized P&L on open positions using latest market price
  5. Portfolio summary shows total invested, current market value, and total return percentage; trade history is sortable and filterable
**Plans**: TBD
**UI hint**: yes

### Phase 9: AI Prompt Improvements
**Goal**: AI analysis produces more consistent, accurately calibrated recommendations with structured output reliability
**Depends on**: Phase 6
**Requirements**: AI-07, AI-08, AI-09, AI-10, AI-11, AI-12, AI-13
**Success Criteria** (what must be TRUE):
  1. AI prompts use system_instruction for persona separation and include few-shot examples for each analysis type
  2. Scoring rubric with explicit anchors (1-2 weak through 9-10 very strong) is applied consistently across analysis types
  3. Technical analysis prompt includes latest close price and price-vs-SMA percentages for grounded quantitative context
  4. Structured output failures trigger one retry at lower temperature before falling back to JSON parse
  5. Language usage is consistent per analysis type (English for technical/fundamental, Vietnamese for combined/sentiment) and temperature is tuned per type
**Plans**: TBD

### Phase 10: System Health Dashboard
**Goal**: User can monitor system health, data freshness, and error rates from a dedicated dashboard page
**Depends on**: Phase 6
**Requirements**: HEALTH-01, HEALTH-02, HEALTH-03, HEALTH-04, HEALTH-05, HEALTH-06, HEALTH-07
**Success Criteria** (what must be TRUE):
  1. Health page at `/dashboard/health` shows data freshness per data type with stale data flags and last update timestamps
  2. Each scheduled job displays color-coded status (green/yellow/red) based on last execution result
  3. Error rate per job over the last 7 days is visible as a metric or chart
  4. User can manually trigger crawl, indicator computation, or AI analysis jobs from the health dashboard
  5. Database connection pool status (active/idle connections) is displayed on the health page
**Plans**: TBD
**UI hint**: yes

### Phase 11: Telegram Portfolio
**Goal**: User can manage portfolio and receive P&L updates directly through Telegram commands
**Depends on**: Phase 8
**Requirements**: TBOT-01, TBOT-02, TBOT-03, TBOT-04, TBOT-05, TBOT-06
**Success Criteria** (what must be TRUE):
  1. `/buy <ticker> <qty> <price>` records a buy trade and `/sell <ticker> <qty> <price>` records a sell trade showing realized P&L
  2. `/portfolio` command displays all current holdings with per-position and total P&L
  3. `/pnl <ticker>` command shows detailed P&L breakdown with FIFO lot information
  4. Daily portfolio P&L notification is sent at 16:00 alongside the existing market summary
  5. Daily summary message highlights owned tickers first with position-specific P&L context
**Plans**: TBD

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 6. Resilience Foundation | 0/4 | Planning complete | - |
| 7. Corporate Actions | 0/? | Not started | - |
| 8. Portfolio Core | 0/? | Not started | - |
| 9. AI Prompt Improvements | 0/? | Not started | - |
| 10. System Health Dashboard | 0/? | Not started | - |
| 11. Telegram Portfolio | 0/? | Not started | - |

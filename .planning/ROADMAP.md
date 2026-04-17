# Roadmap: Holo — Stock Intelligence Platform

## Overview

Holo delivers AI-powered multi-dimensional stock analysis for 400 HOSE tickers through a data pipeline that feeds technical indicators, fundamental metrics, and news sentiment into Google Gemini — surfacing buy/sell/hold recommendations via Telegram bot and web dashboard.

## Milestones

- ✅ **v1.0 Holo Stock Intelligence Platform** — Phases 1-5 (shipped 2026-04-15)
- ✅ **v1.1 Reliability & Portfolio** — Phases 6-11 (shipped 2026-04-17)
- 🚧 **v2.0 Full Coverage & Real-Time** — Phases 12-16 (in progress)

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

### 🚧 v2.0 Full Coverage & Real-Time

- [x] **Phase 12: Multi-Market Foundation** — HNX/UPCOM crawling, exchange filters, tiered AI analysis (completed 2026-04-17)
- [x] **Phase 13: Portfolio Enhancements** — Dividend tracking, performance/allocation charts, trade edit/delete, CSV import (completed 2026-04-17)
- [ ] **Phase 14: Corporate Actions Enhancements** — Rights issues, ex-date alerts, event calendar, adjusted/raw toggle
- [ ] **Phase 15: Health & Monitoring** — Gemini usage tracking, pipeline timeline, Telegram health alerts
- [ ] **Phase 16: Real-Time WebSocket** — WebSocket price streaming, 30s polling, market-hours auto-connect

## Phase Details

### Phase 12: Multi-Market Foundation
**Goal**: Dashboard and analysis cover all Vietnamese stock exchanges (HOSE, HNX, UPCOM), not just HOSE
**Depends on**: Phase 11 (v1.1 complete)
**Requirements**: MKT-01, MKT-02, MKT-03, MKT-04
**Success Criteria** (what must be TRUE):
  1. User can view OHLCV data and charts for HNX and UPCOM tickers alongside existing HOSE tickers
  2. User can filter stock lists, market overview, and heatmap by exchange (HOSE/HNX/UPCOM/All)
  3. HNX and UPCOM tickers are crawled daily on staggered schedules without exceeding the pipeline window or starving the DB pool
  4. AI analysis runs daily for all HOSE tickers and watchlisted HNX/UPCOM tickers; remaining HNX/UPCOM tickers are analyzed on-demand only
**Plans:** 4/4 plans complete

Plans:
- [x] 12-01-PLAN.md — Backend services + config: exchange-parameterized TickerService, PriceService
- [x] 12-02-PLAN.md — Backend scheduler + API + AI tiering: staggered crons, exchange API params, tiered analysis
- [x] 12-03-PLAN.md — Frontend foundation + market overview: types, store, hooks, CSS, ExchangeFilter, heatmap
- [x] 12-04-PLAN.md — Frontend pages + on-demand analysis: watchlist, dashboard, ticker detail, AnalyzeNow

**UI hint**: yes

### Phase 13: Portfolio Enhancements
**Goal**: Portfolio management supports dividend income, visual analytics, trade corrections, and bulk import
**Depends on**: Phase 12
**Requirements**: PORT-08, PORT-09, PORT-10, PORT-11, PORT-12
**Success Criteria** (what must be TRUE):
  1. User can see dividend income credited to held positions when corporate events have matching record dates
  2. User can view portfolio total value over time as a line chart showing historical performance
  3. User can view portfolio allocation as a pie chart broken down by ticker or by sector
  4. User can edit or delete existing trades with all FIFO lots and P&L automatically recalculated
  5. User can import trades from a broker CSV file with format preview and dry-run validation before committing
**Plans:** 5/5 plans complete

Plans:
- [x] 13-01-PLAN.md — Backend service: dividend income + performance snapshots + allocation data
- [x] 13-02-PLAN.md — Backend service: FIFO recalculation + trade edit/delete + CSV import parsing
- [x] 13-03-PLAN.md — Backend API: all new portfolio endpoints (performance, allocation, trade CRUD, CSV import)
- [x] 13-04-PLAN.md — Frontend: types, hooks, charts, dividend card, page layout
- [x] 13-05-PLAN.md — Frontend: trade edit/delete dialogs, CSV import dialog, visual verification

**UI hint**: yes

### Phase 14: Corporate Actions Enhancements
**Goal**: Corporate actions system covers rights issues, proactively alerts on ex-dates, and provides calendar and chart views
**Depends on**: Phase 12
**Requirements**: CORP-06, CORP-07, CORP-08, CORP-09
**Success Criteria** (what must be TRUE):
  1. Rights issues are tracked from VNDirect with dilution impact displayed on affected portfolio positions
  2. User receives Telegram alerts before upcoming ex-dates for watchlisted and held tickers
  3. User can view a corporate events calendar on the dashboard filterable by event type
  4. User can toggle between adjusted and raw price display on candlestick charts
**Plans:** 2/4 plans executed

Plans:
- [x] 14-01-PLAN.md — Backend foundation: RIGHTS_ISSUE type, alert_sent column, migration, crawler update
- [x] 14-02-PLAN.md — Ex-date alert service: Telegram alerts for upcoming ex-dates, scheduler job
- [ ] 14-03-PLAN.md — Calendar API + price toggle: corporate events endpoint, adjusted param on prices
- [ ] 14-04-PLAN.md — Frontend: calendar page, price toggle on chart, dilution badge on holdings

**UI hint**: yes

### Phase 15: Health & Monitoring
**Goal**: System health monitoring covers API usage budgets, pipeline performance visualization, and proactive Telegram alerts
**Depends on**: Phase 12
**Requirements**: HEALTH-08, HEALTH-09, HEALTH-10
**Success Criteria** (what must be TRUE):
  1. Health dashboard shows Gemini API usage (tokens consumed, requests made) against free-tier daily limits
  2. Health dashboard shows pipeline execution timeline with per-step duration as a Gantt-style bar chart
  3. System sends Telegram notification when health checks detect sustained errors or stale data beyond configured thresholds
**Plans**: TBD
**UI hint**: yes

### Phase 16: Real-Time WebSocket
**Goal**: Dashboard displays live price updates during market hours without manual page refresh
**Depends on**: Phase 12
**Requirements**: RT-01, RT-02, RT-03
**Success Criteria** (what must be TRUE):
  1. Dashboard receives and displays price updates via WebSocket during market hours without manual refresh
  2. System polls VCI at 30-second intervals for watchlist and portfolio tickers during market hours
  3. WebSocket connection automatically establishes at market open (9:00 UTC+7) and tears down after market close (14:45 UTC+7)
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:** Phases 12 → 13 → 14 → 15 → 16

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 12. Multi-Market Foundation | 4/4 | Complete    | 2026-04-17 |
| 13. Portfolio Enhancements | 5/5 | Complete    | 2026-04-17 |
| 14. Corporate Actions Enhancements | 2/4 | In Progress|  |
| 15. Health & Monitoring | 0/? | Not started | - |
| 16. Real-Time WebSocket | 0/? | Not started | - |

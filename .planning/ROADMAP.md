# Roadmap: Holo — Stock Intelligence Platform

## Overview

Holo delivers AI-powered multi-dimensional stock analysis for Vietnamese stock exchanges (HOSE, HNX, UPCOM) through a data pipeline that feeds technical indicators, fundamental metrics, and news sentiment into Google Gemini — surfacing buy/sell/hold recommendations via Telegram bot and real-time web dashboard.

## Milestones

- ✅ **v1.0 Holo Stock Intelligence Platform** — Phases 1-5 (shipped 2026-04-15)
- ✅ **v1.1 Reliability & Portfolio** — Phases 6-11 (shipped 2026-04-17)
- ✅ **v2.0 Full Coverage & Real-Time** — Phases 12-16 (shipped 2026-04-17)
- 🚧 **v3.0 Smart Trading Signals** — Phases 17-21 (in progress)

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

### 🚧 v3.0 Smart Trading Signals

- [x] **Phase 17: Enhanced Technical Indicators** — ATR, ADX, Stochastic computation + display (completed 2026-04-20)
- [x] **Phase 18: Support & Resistance Levels** — Pivot points, Fibonacci retracements (completed 2026-04-20)
- [ ] **Phase 19: AI Trading Signal Pipeline** — Dual-direction schema, Gemini prompt, batch processing (3 plans)
- [ ] **Phase 20: Trading Plan Dashboard Panel** — Trading plan component on ticker detail page
- [ ] **Phase 21: Chart Price Line Overlays** — Entry/SL/TP lines on candlestick chart

## Phase Details

### Phase 17: Enhanced Technical Indicators
**Goal**: User can view volatility (ATR), trend strength (ADX), and momentum (Stochastic) indicators for any ticker
**Depends on**: Phase 16 (v2.0 complete)
**Requirements**: SIG-01, SIG-02, SIG-03
**Success Criteria** (what must be TRUE):
  1. User can view ATR (Average True Range) value for any ticker, reflecting recent price volatility
  2. User can view ADX (Average Directional Index) value for any ticker, indicating trend strength on a 0-100 scale
  3. User can view Stochastic oscillator (%K/%D) values for any ticker, indicating overbought/oversold conditions
  4. New indicators compute daily as part of the existing indicator pipeline without extending the pipeline window beyond current limits
**Plans**: 2 plans
Plans:
- [x] 17-01-PLAN.md — Backend: Tests + DB migration + indicator computation + API
- [x] 17-02-PLAN.md — Frontend: shadcn Accordion + 3 new chart components
**UI hint**: yes

### Phase 18: Support & Resistance Levels
**Goal**: User can view computed support/resistance and Fibonacci retracement price levels for any ticker
**Depends on**: Phase 17
**Requirements**: SIG-04, SIG-05
**Success Criteria** (what must be TRUE):
  1. User can view pivot-point-based support and resistance levels (S1/S2/R1/R2) for any ticker
  2. User can view Fibonacci retracement levels (23.6%, 38.2%, 50%, 61.8%) calculated from recent swing high/low for any ticker
  3. Support/resistance and Fibonacci levels update daily as part of the indicator pipeline
**Plans**: 2 plans
Plans:
- [x] 18-01-PLAN.md — Backend: Migration 011 + model + schema + service computation + API + tests
- [ ] 18-02-PLAN.md — Frontend: IndicatorData type + SupportResistanceCard component + page integration
**UI hint**: yes

### Phase 19: AI Trading Signal Pipeline
**Goal**: AI generates dual-direction trading plans with concrete entry/SL/TP targets, risk/reward, and position sizing for each analyzed ticker
**Depends on**: Phase 18
**Requirements**: PLAN-01, PLAN-02, PLAN-03, PLAN-04, PLAN-05, PLAN-06
**Success Criteria** (what must be TRUE):
  1. Trading signal analysis runs daily as a 5th analysis type, producing dual-direction (LONG + BEARISH) output with independent confidence scores (1-10) per ticker
  2. Each signal includes specific entry price, stop-loss, and take-profit targets for the recommended direction, anchored to computed support/resistance levels
  3. Each signal includes risk/reward ratio, position sizing (% of portfolio), and timeframe recommendation (swing or position)
  4. Each signal includes Vietnamese-language rationale explaining the trading logic for each direction
  5. Batch processing respects Gemini 15 RPM rate limit with reduced batch size (~15 tickers) and completes within the daily pipeline window
**Plans**: 3 plans
Plans:
- [x] 19-01-PLAN.md — Schema contracts + DB migration + config settings
- [ ] 19-02-PLAN.md — Service core: Gemini extension + context/prompt + validation
- [ ] 19-03-PLAN.md — Pipeline wiring: scheduler job + API endpoints

### Phase 20: Trading Plan Dashboard Panel
**Goal**: Trading plans are displayed in a dedicated panel on the ticker detail page with full LONG and BEARISH analysis
**Depends on**: Phase 19
**Requirements**: DISP-01
**Success Criteria** (what must be TRUE):
  1. User can view a Trading Plan panel on the ticker detail page showing LONG and BEARISH analysis side-by-side
  2. Panel displays entry/SL/TP targets, risk/reward ratio, timeframe, and position sizing for the recommended direction
  3. Panel shows Vietnamese rationale text and color-coded confidence indicators for each direction
**Plans**: TBD
**UI hint**: yes

### Phase 21: Chart Price Line Overlays
**Goal**: Entry, stop-loss, and take-profit levels are visualized as horizontal price lines on the candlestick chart
**Depends on**: Phase 20
**Requirements**: DISP-02
**Success Criteria** (what must be TRUE):
  1. User can see entry price, stop-loss, and take-profit as distinct colored horizontal lines overlaid on the candlestick chart
  2. Price lines are visually distinguishable with different colors and labels (e.g., green entry, red stop-loss, blue take-profit)
  3. Price lines update automatically when the user navigates between tickers or when new trading signals are generated
**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:** Phases 17 → 18 → 19 → 20 → 21

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 17. Enhanced Technical Indicators | 2/2 | Complete   | 2026-04-20 |
| 18. Support & Resistance Levels | 2/2 | Complete   | 2026-04-20 |
| 19. AI Trading Signal Pipeline | 1/3 | In Progress|  |
| 20. Trading Plan Dashboard Panel | 0/0 | Not started | - |
| 21. Chart Price Line Overlays | 0/0 | Not started | - |
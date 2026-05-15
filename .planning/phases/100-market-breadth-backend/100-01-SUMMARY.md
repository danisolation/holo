---
phase: 100-market-breadth-backend
plan: 01
subsystem: backend/market-breadth
tags: [market-breadth, a-d-line, ma-breadth, highs-lows, api]
dependency_graph:
  requires: [DailyPrice, TechnicalIndicator, TickerService]
  provides: [MarketBreadthService, GET /api/market/breadth]
  affects: [frontend market dashboard]
tech_stack:
  added: []
  patterns: [pandas batch computation, TTLCache, rolling window]
key_files:
  created:
    - backend/app/services/market_breadth_service.py
    - backend/app/schemas/market_breadth.py
    - backend/app/api/market.py
    - backend/tests/test_market_breadth_service.py
  modified:
    - backend/app/api/router.py
decisions:
  - Used pandas groupby+diff for A/D line (consistent with IndicatorService pattern)
  - JOIN DailyPrice+TechnicalIndicator for MA breadth (reuse pre-computed SMA values)
  - Rolling 252-day window for 52-week highs/lows with 370 calendar day buffer
  - TTLCache 300s with 16 entries for date range combos
metrics:
  duration: ~3 minutes
  completed: 2026-05-15
  tasks_completed: 2
  tasks_total: 2
  test_count: 8
  test_pass: 8
---

# Phase 100 Plan 01: Market Breadth Backend Summary

MarketBreadthService computing 3 HOSE market-wide health indicators (A/D line via pandas diff, MA breadth via TechnicalIndicator JOIN, 52-week highs/lows via rolling 252-day window) exposed at GET /api/market/breadth with 300s TTLCache.

## What Was Built

### MarketBreadthService (`backend/app/services/market_breadth_service.py`)
- **get_ad_line()**: Fetches DailyPrice with 10-day calendar buffer, uses pandas `groupby('ticker_id').close.diff()` to classify tickers as advancing/declining/unchanged per day.
- **get_ma_breadth()**: JOINs DailyPrice with TechnicalIndicator on (ticker_id, date), counts tickers with close > sma_50 and close > sma_200. NULL SMAs excluded from respective counts.
- **get_highs_lows()**: Fetches 370 calendar days of price history, computes `rolling(252).max()/.min()` per ticker, flags new highs/lows. Tickers with <252 days excluded.
- **get_all_breadth()**: Orchestrates all 3, returns dict matching MarketBreadthResponse.

### Schemas (`backend/app/schemas/market_breadth.py`)
- ADLineItem, MABreadthItem, HighsLowsItem, MarketBreadthResponse

### API Endpoint (`backend/app/api/market.py`)
- GET /api/market/breadth with optional start_date/end_date query params (default: 90 days)
- TTLCache (300s TTL, 16 entries) prevents redundant computation
- Registered in router.py as market_router

### Tests (`backend/tests/test_market_breadth_service.py`)
- 8 tests covering: basic A/D line, all advancing, MA breadth, NULL SMA exclusion, new highs, new lows, empty data, single ticker
- All pass (507 total suite tests pass)

## Decisions Made

1. **Pandas approach over raw SQL window functions** — Consistent with existing IndicatorService pattern; simpler for rolling window computation.
2. **Reuse TechnicalIndicator.sma_50/sma_200** — Avoids recomputing SMAs; leverages existing daily computation pipeline.
3. **370 calendar day buffer for 252 trading days** — Conservative buffer ensures enough trading days even with holidays/weekends.

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | cb35c89 | test(100-01): add failing tests for market breadth service |
| 2 | 02e93b4 | feat(100-01): implement MarketBreadthService with A/D line, MA breadth, 52-week highs/lows |
| 3 | 889de34 | feat(100-01): add GET /api/market/breadth endpoint with TTLCache |

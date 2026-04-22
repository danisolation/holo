---
phase: 33-analytics-benchmark-computation
plan: "01"
subsystem: backtest-analytics
tags: [analytics, benchmark, vnindex, sharpe-ratio, backtest]
dependency_graph:
  requires:
    - "32-01: BacktestRun, BacktestTrade, BacktestEquity models"
    - "32-02: BacktestEngine populates equity/trade data"
  provides:
    - "BacktestAnalyticsService for on-demand analytics computation"
    - "GET /backtest/runs/{id}/analytics endpoint"
    - "GET /backtest/runs/{id}/benchmark endpoint"
  affects:
    - "Phase 34: Dashboard will consume these endpoints"
tech_stack:
  added: []
  patterns:
    - "Session-per-request analytics service (follows PaperTradeAnalyticsService)"
    - "SQLAlchemy case() for bucket grouping"
    - "VnstockCrawler for VN-Index data with graceful fallback"
    - "Equity curve peak-to-trough drawdown calculation"
    - "Annualized Sharpe ratio: (mean/std) * sqrt(252)"
key_files:
  created:
    - backend/app/services/backtest_analytics_service.py
  modified:
    - backend/app/schemas/backtest.py
    - backend/app/api/backtest.py
decisions:
  - "Used statistics.mean/stdev for Sharpe rather than numpy to keep lightweight"
  - "VN-Index benchmark uses try/except with None fallback (not hard failure)"
  - "Holding days computed via PostgreSQL date subtraction (closed_date - entry_date)"
  - "Confidence bucket labels include ranges: 'LOW (1-3)', 'MEDIUM (4-6)', 'HIGH (7-10)'"
metrics:
  duration: "~4 min"
  completed: "2026-04-22"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 2
requirements:
  - BENCH-01
  - BENCH-02
  - BENCH-03
  - BENCH-04
  - BENCH-05
---

# Phase 33 Plan 01: BacktestAnalyticsService + API Endpoints Summary

**One-liner:** On-demand backtest analytics with Sharpe ratio, max drawdown, VN-Index benchmark comparison, and sector/confidence/timeframe breakdowns via 2 new API endpoints.

## What Was Built

### BacktestAnalyticsService (backend/app/services/backtest_analytics_service.py)

New service class with 5 computation methods + 1 helper, following `PaperTradeAnalyticsService` patterns:

1. **`get_performance_summary(run_id)`** (BENCH-02) — Win rate, total P&L, P&L%, avg P&L per trade, max drawdown (VND + %), and annualized Sharpe ratio from equity curve daily returns.

2. **`get_benchmark_comparison(run_id)`** (BENCH-01) — AI equity curve aligned with VN-Index buy-and-hold returns. Fetches VN-Index OHLCV via `VnstockCrawler.fetch_ohlcv("VNINDEX", ...)`. Graceful fallback: returns `vnindex_return_pct: None` if fetch fails.

3. **`get_sector_breakdown(run_id)`** (BENCH-03) — JOINs BacktestTrade with Ticker, groups by `Ticker.industry` (coalesced to "Unknown"), shows per-sector win rate + P&L.

4. **`get_confidence_breakdown(run_id)`** (BENCH-04) — Buckets trades using SQLAlchemy `case()`: LOW (1-3), MEDIUM (4-6), HIGH (7-10). Per-bucket win rate, avg P&L, avg P&L%.

5. **`get_timeframe_breakdown(run_id)`** (BENCH-05) — Buckets by actual holding days (`closed_date - entry_date`): SHORT (1-5d), MEDIUM (6-15d), LONG (16+d). Per-bucket stats including avg holding days.

**Helper `_get_run(run_id)`** — Validates run exists and status == COMPLETED, raises 404/400 otherwise.

### Pydantic Schemas (backend/app/schemas/backtest.py)

7 new response schemas appended after existing schemas:
- `PerformanceSummaryResponse` — 10 fields covering all BENCH-02 metrics
- `BenchmarkPointResponse` — per-date AI equity + VN-Index return
- `BenchmarkComparisonResponse` — summary + time-series data list
- `SectorBreakdownResponse` — per-sector stats
- `ConfidenceBreakdownResponse` — per-confidence-bucket stats
- `TimeframeBreakdownResponse` — per-holding-period stats
- `BacktestAnalyticsResponse` — combined response wrapping summary + all breakdowns

### API Endpoints (backend/app/api/backtest.py)

2 new endpoints on `/backtest` router:
- `GET /backtest/runs/{run_id}/analytics` → `BacktestAnalyticsResponse`
- `GET /backtest/runs/{run_id}/benchmark` → `BenchmarkComparisonResponse`

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Mitigation | Implementation |
|-----------|-----------|----------------|
| T-33-02 | VN-Index fetch wrapped in try/except | Returns partial response (AI data only) on failure, logs error |
| T-33-04 | VN-Index DataFrame validated | Checks for `close` and `time` columns, skips gracefully if malformed |

## Verification Results

| Check | Result |
|-------|--------|
| Service import | ✅ `BacktestAnalyticsService` imports cleanly |
| Schema import | ✅ All 7 new schemas import cleanly |
| Endpoint registration | ✅ Both `/analytics` and `/benchmark` registered on router |
| Existing tests | ✅ 50/50 backtest tests pass (no regressions) |

## Commits

| # | Hash | Message | Files |
|---|------|---------|-------|
| 1 | `b43e1a4` | feat(33-01): BacktestAnalyticsService with 5 computation methods | `backtest_analytics_service.py` (new) |
| 2 | `be48d7f` | feat(33-01): analytics schemas and API endpoints | `schemas/backtest.py`, `api/backtest.py` |

## Self-Check: PASSED

All 4 files verified present. Both commits (b43e1a4, be48d7f) verified in git log.

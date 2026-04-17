---
phase: 12-multi-market-foundation
plan: "02"
subsystem: backend-services
tags: [scheduler, api-exchange-filter, tiered-ai-analysis, on-demand-endpoint]
dependency_graph:
  requires: [exchange-parameterized-ticker-service, exchange-parameterized-price-service]
  provides: [staggered-exchange-scheduler, exchange-filtered-api, tiered-ai-analysis, on-demand-analysis-endpoint]
  affects: [backend/app/scheduler/jobs.py, backend/app/scheduler/manager.py, backend/app/api/tickers.py, backend/app/api/analysis.py, backend/app/services/ai_analysis_service.py]
tech_stack:
  added: []
  patterns: [staggered-cron-jobs, exchange-query-param-validation, ticker-filter-passthrough, on-demand-background-analysis]
key_files:
  created:
    - backend/tests/test_ai_analysis_tiered.py
  modified:
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
    - backend/app/api/tickers.py
    - backend/app/api/analysis.py
    - backend/app/services/ai_analysis_service.py
    - backend/tests/test_scheduler.py
    - backend/tests/test_api.py
    - backend/tests/test_telegram.py
decisions:
  - Chain triggers from daily_price_crawl_upcom (last exchange) to ensure all data available before indicators
  - Daily summary moved to 18:30 to accommodate staggered pipeline finishing later
  - analyze_all_tickers ticker_filter parameter enables single-ticker and filtered analysis without refactoring run_* methods
  - On-demand analysis runs all 4 types (technical, fundamental, sentiment, combined) in background
metrics:
  duration: "12m 19s"
  completed: "2026-04-17T10:53:28Z"
  tasks: 2
  tests_added: 8
  tests_total: 222
  files_changed: 8
requirements:
  - MKT-02
  - MKT-03
  - MKT-04
---

# Phase 12 Plan 02: Staggered Scheduler, Exchange API, Tiered AI Analysis Summary

**One-liner:** Staggered exchange cron jobs (HOSE 15:30, HNX 16:00, UPCOM 16:30) with exchange-filtered API endpoints, tiered HNX/UPCOM watchlist-only AI analysis capped at 50, and on-demand single-ticker analysis endpoint.

## What Was Built

### Task 1: Staggered Scheduler Jobs + API Exchange Params

**Scheduler (jobs.py + manager.py):**
- `daily_price_crawl_for_exchange(exchange)` — parameterized crawl with same resilience pattern (retry + DLQ)
- `VALID_EXCHANGES = ("HOSE", "HNX", "UPCOM")` — shared validation tuple
- `EXCHANGE_CRAWL_SCHEDULE` — staggered: HOSE 15:30, HNX 16:00, UPCOM 16:30
- Chain triggers from `daily_price_crawl_upcom` (last exchange) → indicators → AI pipeline
- `daily_hnx_upcom_analysis` job — chained after `daily_combined`, parallel with signal alerts
- `weekly_ticker_refresh` now syncs all 3 exchanges sequentially
- `daily_summary_send` moved to 18:30 (pipeline finishes later with 3 staggered crawls)

**API (tickers.py):**
- `ALLOWED_EXCHANGES = {"HOSE", "HNX", "UPCOM"}` — ASVS V5 input validation
- `GET /api/tickers/?exchange=HOSE` — filters by exchange, returns 400 for invalid values
- `GET /api/tickers/market-overview?exchange=HNX` — exchange filter + exchange field in response
- `TickerResponse` and `MarketTickerResponse` now include `exchange` field

### Task 2: Tiered AI Analysis + On-Demand Endpoint (TDD)

**AIAnalysisService (ai_analysis_service.py):**
- `analyze_watchlisted_tickers(exchanges, max_extra=50)` — queries UserWatchlist × Ticker for target exchanges, caps at 50, runs technical + fundamental analysis
- `analyze_single_ticker(ticker_id, symbol)` — runs all 4 analysis types for one ticker
- `analyze_all_tickers` now accepts `ticker_filter: dict[str, int] | None` — all 4 `run_*` methods pass through to avoid re-querying ticker list
- `run_technical_analysis`, `run_fundamental_analysis`, `run_sentiment_analysis`, `run_combined_analysis` — all accept `ticker_filter` param

**API (analysis.py):**
- `POST /api/analysis/{symbol}/analyze-now` — on-demand endpoint, verifies ticker exists (404 if not), runs background analysis via `analyze_single_ticker`

### Test Coverage
- 8 new tests across 3 files:
  - `test_ai_analysis_tiered.py`: caps at max_extra, exchange filter in query, return shape, single ticker calls all types, on-demand 200, on-demand 404
  - `test_api.py`: TestExchangeFilter with invalid exchange validation (list_tickers + market_overview)
- Updated 5 existing tests in `test_scheduler.py` for new job IDs
- Updated 2 existing tests in `test_telegram.py` for new job IDs
- Full suite: **222 passed, 0 failed**

## Commits

| # | Hash | Type | Description |
|---|------|------|-------------|
| 1 | `80206fc` | feat | Staggered exchange scheduler jobs + API exchange params + tests |
| 2 | `9004301` | test | Failing tests for tiered AI analysis + on-demand endpoint (RED) |
| 3 | `e8f7ba6` | feat | Tiered AI analysis + on-demand endpoint + ticker_filter (GREEN) |

## Backward Compatibility

- Existing `daily_price_crawl` function kept unchanged (for manual triggers)
- `analyze_all_tickers(analysis_type="both")` works exactly as before when `ticker_filter=None`
- All `run_*` methods default `ticker_filter=None` — same behavior when called without filter
- `list_tickers` and `market_overview` work without exchange param (returns all, same as before)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_telegram.py referencing old daily_price_crawl job ID**
- **Found during:** Task 2, full suite run
- **Issue:** `test_configure_jobs_registers_summary_cron` and `test_price_crawl_chains_to_both_indicators_and_price_alerts` in `test_telegram.py` asserted `daily_price_crawl` in job_ids, which no longer exists after scheduler refactor
- **Fix:** Updated to use `daily_price_crawl_hose` and `daily_price_crawl_upcom` respectively
- **Files modified:** backend/tests/test_telegram.py
- **Commit:** `e8f7ba6`

## Threat Mitigations

| Threat ID | Disposition | Implementation |
|-----------|-------------|----------------|
| T-12-03 (Tampering: exchange param) | mitigated | ALLOWED_EXCHANGES set validates input, 400 on invalid |
| T-12-04 (DoS: analyze-now) | mitigated | BackgroundTasks prevents blocking; 404 for invalid ticker |
| T-12-05 (Tampering: analyze-now symbol) | mitigated | _get_ticker_by_symbol validates symbol exists in DB, 404 if not |
| T-12-06 (DoS: Gemini RPD budget) | mitigated | max_extra=50 cap on watchlisted HNX/UPCOM analysis |

## Self-Check: PASSED

All files exist, all commits verified.

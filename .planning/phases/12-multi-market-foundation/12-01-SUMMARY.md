---
phase: 12-multi-market-foundation
plan: "01"
subsystem: backend-services
tags: [multi-exchange, ticker-service, price-service, data-foundation]
dependency_graph:
  requires: []
  provides: [exchange-parameterized-ticker-service, exchange-parameterized-price-service, per-exchange-deactivation]
  affects: [backend/app/services/ticker_service.py, backend/app/services/price_service.py]
tech_stack:
  added: []
  patterns: [per-exchange-config-dict, exchange-scoped-deactivation, optional-exchange-filter]
key_files:
  created:
    - backend/tests/test_ticker_service_multi.py
  modified:
    - backend/app/services/ticker_service.py
    - backend/app/services/price_service.py
decisions:
  - EXCHANGE_MAX_TICKERS dict in ticker_service.py (not config.py) — consistent with existing MAX_TICKERS pattern
  - Default exchange="HOSE" for fetch_and_sync_tickers — backward compatible
  - Default exchange=None for query methods — returns all exchanges when unfiltered
metrics:
  duration: "4m 8s"
  completed: "2026-04-17T10:38:46Z"
  tasks: 1
  tests_added: 8
  tests_total: 213
  files_changed: 3
requirements:
  - MKT-01
  - MKT-03
---

# Phase 12 Plan 01: Multi-Exchange Service Parameterization Summary

**One-liner:** Exchange-parameterized TickerService (HOSE=400, HNX=200, UPCOM=200) with per-exchange deactivation scoping to prevent cross-exchange data corruption, plus PriceService exchange filtering.

## What Was Built

### TickerService Multi-Exchange Support
- **EXCHANGE_MAX_TICKERS** config: `{"HOSE": 400, "HNX": 200, "UPCOM": 200}`
- `fetch_and_sync_tickers(exchange="HOSE")` — fetches listing for specified exchange, limits to per-exchange max
- **Critical fix:** Deactivation query now scoped with `Ticker.exchange == exchange` — prevents syncing HNX from deactivating all HOSE tickers (T-12-01 threat mitigated)
- `get_active_symbols(exchange=None)` — optional exchange filter, returns all if None
- `get_ticker_id_map(exchange=None)` — optional exchange filter, returns all if None
- Upsert sets `exchange` field correctly on both INSERT and ON CONFLICT UPDATE

### PriceService Exchange Filtering
- `crawl_daily(exchange=None)` — passes exchange filter through to `get_ticker_id_map`
- When exchange is specified, only crawls tickers for that exchange
- When None, crawls all active tickers (backward compatible)

### Test Coverage
- 8 new tests in `test_ticker_service_multi.py`:
  - HNX max 200 tickers limit
  - HOSE max 400 tickers limit
  - UPCOM max 200 tickers limit
  - Deactivation SQL includes exchange filter (critical corruption prevention)
  - `get_active_symbols` with exchange filter
  - `get_active_symbols` without filter returns all
  - `get_ticker_id_map` with exchange filter
  - Upsert sets exchange field correctly

## Commits

| # | Hash | Type | Description |
|---|------|------|-------------|
| 1 | `0f522e9` | test | Failing tests for multi-exchange ticker service (RED) |
| 2 | `78c5905` | feat | Parameterize TickerService + PriceService for multi-exchange support (GREEN) |

## Backward Compatibility

All new parameters have default values matching previous behavior:
- `fetch_and_sync_tickers()` → defaults to `exchange="HOSE"` (same as before)
- `get_active_symbols()` → defaults to `exchange=None` (returns all, same as before)
- `get_ticker_id_map()` → defaults to `exchange=None` (returns all, same as before)
- `crawl_daily()` → defaults to `exchange=None` (crawls all, same as before)

15 existing callers verified compatible. Full test suite: **213 passed, 0 failed**.

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations

| Threat ID | Disposition | Implementation |
|-----------|-------------|----------------|
| T-12-01 (Tampering: cross-exchange deactivation) | mitigated | `Ticker.exchange == exchange` added to deactivation WHERE clause, verified by test |
| T-12-02 (Info disclosure: exchange field) | accepted | Non-sensitive public market data |

## Self-Check: PASSED

All files exist, all commits verified.

---
phase: 13-portfolio-enhancements
plan: "03"
subsystem: portfolio-api
tags: [portfolio, api, endpoints, performance, allocation, trade-edit, csv-import, backend]
dependency_graph:
  requires: [PortfolioService, CSVImportService, portfolio_schemas, get_performance_data, get_allocation_data, update_trade, delete_trade]
  provides: [GET_performance_endpoint, GET_allocation_endpoint, PUT_trades_endpoint, DELETE_trades_endpoint, POST_import_endpoint]
  affects: [portfolio_router, portfolio_api]
tech_stack:
  added: []
  patterns: [multipart-file-upload, encoding-detection-fallback, dry-run-toggle]
key_files:
  created: []
  modified:
    - backend/app/api/portfolio.py
    - backend/tests/test_portfolio.py
decisions:
  - "CSV import endpoint passes PortfolioService instance to CSVImportService.import_trades to avoid circular dependency"
  - "File size check (5MB) before encoding decode to fail fast on oversized uploads"
  - "Encoding fallback: UTF-8 first, then CP1252 for Vietnamese broker exports"
metrics:
  duration: "2m"
  completed: "2026-04-17"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 1
  tests_total: 60
  files_modified: 2
---

# Phase 13 Plan 03: Portfolio API Endpoints Summary

Five new API routes exposing service methods from Plans 01/02: performance chart data, allocation breakdown, trade edit/delete with FIFO recalculation, and CSV import with dry-run/commit modes.

## One-liner

Five new portfolio API endpoints: GET performance/allocation analytics, PUT/DELETE trade edit/delete, POST CSV import with dry-run toggle and encoding detection.

## What Was Built

### Task 1: Analytics + Dividend API Endpoints

**GET /portfolio/performance** — Accepts `period` query param validated via regex `^(1M|3M|6M|1Y|ALL)$` (default 3M). Calls `PortfolioService.get_performance_data(period)`, returns `PerformanceResponse` with `data: list[PerformanceDataPoint]` and `period`. Per PORT-09, T-13-09 mitigated.

**GET /portfolio/allocation** — Accepts `mode` query param validated via regex `^(ticker|sector)$` (default ticker). Calls `PortfolioService.get_allocation_data(mode)`, computes `total_value` from response data, returns `AllocationResponse`. Per PORT-10.

**Existing endpoints verified** — `/holdings` and `/summary` already include `dividend_income` field in responses via Plan 01 schema updates (HoldingResponse.dividend_income, PortfolioSummaryResponse.dividend_income). Per PORT-08.

Updated imports to include all new schema types: `PerformanceResponse`, `PerformanceDataPoint`, `AllocationResponse`, `AllocationItem`, `TradeUpdateRequest`, `CSVDryRunResponse`, `CSVImportResponse`, and `CSVImportService`.

### Task 2: Trade Edit/Delete + CSV Import API Endpoints

**PUT /portfolio/trades/{trade_id}** — Accepts `TradeUpdateRequest` body (Pydantic-validated side/quantity/price/trade_date/fees). Calls `PortfolioService.update_trade()` which triggers FIFO recalculation. Returns 404 for missing trade, 400 for validation errors. Per PORT-11, T-13-07 mitigated.

**DELETE /portfolio/trades/{trade_id}** — Path param `trade_id` auto-validated as int. Calls `PortfolioService.delete_trade()` which triggers FIFO recalculation. Returns 404 for missing trade, 400 for validation errors. Per PORT-11, T-13-10 mitigated.

**POST /portfolio/import** — Multipart file upload with `dry_run` query toggle (default true). T-13-08 mitigated: 5MB file size limit enforced before decoding. Encoding detection: UTF-8 first, CP1252 fallback for Vietnamese broker exports. `dry_run=true` calls `CSVImportService.dry_run()` returning per-row validation preview. `dry_run=false` calls `CSVImportService.import_trades(csv_text, portfolio_service)` — passes `PortfolioService` instance to avoid circular dependency. Per PORT-12.

**TestAPIRouter updated** — Route count assertion updated from 4 to 9. New test `test_new_portfolio_routes_registered` verifies `/performance`, `/allocation`, `/import`, `/trades/{trade_id}` paths exist.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `499de55` | feat(13-03): add GET /performance and GET /allocation API endpoints |
| 2 | `003c6e4` | feat(13-03): add trade edit/delete and CSV import API endpoints |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] CSV import_trades requires portfolio_service parameter**
- **Found during:** Task 2
- **Issue:** Plan code example called `service.import_trades(csv_text)` but actual `CSVImportService.import_trades()` signature requires a `portfolio_service` parameter for `record_trade` calls
- **Fix:** Created `PortfolioService` instance in the same session and passed it: `csv_service.import_trades(csv_text, portfolio_service)`
- **Files modified:** backend/app/api/portfolio.py
- **Commit:** 003c6e4

## Decisions Made

1. **CSV import PortfolioService injection** — Import endpoint creates both CSVImportService and PortfolioService from the same session, passes PortfolioService to import_trades to avoid circular dependency
2. **File size check before decode** — Check 5MB limit on raw bytes before attempting UTF-8/CP1252 decode to fail fast
3. **Encoding fallback order** — UTF-8 → CP1252 covers both standard CSVs and Vietnamese broker exports (VNDirect/SSI)

## Test Results

```
60 passed, 4 warnings in 4.24s
```

- 59 existing tests: all pass (FIFO, P&L, validation, recording, schema, dividend, performance, allocation, recalculate, update/delete, CSV import)
- 1 new test: test_new_portfolio_routes_registered
- Router count test updated: 4 → 9 routes

## Self-Check: PASSED

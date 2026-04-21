---
phase: 28
plan: 2
subsystem: e2e-tests
tags: [api-tests, smoke-tests, playwright, paper-trading, error-handling]
dependency_graph:
  requires: [27-1, 28-1]
  provides: [api-smoke-tests, paper-trading-api-tests, api-error-tests]
  affects: [frontend/e2e]
tech_stack:
  added: []
  patterns: [api-request-fixture, structure-based-assertions, non-destructive-config-roundtrip]
key_files:
  created:
    - frontend/e2e/api-smoke.spec.ts
    - frontend/e2e/api-paper-trading.spec.ts
    - frontend/e2e/api-errors.spec.ts
  modified: []
decisions:
  - Analysis endpoints accept 200|404 as valid (no data = valid response)
  - Paper trading POST endpoints excluded to avoid test data creation
  - Added 400 error tests beyond plan scope for exchange/month validation
metrics:
  duration: 2m
  completed: "2026-04-21"
---

# Phase 28 Plan 2: API Health Check Tests Summary

**One-liner:** Playwright API tests covering all 7 endpoint groups (health, tickers, analysis, corporate-events, portfolio, paper-trading) with structure-based assertions and error handling validation for 404/422/400.

## What Was Done

### Task 1: API Smoke Tests — All Endpoint Groups (3265ea0)

Created `frontend/e2e/api-smoke.spec.ts` with 22 tests across 5 endpoint groups:

- **Health (7 tests):** `/health`, `/health/jobs`, `/health/data-freshness`, `/health/db-pool`, `/health/summary`, `/health/pipeline-timeline`, `/health/gemini-usage`
- **Tickers (3 tests):** `/tickers`, `/tickers/{symbol}/prices`, `/tickers/market-overview`
- **Analysis (7 tests):** `/analysis/{symbol}/summary`, `indicators`, `trading-signal`, `technical`, `fundamental`, `sentiment`, `combined` — all accept 200|404
- **Corporate Events (1 test):** `/corporate-events`
- **Portfolio (5 tests):** `/portfolio/summary`, `holdings`, `trades`, `performance`, `allocation`

### Task 2: Paper Trading API Tests (fd2b52e)

Created `frontend/e2e/api-paper-trading.spec.ts` with 16 tests:

- **Config (2 tests):** GET + PUT with non-destructive round-trip
- **Trades (2 tests):** GET with and without query filters
- **Analytics (12 tests):** `summary`, `equity-curve`, `drawdown`, `direction`, `confidence`, `risk-reward`, `profit-factor`, `sector`, `streaks`, `timeframe`, `periodic`, `calendar`

POST endpoints (`/trades/follow`, `/trades/{id}/close`) excluded to avoid creating test data — those are integration test scope (Phase 29).

### Task 3: API Error Handling Tests (3b3f0b6)

Created `frontend/e2e/api-errors.spec.ts` with 9 tests:

- **404 Not Found (6 tests):** Invalid ticker for prices/analysis/indicators/trading-signal, non-existent paper trade ID, non-existent API route
- **422 Validation (3 tests):** Invalid config body type, invalid days param, invalid direction filter
- **400 Bad Request (2 tests):** Invalid exchange filter, invalid corporate events month format

## Deviations from Plan

### Auto-added Improvements

**1. [Rule 2 - Coverage] Added health/summary, health/pipeline-timeline, health/gemini-usage tests**
- Plan only listed jobs/data-freshness/db-pool under health
- Backend has 7 health endpoints; all now tested

**2. [Rule 2 - Coverage] Added all 7 analysis sub-endpoints**
- Plan only listed summary/indicators/trading-signal
- Backend has technical/fundamental/sentiment/combined too; all now tested

**3. [Rule 2 - Coverage] Added portfolio trades/performance/allocation tests**
- Plan only listed summary/holdings
- Backend has 5 GET portfolio endpoints; all now tested

**4. [Rule 2 - Coverage] Added 400 Bad Request error tests**
- Plan only covered 404/422
- Exchange validation and month format validation return 400; now tested

## Decisions Made

1. **Analysis 200|404 tolerance:** All analysis endpoints accept both 200 and 404 as valid because analysis data may not exist for a ticker
2. **Non-destructive PUT config:** Read current config first, write back same value — prevents altering live data
3. **POST endpoint exclusion:** Paper trading follow/close endpoints excluded to prevent test data creation in live DB

## Known Stubs

None — all tests are complete with real assertions.

## Self-Check: PASSED

- [x] `frontend/e2e/api-smoke.spec.ts` exists (22 tests)
- [x] `frontend/e2e/api-paper-trading.spec.ts` exists (16 tests)
- [x] `frontend/e2e/api-errors.spec.ts` exists (9 tests)
- [x] Commit 3265ea0 verified
- [x] Commit fd2b52e verified
- [x] Commit 3b3f0b6 verified

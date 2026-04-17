---
phase: 13-portfolio-enhancements
plan: "01"
subsystem: portfolio-service
tags: [portfolio, dividend, performance, allocation, backend]
dependency_graph:
  requires: [corporate_events, lots, daily_prices, trades, tickers]
  provides: [get_dividend_income, get_performance_data, get_allocation_data, PerformanceDataPoint, PerformanceResponse, AllocationItem, AllocationResponse]
  affects: [get_holdings, get_summary, HoldingResponse, PortfolioSummaryResponse]
tech_stack:
  added: []
  patterns: [CASH_DIVIDEND-lots-join, trade-replay-chronological, allocation-grouping]
key_files:
  created: []
  modified:
    - backend/app/services/portfolio_service.py
    - backend/app/schemas/portfolio.py
    - backend/tests/test_portfolio.py
decisions:
  - "Dividend income computed by joining CASH_DIVIDEND events with lots held before record_date — no new table needed"
  - "Performance data replays trades chronologically against bulk-fetched daily prices — single SELECT for T-13-01 DoS mitigation"
  - "Allocation uses get_holdings() internally for consistent market_value source"
  - "Null sector grouped under 'Khác' label for Vietnamese UI"
metrics:
  duration: "5m"
  completed: "2026-04-17"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 16
  tests_total: 34
  files_modified: 3
---

# Phase 13 Plan 01: Portfolio Service Enhancements Summary

Dividend income from CASH_DIVIDEND corporate events joined with FIFO lots, daily performance snapshots via trade-replay against DailyPrice, and allocation breakdown by ticker/sector with percentage computation.

## One-liner

Dividend income via CASH_DIVIDEND×lots join, performance snapshots via chronological trade replay, allocation grouping by ticker/sector with percentages.

## What Was Built

### Task 1: Dividend Income Computation (TDD)

**get_dividend_income(ticker_id)** — Queries `corporate_events` for `CASH_DIVIDEND` events with valid `record_date`, then for each event finds lots held on that record_date (`buy_date <= record_date AND remaining_quantity > 0`), summing `dividend_amount × remaining_quantity`.

**Holdings updates** — `get_holdings()` now calls `get_dividend_income(ticker_id)` per holding and includes `dividend_income` and `sector` (from Ticker model) in each holding dict.

**Summary updates** — `get_summary()` aggregates `dividend_income` from all holdings.

**Schema updates** — `HoldingResponse` gains `dividend_income: float = 0` and `sector: str | None = None`. `PortfolioSummaryResponse` gains `dividend_income: float = 0`.

**Tests (8):** Basic computation, multiple events, no events returns 0, skips lots bought after record_date, ignores non-cash events, holdings includes dividend_income, holdings includes sector, summary includes dividend_income.

### Task 2: Performance Data + Allocation Data (TDD)

**get_performance_data(period)** — Replays trades chronologically against bulk-fetched daily prices. Maintains `positions: Dict[ticker_id, int]` updated by BUY/SELL trades. For each date, computes `Σ(position × close_price)`. Supports 1M/3M/6M/1Y/ALL periods. Single bulk SELECT for prices (T-13-01 mitigation).

**get_allocation_data(mode)** — Calls `get_holdings()`, filters for valid `market_value`, then either groups by ticker (each holding → item) or by sector (sum market values per sector). Null sectors default to "Khác". Returns items sorted by value descending with percentage.

**New schemas** — `PerformanceDataPoint(date, value)`, `PerformanceResponse(data, period)`, `AllocationItem(name, value, percentage)`, `AllocationResponse(data, mode, total_value)`.

**Tests (8):** 3M snapshots, no trades returns empty, BUY+SELL position tracking, 1M period, allocation by ticker, by sector, null sector default, no market price returns empty.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `539fad9` | test(13-01): add failing tests for dividend income, holdings sector, summary dividend |
| 2 | `52d73db` | feat(13-01): implement dividend income computation with holdings/summary integration |
| 3 | `1a1b065` | test(13-01): add failing tests for performance data and allocation data |
| 4 | `7b994c3` | feat(13-01): implement performance data and allocation data methods |

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **Dividend income as float accumulator** — Used `Decimal("0")` internally then cast to `float` at return for consistency with existing P&L patterns
2. **Performance data trade-replay approach** — Processes trades in date order, applying all trades on/before each price date, then computing portfolio value — handles mid-period position changes correctly
3. **Allocation null sector → "Khác"** — Vietnamese default label for uncategorized holdings, consistent with UI language patterns

## Test Results

```
34 passed, 4 warnings in 8.78s
```

- 18 existing tests: all pass (FIFO, P&L, validation, recording, schema, router)
- 16 new tests: all pass (dividend, performance, allocation)

## Self-Check: PASSED

All 3 files verified present. All 4 commit hashes found. All key methods and classes confirmed in source.

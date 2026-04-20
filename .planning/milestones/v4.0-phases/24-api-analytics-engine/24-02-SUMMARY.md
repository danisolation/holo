---
phase: 24-api-analytics-engine
plan: "02"
subsystem: paper-trade-analytics
tags: [analytics, sql-aggregates, equity-curve, drawdown, risk-reward, profit-factor]
dependency_graph:
  requires: [24-01]
  provides: [analytics-endpoints]
  affects: [25-dashboard, 26-visualization]
tech_stack:
  added: []
  patterns: [sql-aggregate-service, peak-trough-drawdown, case-when-brackets]
key_files:
  created:
    - backend/tests/test_paper_trade_analytics.py
  modified:
    - backend/app/schemas/paper_trading.py
    - backend/app/services/paper_trade_analytics_service.py
    - backend/app/api/paper_trading.py
decisions:
  - "Confidence brackets: 1-3 LOW, 4-6 MEDIUM, 7-10 HIGH per CONTEXT.md"
  - "R:R uses abs(entry-SL) for risk to handle both LONG and BEARISH correctly"
  - "Profit factor returns None (not infinity) when gross_loss == 0"
  - "Sector analysis uses coalesce(Ticker.industry, 'Unknown') for NULL industries"
  - "Drawdown limits to last 5 periods for response size"
metrics:
  duration: "5 min"
  completed: "2026-04-20"
  tasks: 2
  files: 4
  tests: 26
---

# Phase 24 Plan 02: Analytics Engine Implementation Summary

**One-liner:** 8 analytics endpoints (summary, equity curve, drawdown, direction, confidence brackets, R:R, profit factor, sector) with SQL aggregates on closed trades, peak-trough drawdown algorithm, and 26 passing tests

## What Was Done

### Task 1: Core Analytics — Summary, Equity Curve, Drawdown (AN-01 to AN-04)
- **Commit:** `7d7fe12`
- Added `AnalyticsSummaryResponse`, `EquityCurvePoint`, `EquityCurveResponse`, `DrawdownPeriod`, `DrawdownResponse` schemas
- Implemented `get_summary()`: SQL COUNT/SUM with CLOSED_STATUSES filter, win_rate %, P&L as % of initial_capital from SimulationConfig
- Implemented `get_equity_curve()`: GROUP BY closed_date, SUM(realized_pnl), cumulative sum in Python, ordered ascending
- Implemented `get_drawdown()`: peak-to-trough algorithm with period tracking (last 5), handles empty curve and all-losses scenarios
- Added 3 GET endpoints: `/analytics/summary`, `/analytics/equity-curve`, `/analytics/drawdown`
- 10 tests: drawdown algorithm (5 edge cases), summary schema (2), equity curve schema (1), drawdown schema (2)

### Task 2: Breakdown Analytics — Direction, Confidence, R:R, Profit Factor, Sector (AN-05 to AN-09)
- **Commit:** `d45fc9b`
- Added `DirectionAnalysisItem`, `ConfidenceBracketItem`, `RiskRewardResponse`, `ProfitFactorResponse`, `SectorAnalysisItem` schemas
- Implemented `get_direction_analysis()`: GROUP BY direction (LONG/BEARISH)
- Implemented `get_confidence_analysis()`: SQL CASE WHEN brackets (1-3 LOW, 4-6 MEDIUM, 7-10 HIGH)
- Implemented `get_risk_reward()`: abs(entry-SL)*qty for risk, handles both LONG and BEARISH via abs()
- Implemented `get_profit_factor()`: gross_profit/abs(gross_loss), returns None if no losses
- Implemented `get_sector_analysis()`: JOIN tickers, coalesce(industry, 'Unknown'), ORDER BY count DESC
- Added 5 GET endpoints: `/analytics/direction`, `/analytics/confidence`, `/analytics/risk-reward`, `/analytics/profit-factor`, `/analytics/sector`
- 16 additional tests: direction (2), confidence brackets (1+3 boundary), R:R computation (3+1 schema), profit factor (2+2 schema), sector (2)

## Requirements Coverage

| Requirement | Description | Endpoint | Status |
|-------------|-------------|----------|--------|
| AN-01 | Win rate | GET /analytics/summary | ✅ |
| AN-02 | Total P&L VND + % | GET /analytics/summary | ✅ |
| AN-03 | Equity curve | GET /analytics/equity-curve | ✅ |
| AN-04 | Max drawdown | GET /analytics/drawdown | ✅ |
| AN-05 | Direction analysis | GET /analytics/direction | ✅ |
| AN-06 | Confidence brackets | GET /analytics/confidence | ✅ |
| AN-07 | R:R achieved vs predicted | GET /analytics/risk-reward | ✅ |
| AN-08 | Profit factor + EV | GET /analytics/profit-factor | ✅ |
| AN-09 | Sector analysis | GET /analytics/sector | ✅ |

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **Confidence brackets**: 1-3 LOW, 4-6 MEDIUM, 7-10 HIGH (per CONTEXT.md, not requirements.md 1-4/5-7/8-10)
2. **R:R formula**: `abs(entry_price - stop_loss) * quantity` as risk denominator — abs() handles both LONG and BEARISH
3. **Profit factor None**: Returns `None` when `gross_loss == 0` instead of infinity/NaN (threat T-24-06)
4. **Sector coalesce**: `coalesce(Ticker.industry, 'Unknown')` for tickers with NULL industry
5. **Drawdown periods**: Capped at last 5 periods for response size control

## Verification

- 8 analytics endpoints confirmed via router introspection
- 26 tests passing (10 core + 16 breakdown)
- 12 Plan 01 tests still passing (no regressions)
- Total paper trading routes: 14 (6 CRUD + 8 analytics)

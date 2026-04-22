---
plan: 37-01
phase: 37-backend-analytics-consolidation
status: complete
started: 2025-07-22
completed: 2025-07-22
---

## Summary

Extracted shared analytics logic and trade response schemas. Deferred composition pattern to Phase 38.

## What Was Built

- **schemas/trade.py** (NEW): TradeBaseResponse with 21 shared fields
- **BacktestTradeResponse**: now inherits TradeBaseResponse, adds only run_id + backtest_analysis_id
- **PaperTradeResponse**: now inherits TradeBaseResponse
- **services/analytics_base.py** (NEW): CLOSED_STATUSES + 4 shared computation functions
- **backtest_analytics_service.py**: uses shared calc_win_rate, calc_pnl_pct, calc_avg_pnl, calc_max_drawdown
- **paper_trade_analytics_service.py**: uses same shared functions, CLOSED_STATUSES imported

## Deviation

BCK-02 (composition pattern for BacktestAnalysisService) deferred to Phase 38, which already plans to decompose AIAnalysisService into focused modules. The composition pattern requires understanding the decomposed AI service structure.

## Metrics

- Tests: 689 passing (unchanged)
- Files created: 2 (trade.py, analytics_base.py)
- Files modified: 4 (backtest.py schema, paper_trading.py schema, both analytics services)
- LOC removed: ~3 net (slight reduction from deduplication)

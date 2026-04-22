# Phase 33: Analytics & Benchmark Computation — Context

## Phase Goal
After backtest completion, compute comprehensive performance metrics and multi-dimensional breakdowns comparing AI strategy returns vs VN-Index buy-and-hold.

## Requirements
- BENCH-01: So sánh equity curve AI strategy vs VN-Index buy-and-hold
- BENCH-02: Tính toán win rate, total P&L, max drawdown, Sharpe ratio
- BENCH-03: Thống kê hiệu suất AI theo ngành
- BENCH-04: Thống kê theo confidence level
- BENCH-05: Thống kê theo timeframe

## Key Decisions

1. **Data Source**: All backtest data from `backtest_runs`, `backtest_trades`, `backtest_equity`, `backtest_analyses` tables (Phase 32)
2. **VN-Index Data**: Use vnstock to fetch VN-Index (VNINDEX) OHLCV for the same date range, compute buy-and-hold returns
3. **Computation Timing**: Analytics computed on-demand when requested via API (not pre-computed) — keeps it simple, data is already in DB
4. **Service Pattern**: New `BacktestAnalyticsService` class with methods for each metric category
5. **API Pattern**: Add analytics endpoints to existing backtest router — `/runs/{id}/analytics`, `/runs/{id}/benchmark`
6. **Sharpe Ratio**: Use daily returns from backtest_equity table, risk-free rate = 0 (VN market), annualize with sqrt(252)
7. **Max Drawdown**: Compute from equity curve peak-to-trough
8. **Sector Breakdown**: Join backtest_trades → tickers → industry field
9. **Confidence Breakdown**: Parse from backtest_analyses score field, bucket into 1-3 (low), 4-6 (medium), 7-10 (high)
10. **Timeframe Breakdown**: Categorize trades by holding_days: short (1-5), medium (6-15), long (16+)

## Dependencies
- Phase 32 complete ✅ — all backtest models, engine, and tests in place
- vnstock library for VN-Index historical data

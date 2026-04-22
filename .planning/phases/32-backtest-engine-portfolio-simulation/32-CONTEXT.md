# Phase 32: Backtest Engine & Portfolio Simulation - Context

**Gathered:** 2025-07-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a complete backtest engine that replays historical trading sessions (up to 6 months / 120 sessions) for 400+ HOSE/HNX/UPCOM tickers. At each session, the engine calls Gemini AI (technical + combined + trading signal) using the SAME prompts as live analysis, then opens/closes virtual positions based on signals. Includes portfolio simulation with position sizing, slippage, SL/TP/timeout monitoring, and per-session equity tracking. Must support checkpoint/resume for the ~53-hour compute workload.

</domain>

<decisions>
## Implementation Decisions

### Data Architecture
- Backtest trades stored in separate `backtest_trades` table — completely isolated from live `paper_trades`
- Each backtest run stored in `backtest_runs` table (id, start_date, end_date, capital, slippage, status, progress, last_completed_date)
- Per-session equity snapshots stored in `backtest_equity` table (run_id + date + cash + positions_value + total_equity)
- AI analysis for backtest stored in separate `backtest_analyses` table — NEVER overwrites live `ai_analyses`

### Engine Execution Model
- Date-first iteration: each session processes ALL 400 tickers → evaluate positions → next day (reflects real trading)
- D+1 open entry: signal generated day D, position opened at open price day D+1 (matches live paper trading)
- No limit on simultaneous open positions — position sizing auto-adjusts to current capital
- Full Gemini pipeline per day: batch 400 tickers → technical + combined + trading_signal → filter signals → open trades

### Gemini API Strategy
- Batch size 25 tickers/batch (same as live) — 16 batches × 3 analysis types × 120 days = ~5,760 Gemini calls
- 4s delay between batches + retry 429 with exponential backoff (reuse `_run_batched_analysis` pattern)
- On persistent Gemini failure: skip that day, log to `backtest_errors`, continue to next day
- Use identical prompts and system instructions as live analysis — same prompt builders, only data differs

### Checkpoint & Resume
- Checkpoint after each completed day — update `backtest_runs.last_completed_date` + commit all trades/equity
- Resume by querying `last_completed_date`, skip to next day, reload open positions from DB
- Singleton pattern: only 1 backtest running at a time, reject if already running
- Cancel via `POST /backtest/{id}/cancel` — engine checks cancel flag each day, stops gracefully

### Agent's Discretion
- Internal data structures for in-memory position tracking during session loop
- Error logging format and granularity
- Alembic migration strategy for new tables

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `paper_trade_service.py`: `calculate_position_size()`, `calculate_pnl()`, `apply_partial_tp()`, `evaluate_long_position()`, `evaluate_bearish_position()`, `VALID_TRANSITIONS`, `TIMEOUT_TRADING_DAYS` — all pure Python, no ORM deps
- `ai_analysis_service.py`: `_run_batched_analysis()` pattern, retry logic (429/503), rate limiting, prompt builders
- `scheduler/jobs.py`: `paper_trade_auto_track()` signal→trade creation logic, `paper_position_monitor()` daily evaluation loop

### Established Patterns
- Async SQLAlchemy with asyncpg for all DB operations
- Pydantic v2 models for API request/response validation
- APScheduler for background job execution
- FastAPI BackgroundTasks for on-demand async operations
- Tenacity retry decorators for external API calls
- Per-batch DML commits (not bulk)

### Integration Points
- New API router: `backend/app/api/backtest.py` → mount at `/api/backtest/`
- New service: `backend/app/services/backtest_engine.py`
- New models: `backend/app/models/backtest.py` (BacktestRun, BacktestTrade, BacktestEquity, BacktestAnalysis)
- New Alembic migration for backtest tables
- Import from `paper_trade_service.py` for business logic
- Import from `ai_analysis_service.py` for Gemini calls (or create dedicated backtest analysis method)

</code_context>

<specifics>
## Specific Ideas

- Reuse v4.0 paper trading business logic verbatim (position sizing, P&L calc, SL/TP evaluation)
- Historical OHLCV data already in `daily_prices` table — no crawling needed
- VN-Index benchmark data: query VN-Index ticker from `daily_prices` for same date range
- Slippage: apply configurable % to entry/exit prices (e.g., 0.5% = buy higher, sell lower)

</specifics>

<deferred>
## Deferred Ideas

- Multi-strategy comparison (run same period with different AI models/configs)
- Walk-forward optimization
- Monte Carlo stress testing

</deferred>

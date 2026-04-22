# Phase 32: Backtest Engine & Portfolio Simulation - Research

**Researched:** 2025-07-21
**Domain:** Backtest engine, portfolio simulation, Gemini AI batch processing, checkpoint/resume
**Confidence:** HIGH

## Summary

Phase 32 builds a complete backtest engine that replays 120 historical trading sessions for 400+ tickers, calling Gemini AI at each session to generate trading signals, then managing virtual positions with portfolio simulation. The codebase has excellent reusable assets: `paper_trade_service.py` contains pure-Python business logic (position sizing, P&L, SL/TP evaluation) that can be imported directly, and `ai_analysis_service.py` has the entire batched Gemini pipeline (rate limiting, retries, prompt builders). The main architectural challenge is adapting the AI analysis pipeline to work with historical dates — all context-gathering methods (`_get_technical_context`, `_get_combined_context`, `_get_trading_signal_context`) currently query for LATEST data, and `_store_analysis` writes to the live `ai_analyses` table. The backtest needs date-aware variants that query as-of-date data and store results in separate `backtest_analyses` table.

The position monitoring logic in `scheduler/jobs.py::paper_position_monitor()` is a direct template for the daily evaluation loop — it already handles PENDING activation at D+1 open, SL/TP evaluation via the pure functions, timeout counting from `daily_prices`, and P&L calculation on close. The signal-to-trade creation logic in `paper_trade_auto_track()` provides the template for converting backtest signals into trades.

**Primary recommendation:** Create a `BacktestEngine` service class that composes `AIAnalysisService` (subclass with date-aware overrides for context/storage methods) and directly imports pure functions from `paper_trade_service.py`. The engine's main loop iterates date-first across all tickers, with checkpoint after each completed day.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Backtest trades stored in separate `backtest_trades` table — completely isolated from live `paper_trades`
- Each backtest run stored in `backtest_runs` table (id, start_date, end_date, capital, slippage, status, progress, last_completed_date)
- Per-session equity snapshots stored in `backtest_equity` table (run_id + date + cash + positions_value + total_equity)
- AI analysis for backtest stored in separate `backtest_analyses` table — NEVER overwrites live `ai_analyses`
- Date-first iteration: each session processes ALL 400 tickers → evaluate positions → next day
- D+1 open entry: signal generated day D, position opened at open price day D+1
- No limit on simultaneous open positions — position sizing auto-adjusts to current capital
- Full Gemini pipeline per day: batch 400 tickers → technical + combined + trading_signal → filter signals → open trades
- Batch size 25 tickers/batch, 4s delay between batches + retry 429 with exponential backoff
- On persistent Gemini failure: skip that day, log to `backtest_errors`, continue to next day
- Use identical prompts and system instructions as live analysis
- Checkpoint after each completed day — update `backtest_runs.last_completed_date` + commit all trades/equity
- Resume by querying `last_completed_date`, skip to next day, reload open positions from DB
- Singleton pattern: only 1 backtest running at a time, reject if already running
- Cancel via `POST /backtest/{id}/cancel` — engine checks cancel flag each day, stops gracefully

### Agent's Discretion
- Internal data structures for in-memory position tracking during session loop
- Error logging format and granularity
- Alembic migration strategy for new tables

### Deferred Ideas (OUT OF SCOPE)
- Multi-strategy comparison (run same period with different AI models/configs)
- Walk-forward optimization
- Monte Carlo stress testing
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BT-01 | User can choose backtest time period (1-6 months, default 6 months / 120 sessions) | BacktestRun model with start_date/end_date + API endpoint accepting date range |
| BT-02 | System replays each historical session, calling Gemini AI for technical + combined + trading_signal | BacktestAnalysisService with date-aware context methods + existing prompt builders |
| BT-03 | System auto-opens virtual positions from AI signals (direction, entry price, SL/TP from trading plan) | Reuse `paper_trade_auto_track()` pattern + `calculate_position_size()` from paper_trade_service |
| BT-04 | System monitors and closes positions via SL/TP/timeout at each subsequent session | Reuse `evaluate_long_position()`, `evaluate_bearish_position()`, `apply_partial_tp()`, `calculate_pnl()` from paper_trade_service + `paper_position_monitor()` pattern |
| BT-05 | Checkpoint/resume — save progress, continue if interrupted | `last_completed_date` in backtest_runs + reload open positions from DB |
| BT-06 | Runs on all 400+ tickers with smart batching to avoid Gemini rate limit (15 RPM) | Reuse `_run_batched_analysis()` pattern with batch_size=25, 4s delay, 429 retry |
| SIM-01 | User can configure starting capital (default 100M VND) | BacktestRun.initial_capital field + API request parameter |
| SIM-02 | Position sizing via % of current capital, reuse paper trading v4.0 logic | Direct import of `calculate_position_size()` with dynamic capital tracking |
| SIM-03 | Slippage simulation — configurable % applied to entry/exit prices | Apply slippage_pct to all entry/exit prices (buy higher, sell lower) |
| SIM-04 | Equity tracking per session — cash, open positions value, cumulative P&L, % return | BacktestEquity table with per-session snapshots computed from cash + mark-to-market positions |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.49 | Async ORM for all DB operations | Already used throughout project [VERIFIED: codebase] |
| FastAPI | 0.135.3 | API endpoints for backtest control | Already used for all routes [VERIFIED: codebase] |
| Pydantic | 2.13.0 | Request/response validation | Already used for all schemas [VERIFIED: codebase] |
| google-genai | (installed) | Gemini AI calls | Already used by ai_analysis_service [VERIFIED: codebase] |
| Alembic | 1.18.4 | Database migration for new tables | Already used for all 13 prior migrations [VERIFIED: codebase] |
| loguru | (installed) | Structured logging | Already used throughout project [VERIFIED: codebase] |
| tenacity | (installed) | Retry with exponential backoff | Already used for Gemini calls [VERIFIED: codebase] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio.Lock | stdlib | Singleton backtest execution | Prevent concurrent backtest runs |
| decimal.Decimal | stdlib | VND price calculations | All price/P&L math (avoid float errors) |

**No new dependencies needed.** All required libraries are already installed. [VERIFIED: `python -c "import ..."` checks]

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── models/backtest.py           # BacktestRun, BacktestTrade, BacktestEquity, BacktestAnalysis, BacktestError
├── schemas/backtest.py          # Pydantic request/response schemas
├── services/backtest_engine.py  # Core engine: date loop, signal processing, position management
├── services/backtest_analysis_service.py  # Subclass of AIAnalysisService with date-aware context + storage
├── api/backtest.py              # REST endpoints: start, status, cancel, results
└── alembic/versions/014_backtest_tables.py  # Migration for 5 new tables
```

### Pattern 1: Date-Aware Analysis Service (Critical Architecture)
**What:** Subclass `AIAnalysisService` to override context-gathering and storage methods for historical dates.
**When to use:** Every Gemini call during backtest must use historical data, not current data.
**Why necessary:** The live `AIAnalysisService` has 3 critical assumptions that break for backtesting:
1. `_get_technical_context()` queries `ORDER BY date DESC LIMIT 5` — gets TODAY's data, not historical
2. `_get_combined_context()` reads from `ai_analyses` table — would read live data, not backtest results
3. `_store_analysis()` writes to `ai_analyses` with UPSERT — would OVERWRITE live analysis data
4. `_get_trading_signal_context()` queries latest indicators and prices — not historical

[VERIFIED: ai_analysis_service.py lines 976-1060, 1124-1186, 1189-1266, 1412-1445]

**Example:**
```python
# Source: Codebase pattern from ai_analysis_service.py
class BacktestAnalysisService(AIAnalysisService):
    """Date-aware analysis service for backtesting.
    
    Overrides context-gathering to use as_of_date instead of latest data,
    and storage to write to backtest_analyses instead of ai_analyses.
    """
    def __init__(self, session: AsyncSession, run_id: int, as_of_date: date, api_key: str | None = None):
        super().__init__(session, api_key)
        self.run_id = run_id
        self.as_of_date = as_of_date
    
    async def _get_technical_context(self, ticker_id: int, symbol: str) -> dict | None:
        """Get 5-day indicator window AS OF self.as_of_date."""
        result = await self.session.execute(
            select(TechnicalIndicator)
            .where(TechnicalIndicator.ticker_id == ticker_id)
            .where(TechnicalIndicator.date <= self.as_of_date)  # KEY: date filter
            .order_by(TechnicalIndicator.date.desc())
            .limit(5)
        )
        # ... same processing as parent
    
    async def _get_combined_context(self, ticker_id: int, symbol: str) -> dict | None:
        """Read from backtest_analyses (not ai_analyses) for this run."""
        result = await self.session.execute(
            select(BacktestAnalysis)
            .where(BacktestAnalysis.run_id == self.run_id)
            .where(BacktestAnalysis.ticker_id == ticker_id)
            .where(BacktestAnalysis.analysis_type.in_([...]))
            .where(BacktestAnalysis.analysis_date <= self.as_of_date)
            .order_by(BacktestAnalysis.analysis_date.desc())
        )
        # ... same grouping logic as parent
    
    async def _store_analysis(self, ticker_id, analysis_type, analysis_date, signal, score, reasoning, raw_response):
        """Write to backtest_analyses table with run_id."""
        # INSERT INTO backtest_analyses (run_id, ...) VALUES (self.run_id, ...)
```

### Pattern 2: Date-First Engine Loop with Checkpoint
**What:** The main backtest loop iterates by date, processing ALL tickers per day before advancing.
**When to use:** This is the core execution model per locked decisions.
**Example:**
```python
# Source: Derived from paper_position_monitor pattern (jobs.py lines 894-1050)
class BacktestEngine:
    async def run(self, run_id: int):
        run = await self._load_run(run_id)
        trading_dates = await self._get_trading_dates(run.start_date, run.end_date)
        
        # Resume: skip already-completed dates
        if run.last_completed_date:
            trading_dates = [d for d in trading_dates if d > run.last_completed_date]
        
        # Reload open positions from DB (for resume)
        open_positions = await self._load_open_positions(run_id)
        cash = await self._compute_current_cash(run)
        
        for session_date in trading_dates:
            # Check cancel flag
            if await self._is_cancelled(run_id):
                break
            
            # 1. Run AI pipeline for this date
            analysis_svc = BacktestAnalysisService(session, run_id, session_date)
            await analysis_svc.run_technical_analysis(ticker_filter)
            await analysis_svc.run_combined_analysis(ticker_filter)
            await analysis_svc.run_trading_signal_analysis(ticker_filter)
            
            # 2. Evaluate existing positions against today's OHLCV
            #    (same logic as paper_position_monitor)
            await self._evaluate_positions(run_id, session_date, open_positions)
            
            # 3. Open new trades from today's signals (D+1 entry for yesterday's signals)
            #    Note: signals from previous day activate today
            await self._activate_pending_trades(run_id, session_date)
            await self._process_new_signals(run_id, session_date, cash)
            
            # 4. Record equity snapshot
            await self._record_equity(run_id, session_date, cash, open_positions)
            
            # 5. Checkpoint
            await self._checkpoint(run_id, session_date)
```

### Pattern 3: Slippage Application
**What:** Apply configurable slippage % to all entry/exit prices.
**When to use:** SIM-03 — every price at which a trade opens or closes.
**Example:**
```python
# Source: Domain knowledge for Vietnam stock market slippage
def apply_slippage(price: Decimal, slippage_pct: Decimal, is_buy: bool) -> Decimal:
    """Apply slippage: buying costs more, selling receives less."""
    if is_buy:
        return price * (1 + slippage_pct / 100)  # Buy higher
    else:
        return price * (1 - slippage_pct / 100)  # Sell lower
```

### Pattern 4: Equity Tracking
**What:** Per-session snapshot of cash + mark-to-market open positions.
**When to use:** SIM-04 — after processing each day.
**Example:**
```python
# Source: Derived from paper trade equity curve logic
async def _record_equity(self, run_id: int, session_date: date, cash: Decimal, open_positions: list):
    """Compute and store equity snapshot for this session."""
    positions_value = Decimal("0")
    for pos in open_positions:
        # Get closing price for this ticker on this date
        close_price = await self._get_close_price(pos.ticker_id, session_date)
        if close_price:
            positions_value += close_price * pos.quantity  # Long: value is shares × price
    
    total_equity = cash + positions_value
    initial = run.initial_capital
    cumulative_return = float((total_equity - initial) / initial * 100)
    
    equity = BacktestEquity(
        run_id=run_id, date=session_date,
        cash=cash, positions_value=positions_value,
        total_equity=total_equity, cumulative_return_pct=cumulative_return,
    )
    session.add(equity)
```

### Anti-Patterns to Avoid
- **Don't copy-paste paper_trade_service.py functions:** Import them directly. They're pure Python with no DB or async dependencies. [VERIFIED: paper_trade_service.py lines 1-10 comment "Pure Python functions — no DB, no async"]
- **Don't call live analysis endpoints:** The backtest must never use `POST /api/analysis/trigger` or the daily scheduler. Create a separate service that reuses the internal methods.
- **Don't write to ai_analyses table:** All backtest analyses go to `backtest_analyses`. The `_store_analysis` override is critical.
- **Don't query "latest" data without date bounds:** Every DB query in the backtest context methods MUST have `WHERE date <= as_of_date`. Omitting this creates lookahead bias.
- **Don't accumulate all positions in memory across 120 days:** Checkpoint to DB and reload — the 53-hour runtime means memory leaks are fatal.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Position sizing (100-lot rounding) | Custom position sizing | `paper_trade_service.calculate_position_size()` | Already handles VN 100-share lots, edge cases [VERIFIED: codebase] |
| P&L calculation (partial TP support) | Custom P&L calculator | `paper_trade_service.calculate_pnl()` | Handles 2-leg trades, long+bearish directions [VERIFIED: codebase] |
| SL/TP evaluation against OHLCV bar | Custom evaluation logic | `paper_trade_service.evaluate_long_position()` / `evaluate_bearish_position()` | Handles gap-through, ambiguous bar rule, TP1/TP2 states [VERIFIED: codebase] |
| Partial take-profit logic | Custom partial close | `paper_trade_service.apply_partial_tp()` | Handles qty rounding, breakeven SL, edge case qty=100 [VERIFIED: codebase] |
| State machine transitions | Custom status tracking | `paper_trade_service.VALID_TRANSITIONS` / `validate_transition()` | Complete state machine already validated [VERIFIED: codebase] |
| Gemini rate limiting & retry | Custom retry loops | `AIAnalysisService._run_batched_analysis()` pattern | Handles 429 with retry-after parsing, 503 progressive backoff, batch orchestration [VERIFIED: codebase] |
| Timeout day counting | Custom date math | Query `daily_prices` count (same as paper_position_monitor) | Correctly counts trading days only, not calendar days [VERIFIED: jobs.py lines 1013-1018] |

**Key insight:** The backtest engine's core innovation is the date loop, checkpoint/resume, and analysis service date-awareness. Everything else — position sizing, P&L, evaluation, state machine, retry logic — is already battle-tested in the live paper trading system.

## Common Pitfalls

### Pitfall 1: Lookahead Bias in Context Queries
**What goes wrong:** Context-gathering queries return data from AFTER the simulated date, giving AI information it wouldn't have had in real-time.
**Why it happens:** All existing `_get_*_context` methods query `ORDER BY date DESC LIMIT N` without a date ceiling.
**How to avoid:** Every DB query in `BacktestAnalysisService` MUST include `WHERE date <= self.as_of_date`. This applies to:
- `_get_technical_context`: indicators 5-day window
- `_get_trading_signal_context`: latest indicators + prices + 52-week high/low
- `_get_combined_context`: prior analysis results
- Price lookups for evaluation
**Warning signs:** Backtest results that are suspiciously good (>90% win rate).

### Pitfall 2: Combined Analysis Reading Live Data Instead of Backtest Data
**What goes wrong:** The combined analysis step reads tech/fund/sentiment scores from `ai_analyses` (live table) instead of `backtest_analyses`, mixing real analysis with backtest.
**Why it happens:** The parent `_get_combined_context` queries `AIAnalysis` model which maps to `ai_analyses` table.
**How to avoid:** Override `_get_combined_context` to query `BacktestAnalysis` model, filtered by `run_id` and `analysis_date <= as_of_date`.
**Warning signs:** Combined scores that don't correlate with the day's technical analysis.

### Pitfall 3: Capital Tracking Drift
**What goes wrong:** Cash balance becomes incorrect over many days because entry/exit costs aren't properly deducted/added.
**Why it happens:** Position sizing uses capital %, but actual cash deduction must account for slippage-adjusted price × quantity. Partial TPs return partial cash.
**How to avoid:** Track cash explicitly:
- On trade open: `cash -= slippage_adjusted_entry_price × quantity`
- On partial TP: `cash += slippage_adjusted_tp1_price × closed_quantity`
- On full close: `cash += slippage_adjusted_exit_price × remaining_quantity`
**Warning signs:** Negative cash, or equity > initial_capital when all positions are losing.

### Pitfall 4: Checkpoint Resume Loading Stale In-Memory State
**What goes wrong:** After resume, in-memory position tracking doesn't match DB state.
**Why it happens:** Positions may have been partially updated (partial TP) before crash.
**How to avoid:** On resume, reload ALL open positions from `backtest_trades` (status IN pending, active, partial_tp) and recompute cash from `backtest_equity.cash` of last completed day.
**Warning signs:** Duplicate trade entries, positions evaluated twice.

### Pitfall 5: Connection Pool Exhaustion During 53-Hour Run
**What goes wrong:** Aiven PostgreSQL connection pool (max 8) exhausted, causing query timeouts.
**Why it happens:** Long-running async session not properly closed, or multiple sessions opened simultaneously.
**How to avoid:** Use single `async_session()` context per day, commit and close after checkpoint. Don't open new sessions within the day loop. Follow the paper_position_monitor pattern of 2-batch queries. [VERIFIED: database.py pool_size=5, max_overflow=3]
**Warning signs:** `asyncpg.exceptions.TooManyConnectionsError` after running for hours.

### Pitfall 6: Gemini Module Lock Blocking Live Analysis
**What goes wrong:** The `_gemini_lock` in `ai_analysis_service.py` (module-level `asyncio.Lock`) blocks ALL Gemini access. If backtest is running, live daily analysis can't run.
**Why it happens:** The lock serializes all Gemini calls across the entire process.
**How to avoid:** The backtest engine should run via `FastAPI.BackgroundTasks` (not APScheduler), and the singleton check should prevent overlap. Consider adding a clear warning in the UI when backtest is running. Live analysis can be paused during backtest or the backtest scheduled during off-hours.
**Warning signs:** Daily analysis jobs timing out while backtest is running.

### Pitfall 7: Signal Date vs Entry Date Off-By-One
**What goes wrong:** Signals generated on day D should open positions at D+1 open price. If the engine processes signals and opens trades on the same day D, it creates lookahead bias.
**Why it happens:** Confusion between "generate signal" and "activate trade" timing.
**How to avoid:** Follow exact `paper_position_monitor` pattern:
1. Signals created as `PENDING` with `signal_date = D`
2. On day D+1, activate PENDING trades where `signal_date < current_date`, set `entry_price = bar.open` of D+1
3. Don't evaluate newly activated trades on the same day they activate
[VERIFIED: jobs.py lines 956-963 — exact pattern]

### Pitfall 8: Sentiment Data Unavailable for Historical Dates
**What goes wrong:** CafeF news scraping only captures current news. Historical news titles aren't available for backtesting.
**Why it happens:** News articles in DB only cover the period since the crawler started running.
**How to avoid:** The combined analysis has graceful degradation: if sentiment is missing, it defaults to `sent_signal="neutral", sent_score=5` [VERIFIED: ai_analysis_service.py lines 1178-1184]. This means backtest combined analysis will work but without sentiment input. Document this limitation.
**Warning signs:** None — this is expected behavior, not an error.

## Code Examples

### Database Models (BacktestRun, BacktestTrade, BacktestEquity, BacktestAnalysis)
```python
# Source: Derived from paper_trade.py (lines 1-87) and ai_analysis.py (lines 1-65)
import enum
from decimal import Decimal
from datetime import date, datetime

from sqlalchemy import (
    Integer, BigInteger, String, Numeric, Date, Float, Boolean,
    ForeignKey, Enum as SAEnum, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP
from app.models import Base
from app.models.paper_trade import TradeStatus, TradeDirection  # Reuse existing enums


class BacktestStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, server_default="100000000")
    slippage_pct: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False, server_default="0.5")
    status: Mapped[BacktestStatus] = mapped_column(
        SAEnum(BacktestStatus, name="backtest_status", create_constraint=False,
               native_enum=True, values_callable=lambda e: [m.value for m in e]),
        nullable=False, server_default="running",
    )
    last_completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_sessions: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    completed_sessions: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    is_cancelled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class BacktestTrade(Base):
    """Mirrors PaperTrade but scoped to a backtest run."""
    __tablename__ = "backtest_trades"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("backtest_runs.id"), nullable=False)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    backtest_analysis_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("backtest_analyses.id"), nullable=True)
    direction: Mapped[TradeDirection] = mapped_column(
        SAEnum(TradeDirection, name="trade_direction", create_constraint=False,
               native_enum=True, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    status: Mapped[TradeStatus] = mapped_column(
        SAEnum(TradeStatus, name="trade_status", create_constraint=False,
               native_enum=True, values_callable=lambda e: [m.value for m in e]),
        nullable=False, server_default="pending",
    )
    # Prices (same as PaperTrade)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    take_profit_1: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    take_profit_2: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    adjusted_stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    closed_quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    realized_pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    partial_exit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    signal_date: Mapped[date] = mapped_column(Date, nullable=False)
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    closed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(20), nullable=False)
    position_size_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_reward_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    @property
    def effective_stop_loss(self) -> Decimal:
        return self.adjusted_stop_loss if self.adjusted_stop_loss is not None else self.stop_loss


class BacktestAnalysis(Base):
    """Mirrors AIAnalysis but scoped to a backtest run."""
    __tablename__ = "backtest_analyses"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("backtest_runs.id"), nullable=False)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(20), nullable=False)  # Use string to avoid enum dependency
    analysis_date: Mapped[date] = mapped_column(Date, nullable=False)
    signal: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_response: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("run_id", "ticker_id", "analysis_type", "analysis_date",
                         name="uq_backtest_analyses_run_ticker_type_date"),
    )


class BacktestEquity(Base):
    __tablename__ = "backtest_equity"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("backtest_runs.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    positions_value: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    total_equity: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False)
    daily_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    cumulative_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (
        UniqueConstraint("run_id", "date", name="uq_backtest_equity_run_date"),
    )
```

### Signal-to-Trade Creation (from paper_trade_auto_track pattern)
```python
# Source: Derived from scheduler/jobs.py lines 824-877
async def _process_new_signals(self, run_id: int, session_date: date, cash: Decimal):
    """Create PENDING trades from today's valid trading signals.
    Mirrors paper_trade_auto_track logic exactly."""
    from app.schemas.analysis import TickerTradingSignal
    from app.services.paper_trade_service import calculate_position_size
    
    # Query today's valid backtest signals
    stmt = select(BacktestAnalysis).where(
        BacktestAnalysis.run_id == run_id,
        BacktestAnalysis.analysis_type == "trading_signal",
        BacktestAnalysis.analysis_date == session_date,
        BacktestAnalysis.score > 0,
    )
    signals = (await self.session.execute(stmt)).scalars().all()
    
    for analysis in signals:
        signal_data = TickerTradingSignal.model_validate(analysis.raw_response)
        direction = signal_data.recommended_direction.value
        dir_analysis = (signal_data.long_analysis if direction == "long"
                       else signal_data.bearish_analysis)
        
        plan = dir_analysis.trading_plan
        entry_price = Decimal(str(plan.entry_price))
        
        quantity = calculate_position_size(
            capital=cash,  # Use CURRENT cash, not initial capital
            allocation_pct=plan.position_size_pct,
            entry_price=entry_price,
        )
        if quantity == 0:
            continue
        
        trade = BacktestTrade(
            run_id=run_id,
            ticker_id=...,  # resolve from ticker symbol
            backtest_analysis_id=analysis.id,
            direction=TradeDirection(direction),
            status=TradeStatus.PENDING,
            entry_price=entry_price,
            stop_loss=Decimal(str(plan.stop_loss)),
            take_profit_1=Decimal(str(plan.take_profit_1)),
            take_profit_2=Decimal(str(plan.take_profit_2)),
            quantity=quantity,
            signal_date=session_date,
            confidence=dir_analysis.confidence,
            timeframe=plan.timeframe.value,
            position_size_pct=plan.position_size_pct,
            risk_reward_ratio=plan.risk_reward_ratio,
        )
        self.session.add(trade)
```

### Position Evaluation Loop (from paper_position_monitor pattern)
```python
# Source: Derived from scheduler/jobs.py lines 949-1033
async def _evaluate_positions(self, run_id: int, session_date: date):
    """Evaluate all open positions against today's OHLCV.
    Mirrors paper_position_monitor logic exactly."""
    from app.services.paper_trade_service import (
        evaluate_long_position, evaluate_bearish_position,
        apply_partial_tp, calculate_pnl, TIMEOUT_TRADING_DAYS,
    )
    
    # Query open positions for this run
    positions = ...  # status IN (pending, active, partial_tp) AND run_id = run_id
    
    # Get today's prices for all tickers with positions
    price_map = ...  # ticker_id → DailyPrice for session_date
    
    for trade in positions:
        bar = price_map.get(trade.ticker_id)
        if not bar:
            continue
        
        # PENDING activation at D+1 open
        if trade.status == TradeStatus.PENDING:
            if bar.date > trade.signal_date:
                trade.status = TradeStatus.ACTIVE
                trade.entry_price = apply_slippage(bar.open, slippage_pct, is_buy=True)
                trade.entry_date = bar.date
                cash -= trade.entry_price * trade.quantity  # Deduct from cash
            continue
        
        # Active/Partial_TP evaluation — reuse pure functions
        if trade.direction == TradeDirection.LONG:
            new_status, exit_price = evaluate_long_position(...)
        else:
            new_status, exit_price = evaluate_bearish_position(...)
        
        if new_status == TradeStatus.PARTIAL_TP:
            apply_partial_tp(trade, exit_price)
            cash += apply_slippage(exit_price, slippage_pct, is_buy=False) * trade.closed_quantity
        elif new_status is not None:
            slipped_exit = apply_slippage(exit_price, slippage_pct, is_buy=False)
            trade.status = new_status
            trade.exit_price = slipped_exit
            trade.closed_date = session_date
            pnl, pnl_pct = calculate_pnl(...)
            trade.realized_pnl = pnl
            trade.realized_pnl_pct = pnl_pct
            remaining = trade.quantity - trade.closed_quantity
            cash += slipped_exit * remaining
        else:
            # Timeout check
            ...
```

### API Endpoints Pattern
```python
# Source: Derived from paper_trading.py API pattern
from fastapi import APIRouter, BackgroundTasks, HTTPException

router = APIRouter(prefix="/backtest", tags=["backtest"])

@router.post("/runs", status_code=201)
async def start_backtest(request: BacktestStartRequest, bg: BackgroundTasks):
    """BT-01, SIM-01, SIM-03: Start a new backtest run."""
    # Check singleton: no other run is RUNNING
    async with async_session() as session:
        existing = await session.execute(
            select(BacktestRun).where(BacktestRun.status == BacktestStatus.RUNNING)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(409, "A backtest is already running")
        
        run = BacktestRun(
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=Decimal(str(request.initial_capital)),
            slippage_pct=Decimal(str(request.slippage_pct)),
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)
    
    # Launch engine in background
    bg.add_task(engine.run, run.id)
    return {"id": run.id, "status": "running"}

@router.get("/runs/{run_id}")
async def get_run_status(run_id: int):
    """BT-05: Get backtest run status and progress."""
    ...

@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: int):
    """Cancel a running backtest. Engine checks flag each day."""
    async with async_session() as session:
        run = await session.get(BacktestRun, run_id)
        if not run or run.status != BacktestStatus.RUNNING:
            raise HTTPException(404, "No running backtest with this ID")
        run.is_cancelled = True
        await session.commit()
    return {"status": "cancelling"}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Backtest using historical AI results | Backtest calling Gemini LIVE on historical data | This phase | More expensive (53h compute) but tests the actual AI pipeline, not cached results |
| Single analysis table for all data | Separate backtest_analyses table | This phase (decision) | Complete isolation — backtest can never corrupt live data |

**Key design rationale:** The project deliberately chose to call Gemini at each historical session (rather than replaying cached analysis) because the goal is to validate the AI model's signal quality. This requires identical prompts + identical data → fresh Gemini response for each historical day. [VERIFIED: CONTEXT.md locked decision]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Historical `technical_indicators` data exists for 6 months back for all tickers | Architecture Patterns | If indicators aren't precomputed historically, technical analysis context will be empty for early dates — need to verify indicator coverage dates |
| A2 | Historical `daily_prices` data exists for 6 months back for all tickers | Architecture Patterns | If price data is missing, positions can't be evaluated on those dates — need to verify price coverage |
| A3 | BacktestAnalysis can use String type for analysis_type instead of the PostgreSQL native ENUM to avoid migration complexity | Code Examples | If the existing code strictly requires the native analysis_type ENUM, would need different approach |
| A4 | `BackgroundTasks` is sufficient for the 53-hour engine run (vs a separate worker process) | Architecture Patterns | FastAPI BackgroundTask runs in the same event loop — if the server restarts, the backtest stops. Checkpoint/resume mitigates this. |
| A5 | The Gemini module-level `_gemini_lock` won't cause issues when backtest and live analysis don't overlap | Pitfalls | If user runs backtest during market hours, live analysis will queue behind backtest batches |

## Open Questions

1. **Historical data coverage**
   - What we know: `daily_prices` and `technical_indicators` tables exist with historical data
   - What's unclear: How far back does the data go? Is it 6 months? 1 year? Are there gaps?
   - Recommendation: Add a pre-flight check in the engine that validates data coverage for the requested date range before starting

2. **Fundamental data for backtest**
   - What we know: `_get_fundamental_context` queries latest financial by year/quarter DESC
   - What's unclear: For backtesting, should fundamental context be date-aware too (use the quarterly report available at that historical date)?
   - Recommendation: Keep simple — fundamental data changes quarterly, and the same financial data was likely available during the backtest period. Only filter by `year <= backtest_year`. LOW priority compared to technical context.

3. **Trading dates source**
   - What we know: Need to iterate only trading days (exclude weekends/holidays)
   - What's unclear: Is there a calendar table, or should trading dates be derived from `daily_prices` DISTINCT dates?
   - Recommendation: Query `SELECT DISTINCT date FROM daily_prices WHERE date BETWEEN start AND end ORDER BY date` — this automatically captures only actual trading days and handles holidays.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | backend/tests/conftest.py (mock_db_session fixture) |
| Quick run command | `cd backend && python -m pytest tests/test_backtest_engine.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BT-01 | Date range validation (1-6 months) | unit | `pytest tests/test_backtest_api.py::test_date_range_validation -x` | ❌ Wave 0 |
| BT-02 | Session replay calls Gemini per day | unit (mocked) | `pytest tests/test_backtest_engine.py::test_session_replay -x` | ❌ Wave 0 |
| BT-03 | Signal → PENDING trade creation | unit | `pytest tests/test_backtest_engine.py::test_signal_to_trade -x` | ❌ Wave 0 |
| BT-04 | SL/TP/timeout evaluation | unit | `pytest tests/test_backtest_engine.py::test_position_evaluation -x` | ❌ Wave 0 |
| BT-05 | Checkpoint save + resume | unit | `pytest tests/test_backtest_engine.py::test_checkpoint_resume -x` | ❌ Wave 0 |
| BT-06 | Batch size 25, rate limiting | unit (mocked) | `pytest tests/test_backtest_engine.py::test_batching -x` | ❌ Wave 0 |
| SIM-01 | Initial capital configuration | unit | `pytest tests/test_backtest_api.py::test_capital_config -x` | ❌ Wave 0 |
| SIM-02 | Position sizing with current capital | unit | `pytest tests/test_backtest_engine.py::test_position_sizing -x` | ❌ Wave 0 |
| SIM-03 | Slippage applied to entry/exit | unit | `pytest tests/test_backtest_engine.py::test_slippage -x` | ❌ Wave 0 |
| SIM-04 | Equity snapshot per session | unit | `pytest tests/test_backtest_engine.py::test_equity_tracking -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_backtest_engine.py -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_backtest_engine.py` — covers BT-02 through BT-06, SIM-02 through SIM-04
- [ ] `tests/test_backtest_api.py` — covers BT-01, SIM-01 (API request validation)
- [ ] `tests/test_backtest_models.py` — covers model definitions and constraints

## Sources

### Primary (HIGH confidence)
- `backend/app/services/paper_trade_service.py` — Full file reviewed: pure Python functions for position sizing, P&L, evaluation, state machine
- `backend/app/services/ai_analysis_service.py` — Lines 220-745, 976-1060, 1124-1266, 1412-1446: batch analysis pattern, context gathering, storage, retry logic
- `backend/app/scheduler/jobs.py` — Lines 767-1050: `paper_trade_auto_track` and `paper_position_monitor` complete implementations
- `backend/app/models/paper_trade.py` — Full file: PaperTrade model schema, enums
- `backend/app/models/ai_analysis.py` — Full file: AIAnalysis model, AnalysisType enum
- `backend/app/models/daily_price.py` — Full file: DailyPrice OHLCV model
- `backend/app/models/simulation_config.py` — Full file: singleton config pattern
- `backend/app/database.py` — Connection pool configuration (pool_size=5, max_overflow=3)
- `backend/app/config.py` — Gemini settings: batch_size=25, delay=4s, model=gemini-2.5-flash-lite
- `backend/alembic/versions/013_paper_trade_tables.py` — Migration pattern for new tables

### Secondary (MEDIUM confidence)
- Package versions verified via `python -c "import ..."`: SQLAlchemy 2.0.49, FastAPI 0.135.3, Pydantic 2.13.0, Alembic 1.18.4, pytest 8.4.2

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, no new dependencies
- Architecture: HIGH — all reusable code reviewed line-by-line, patterns are clear
- Pitfalls: HIGH — identified from actual code analysis (lookahead bias, live data contamination, connection pools)
- Database models: HIGH — derived directly from existing PaperTrade and AIAnalysis models

**Research date:** 2025-07-21
**Valid until:** 2025-08-21 (stable — internal project, no external dependency changes expected)

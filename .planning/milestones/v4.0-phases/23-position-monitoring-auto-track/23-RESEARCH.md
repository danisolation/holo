# Phase 23: Position Monitoring & Auto-Track - Research

**Researched:** 2026-04-21
**Domain:** Scheduler job development — auto-track AI signals as paper trades + daily position monitoring with TP/SL/timeout evaluation
**Confidence:** HIGH

## Summary

Phase 23 implements two new scheduler jobs that form the operational backbone of the paper trading system: (1) **auto-track** creates PaperTrade records from valid AI trading signals immediately after signal generation, and (2) **position monitor** checks all open positions daily against OHLCV data to execute state transitions (activation, TP hits, SL hits, timeouts). Both jobs follow the exact established patterns in `backend/app/scheduler/jobs.py` — async functions using `async_session()`, `JobExecutionService` for tracking, and never-raise behavior for non-critical paths.

The Phase 22 foundation is solid: `PaperTrade` model with 7-state enum, `SimulationConfig` singleton, `paper_trade_service.py` with pure-Python `validate_transition()`, `calculate_pnl()`, `calculate_position_size()`, and `apply_partial_tp()`. Phase 23 builds on top of this by (a) integrating with the scheduler chain at two insertion points and (b) implementing the orchestration logic that reads AI signal data from `raw_response` JSONB, creates positions, and evaluates them against `DailyPrice` data.

**Primary recommendation:** Implement as two independent async job functions (`paper_trade_auto_track` and `paper_position_monitor`) in `jobs.py`, wire them into `manager.py` at the two chain points specified in CONTEXT.md, and use batch queries (2 total per monitor run) to respect the Aiven pool constraint of 8 max connections.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Hook into existing scheduler chain: `combined → trading_signal → signal_alerts`
- Add two new jobs after signal_alerts: `auto_track_signals` and `monitor_positions`
- Use APScheduler 3.11 (already installed), follow `backend/app/scheduler/manager.py` patterns
- Auto-Track source: `ai_analyses` table where `analysis_type = 'trading_signal'`
- Filter: `score > 0` AND not already tracked (dedup by ai_analysis_id)
- Extract from `raw_response` JSONB: entry, SL, TP1, TP2, direction, timeframe, confidence, position_size_pct, risk_reward_ratio
- Create PaperTrade in PENDING status
- Position sizing via `calculate_position_size()` from Phase 22
- SimulationConfig: read `min_confidence_threshold` and `auto_track_enabled`
- Position monitor runs daily after price crawl
- PENDING trades: activate at D+1 open price
- Active positions: check SL first (low <= effective_stop_loss), then TP1, then TP2
- Ambiguous bar rule: SL wins when both SL and TP breached same day
- Timeout: swing > 15 trading days, position > 60 trading days → close at market close price
- Batch query strategy: 2 queries (positions + prices), process in-memory
- Pool constraint: pool_size=5, max_overflow=3 (8 max connections)
- No OHLCV data → skip position (market holiday, suspended)
- SimulationConfig auto_track_enabled=false → skip auto-track job
- No open positions → monitor returns early

### Agent's Discretion
- Internal function decomposition within each job
- Error handling granularity (per-trade vs batch)
- Logging verbosity levels
- Whether to add a `last_checked_date` column or track by signal_date comparison
- Telegram notification on trade events (can be deferred to Phase 25)

### Deferred Ideas (OUT OF SCOPE)
- API endpoints (Phase 24)
- Frontend dashboard (Phase 25+)
- Telegram /paper command (Phase 25)
- Manual "Follow Signal" feature (Phase 24)
- Analytics queries (Phase 24)
- Fee simulation (ADV-01, future)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PT-01 | Auto-track all valid AI signals (score > 0) as paper trades | Scheduler chain integration after `daily_trading_signal_triggered`; extract from `raw_response` JSONB → `TickerTradingSignal` schema; dedup by `ai_analysis_id` |
| PT-04 | Daily position monitoring — check SL/TP/timeout against OHLCV | Position monitor job chained after `daily_price_crawl_upcom`; batch-load positions + prices; state machine transitions using Phase 22's `validate_transition()` |
| PT-06 | PENDING trades activate at D+1 open price (no lookahead bias) | Monitor checks PENDING trades → if next-day price data available, activate at `DailyPrice.open`; PENDING signal_date is D, activation date is D+1 |
| PT-08 | Exclude score=0 invalid signals with deduplication | Filter `WHERE score > 0 AND signal != 'invalid'`; unique constraint or pre-check on `ai_analysis_id` prevents duplicate creation |
</phase_requirements>

## Standard Stack

### Core (all existing — zero new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | 3.11.2 | Job scheduling | Already installed; EVENT_JOB_EXECUTED chaining pattern proven across 10+ jobs [VERIFIED: manager.py] |
| SQLAlchemy | 2.0 | Async ORM queries | `async_session()` pattern; `select()`, `.where()`, `.in_()` for batch queries [VERIFIED: database.py] |
| asyncpg | 0.31 | PostgreSQL async driver | Powers the `create_async_engine` in database.py [VERIFIED: database.py] |
| loguru | 0.7.3 | Structured logging | Used in every job function for structured START/COMPLETE/FAILED logging [VERIFIED: jobs.py] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic | 2.x | Parse `raw_response` JSONB back to `TickerTradingSignal` | When extracting signal data from ai_analyses.raw_response |
| Decimal (stdlib) | — | All price/P&L arithmetic | Required by Numeric(12,2) columns; avoid float for financial math |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-memory batch processing | Per-position queries | Would cause N+1 pool exhaustion — REJECTED per CONTEXT.md |
| Pydantic model_validate for JSONB parsing | Manual dict access | Pydantic gives type safety + validation; slightly more imports but much safer |
| Single combined job | Two separate jobs | Two jobs allows independent failure/retry; matches existing architecture |

**No installation needed** — all dependencies are already in the project.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── scheduler/
│   ├── manager.py        # ADD: 2 chain points (6 lines total)
│   └── jobs.py           # ADD: 2 new async job functions (~120 lines each)
├── services/
│   └── paper_trade_service.py  # EXTEND: add auto_track_signals() + monitor_positions() orchestration methods
├── models/
│   ├── paper_trade.py    # EXISTS (Phase 22) — no changes
│   └── simulation_config.py  # EXISTS (Phase 22) — no changes
└── database.py           # EXISTS — async_session pattern (no changes)
```

### Pattern 1: Scheduler Job Function (proven pattern)
**What:** Every scheduler job follows the same structure: `async with async_session()`, start execution tracking, try/except, commit
**When to use:** All new scheduled tasks
**Example:**
```python
# Source: backend/app/scheduler/jobs.py lines 443-481 (daily_trading_signal_analysis)
async def paper_trade_auto_track():
    """Auto-create paper trades from today's valid AI signals.
    
    Chained after daily_trading_signal_triggered.
    Never raises on partial failure (pipeline continues).
    """
    logger.info("=== PAPER TRADE AUTO-TRACK START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("paper_trade_auto_track")
        try:
            # 1. Check if auto-track enabled
            config = await _get_simulation_config(session)
            if not config.auto_track_enabled:
                await job_svc.complete(execution, status="skipped",
                    result_summary={"reason": "auto_track_enabled=false"})
                await session.commit()
                return

            # 2. Query today's valid signals
            # 3. Create paper trades (dedup check)
            # 4. Track results
            ...
            
            await job_svc.complete(execution, status=status, result_summary=summary)
            await session.commit()
            logger.info(f"=== PAPER TRADE AUTO-TRACK COMPLETE: {summary} ===")

        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== PAPER TRADE AUTO-TRACK FAILED: {e} ===")
            raise
```

### Pattern 2: Job Chain Insertion (proven pattern)
**What:** Add new job to the `_on_job_executed` event handler in manager.py
**When to use:** When a new job needs to trigger after an existing job completes
**Example:**
```python
# Source: backend/app/scheduler/manager.py lines 170-188
# In the elif block for "daily_trading_signal_triggered":
elif event.job_id in ("daily_trading_signal_triggered",):
    # ... existing signal_alert_check chain ...
    # ... existing hnx_upcom_analysis chain ...
    
    # NEW: Paper trade auto-tracking (parallel with alerts)
    from app.scheduler.jobs import paper_trade_auto_track
    logger.info("Chaining: daily_trading_signal → paper_trade_auto_track")
    scheduler.add_job(
        paper_trade_auto_track,
        id="paper_trade_auto_track_triggered",
        replace_existing=True,
        misfire_grace_time=3600,
    )
```

### Pattern 3: Batch Query for Positions + Prices (pool-safe)
**What:** Load all needed data in exactly 2 queries, process in-memory
**When to use:** Position monitoring — avoids N+1 against limited pool
**Example:**
```python
# Query 1: All open positions
from sqlalchemy import select
stmt_positions = select(PaperTrade).where(
    PaperTrade.status.in_([
        TradeStatus.PENDING,
        TradeStatus.ACTIVE,
        TradeStatus.PARTIAL_TP,
    ])
)
positions = (await session.execute(stmt_positions)).scalars().all()

if not positions:
    # No open positions — early return
    return {"checked": 0, "transitions": 0}

# Query 2: Today's prices for all tickers with open positions
ticker_ids = list({p.ticker_id for p in positions})
stmt_prices = select(DailyPrice).where(
    DailyPrice.ticker_id.in_(ticker_ids),
    DailyPrice.date == today,
)
prices = (await session.execute(stmt_prices)).scalars().all()
price_map = {p.ticker_id: p for p in prices}  # O(1) lookup
```

### Pattern 4: raw_response JSONB Extraction
**What:** Parse stored JSONB back into typed Pydantic model for safe field access
**When to use:** Auto-track job extracting signal data from ai_analyses
**Example:**
```python
# raw_response is stored via analysis.model_dump() — a TickerTradingSignal dict
# Source: ai_analysis_service.py line 681
from app.schemas.analysis import TickerTradingSignal

raw = analysis_row.raw_response  # dict from JSONB
signal = TickerTradingSignal.model_validate(raw)

# Determine which direction to track (recommended_direction from signal)
recommended = signal.recommended_direction.value  # "long" or "bearish"
if recommended == "long":
    plan = signal.long_analysis.trading_plan
    confidence = signal.long_analysis.confidence
else:
    plan = signal.bearish_analysis.trading_plan
    confidence = signal.bearish_analysis.confidence

# Extract all needed fields
entry_price = Decimal(str(plan.entry_price))
stop_loss = Decimal(str(plan.stop_loss))
take_profit_1 = Decimal(str(plan.take_profit_1))
take_profit_2 = Decimal(str(plan.take_profit_2))
position_size_pct = plan.position_size_pct
timeframe = plan.timeframe.value  # "swing" or "position"
risk_reward_ratio = plan.risk_reward_ratio
```

### Pattern 5: Position Monitor State Machine Evaluation
**What:** Evaluate each open position against today's OHLCV bar with priority ordering
**When to use:** Daily position monitoring
**Example:**
```python
# Priority: SL first → TP2 → TP1 (conservative)
# For LONG direction:
def evaluate_long_position(trade: PaperTrade, bar: DailyPrice) -> tuple[TradeStatus | None, Decimal | None]:
    """Evaluate a LONG position against today's bar.
    
    Returns (new_status, exit_price) or (None, None) if no transition.
    """
    effective_sl = trade.effective_stop_loss
    
    # Gap-through at open? (open already past SL)
    if bar.open <= effective_sl:
        return _determine_sl_status(trade), bar.open  # Fill at gap price
    
    # SL check (ALWAYS first — conservative/ambiguous bar rule)
    if bar.low <= effective_sl:
        return _determine_sl_status(trade), effective_sl
    
    # TP2 check (if PARTIAL_TP state)
    if trade.status == TradeStatus.PARTIAL_TP:
        if bar.open >= trade.take_profit_2:
            return TradeStatus.CLOSED_TP2, bar.open  # Gap-through TP2
        if bar.high >= trade.take_profit_2:
            return TradeStatus.CLOSED_TP2, trade.take_profit_2
    
    # TP1 check (if ACTIVE state)
    if trade.status == TradeStatus.ACTIVE:
        if bar.open >= trade.take_profit_1:
            # Gap through TP1 — still apply partial TP at open price
            return TradeStatus.PARTIAL_TP, bar.open
        if bar.high >= trade.take_profit_1:
            return TradeStatus.PARTIAL_TP, trade.take_profit_1
    
    return None, None
```

### Anti-Patterns to Avoid
- **N+1 queries in position monitor:** Never loop and query price per position. Always batch-load all prices in one query.
- **Using calendar days for timeout:** Must count trading days from `daily_prices` rows, not `timedelta(days=N)`.
- **Float for price comparison:** Always use `Decimal` for all price arithmetic. The model uses `Numeric(12,2)`.
- **Modifying existing job chain behavior:** Only ADD new chain branches, never modify existing chains.
- **Raising exceptions in auto-track:** Auto-track should be "never-raises" (like signal_alert_check) — its failure shouldn't break the signal pipeline.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| State machine transitions | Custom if/elif chains | `validate_transition()` from paper_trade_service.py | Already covers all 7 states + validates preconditions |
| Position sizing | Manual calculation | `calculate_position_size()` from paper_trade_service.py | Handles 100-lot rounding, minimum checks |
| Partial TP logic | Inline field mutations | `apply_partial_tp()` from paper_trade_service.py | Handles half-qty rounding, breakeven SL, status change |
| P&L calculation | Custom arithmetic | `calculate_pnl()` from paper_trade_service.py | Handles LONG/BEARISH, partial TP legs |
| JSONB → typed schema | Manual dict access | `TickerTradingSignal.model_validate(raw)` | Type-safe, validated, matches storage format |
| Job execution tracking | Manual logging | `JobExecutionService` start/complete/fail | Already used by all 10+ existing jobs |

**Key insight:** Phase 22 built all the computation primitives. Phase 23's job is orchestration only — read data, call existing service functions, write results.

## Common Pitfalls

### Pitfall 1: SL/TP Ambiguous Bar
**What goes wrong:** Both SL and TP breach in the same daily candle; system picks the wrong one
**Why it happens:** Daily OHLCV has no intraday path information
**How to avoid:** Check SL FIRST, always. If `low <= effective_sl`, close at SL regardless of whether `high >= TP`. This is codified in CONTEXT.md as a locked decision.
**Warning signs:** Paper trades showing TP hit on days where the low was also below SL

### Pitfall 2: Lookahead Bias in Entry
**What goes wrong:** Using same-day close as entry price instead of D+1 open
**Why it happens:** Signal generated at day D's market close; temptation to use D's close as entry
**How to avoid:** PENDING status: trade created on signal_date=D. Activation happens when position monitor sees D+1's DailyPrice data → entry_date = D+1, entry at D+1 open price
**Warning signs:** entry_date == signal_date in paper_trades table

### Pitfall 3: Gap-Through at Wrong Fill Price
**What goes wrong:** Stock gaps past SL/TP at open; system records fill at SL/TP level instead of actual gap price
**Why it happens:** Simple comparison `if low <= SL: fill at SL` ignores open price check
**How to avoid:** Always check open price first: `if open <= effective_sl: fill at open` (for LONG). Apply to ALL exit types.
**Warning signs:** Fill prices always exactly equal to SL/TP — never at gap prices

### Pitfall 4: Duplicate Trades on Job Retry
**What goes wrong:** Auto-track job re-runs (misfire recovery) and creates duplicate paper trades
**Why it happens:** No deduplication check before INSERT
**How to avoid:** Check `WHERE ai_analysis_id = :id` before creating. The CONTEXT.md specifies dedup by ai_analysis_id. Consider `INSERT ... ON CONFLICT DO NOTHING` if a unique constraint is added.
**Warning signs:** Multiple paper_trades with same ai_analysis_id

### Pitfall 5: Pool Exhaustion
**What goes wrong:** Position monitor opens multiple connections for per-trade queries
**Why it happens:** Aiven pool is only 5+3=8; N+1 pattern saturates pool
**How to avoid:** Exactly 2 queries per monitor run (positions + prices), process in-memory, single batch commit
**Warning signs:** `TimeoutError` from asyncpg pool during position monitor runs

### Pitfall 6: Calendar-Day Timeout
**What goes wrong:** Timeout triggered based on `signal_date + timedelta(days=15)` instead of counting trading days
**Why it happens:** Calendar math is simpler but wrong for VN market (holidays, weekends)
**How to avoid:** Count distinct dates in `daily_prices` for the ticker after entry_date. Query: `SELECT COUNT(DISTINCT date) FROM daily_prices WHERE ticker_id=:tid AND date > :entry_date`
**Warning signs:** Positions timing out day after Vietnamese holidays (5+ day non-trading stretches)

### Pitfall 7: BEARISH Direction Inverted Comparisons
**What goes wrong:** Using LONG logic (low <= SL) for BEARISH positions where SL is above entry
**Why it happens:** BEARISH SL is higher than entry; TP is lower. All comparisons are inverted.
**How to avoid:** Explicit direction-conditional logic: LONG checks low vs SL (hit if low drops), BEARISH checks high vs SL (hit if high rises)
**Warning signs:** BEARISH positions hitting "SL" when price drops (should be profitable)

## Code Examples

### Complete Auto-Track Job Structure
```python
# Source: Pattern derived from jobs.py lines 443-481 + CONTEXT.md specification
from datetime import date
from decimal import Decimal

from loguru import logger
from sqlalchemy import select

from app.database import async_session
from app.models.ai_analysis import AIAnalysis, AnalysisType
from app.models.paper_trade import PaperTrade, TradeStatus, TradeDirection
from app.models.simulation_config import SimulationConfig
from app.schemas.analysis import TickerTradingSignal
from app.services.job_execution_service import JobExecutionService
from app.services.paper_trade_service import calculate_position_size


async def paper_trade_auto_track():
    """Auto-create paper trades from today's valid trading signals.

    Chained after daily_trading_signal_triggered.
    Never raises — auto-track failure must not break pipeline.
    """
    logger.info("=== PAPER TRADE AUTO-TRACK START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("paper_trade_auto_track")
        try:
            # 1. Check config
            config_row = await session.get(SimulationConfig, 1)
            if not config_row or not config_row.auto_track_enabled:
                await job_svc.complete(execution, status="skipped",
                    result_summary={"reason": "auto_track_disabled"})
                await session.commit()
                logger.info("=== PAPER TRADE AUTO-TRACK SKIPPED (disabled) ===")
                return

            # 2. Query today's valid trading signals
            today = date.today()
            stmt = select(AIAnalysis).where(
                AIAnalysis.analysis_type == AnalysisType.TRADING_SIGNAL,
                AIAnalysis.analysis_date == today,
                AIAnalysis.score > 0,
            )
            signals = (await session.execute(stmt)).scalars().all()

            # 3. Get already-tracked analysis IDs (dedup)
            existing_ids_stmt = select(PaperTrade.ai_analysis_id).where(
                PaperTrade.ai_analysis_id.in_([s.id for s in signals])
            )
            existing_ids = set(
                (await session.execute(existing_ids_stmt)).scalars().all()
            )

            # 4. Create paper trades for untracked signals
            created = 0
            skipped = 0
            for analysis in signals:
                if analysis.id in existing_ids:
                    skipped += 1
                    continue
                    
                # Filter by min_confidence_threshold
                # Parse raw_response → TickerTradingSignal
                try:
                    signal = TickerTradingSignal.model_validate(analysis.raw_response)
                except Exception:
                    skipped += 1
                    continue

                # Determine direction + extract plan
                direction = signal.recommended_direction.value
                dir_analysis = (signal.long_analysis if direction == "long"
                               else signal.bearish_analysis)
                
                if dir_analysis.confidence < config_row.min_confidence_threshold:
                    skipped += 1
                    continue

                plan = dir_analysis.trading_plan
                entry_price = Decimal(str(plan.entry_price))
                
                quantity = calculate_position_size(
                    capital=config_row.initial_capital,
                    allocation_pct=plan.position_size_pct,
                    entry_price=entry_price,
                )
                if quantity == 0:
                    skipped += 1
                    continue

                trade = PaperTrade(
                    ticker_id=analysis.ticker_id,
                    ai_analysis_id=analysis.id,
                    direction=TradeDirection(direction),
                    status=TradeStatus.PENDING,
                    entry_price=entry_price,
                    stop_loss=Decimal(str(plan.stop_loss)),
                    take_profit_1=Decimal(str(plan.take_profit_1)),
                    take_profit_2=Decimal(str(plan.take_profit_2)),
                    quantity=quantity,
                    signal_date=today,
                    confidence=dir_analysis.confidence,
                    timeframe=plan.timeframe.value,
                    position_size_pct=plan.position_size_pct,
                    risk_reward_ratio=plan.risk_reward_ratio,
                )
                session.add(trade)
                created += 1

            summary = {"created": created, "skipped": skipped, "signals_total": len(signals)}
            await job_svc.complete(execution, status="success", result_summary=summary)
            await session.commit()
            logger.info(f"=== PAPER TRADE AUTO-TRACK COMPLETE: {summary} ===")

        except Exception as e:
            await job_svc.complete(
                execution, status="partial",
                result_summary={"error": str(e)[:200]},
            )
            await session.commit()
            logger.error(f"=== PAPER TRADE AUTO-TRACK FAILED: {e} ===")
            # Never raises — per pattern of daily_signal_alert_check
```

### Position Monitor — PENDING Activation Logic
```python
# PENDING → ACTIVE at D+1 open price
# trade.signal_date is D; we look for DailyPrice on date > signal_date
def activate_pending_trade(trade: PaperTrade, bar: DailyPrice) -> None:
    """Activate a PENDING trade at the bar's open price (D+1 open)."""
    trade.status = TradeStatus.ACTIVE
    trade.entry_date = bar.date
    # Entry is at D+1 open — no lookahead bias
    # Note: entry_price stays as the AI's target (for reference)
    # but actual fill is at open
```

### Timeout Evaluation via Trading Days
```python
# Count trading days from daily_prices for timeout check
from sqlalchemy import func as sqlfunc

TIMEOUT_DAYS = {"swing": 15, "position": 60}

async def check_timeout(session, trade: PaperTrade, today: date) -> bool:
    """Check if trade has exceeded timeout in trading days."""
    if not trade.entry_date:
        return False
    max_days = TIMEOUT_DAYS.get(trade.timeframe, 60)
    stmt = select(sqlfunc.count()).select_from(DailyPrice).where(
        DailyPrice.ticker_id == trade.ticker_id,
        DailyPrice.date > trade.entry_date,
        DailyPrice.date <= today,
    )
    trading_days = (await session.execute(stmt)).scalar() or 0
    return trading_days >= max_days
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Per-position DB queries | Batch-load all positions + prices in 2 queries | Architecture research | Prevents pool exhaustion on Aiven (5+3 pool) |
| Calendar-day timeouts | Trading-day timeouts (count daily_prices rows) | Architecture research | Prevents premature timeout across VN holidays |
| Entry at signal-day close | Entry at D+1 open (PENDING → ACTIVE) | Locked decision | Eliminates lookahead bias in all analytics |
| TP-first evaluation | SL-first evaluation (conservative) | Locked decision | Pessimistic bias ensures honest signal validation |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Timeout for `position` timeframe is 60 trading days (CONTEXT.md says 60) vs research doc ARCHITECTURE.md that says 45 | Code Examples | Incorrect timeout could prematurely close or leave stale positions; CONTEXT.md says 60, which takes precedence |
| A2 | Auto-track job should use "never-raises" pattern (like signal_alert_check) rather than "raises on complete failure" pattern | Architecture | If it raises, it would break the signal pipeline chain for downstream jobs |
| A3 | `TickerTradingSignal.model_validate(raw_response)` works because raw_response stores `analysis.model_dump()` | Code Examples | If raw_response format differs, parsing will fail silently |
| A4 | Position monitor should be chained after `daily_price_crawl_upcom` (not after trading_signal) | Architecture | CONTEXT.md says "run after market close (after price crawl completes)" — aligns with this |

## Open Questions

1. **Entry price semantics for PENDING → ACTIVE**
   - What we know: CONTEXT.md says "PENDING activates at D+1 open price"
   - What's unclear: Should the `entry_price` column be overwritten with actual open, or should we keep AI's target and add a separate `filled_price` column?
   - Recommendation: The model has `entry_price` (from signal) but no separate `filled_price`. Overwrite `entry_price` with D+1 open since Phase 22 model doesn't have a filled_price field. This is acceptable because `ai_analysis_id` FK preserves original signal data.

2. **Timeout trading days query: per-trade or batch?**
   - What we know: We need to count trading days per ticker since entry_date
   - What's unclear: Whether to batch this across all positions or query per-trade
   - Recommendation: For timeout check, use batch approach: load count of distinct dates per ticker_id since earliest entry_date, group by ticker_id. One query covers all positions.

3. **BEARISH direction handling in position monitor**
   - What we know: BEARISH direction inverts all comparisons (SL is above entry, TPs are below)
   - What's unclear: CONTEXT.md doesn't explicitly state the BEARISH evaluation rules
   - Recommendation: For BEARISH: `high >= effective_sl → SL hit`; `low <= take_profit_1 → TP1 hit`; `low <= take_profit_2 → TP2 hit`. Gap-through: `open >= effective_sl → fill at open`.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already configured) |
| Config file | backend/tests/conftest.py |
| Quick run command | `cd backend && python -m pytest tests/test_paper_trade_auto_track.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PT-01 | Auto-track creates paper trades from valid signals | unit | `pytest tests/test_paper_trade_auto_track.py::TestAutoTrack -x` | ❌ Wave 0 |
| PT-04 | Position monitor checks SL/TP/timeout against OHLCV | unit | `pytest tests/test_position_monitor.py::TestPositionMonitor -x` | ❌ Wave 0 |
| PT-06 | PENDING activates at D+1 open (no lookahead) | unit | `pytest tests/test_position_monitor.py::TestPendingActivation -x` | ❌ Wave 0 |
| PT-08 | Score=0 excluded, dedup prevents duplicates | unit | `pytest tests/test_paper_trade_auto_track.py::TestDeduplication -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_paper_trade_auto_track.py tests/test_position_monitor.py -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_paper_trade_auto_track.py` — covers PT-01, PT-08
- [ ] `tests/test_position_monitor.py` — covers PT-04, PT-06
- [ ] No new fixtures needed beyond existing `mock_db_session` from conftest.py — all business logic is pure Python functions

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user app, no auth |
| V3 Session Management | No | Scheduler jobs, no user sessions |
| V4 Access Control | No | Internal jobs only |
| V5 Input Validation | Yes | Pydantic model_validate for JSONB parsing; Decimal for price math |
| V6 Cryptography | No | No secrets handled in this phase |

### Known Threat Patterns for Scheduler Jobs

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed JSONB in raw_response | Tampering | `model_validate()` with try/except — skip invalid |
| Integer overflow in position sizing | Tampering | `calculate_position_size()` already bounds to 100-lot |
| Pool exhaustion (DoS-like) | Denial of Service | Batch queries (2 max per run) per CONTEXT.md |

## Sources

### Primary (HIGH confidence)
- `backend/app/scheduler/manager.py` — Full job chain structure, _on_job_executed handler [VERIFIED: lines 77-188]
- `backend/app/scheduler/jobs.py` — All job function patterns, daily_trading_signal_analysis [VERIFIED: lines 443-481]
- `backend/app/models/paper_trade.py` — PaperTrade model with TradeStatus enum [VERIFIED: full file]
- `backend/app/models/simulation_config.py` — SimulationConfig singleton [VERIFIED: full file]
- `backend/app/services/paper_trade_service.py` — validate_transition, calculate_pnl, calculate_position_size, apply_partial_tp [VERIFIED: full file]
- `backend/app/models/ai_analysis.py` — AIAnalysis model with raw_response JSONB [VERIFIED: full file]
- `backend/app/models/daily_price.py` — DailyPrice OHLCV model [VERIFIED: full file]
- `backend/app/schemas/analysis.py` — TickerTradingSignal, TradingPlanDetail, DirectionAnalysis schemas [VERIFIED: lines 109-152]
- `backend/app/database.py` — async_session factory, pool_size=5, max_overflow=3 [VERIFIED: full file]
- `backend/alembic/versions/013_paper_trade_tables.py` — Migration establishing DB schema [VERIFIED: full file]
- `backend/app/services/ai_analysis_service.py` — How raw_response is stored (model_dump) [VERIFIED: line 681]

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md` — Integration point specifications, data flow details [VERIFIED: project research]
- `.planning/research/PITFALLS.md` — All 18 pitfalls with prevention strategies [VERIFIED: project research]
- `.planning/research/SUMMARY.md` — Phase structure rationale [VERIFIED: project research]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and used by 10+ existing jobs
- Architecture: HIGH — both integration points verified against actual code, exact line numbers
- Pitfalls: HIGH — all pitfalls documented in project research with verified codebase context

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 (stable internal architecture, no external dependencies changing)

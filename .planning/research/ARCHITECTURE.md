# Architecture: Paper Trading & Signal Verification Integration

**Domain:** Paper trading simulation + AI signal accuracy analytics
**Researched:** 2026-04-21
**Confidence:** HIGH — all integration points verified against existing codebase

## Recommended Architecture

The paper trading system integrates as a **parallel subsystem** that hooks into two existing pipeline stages: (1) the trading signal output and (2) the daily price crawl. It adds **one new model** (PaperTrade), **one config table** (SimulationConfig), **one new service** (PaperTradingService), **one new API router** (`/api/paper-trading`), **two new scheduler jobs** (auto-track + position monitor), and extends the existing scheduler chain at two points. No existing code is modified structurally — only two injection points in the scheduler chain plus standard registrations.

### Design Philosophy

Single-user personal app. No need for:
- Separate PaperPosition model — a PaperTrade IS a position (one signal = one position, no averaging in)
- Event sourcing — state machine on PaperTrade.status handles the full lifecycle
- Complex matching engine — daily OHLCV is sufficient for TP/SL checks
- Real-time monitoring — price checks run once daily after market close

### System Overview

```
EXISTING PIPELINE (unchanged):
price_crawl → indicators → AI → news → sentiment → combined → trading_signal
                                                                     │
NEW CHAIN EXTENSIONS:                                                │
                                                                     ├──→ signal_alert_check (existing)
                                                                     ├──→ hnx_upcom_analysis (existing)
                                                                     └──→ paper_trade_auto_track (NEW)
                                                                              │
                                                                              ▼
                                                                     Create PaperTrade records
                                                                     from today's signals

price_crawl_upcom ──→ indicator_compute (existing)
         │
         └──→ paper_position_monitor (NEW, parallel with indicators)
                     │
                     ▼
              Check ACTIVE/PARTIAL_TP trades against today's H/L
              → TP1/TP2/SL/Timeout transitions
              → Telegram notifications
              → Update SimulationConfig.current_capital
```

### Component Boundaries

| Component | Responsibility | Location | Communicates With |
|-----------|---------------|----------|-------------------|
| **PaperTrade model** | Data persistence — single table for full trade lifecycle | `app/models/paper_trade.py` | Database via SQLAlchemy |
| **SimulationConfig model** | Virtual capital & auto-track settings (one row) | `app/models/simulation_config.py` | Database via SQLAlchemy |
| **PaperTradingService** | All business logic: create, monitor, close, analytics queries | `app/services/paper_trading_service.py` | PaperTrade model, AIAnalysis model, DailyPrice model, Ticker model |
| **Paper Trading API** | REST endpoints for trades, config, analytics | `app/api/paper_trading.py` | PaperTradingService |
| **Auto-track job** | Scheduler job — creates PaperTrades from new signals | `app/scheduler/jobs.py` (extend) | PaperTradingService, AIAnalysis model |
| **Position monitor job** | Scheduler job — checks TP/SL/timeout daily | `app/scheduler/jobs.py` (extend) | PaperTradingService, DailyPrice model |
| **Telegram integration** | Notifications for trade events + manual commands | `app/telegram/` (extend) | PaperTradingService, MessageFormatter |
| **Frontend dashboard** | Analytics page with charts, tables, filters | `src/app/dashboard/paper-trading/page.tsx` | Paper Trading API |

---

## Data Model

### PaperTrade — Single Table, Full Lifecycle

**Rationale:** The milestone mentions PaperTrade + PaperPosition + SimulationConfig. After analyzing the domain, PaperPosition is unnecessary. Each AI signal creates exactly one position — there's no concept of "adding to a position" from multiple signals. A single PaperTrade table with a state machine covers the entire lifecycle, matching the simplicity principle for a single-user app.

```python
# app/models/paper_trade.py
class TradeStatus(str, enum.Enum):
    PENDING = "pending"           # Signal recorded, entry not yet filled
    ACTIVE = "active"             # Entry filled, full position open
    PARTIAL_TP = "partial_tp"     # TP1 hit, 50% closed, SL moved to breakeven
    CLOSED = "closed"             # Fully closed

class CloseReason(str, enum.Enum):
    TAKE_PROFIT_1 = "tp1"        # Closed at TP1 (if no partial TP mode)
    TAKE_PROFIT_2 = "tp2"        # TP2 hit after partial TP
    STOP_LOSS = "stop_loss"      # SL hit from ACTIVE state
    BREAKEVEN = "breakeven"      # Breakeven SL hit after TP1 partial
    TIMEOUT = "timeout"          # Timeframe expired, closed at market
    MANUAL = "manual"            # User manually closed
    EXPIRED_UNFILLED = "expired" # Entry never filled within timeframe

class TradeSource(str, enum.Enum):
    AUTO = "auto"                # Auto-tracked from AI signal
    MANUAL = "manual"            # User-initiated from signal

class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id: BigInteger, PK
    ticker_id: Integer, FK(tickers.id)
    ai_analysis_id: BigInteger, FK(ai_analyses.id), nullable  # Link to source signal
    source: TradeSource                                        # auto or manual
    direction: String(10)                                      # "long" or "bearish"
    status: TradeStatus, default=PENDING

    # Plan (from AI signal, optionally modified for manual trades)
    entry_price: Numeric(12,2)
    stop_loss: Numeric(12,2)
    take_profit_1: Numeric(12,2)
    take_profit_2: Numeric(12,2)
    quantity: Integer                    # Shares (calculated from position_size_pct × capital)
    position_size_pct: Integer           # From AI recommendation (1-100)
    timeframe: String(20)                # "swing" or "position"
    timeout_date: Date                   # Calculated: opened_at + timeframe_days

    # Execution tracking
    effective_sl: Numeric(12,2)          # Current SL (moves to breakeven after TP1)
    entry_filled_at: Date, nullable      # When entry was filled
    entry_filled_price: Numeric(12,2), nullable  # Actual fill price (day's close or open)

    # Partial TP tracking
    tp1_hit: Boolean, default=False
    tp1_hit_date: Date, nullable
    tp1_pnl: Numeric(12,2), nullable     # P&L from the 50% closed at TP1

    # Final close tracking
    closed_at: Date, nullable
    close_reason: CloseReason, nullable
    exit_price: Numeric(12,2), nullable  # Final exit price for remaining position
    pnl_amount: Numeric(12,2), nullable  # Total P&L (tp1_pnl + remaining_pnl)
    pnl_pct: Numeric(8,4), nullable      # Return percentage
    risk_reward_actual: Numeric(8,4), nullable  # Actual R:R achieved

    # Metadata (denormalized for analytics — never changes after creation)
    ai_confidence: Integer, nullable     # Cached from AI signal for analytics queries
    ai_score: Integer, nullable          # Cached signal score for analytics
    sector: String(100), nullable        # Cached from ticker for analytics grouping
    notes: Text, nullable                # User notes for manual trades

    created_at: TIMESTAMP(tz=True), server_default=now()
    updated_at: TIMESTAMP(tz=True), onupdate=now()

    __table_args__ = (
        Index("ix_paper_trades_status", "status"),
        Index("ix_paper_trades_ticker_date", "ticker_id", "created_at"),
        Index("ix_paper_trades_closed_at", "closed_at"),  # For analytics date range queries
    )
```

**Why cache `ai_confidence`, `ai_score`, `sector`?** Analytics queries (win rate by confidence bracket, P&L by sector) would otherwise require 3-way JOINs on every dashboard load. Denormalization is correct here — these values never change after creation, and there are at most ~400 paper trades per day.

### SimulationConfig — Single Row

```python
# app/models/simulation_config.py
class SimulationConfig(Base):
    __tablename__ = "simulation_config"

    id: Integer, PK, default=1          # Always row 1 (single-user)
    initial_capital: Numeric(15,2), default=100_000_000  # 100M VND default
    current_capital: Numeric(15,2), default=100_000_000  # Updated on each trade close
    max_position_pct: Integer, default=10                # Max % of capital per trade
    auto_track_enabled: Boolean, default=True
    auto_track_min_confidence: Integer, default=7        # Only auto-track signals >= this
    auto_track_direction: String(20), default="recommended"  # "recommended", "long", "bearish", "both"
    partial_tp_enabled: Boolean, default=True             # Enable 50%/50% TP strategy
    created_at: TIMESTAMP(tz=True)
    updated_at: TIMESTAMP(tz=True)
```

**Timeframe-to-days mapping** (constant, not in DB):
```python
TIMEFRAME_DAYS = {
    "swing": 15,       # Max 15 trading days
    "position": 45,    # Max 45 trading days
}
```

---

## Integration Points (Modifications to Existing Code)

### Integration Point 1: Scheduler Chain — Auto-Track After Signals

**File:** `app/scheduler/manager.py` — `_on_job_executed()`
**Change:** Add `paper_trade_auto_track` to existing `daily_trading_signal_triggered` branch

```python
# EXISTING code (line 170-188) — ADD 3 lines at the end:
elif event.job_id in ("daily_trading_signal_triggered",):
    from app.scheduler.jobs import daily_signal_alert_check
    scheduler.add_job(daily_signal_alert_check, ...)  # existing
    from app.scheduler.jobs import daily_hnx_upcom_analysis
    scheduler.add_job(daily_hnx_upcom_analysis, ...)  # existing

    # NEW: Paper trade auto-tracking (parallel with alerts)
    from app.scheduler.jobs import paper_trade_auto_track
    scheduler.add_job(paper_trade_auto_track,
        id="paper_trade_auto_track_triggered",
        replace_existing=True, misfire_grace_time=3600)
```

**Impact:** 3 lines added. Auto-track runs in parallel with existing signal_alert_check and hnx_upcom_analysis. No existing behavior changed.

### Integration Point 2: Scheduler Chain — Position Monitor After Price Crawl

**File:** `app/scheduler/manager.py` — `_on_job_executed()`
**Change:** Add position monitor to the UPCOM crawl chain

```python
# EXISTING code (line 87-113) for daily_price_crawl_upcom — ADD 3 lines:
if event.job_id == "daily_price_crawl_upcom":
    scheduler.add_job(daily_indicator_compute, ...)    # existing
    scheduler.add_job(daily_price_alert_check, ...)    # existing
    scheduler.add_job(daily_corporate_action_check, ...)  # existing

    # NEW: Paper position monitor (parallel with indicators)
    from app.scheduler.jobs import paper_position_monitor
    scheduler.add_job(paper_position_monitor,
        id="paper_position_monitor_triggered",
        replace_existing=True, misfire_grace_time=3600)
```

**Impact:** 3 lines added. Position monitor runs in parallel with indicator compute — no pipeline delay.

### Integration Point 3: API Router Registration

**File:** `app/api/router.py` — 1 import + 1 include_router call

### Integration Point 4: Model Registration for Alembic

**File:** `app/models/__init__.py` — 2 imports (PaperTrade, SimulationConfig)

### Integration Point 5: Telegram Handler Registration

**File:** `app/telegram/handlers.py` — `register_handlers()` — add `/paper`, `/paper_status` commands

### Integration Point 6: Navbar Link

**File:** `frontend/src/components/navbar.tsx` — add to NAV_LINKS array:
```typescript
{ href: "/dashboard/paper-trading", label: "Giả lập" }
```

---

## Data Flow Details

### Flow 1: Auto-Track (runs daily after trading_signal job)

```
paper_trade_auto_track job:
1. Read SimulationConfig (auto_track_enabled, min_confidence, direction filter)
2. If disabled → return early
3. Query today's AIAnalysis WHERE analysis_type='trading_signal' AND analysis_date=today
4. For each signal:
   a. Parse raw_response JSONB → TickerTradingSignal
   b. Determine which direction to track based on config:
      - "recommended" → use recommended_direction
      - "long"/"bearish" → use that direction only
      - "both" → create 2 PaperTrades (one per direction)
   c. Filter by confidence >= min_confidence
   d. Calculate quantity from position_size_pct × current_capital ÷ entry_price
      (round down to VN lot size of 100 shares)
   e. Calculate timeout_date from timeframe + today
   f. Check if entry is already fillable (today's close near entry_price ±1%)
      - If yes: status=ACTIVE, entry_filled_at=today, entry_filled_price=close
      - If no: status=PENDING
   g. INSERT PaperTrade with denormalized ai_confidence, ai_score, sector
5. Log summary: "Auto-tracked X signals (Y active, Z pending)"
```

**Critical: No duplicates.** Before inserting, check `NOT EXISTS paper_trade WHERE ticker_id=X AND ai_analysis_id=Y AND source='auto'`. Prevents double-creation on misfire recovery.

### Flow 2: Position Monitor (runs daily after price crawl)

```
paper_position_monitor job:
1. Query all PaperTrades WHERE status IN ('pending', 'active', 'partial_tp')
2. For each trade, fetch today's DailyPrice (high, low, close)
3. State machine transitions:

   PENDING:
   ├─ Entry fillable? (LONG: low ≤ entry_price; BEARISH: high ≥ entry_price)
   │   → status=ACTIVE, entry_filled_at=today, entry_filled_price=entry_price
   │   → Fall through to ACTIVE check for same day
   ├─ today > timeout_date?
   │   → status=CLOSED, close_reason=EXPIRED_UNFILLED
   └─ Else: remain PENDING

   ACTIVE:
   ├─ LONG direction:
   │   ├─ low ≤ effective_sl → CLOSED, reason=STOP_LOSS, exit=effective_sl
   │   ├─ high ≥ take_profit_1 AND partial_tp_enabled:
   │   │   → PARTIAL_TP, tp1_hit=true, tp1_hit_date=today
   │   │   → tp1_pnl = (tp1 - entry) × (quantity/2)
   │   │   → effective_sl = entry_price (breakeven)
   │   ├─ high ≥ take_profit_2 (non-partial mode):
   │   │   → CLOSED, reason=TAKE_PROFIT_2, exit=tp2
   │   ├─ today > timeout_date → CLOSED, reason=TIMEOUT, exit=close
   │   └─ Else: remain ACTIVE
   ├─ BEARISH direction (inverted H/L):
   │   ├─ high ≥ effective_sl → CLOSED, reason=STOP_LOSS
   │   ├─ low ≤ take_profit_1 → PARTIAL_TP
   │   └─ (mirror of LONG logic with inverted comparisons)

   PARTIAL_TP:
   ├─ LONG: low ≤ effective_sl (breakeven) → CLOSED, reason=BREAKEVEN
   ├─ LONG: high ≥ take_profit_2 → CLOSED, reason=TAKE_PROFIT_2
   ├─ today > timeout_date → CLOSED, reason=TIMEOUT
   └─ Else: remain PARTIAL_TP

4. Conflict resolution: If both SL and TP within day's H/L range:
   → SL wins (pessimistic assumption — prevents false analytics optimism)

5. For each CLOSED transition:
   a. Calculate pnl_amount, pnl_pct, risk_reward_actual
   b. Update SimulationConfig.current_capital += pnl_amount
   c. Send Telegram notification
```

### Flow 3: Manual Paper Trade (via API or Telegram)

```
User on ticker detail page → clicks "Follow Signal" button
1. POST /api/paper-trading/trades
   Body: { ai_analysis_id, direction?, entry_price?, stop_loss?, take_profit_1?, take_profit_2? }
2. Service:
   a. Load AIAnalysis by id → extract TickerTradingSignal from raw_response
   b. Use AI values as defaults, override with user-provided values
   c. Calculate quantity from SimulationConfig capital + position size
   d. Create PaperTrade(source=MANUAL, ...)
   e. Same entry fill check as auto-track
3. Return created PaperTrade
```

### Flow 4: Analytics Queries

All analytics computed from PaperTrade WHERE status=CLOSED (no new tables needed):

```sql
-- Win rate
SELECT COUNT(*) FILTER (WHERE pnl_amount > 0) as wins,
       COUNT(*) FILTER (WHERE pnl_amount <= 0) as losses
FROM paper_trades WHERE status='closed' AND close_reason != 'expired';

-- P&L by AI confidence bracket
SELECT CASE WHEN ai_confidence >= 8 THEN 'high'
            WHEN ai_confidence >= 5 THEN 'medium'
            ELSE 'low' END as bracket,
       AVG(pnl_pct), COUNT(*)
FROM paper_trades WHERE status='closed' GROUP BY 1;

-- Equity curve
SELECT closed_at, SUM(pnl_amount) OVER (ORDER BY closed_at) as cumulative_pnl
FROM paper_trades WHERE status='closed' ORDER BY closed_at;

-- Calendar heatmap
SELECT closed_at, SUM(pnl_amount), COUNT(*)
FROM paper_trades WHERE status='closed' GROUP BY closed_at;
```

---

## API Endpoint Design

```
Router: /api/paper-trading

# Trade Management
GET    /trades                    List trades (filters: status, direction, ticker, date range)
GET    /trades/{id}               Single trade detail with full lifecycle
POST   /trades                    Create manual paper trade from signal
PUT    /trades/{id}               Modify pending trade (entry/SL/TP)
DELETE /trades/{id}               Cancel pending or close active trade manually

# Simulation Config
GET    /config                    Get current config
PUT    /config                    Update config (capital, auto-track settings)
POST   /config/reset              Reset capital to initial, optionally clear all trades

# Analytics
GET    /analytics/summary         Win rate, total P&L, avg R:R, max drawdown
GET    /analytics/equity-curve    Daily equity curve data points
GET    /analytics/breakdown       P&L by sector, direction, confidence bracket, timeframe
GET    /analytics/calendar        Calendar heatmap (daily P&L per day)
GET    /analytics/streaks         Current and longest win/loss streaks

# Active Positions
GET    /positions/active          Open positions (status IN pending/active/partial_tp)
```

**Naming convention:** Follows existing pattern (`/api/portfolio/trades`, `/api/portfolio/summary`). Paper trading is parallel to portfolio, not nested under it.

---

## Frontend Page Architecture

### New Route: `/dashboard/paper-trading`

Single page with tab navigation (same pattern as health dashboard):

```
/dashboard/paper-trading
├── Tab: Tổng quan (Overview)          — Summary cards + equity curve + recent trades
├── Tab: Lệnh đang mở (Active)        — Active positions table with live status
├── Tab: Lịch sử (History)            — Closed trades table with filters
├── Tab: Phân tích (Analytics)         — Win rate charts, breakdown, calendar heatmap
└── Tab: Cấu hình (Config)            — Simulation settings form
```

### New Components

| Component | Location | Description |
|-----------|----------|-------------|
| `paper-trading-summary.tsx` | `/components/` | 5 stat cards: Win Rate, Total P&L, Avg R:R, Max Drawdown, Active Count |
| `equity-curve-chart.tsx` | `/components/` | Recharts AreaChart — cumulative P&L over time |
| `paper-trades-table.tsx` | `/components/` | @tanstack/react-table — trade list with status badges, P&L coloring |
| `paper-trade-detail-dialog.tsx` | `/components/` | shadcn Dialog — full trade lifecycle (signal → entry → TP1 → close) |
| `active-positions-table.tsx` | `/components/` | Compact table of open trades with current price vs entry/SL/TP |
| `analytics-breakdown.tsx` | `/components/` | Recharts BarCharts for P&L by sector, direction, confidence |
| `calendar-heatmap.tsx` | `/components/` | Grid calendar — daily P&L as colored cells (green/red intensity) |
| `streak-display.tsx` | `/components/` | Current win/loss streak + longest streak badges |
| `simulation-config-form.tsx` | `/components/` | Form for capital, auto-track toggle, confidence threshold |
| `follow-signal-button.tsx` | `/components/` | Button on ticker detail page — creates manual paper trade |

### Ticker Detail Page Integration

Add "Follow Signal" button to existing `TradingPlanPanel` component:

```tsx
// In trading-plan-panel.tsx, after the direction columns:
<FollowSignalButton
  analysisId={analysisId}
  direction={recommendedDirection}
  ticker={symbol}
/>
```

This button: (1) only shows when trading signal exists, (2) opens confirm/customize dialog, (3) POSTs to `/api/paper-trading/trades`, (4) shows success toast with dashboard link.

### React Query Hooks (follows existing pattern)

```typescript
export function usePaperTrades(filters?: PaperTradeFilters) {
  return useQuery({
    queryKey: ["paper-trades", filters],
    queryFn: () => fetchPaperTrades(filters),
    staleTime: 60 * 1000,  // 1 min — trades update daily
  });
}

export function usePaperTradingAnalytics() {
  return useQuery({
    queryKey: ["paper-trading-analytics"],
    queryFn: fetchPaperTradingAnalytics,
    staleTime: 5 * 60 * 1000,  // 5 min — analytics are stable
  });
}
```

---

## Telegram Integration

### New Commands

| Command | Format | Description |
|---------|--------|-------------|
| `/paper <mã>` | `/paper VNM` | Follow latest signal for ticker (manual paper trade) |
| `/paper_status` | `/paper_status` | Summary: active count, today's P&L, overall win rate |

### Auto-Notifications (triggered by position monitor job)

```
🟢 PAPER TRADE — TP1 Hit
VNM LONG: Entry 85,000 → TP1 87,500 ✅
P&L: +2,500 × 500cp = +1,250,000đ
Đã đóng 50%, SL dời → breakeven (85,000)

🔴 PAPER TRADE — Stop Loss
FPT LONG: Entry 120,000 → SL 115,000 ❌
P&L: -5,000 × 200cp = -1,000,000đ

📊 PAPER TRADE — Timeout
HPG BEARISH: Entry 28,000 → Close 27,500
P&L: +500 × 1,000cp = +500,000đ
Hết timeframe (swing 15 ngày)
```

**Implementation:** Extend `MessageFormatter` with `paper_trade_event()` and `paper_status_summary()` static methods. Send via existing `telegram_bot.send_message()` pattern (never-raise).

---

## Database Migration Strategy

Single Alembic migration creates both tables:

```python
# alembic/versions/xxx_add_paper_trading.py
# 1. Create trade_status PostgreSQL enum
# 2. Create close_reason enum
# 3. Create trade_source enum
# 4. Create simulation_config table
# 5. Create paper_trades table with FKs to tickers and ai_analyses
# 6. Create indexes
# 7. INSERT default SimulationConfig row (id=1, capital=100M VND)
```

**No changes to existing tables.** `ai_analyses.raw_response` JSONB already contains full trading plan data. PaperTrade references via `ai_analysis_id` FK.

---

## Patterns to Follow

### Pattern 1: Service Layer (matches existing architecture)

All business logic in `PaperTradingService`, never in API routes or jobs. Matches `PortfolioService`, `AIAnalysisService`, `AlertService`.

```python
class PaperTradingService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def auto_track_signals(self, analysis_date: date) -> dict:
        """Called by scheduler. Returns {created: int, skipped: int}."""

    async def monitor_positions(self, price_date: date) -> dict:
        """Called by scheduler. Returns {checked: int, closed: int, events: list}."""

    async def create_manual_trade(self, ai_analysis_id: int, overrides: dict) -> PaperTrade:
        """Called by API or Telegram handler."""

    async def close_trade(self, trade_id: int, reason: str = "manual") -> PaperTrade:
        """Manually close a trade."""

    async def get_analytics_summary(self, days: int | None = None) -> dict:
    async def get_equity_curve(self, days: int = 90) -> list[dict]:
    async def get_breakdown(self, group_by: str = "sector") -> list[dict]:
```

### Pattern 2: Never-Raise Scheduler Jobs (matches alert jobs)

```python
async def paper_trade_auto_track():
    """Auto-track today's signals. Never raises — non-critical job."""
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("paper_trade_auto_track")
        try:
            service = PaperTradingService(session)
            result = await service.auto_track_signals(date.today())
            await job_svc.complete(execution, status="success", result_summary=result)
            await session.commit()
        except Exception as e:
            await job_svc.complete(execution, status="partial",
                result_summary={"error": str(e)[:200]})
            await session.commit()
            logger.error(f"Paper trade auto-track failed: {e}")
```

**Critical:** Both paper trading jobs follow the "never raise" pattern of `daily_signal_alert_check` — paper trading is non-critical and must never break the main pipeline.

### Pattern 3: P&L Calculation

```python
def calculate_pnl(trade: PaperTrade, exit_price: Decimal, partial: bool = False):
    """LONG: pnl = (exit - entry) × qty. BEARISH: pnl = (entry - exit) × qty."""
    qty = trade.quantity // 2 if partial else trade.quantity
    if trade.direction == "long":
        pnl = (exit_price - trade.entry_filled_price) * qty
    else:
        pnl = (trade.entry_filled_price - exit_price) * qty
    pnl_pct = pnl / (trade.entry_filled_price * trade.quantity) * 100
    return pnl, pnl_pct
```

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Real-Time Position Monitoring
**What:** Checking TP/SL against WebSocket real-time prices (30s polling).
**Why bad:** Creates constant DB queries for ~400 positions every 30s. Wastes Aiven pool (pool_size=5). Real-time data is in-memory only — not in DailyPrice.
**Instead:** Check once daily after price crawl writes to DailyPrice. VN market has no intraday trading for retail anyway (T+2.5 settlement).

### Anti-Pattern 2: Separate Position and Trade Tables
**What:** Creating both PaperTrade and PaperPosition tables.
**Why bad:** Over-normalized for single-user. Each signal = one position, no averaging in. Two tables = JOINs on every query + complex state sync.
**Instead:** Single PaperTrade with status state machine.

### Anti-Pattern 3: Entry Fill via Exact Price Match
**What:** Requiring close == entry_price exactly.
**Why bad:** Market prices rarely hit exact number. Entries would never fill.
**Instead:** Fill when price crosses entry level: LONG fills when `low ≤ entry_price`, BEARISH fills when `high ≥ entry_price`. Use entry_price as fill price (limit order simulation).

### Anti-Pattern 4: Pre-Computing Analytics Rollup Tables
**What:** Materialized daily stats table updated by triggers.
**Why bad:** Premature optimization. With ~400 trades/day and single user, live queries on indexed `paper_trades` run in <500ms even at 50K rows.
**Instead:** Live aggregate queries. Add rollup only if analytics page becomes slow (unlikely for single-user).

---

## Scalability Considerations

| Concern | Launch | 6 months | 1 year |
|---------|--------|----------|--------|
| Paper trades/day | ~400 (auto-track all) | ~400 | ~400 |
| Active positions | ~200-400 | ~500 (steady state) | ~500 |
| Closed trades total | 0 | ~50,000 | ~100,000 |
| Analytics query time | <100ms | <500ms (indexed) | <1s (indexed) |
| Position monitor job | <5s | <10s | <10s |
| DB storage | ~1MB | ~50MB | ~100MB |

100K rows handled easily by PostgreSQL with proper indexes. No partitioning needed.

---

## Build Order (Dependency-Driven)

```
Phase 1: Data Foundation
├── Alembic migration (paper_trades + simulation_config)
├── PaperTrade model + SimulationConfig model
├── PaperTradingService core (create, close, calculate_pnl)
└── Unit tests for P&L calculation + state machine

Phase 2: Scheduler Integration
├── Auto-track job + chain from trading_signal
├── Position monitor job + chain from price_crawl
├── Entry fill + TP/SL/timeout state machine
└── Tests for each state transition

Phase 3: API + Manual Trades
├── Paper trading router (CRUD + analytics endpoints)
├── Manual trade creation from signal with overrides
├── Analytics query methods in service
└── API tests

Phase 4: Frontend Dashboard
├── Paper trading page with tabs
├── Summary cards + equity curve
├── Trade tables (active + history)
├── Analytics charts (breakdown, calendar, streaks)
├── Follow Signal button on ticker detail
└── Config form

Phase 5: Telegram + Polish
├── /paper and /paper_status commands
├── Auto-notification for TP/SL/timeout events
├── MessageFormatter extensions
└── End-to-end integration test
```

**Rationale:** Models → Jobs → API → Frontend → Telegram. Each phase produces testable output. Frontend comes after API is stable. Telegram last because it's notification-only.

---

## Sources

| Claim | Source | Confidence |
|-------|--------|------------|
| Job chaining via _on_job_executed pattern | `app/scheduler/manager.py` lines 87-188 | HIGH |
| AIAnalysis.raw_response has TickerTradingSignal JSONB | `app/models/ai_analysis.py` + `app/schemas/analysis.py` | HIGH |
| DailyPrice has OHLCV for TP/SL checking | Existing model with open/high/low/close/volume | HIGH |
| pool_size=5, max_overflow=3 constraint | `app/database.py` | HIGH |
| Never-raise pattern for non-critical jobs | `daily_signal_alert_check` + `daily_price_alert_check` | HIGH |
| Navbar NAV_LINKS array | `frontend/src/components/navbar.tsx` line 22-29 | HIGH |
| VN lot size = 100 shares | Vietnam stock exchange standard | HIGH |
| @tanstack/react-table in stack | Already used per STACK.md | HIGH |
| Recharts for non-financial charts | Already used per STACK.md | HIGH |
| Trading signal schema (entry/SL/TP1/TP2) | `app/schemas/analysis.py` TradingPlanDetail | HIGH |

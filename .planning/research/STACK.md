# Technology Stack — v4.0 Paper Trading & Signal Verification

**Project:** Holo — Stock Intelligence Platform
**Milestone:** v4.0 Paper Trading & Signal Verification
**Researched:** 2026-04-20
**Overall confidence:** HIGH

## Executive Summary

v4.0 needs **ONE new frontend package** (`react-activity-calendar`) and **ZERO new Python packages**. The paper trading simulation engine, position management with partial TP, analytics computation, and trade lifecycle tracking are all pure business logic built on the existing SQLAlchemy + APScheduler + Recharts stack. This is the correct approach — paper trading is a domain logic problem, not a library problem.

The single new dependency — `react-activity-calendar@^3.2.0` — provides the GitHub-style calendar heatmap for daily P&L visualization. It supports React 19, uses `date-fns@^4` (already installed), and was last published April 2026. Every other v4.0 visualization (equity curve, drawdown, P&L bars, sector breakdowns, win rate, R:R distribution) maps directly to existing Recharts chart types already used in the codebase.

The backend simulation engine is fundamentally an APScheduler job that runs after daily price crawl, compares current prices against open paper trade TP/SL levels, and triggers state transitions. This is the exact same pattern as `daily_price_alert_check` and `daily_signal_alert_check` — proven patterns in the codebase. Analytics are SQL aggregates + Python arithmetic (win rate = wins/total, drawdown = peak-to-trough on equity series, R:R = (exit-entry)/(entry-SL)). No numpy, no pandas-beyond-what-ta-already-brings, no external analytics library.

---

## Stack Additions

### Frontend: ONE New Package

| Package | Version | Purpose | Why This One |
|---------|---------|---------|--------------|
| `react-activity-calendar` | `^3.2.0` | Calendar heatmap (GitHub-style daily P&L grid) | Only actively maintained React 19-compatible calendar heatmap. Uses `date-fns@^4` (already in project). Built-in tooltips via `@floating-ui/react`. Last published 2026-04-15. |

**Installation:**
```bash
cd frontend
npm install react-activity-calendar@^3.2.0
```

**API shape** (from npm registry + GitHub docs):
```typescript
import ActivityCalendar from 'react-activity-calendar';

// Data format matches our need perfectly
const data = [
  { date: '2026-01-15', count: 3, level: 2 },  // 3 trades closed, green
  { date: '2026-01-16', count: 1, level: 4 },   // big win, dark green
  { date: '2026-01-17', count: 0, level: 0 },   // no activity
];

<ActivityCalendar
  data={data}
  colorScheme="light"       // or "dark" — respects next-themes
  theme={{
    light: ['#ebedf0', '#c6e48b', '#7bc96f', '#239a3b', '#196127'],
    dark:  ['#161b22', '#0e4429', '#006d32', '#26a641', '#39d353'],
  }}
  labels={{ totalCount: '{{count}} lệnh trong năm' }}  // Vietnamese
/>
```

**Dependency tree impact:**
- Adds `@floating-ui/react@^0.27` (transitive) — compatible with existing `@floating-ui/react-dom@2.1.8` already in tree via `@base-ui/react`
- Adds `date-fns@^4.1.0` — **already installed** (deduped, zero additional weight)

**Confidence: HIGH** — Verified: React 19 peer dep (`"react": "^18.0.0 || ^19.0.0"`), date-fns ^4 dep, npm publish date (2026-04-15), API shape from GitHub README.

### Backend: ZERO New Packages

The paper trading engine is pure domain logic. Here's the mapping:

| v4.0 Feature | Covered By (Existing) | How |
|---|---|---|
| Auto-create paper trades from AI signals | SQLAlchemy 2.0 + service layer | After trading signal batch completes, create `PaperTrade` rows from `ai_analyses` where `analysis_type='trading_signal'` |
| Manual paper trade creation | FastAPI endpoint + Pydantic schema | Same pattern as `/api/portfolio/trades` (existing trade creation) |
| TP/SL hit detection | APScheduler job + `daily_prices` query | Compare `close` price against `take_profit_1`, `take_profit_2`, `stop_loss` — same pattern as `daily_price_alert_check` |
| Partial TP (50% at TP1, 50% at TP2) | Python business logic | State machine: OPEN → PARTIAL_TP1 (close 50%, move SL to entry) → TP2_HIT/SL_HIT/TIMEOUT |
| Timeout (close at market after timeframe) | APScheduler + `date` arithmetic | `if today > entry_date + timeframe_days: close at last close price` |
| Virtual capital tracking | PostgreSQL column + Python math | `paper_account.balance` updated on each trade close. Equity = balance + Σ(unrealized P&L) |
| Win rate, P&L, avg R:R | SQL aggregates + Python `statistics` | `SELECT COUNT(*) FILTER (WHERE pnl > 0) / COUNT(*)`, etc. |
| Max drawdown | Python arithmetic | Track peak equity, drawdown = (peak - current) / peak, keep max |
| Equity curve | SQLAlchemy query → Recharts `AreaChart` | Daily snapshots: `SELECT date, equity FROM paper_account_snapshots ORDER BY date` |
| Sector/direction breakdown | SQL `GROUP BY` + Recharts `BarChart` | `GROUP BY ticker.sector`, `GROUP BY direction` |
| AI score high vs low comparison | SQL `CASE WHEN` grouping | `CASE WHEN ai_score >= 7 THEN 'high' ELSE 'low' END` |
| Streak tracking | Python iteration over sorted trades | Track consecutive wins/losses from trade history |
| Telegram TP/SL notifications | `python-telegram-bot 22.7` | Existing `send_message()` pattern with HTML formatting |

---

## What the Existing Stack Already Covers — Detailed

### Recharts (already `^3.8.1`) — All Analytics Charts

Every analytics visualization maps to an existing Recharts component:

| Chart Need | Recharts Component | Already Used In Project? |
|---|---|---|
| Equity curve | `AreaChart` + `Area` | ✅ `performance-chart.tsx` — identical pattern |
| P&L per trade (bar) | `BarChart` + `Bar` + `Cell` (red/green per bar) | Recharts component available |
| Cumulative P&L | `AreaChart` + `Area` | ✅ Same as performance chart |
| Drawdown chart | `AreaChart` + `Area` (inverted, red fill) | Same component, negative Y axis |
| Win rate by category | `BarChart` + `Bar` | Standard bar chart |
| R:R distribution | `BarChart` + `Bar` | Histogram-style |
| Sector/direction pie | `PieChart` + `Pie` + `Cell` | Available in Recharts |
| AI score comparison | `ComposedChart` + `Bar` + `Line` | Overlay bars + line |
| Trade duration distribution | `BarChart` + `Bar` | Histogram-style |

**Key Recharts features needed (all verified available in v3.8.1):**
- `ReferenceLine` — breakeven line on P&L charts (y=0)
- `Cell` — individual bar coloring (green profit, red loss)
- `Brush` — date range selection on equity curve
- `Tooltip` + `Legend` — already used throughout codebase
- `ResponsiveContainer` — already used throughout codebase

**Confidence: HIGH** — Verified all component exports from installed `recharts@3.8.1` via `node -e "require('recharts')"`.

### @tanstack/react-table (already `^8.21.3`) — Trade Log Table

The paper trade history table follows the exact same pattern as `trade-history.tsx` (existing portfolio trade log). Columns: date, ticker, direction, entry, exit, P&L, R:R, duration, status.

### zustand + @tanstack/react-query — State Management

- `react-query` for server state (paper trades, analytics data) — same `useQuery`/`useMutation` patterns as portfolio hooks in `hooks.ts`
- `zustand` for client state (selected filters: date range, sector, direction, score range) — same pattern as existing store

### APScheduler (already `3.11`) — Position Checking Job

New scheduled job `paper_trade_position_check` chains after daily price crawl, same pattern as existing alert checks:

```python
# In scheduler/manager.py — same chaining pattern
_JOB_NAMES["paper_trade_check_triggered"] = "Paper Trade Position Check"

# In scheduler/jobs.py — same session + service pattern
async def check_paper_trade_positions():
    async with async_session() as session:
        service = PaperTradeService(session)
        result = await service.check_all_open_positions()
        # Send Telegram for any TP/SL/timeout hits
```

### python-telegram-bot (already `22.7`) — Trade Notifications

Extend `MessageFormatter` with paper trade alert methods:

```python
@staticmethod
def paper_trade_tp_hit(symbol: str, direction: str, tp_level: int, pnl: float) -> str:
    emoji = "🎯" if tp_level == 1 else "🏆"
    return (
        f"{emoji} <b>Paper Trade TP{tp_level} Hit</b>\n"
        f"Mã: <b>{symbol}</b> ({direction.upper()})\n"
        f"P&L: <b>{pnl:+,.0f}</b> VNĐ"
    )
```

Same `send_message()` flow as existing price alerts and daily summaries.

### SQLAlchemy 2.0 + Alembic — New Tables

Three new tables using existing migration patterns:

**1. `paper_trades`** — Primary entity
```python
class PaperTrade(Base):
    __tablename__ = "paper_trades"
    id: Mapped[int]                    # BigInteger PK
    ticker_id: Mapped[int]             # FK → tickers.id
    ai_analysis_id: Mapped[int | None] # FK → ai_analyses.id (NULL for manual)
    direction: Mapped[str]             # 'long' / 'bearish'
    status: Mapped[str]                # 'open' / 'partial_tp1' / 'closed'
    close_reason: Mapped[str | None]   # 'tp1' / 'tp2' / 'sl' / 'timeout' / 'manual'
    entry_price: Mapped[Decimal]
    stop_loss: Mapped[Decimal]
    take_profit_1: Mapped[Decimal]
    take_profit_2: Mapped[Decimal]
    current_sl: Mapped[Decimal]        # Tracks SL after move to breakeven
    quantity: Mapped[int]              # Position size (units)
    remaining_quantity: Mapped[int]    # After partial TP1
    avg_exit_price: Mapped[Decimal | None]
    realized_pnl: Mapped[Decimal | None]
    risk_reward_actual: Mapped[Decimal | None]
    entry_date: Mapped[date]
    exit_date: Mapped[date | None]
    timeout_date: Mapped[date]         # entry_date + timeframe days
    ai_score: Mapped[int | None]       # Cached from AI signal for analytics grouping
    created_at: Mapped[datetime]
```

**2. `paper_trade_events`** — Lifecycle audit trail
```python
class PaperTradeEvent(Base):
    __tablename__ = "paper_trade_events"
    id: Mapped[int]
    paper_trade_id: Mapped[int]        # FK → paper_trades.id
    event_type: Mapped[str]            # 'opened' / 'tp1_hit' / 'sl_moved' / 'tp2_hit' / 'sl_hit' / 'timeout' / 'manual_close'
    price: Mapped[Decimal]             # Price at event
    quantity_affected: Mapped[int]     # How many shares affected
    pnl_realized: Mapped[Decimal | None]
    notes: Mapped[str | None]
    event_date: Mapped[date]
    created_at: Mapped[datetime]
```

**3. `paper_account_snapshots`** — Daily equity for equity curve
```python
class PaperAccountSnapshot(Base):
    __tablename__ = "paper_account_snapshots"
    id: Mapped[int]
    snapshot_date: Mapped[date]        # Unique
    cash_balance: Mapped[Decimal]
    unrealized_pnl: Mapped[Decimal]
    total_equity: Mapped[Decimal]      # cash + unrealized
    open_positions: Mapped[int]        # Count
    created_at: Mapped[datetime]
```

All follow the exact SQLAlchemy 2.0 `Mapped[]` pattern used in every existing model (Trade, Lot, DailyPrice, AIAnalysis, etc.).

---

## Alternatives Considered (and Rejected)

### Frontend

| Considered | Decision | Rationale |
|---|---|---|
| `react-calendar-heatmap@1.10.0` | **NO** | Last updated Feb 2025, v1.x, no React 19 peer dep declaration. `react-activity-calendar` is actively maintained (April 2026) with explicit React 19 support. |
| `nivo` calendar component | **NO** | Massive bundle (~500KB). Brings D3 as dependency. Only need calendar heatmap — `react-activity-calendar` is ~15KB. |
| `react-heat-map` | **NO** | GitHub-style heatmap but less popular, fewer downloads, no tooltip built-in. |
| `plotly.js` / `react-plotly.js` | **NO** | 3.5MB bundle. Would duplicate what Recharts already does. Overkill for the charts needed. |
| `chart.js` / `react-chartjs-2` | **NO** | Would introduce a second charting library alongside Recharts. Inconsistent patterns. Recharts already handles all chart types needed. |
| `visx` (Airbnb) | **NO** | Low-level D3 wrapper, more code to write than Recharts for same result. Only justified if Recharts can't do something — it can do everything here. |
| Custom SVG calendar heatmap | **NO** | `react-activity-calendar` exists, is small (~15KB), handles year layout, tooltips, theming, responsive. Don't reinvent. |

### Backend

| Considered | Decision | Rationale |
|---|---|---|
| `numpy` for statistics | **NO** | Win rate = division. Drawdown = max(peak - current). R:R = subtraction/division. Adding numpy import for arithmetic that Python stdlib or plain math handles is unnecessary. (numpy is already a transitive dep of `ta`, but no reason to import it directly.) |
| `pandas` for analytics | **NO** | `pandas` is already a transitive dep of `ta`, but importing it directly for analytics adds coupling. SQL aggregates are more efficient — data stays in PostgreSQL, no memory overhead for single-user analytics. |
| `backtrader` / `zipline` | **NO** | Full backtesting frameworks. Extreme overkill — we're tracking forward signals, not replaying historical strategies. They bring massive dependencies and complexity. |
| `redis` for position state | **NO** | Paper trade state belongs in PostgreSQL (durable, queryable, part of analytics). Redis adds infrastructure complexity for zero benefit in a single-user app. |
| `celery` for async position checking | **NO** | APScheduler already handles scheduled jobs. Position checking is one SQL query + comparison — takes <1 second. No need for a task queue. |
| `quantstats` for analytics | **NO** | Python library for trading analytics reports. Generates matplotlib charts (we use Recharts). Heavy dependencies (matplotlib, scipy, pandas). We compute 6 metrics — don't need a library for that. |

---

## Integration Points — Existing Patterns to Reuse

### 1. Service Layer Pattern
Every v4.0 backend feature follows the existing service pattern:
```python
class PaperTradeService:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_from_signal(self, analysis_id: int, capital: Decimal) -> dict: ...
    async def create_manual(self, symbol: str, direction: str, ...) -> dict: ...
    async def check_all_open_positions(self) -> dict: ...
    async def close_position(self, trade_id: int, reason: str, price: Decimal) -> dict: ...
```
Same as `PortfolioService`, `AIAnalysisService`, etc.

### 2. API Router Pattern
```python
# app/api/paper_trading.py — same pattern as portfolio.py
router = APIRouter(prefix="/paper-trading", tags=["paper-trading"])

@router.get("/trades")       # List paper trades with filters
@router.post("/trades")      # Create manual paper trade
@router.get("/analytics")    # Win rate, P&L, drawdown stats
@router.get("/equity-curve") # Daily equity snapshots
@router.get("/heatmap")      # Calendar heatmap data
```

### 3. React Query Hooks Pattern
```typescript
// Same pattern as useTradeHistory, usePortfolioSummary in hooks.ts
export function usePaperTrades(filters?: PaperTradeFilters) {
  return useQuery({
    queryKey: ["paper-trades", filters],
    queryFn: () => fetchPaperTrades(filters),
    staleTime: 60_000,
  });
}

export function usePaperAnalytics(period?: string) {
  return useQuery({
    queryKey: ["paper-analytics", period],
    queryFn: () => fetchPaperAnalytics(period),
    staleTime: 5 * 60_000,
  });
}
```

### 4. Job Chaining Pattern
Paper trade position check chains after daily price crawl:
```python
# Same EVENT_JOB_EXECUTED chaining as indicator → AI → alerts
"daily_price_crawl" → triggers → "paper_trade_check_triggered"
```

Also: auto-create paper trades from new trading signals:
```python
"daily_trading_signal_triggered" → triggers → "paper_trade_auto_create_triggered"
```

---

## Configuration Additions

New settings in `config.py` (no new dependencies):

```python
# Paper Trading (v4.0)
paper_trading_initial_capital: float = 1_000_000_000  # 1 tỷ VNĐ default
paper_trading_tp1_close_pct: int = 50                 # Close 50% at TP1
paper_trading_move_sl_to_breakeven: bool = True        # After TP1 hit
paper_trading_swing_timeout_days: int = 15             # Max days for swing trades
paper_trading_position_timeout_days: int = 60          # Max days for position trades
paper_trading_auto_track_enabled: bool = True          # Auto-create from AI signals
paper_trading_auto_track_min_score: int = 1            # Min AI confidence to auto-track (1 = track all)
```

---

## Database Migration Checklist

All using existing Alembic patterns:

1. **Create `paper_trades` table** — Standard `op.create_table()` migration
2. **Create `paper_trade_events` table** — FK to `paper_trades`, index on `paper_trade_id`
3. **Create `paper_account_snapshots` table** — Unique on `snapshot_date`, index for range queries
4. **Create `paper_trade_status` PostgreSQL ENUM** — `('open', 'partial_tp1', 'closed')`, same pattern as `analysis_type` enum
5. **Index on `paper_trades(status, timeout_date)`** — For efficient open position queries during daily check

---

## What NOT to Add (Explicit Anti-Recommendations)

| Don't Add | Why Not | What to Do Instead |
|---|---|---|
| Any Python statistics library | Win rate, drawdown, R:R are 5-line functions. Importing a library for `wins/total` is absurd. | Python `statistics.mean()` at most, or plain arithmetic. |
| `backtrader` / `zipline` | Backtesting frameworks for historical strategy replay. We're tracking live-forward signals. Wrong tool. | Custom `PaperTradeService` with simple state machine. |
| Second charting library | Recharts handles AreaChart, BarChart, PieChart, ComposedChart — every chart type needed. | Reuse Recharts for all analytics visualizations. |
| `quantstats` | Generates matplotlib charts + PDF reports. We display in React dashboard, not Python-generated images. | Compute metrics in SQL/Python, render in Recharts. |
| `redis` / in-memory cache | Paper trade state must be durable (PostgreSQL). Caching gains nothing for single-user queries returning <1000 rows. | Query PostgreSQL directly. |
| WebSocket for real-time position updates | Position checks run once daily (after market close). Real-time intraday TP/SL tracking is impossible without live exchange WebSocket (not available for free in VN market). | Daily check via APScheduler after price crawl, same as all other daily jobs. |
| New Gemini API calls for analytics | Analytics are pure math on trade results. AI adds no value to "what's my win rate." | SQL aggregates + Python arithmetic. |

---

## Full Stack Summary (v4.0 Delta Only)

### Backend — requirements.txt: NO CHANGES

```
# v4.0 adds ZERO new Python dependencies
# Paper trading engine = pure business logic on existing stack:
# - SQLAlchemy 2.0 (models + queries)
# - APScheduler 3.11 (scheduled position checking)
# - python-telegram-bot 22.7 (TP/SL notifications)
# - FastAPI (new API endpoints)
# - Pydantic (new request/response schemas)
```

### Frontend — package.json: ONE addition

```bash
npm install react-activity-calendar@^3.2.0
```

**Final `dependencies` delta:**
```json
{
  "react-activity-calendar": "^3.2.0"
}
```

No new dev dependencies needed.

---

## Verification Log

| Claim | Method | Result |
|---|---|---|
| `react-activity-calendar` supports React 19 | `npm view peerDependencies` | ✅ `"react": "^18.0.0 \|\| ^19.0.0"` |
| `react-activity-calendar` uses date-fns 4 | `npm view dependencies` | ✅ `"date-fns": "^4.1.0"` — matches project |
| `react-activity-calendar` last published recently | `npm view time` | ✅ 2026-04-15 |
| `react-calendar-heatmap` is outdated | `npm view time` | ✅ Last updated 2025-02-23, v1.10.0 |
| Recharts has AreaChart, BarChart, PieChart, ComposedChart | `node -e "require('recharts')"` in project | ✅ All present in v3.8.1 |
| Recharts has ReferenceLine, Cell, Brush | `node -e` check | ✅ All exported from v3.8.1 |
| `@floating-ui/react` compatible with existing tree | `npm ls --all \| Select-String floating-ui` | ✅ `@floating-ui/react-dom@2.1.8` already in tree via `@base-ui/react` |
| No numpy/pandas needed for analytics | Manual analysis of all metric formulas | ✅ All metrics are basic arithmetic on trade results |
| APScheduler job chaining works for position check | Existing `EVENT_JOB_EXECUTED` pattern in `manager.py` | ✅ Same pattern used for 10+ chained jobs |
| SQLAlchemy 2.0 Mapped[] pattern for new models | Inspected all 12 existing models | ✅ Consistent pattern used throughout |
| Existing `performance-chart.tsx` uses Recharts AreaChart | Inspected component source | ✅ Same Recharts pattern reusable for equity curve |

---

## Sources

- `npm view react-activity-calendar` — Version 3.2.0, peer deps, dependencies, publish date (verified 2026-04-20)
- `npm view react-calendar-heatmap` — Version 1.10.0, last updated 2025-02-23 (verified 2026-04-20)
- `node -e "require('recharts')"` — Verified all chart component exports from installed v3.8.1
- `frontend/package.json` — Current dependency versions (React 19.2.4, Recharts 3.8.1, date-fns 4.1.0)
- `backend/requirements.txt` — Current Python dependency versions
- `backend/app/models/` — All 12 existing SQLAlchemy model patterns (Trade, Lot, DailyPrice, AIAnalysis, etc.)
- `backend/app/services/portfolio_service.py` — Existing trade recording + FIFO lot pattern
- `backend/app/scheduler/manager.py` — Job chaining + naming conventions (50+ job IDs)
- `backend/app/scheduler/jobs.py` — Job function patterns (session creation, service usage, resilience)
- `backend/app/telegram/formatter.py` — Telegram message formatting patterns (HTML parse_mode)
- `backend/app/config.py` — Settings pattern + existing trading signal config
- `frontend/src/components/performance-chart.tsx` — Existing Recharts AreaChart usage pattern
- `frontend/src/lib/hooks.ts` — Existing react-query hook patterns (25+ hooks)
- `frontend/src/components/trade-history.tsx` — Existing @tanstack/react-table usage
- GitHub: `grubersjoe/react-activity-calendar` — API documentation, theming, React 19 compatibility

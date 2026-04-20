# Phase 24: API & Analytics Engine - Research

**Researched:** 2025-01-27
**Domain:** FastAPI REST endpoints + analytics computation for paper trading
**Confidence:** HIGH

## Summary

Phase 24 implements the REST API layer and analytics computation for the paper trading system. It builds on Phase 22-23's PaperTrade model, SimulationConfig model, and paper_trade_service.py pure functions. The work is straightforward: one new FastAPI router with ~14 endpoints, Pydantic schemas for request/response types, and an analytics service that computes all AN-01 through AN-09 metrics via SQL aggregates from the `paper_trades` table.

The existing codebase provides crystal-clear patterns: `portfolio.py` for CRUD router pattern (session-per-request via `async_session()`), `analysis.py` for read-only query endpoints, `schemas/portfolio.py` for Pydantic response models, and `PortfolioService` for the service-layer pattern. Phase 24 follows these exactly — zero new patterns needed.

**Primary recommendation:** Create `backend/app/api/paper_trading.py` router + `backend/app/schemas/paper_trading.py` schemas + `backend/app/services/paper_trade_analytics_service.py` analytics computation. Register router in `router.py`. All analytics computed on-demand from SQL aggregates on indexed `paper_trades` table.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- New FastAPI router: `backend/app/api/paper_trading.py`
- Register in `backend/app/main.py` alongside existing routers
- Follow existing API patterns from `backend/app/api/analysis.py`
- 14 specific endpoints defined (see CONTEXT.md endpoints list)
- All analytics computed from `paper_trades` table (closed trades only for most metrics)
- Equity curve: cumulative P&L ordered by closed_date
- Drawdown: peak-to-trough from equity curve
- Confidence brackets: 1-3 LOW, 4-6 MEDIUM, 7-10 HIGH
- Sector: join paper_trades → tickers → industry field
- R:R achieved: actual P&L / (entry - SL) vs predicted risk_reward_ratio
- Manual follow (PT-09): Accept symbol, direction, entry_price, stop_loss, take_profit_1, take_profit_2, timeframe, confidence, position_size_pct
- Manual follow: ai_analysis_id = NULL, status = PENDING
- Manual follow: use calculate_position_size() for sizing
- Pydantic schemas: create in `backend/app/schemas/paper_trading.py`

### Copilot's Discretion
- Internal organization of analytics service (single class vs separate functions)
- Error handling specifics (HTTP status codes for edge cases)
- Query optimization strategies (single query vs multiple)
- Response pagination approach for trade list

### Deferred Ideas (OUT OF SCOPE)
- Frontend dashboard (Phase 25)
- Calendar heatmap (Phase 26)
- Streak tracking (Phase 26)
- Telegram integration (Phase 25+)
- Fee simulation (future ADV-01)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PT-09 | Manual follow — create paper trade with custom entry/SL/TP via API | POST /api/paper-trading/trades/follow endpoint using calculate_position_size() from paper_trade_service.py |
| AN-01 | Win rate (overall, by direction, by timeframe) | SQL COUNT FILTER on closed trades with realized_pnl > 0 |
| AN-02 | Total realized P&L in VND and % of initial capital | SUM(realized_pnl), reference SimulationConfig.initial_capital |
| AN-03 | Equity curve time-series | Cumulative SUM(realized_pnl) OVER (ORDER BY closed_date) |
| AN-04 | Max drawdown (VND, %, drawdown periods) | Peak-to-trough computation from equity curve data |
| AN-05 | Direction analysis (LONG vs BEARISH performance) | GROUP BY direction on closed trades |
| AN-06 | AI score correlation (confidence bracket → win rate, avg P&L) | CASE WHEN brackets (1-3/4-6/7-10), GROUP BY bracket |
| AN-07 | R:R achieved vs predicted | actual: realized_pnl / (entry_price - stop_loss) × quantity vs risk_reward_ratio field |
| AN-08 | Profit factor + EV per trade | SUM(profits) / ABS(SUM(losses)), AVG(realized_pnl) |
| AN-09 | Sector analysis (performance by industry group) | JOIN paper_trades → tickers ON ticker_id, GROUP BY tickers.industry |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.135.3 | REST API framework | Already installed, all existing routers use it [VERIFIED: pip] |
| Pydantic | 2.13.0 | Request/response schemas | Already installed, all existing schemas use it [VERIFIED: pip] |
| SQLAlchemy | 2.0.49 | Database queries (async) | Already installed, all models use Mapped[] pattern [VERIFIED: pip] |
| pytest | 8.4.2 | Unit + API testing | Already installed, existing test patterns [VERIFIED: pip] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | (installed) | Async test support | For testing async service methods |
| unittest.mock | stdlib | Mocking DB sessions | All existing tests mock async_session |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| SQL aggregates | pandas | Overkill — SQL is sufficient for single-user with <100K rows |
| On-demand compute | Materialized views | Premature optimization — live queries <500ms at projected scale |
| FastAPI TestClient | httpx AsyncClient | TestClient is sync but simpler — matches existing test_api.py pattern |

**Installation:**
```bash
# No new packages needed — all dependencies already installed
```

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── api/
│   └── paper_trading.py      # NEW: 14 endpoints
├── schemas/
│   └── paper_trading.py      # NEW: Pydantic request/response models
├── services/
│   ├── paper_trade_service.py      # EXISTS: pure P&L/sizing functions
│   └── paper_trade_analytics_service.py  # NEW: async DB analytics queries
└── models/
    ├── paper_trade.py        # EXISTS: PaperTrade model
    └── simulation_config.py  # EXISTS: SimulationConfig model
```

### Pattern 1: Router with Session-Per-Request (from portfolio.py)
**What:** Each endpoint opens its own `async_session()` context, creates service, calls method.
**When to use:** All endpoints in this phase.
**Example:**
```python
# Source: backend/app/api/portfolio.py (verified pattern)
from app.database import async_session

router = APIRouter(prefix="/paper-trading", tags=["paper-trading"])

@router.get("/trades", response_model=PaperTradeListResponse)
async def list_trades(
    status: str | None = Query(None, description="Filter by status"),
    direction: str | None = Query(None, description="Filter by direction"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    async with async_session() as session:
        service = PaperTradeAnalyticsService(session)
        result = await service.list_trades(status=status, direction=direction, limit=limit, offset=offset)
        return PaperTradeListResponse(**result)
```

### Pattern 2: Service Layer with Session Injection (from PortfolioService)
**What:** Service class accepts `AsyncSession` in constructor, handles all DB logic.
**When to use:** Analytics computation, trade creation, config updates.
**Example:**
```python
# Source: backend/app/services/portfolio_service.py (verified pattern)
class PaperTradeAnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_summary(self) -> dict:
        """AN-01, AN-02: Win rate + total P&L."""
        result = await self.session.execute(
            select(
                func.count().filter(PaperTrade.realized_pnl > 0).label("wins"),
                func.count().label("total"),
                func.sum(PaperTrade.realized_pnl).label("total_pnl"),
            ).where(PaperTrade.status.in_(CLOSED_STATUSES))
        )
        row = result.one()
        # ...compute win_rate, return dict
```

### Pattern 3: Pydantic Response Models (from schemas/portfolio.py)
**What:** Flat BaseModel classes with explicit field types and optional descriptions.
**When to use:** All response types.
**Example:**
```python
# Source: backend/app/schemas/portfolio.py (verified pattern)
class PaperTradeSummaryResponse(BaseModel):
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    avg_pnl_per_trade: float
```

### Pattern 4: Manual Trade Creation (PT-09)
**What:** POST endpoint accepting trade params, using existing `calculate_position_size()`.
**When to use:** The `/trades/follow` endpoint.
**Example:**
```python
from app.services.paper_trade_service import calculate_position_size

@router.post("/trades/follow", response_model=PaperTradeResponse, status_code=201)
async def create_manual_follow(trade: ManualFollowRequest):
    async with async_session() as session:
        # Get config for capital
        config = await session.execute(select(SimulationConfig).where(SimulationConfig.id == 1))
        sim_config = config.scalar_one()

        quantity = calculate_position_size(
            capital=sim_config.initial_capital,
            allocation_pct=trade.position_size_pct,
            entry_price=Decimal(str(trade.entry_price)),
        )
        if quantity == 0:
            raise HTTPException(status_code=400, detail="Insufficient capital for minimum lot")

        paper_trade = PaperTrade(
            ticker_id=ticker_id,  # resolved from symbol
            ai_analysis_id=None,  # Manual — not linked to signal
            direction=TradeDirection(trade.direction),
            status=TradeStatus.PENDING,
            entry_price=Decimal(str(trade.entry_price)),
            stop_loss=Decimal(str(trade.stop_loss)),
            take_profit_1=Decimal(str(trade.take_profit_1)),
            take_profit_2=Decimal(str(trade.take_profit_2)),
            quantity=quantity,
            # ...
        )
        session.add(paper_trade)
        await session.commit()
        return PaperTradeResponse(...)
```

### Anti-Patterns to Avoid
- **N+1 queries in analytics:** Don't query per-trade for sector info — join tickers table or use the denormalized fields on PaperTrade
- **Decimal/float mixing:** Use `float()` conversion only at the Pydantic boundary; keep Decimal in service layer
- **Forgetting CLOSED_MANUAL in analytics:** All closed statuses are: CLOSED_TP2, CLOSED_SL, CLOSED_TIMEOUT, CLOSED_MANUAL — include all 4 in aggregate queries
- **Filtering by string literal "closed":** Use the enum set `{CLOSED_TP2, CLOSED_SL, CLOSED_TIMEOUT, CLOSED_MANUAL}` — there's no single "closed" status

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Equity curve | In-memory cumulative sum | SQL window function `SUM() OVER (ORDER BY)` | DB handles ordering + null dates correctly |
| Max drawdown | Custom Python loop over all trades | Peak-tracking algorithm on equity curve data | Well-known algorithm: track running max, compute max(peak - current)/peak |
| Pagination | Manual OFFSET/LIMIT logic | SQLAlchemy `.offset()` + `.limit()` + `func.count()` | Matches existing portfolio pattern |
| Ticker resolution | Inline query per endpoint | Shared helper `_get_ticker_by_symbol()` | Already exists in analysis.py — can reuse pattern |
| Date filtering | Custom string parsing | Pydantic `date` type in Query params | Auto-validation + 422 on invalid |

**Key insight:** Analytics are simple SQL aggregates on an indexed table with <100K rows. The complexity is in getting the grouping/filtering right, not in performance optimization.

## Common Pitfalls

### Pitfall 1: Confidence Bracket Mismatch
**What goes wrong:** CONTEXT.md defines brackets as 1-3/4-6/7-10, but REQUIREMENTS.md AN-06 says 1-4/5-7/8-10.
**Why it happens:** Two documents with different bracket boundaries.
**How to avoid:** Use CONTEXT.md definition (1-3 LOW, 4-6 MEDIUM, 7-10 HIGH) since it's the authoritative phase context with explicit "Research-Backed Constraints" heading.
**Warning signs:** Analytics showing unexpected distributions per bracket.

### Pitfall 2: Missing "Win" Definition for BEARISH Trades
**What goes wrong:** Win rate calculation only counts `realized_pnl > 0` but BEARISH trades calculate P&L as (entry - exit) which CAN be positive.
**Why it happens:** BEARISH P&L is already correctly computed by `calculate_pnl()` — profit when price drops.
**How to avoid:** Simply use `realized_pnl > 0` universally — the P&L calculation already handles direction inversion.
**Warning signs:** BEARISH win rate showing 0% when trades should be winning.

### Pitfall 3: Equity Curve With Gaps
**What goes wrong:** Multiple trades closing on same date create duplicate x-axis points; dates with no closes create gaps.
**Why it happens:** Equity curve is by closed_date, not calendar date.
**How to avoid:** GROUP BY closed_date first (sum same-day P&L), then cumulative sum. Frontend handles date gaps naturally with line charts.
**Warning signs:** Chart showing discontinuous jumps or multiple y-values per date.

### Pitfall 4: Division by Zero in Profit Factor
**What goes wrong:** If all trades are winners (gross_loss = 0), profit factor = infinity.
**Why it happens:** Early in system operation, may have few or all-winning trades.
**How to avoid:** Return `null` or a special marker when denominator is 0. Add `trade_count` to response so frontend can show "insufficient data" warning.
**Warning signs:** API returning infinity/NaN JSON values.

### Pitfall 5: R:R Calculation for BEARISH Direction
**What goes wrong:** Risk = |entry - stop_loss| works for LONG (SL below entry) but for BEARISH SL is ABOVE entry.
**Why it happens:** BEARISH has SL > entry_price (price going up = loss), so `entry - stop_loss` is negative.
**How to avoid:** Use `abs(entry_price - stop_loss)` as risk, `realized_pnl / quantity` as reward per share. Or simply: R:R = realized_pnl / (abs(entry_price - stop_loss) × quantity).
**Warning signs:** Negative R:R values that don't match trade outcomes.

### Pitfall 6: Sector Analysis JOIN Performance
**What goes wrong:** Joining paper_trades → tickers for industry field on every request.
**Why it happens:** PaperTrade model doesn't have a denormalized `industry` field (unlike the ARCHITECTURE.md design which suggested caching it).
**How to avoid:** JOIN is fine for <100K rows. Query: `SELECT t.industry, ... FROM paper_trades pt JOIN tickers t ON pt.ticker_id = t.id WHERE ... GROUP BY t.industry`.
**Warning signs:** Slow analytics/sector endpoint (>1s response time).

## Code Examples

### Analytics Summary Query (AN-01, AN-02)
```python
# Source: Pattern from ARCHITECTURE.md Flow 4, adapted for actual model
from sqlalchemy import select, func, case
from app.models.paper_trade import PaperTrade, TradeStatus

CLOSED_STATUSES = [
    TradeStatus.CLOSED_TP2, TradeStatus.CLOSED_SL,
    TradeStatus.CLOSED_TIMEOUT, TradeStatus.CLOSED_MANUAL,
]

async def get_summary(self) -> dict:
    result = await self.session.execute(
        select(
            func.count().label("total"),
            func.count().filter(PaperTrade.realized_pnl > 0).label("wins"),
            func.sum(PaperTrade.realized_pnl).label("total_pnl"),
        ).where(PaperTrade.status.in_(CLOSED_STATUSES))
    )
    row = result.one()
    total = row.total or 0
    wins = row.wins or 0
    total_pnl = float(row.total_pnl or 0)
    win_rate = (wins / total * 100) if total > 0 else 0.0

    # Get initial capital for % calculation
    config_result = await self.session.execute(
        select(SimulationConfig.initial_capital).where(SimulationConfig.id == 1)
    )
    initial_capital = float(config_result.scalar_one())
    total_pnl_pct = (total_pnl / initial_capital * 100) if initial_capital > 0 else 0.0

    return {
        "total_trades": total,
        "wins": wins,
        "losses": total - wins,
        "win_rate": round(win_rate, 2),
        "total_pnl": total_pnl,
        "total_pnl_pct": round(total_pnl_pct, 2),
    }
```

### Equity Curve Query (AN-03)
```python
# Source: ARCHITECTURE.md SQL pattern, adapted for SQLAlchemy
async def get_equity_curve(self) -> list[dict]:
    result = await self.session.execute(
        select(
            PaperTrade.closed_date,
            func.sum(PaperTrade.realized_pnl).label("daily_pnl"),
        )
        .where(
            PaperTrade.status.in_(CLOSED_STATUSES),
            PaperTrade.closed_date.isnot(None),
        )
        .group_by(PaperTrade.closed_date)
        .order_by(PaperTrade.closed_date)
    )
    rows = result.all()

    # Compute cumulative sum in Python (simpler than window function for response building)
    cumulative = 0.0
    curve = []
    for row in rows:
        cumulative += float(row.daily_pnl or 0)
        curve.append({
            "date": row.closed_date.isoformat(),
            "daily_pnl": float(row.daily_pnl or 0),
            "cumulative_pnl": round(cumulative, 2),
        })
    return curve
```

### Max Drawdown Calculation (AN-04)
```python
# Source: Standard drawdown algorithm [ASSUMED - well-known finance formula]
def compute_drawdown(equity_curve: list[dict]) -> dict:
    """Compute max drawdown from equity curve data points."""
    if not equity_curve:
        return {"max_drawdown_vnd": 0, "max_drawdown_pct": 0, "periods": []}

    peak = 0.0
    max_dd_vnd = 0.0
    max_dd_pct = 0.0
    dd_start = None
    dd_periods = []

    for point in equity_curve:
        value = point["cumulative_pnl"]
        if value > peak:
            if dd_start is not None and max_dd_vnd < 0:
                dd_periods.append({"start": dd_start, "end": point["date"], "drawdown": max_dd_vnd})
            peak = value
            dd_start = None
        else:
            dd = value - peak
            if dd_start is None:
                dd_start = point["date"]
            if dd < max_dd_vnd:
                max_dd_vnd = dd
                max_dd_pct = (dd / peak * 100) if peak > 0 else 0.0

    return {
        "max_drawdown_vnd": round(max_dd_vnd, 2),
        "max_drawdown_pct": round(max_dd_pct, 2),
        "periods": dd_periods[-5:],  # Last 5 drawdown periods
    }
```

### Confidence Bracket Analysis (AN-06)
```python
# Source: CONTEXT.md bracket definition + ARCHITECTURE.md SQL pattern
async def get_confidence_analysis(self) -> list[dict]:
    bracket_expr = case(
        (PaperTrade.confidence <= 3, "LOW"),
        (PaperTrade.confidence <= 6, "MEDIUM"),
        else_="HIGH",
    )
    result = await self.session.execute(
        select(
            bracket_expr.label("bracket"),
            func.count().label("total"),
            func.count().filter(PaperTrade.realized_pnl > 0).label("wins"),
            func.avg(PaperTrade.realized_pnl).label("avg_pnl"),
            func.avg(PaperTrade.realized_pnl_pct).label("avg_pnl_pct"),
        )
        .where(PaperTrade.status.in_(CLOSED_STATUSES))
        .group_by(bracket_expr)
    )
    return [
        {
            "bracket": row.bracket,
            "total_trades": row.total,
            "wins": row.wins,
            "win_rate": round(row.wins / row.total * 100, 2) if row.total > 0 else 0,
            "avg_pnl": float(row.avg_pnl or 0),
            "avg_pnl_pct": float(row.avg_pnl_pct or 0),
        }
        for row in result.all()
    ]
```

### Router Registration
```python
# Source: backend/app/api/router.py (verified existing pattern)
# Add to router.py:
from app.api.paper_trading import router as paper_trading_router
api_router.include_router(paper_trading_router)
```

### Manual Follow Request Schema (PT-09)
```python
# Source: Pattern from schemas/portfolio.py TradeRequest
class ManualFollowRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=10)
    direction: str = Field(..., pattern="^(long|bearish)$")
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    take_profit_1: float = Field(..., gt=0)
    take_profit_2: float = Field(..., gt=0)
    timeframe: str = Field(..., pattern="^(swing|position)$")
    confidence: int = Field(..., ge=1, le=10)
    position_size_pct: int = Field(..., ge=1, le=100)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pydantic v1 `.dict()` | Pydantic v2 `.model_dump()` | Pydantic 2.0 | Must use v2 API in schemas |
| `Optional[X]` | `X \| None` | Python 3.10+ | Match existing codebase style |
| `response_model=List[X]` | `response_model=list[X]` | Python 3.9+ | Lowercase generics in response_model |
| `from sqlalchemy.orm import Session` | `from sqlalchemy.ext.asyncio import AsyncSession` | SQLAlchemy 2.0 | All DB access is async in this project |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Max drawdown algorithm (peak-to-trough tracking) is the standard approach | Code Examples | LOW — this is textbook finance. If wrong, only affects drawdown display |
| A2 | Confidence brackets 1-3/4-6/7-10 are correct (per CONTEXT.md, not REQUIREMENTS.md 1-4/5-7/8-10) | Pitfalls | MEDIUM — wrong brackets would misclassify signals. CONTEXT.md is authoritative |
| A3 | No existing analytics endpoint for paper trading exists yet | Architecture | LOW — verified by checking api/ directory |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + pytest-asyncio |
| Config file | `backend/pytest.ini` or pyproject.toml |
| Quick run command | `cd backend && python -m pytest tests/test_paper_trade_api.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -x --timeout=60` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PT-09 | Manual follow creates trade with PENDING status | unit | `pytest tests/test_paper_trade_api.py::TestManualFollow -x` | ❌ Wave 0 |
| AN-01 | Win rate computed correctly (overall, by direction, by timeframe) | unit | `pytest tests/test_paper_trade_analytics.py::TestWinRate -x` | ❌ Wave 0 |
| AN-02 | Total P&L in VND and % | unit | `pytest tests/test_paper_trade_analytics.py::TestTotalPnl -x` | ❌ Wave 0 |
| AN-03 | Equity curve returns sorted cumulative data | unit | `pytest tests/test_paper_trade_analytics.py::TestEquityCurve -x` | ❌ Wave 0 |
| AN-04 | Max drawdown calculation (VND, %) | unit | `pytest tests/test_paper_trade_analytics.py::TestDrawdown -x` | ❌ Wave 0 |
| AN-05 | Direction analysis groups LONG/BEARISH correctly | unit | `pytest tests/test_paper_trade_analytics.py::TestDirection -x` | ❌ Wave 0 |
| AN-06 | Confidence brackets mapped correctly | unit | `pytest tests/test_paper_trade_analytics.py::TestConfidence -x` | ❌ Wave 0 |
| AN-07 | R:R achieved vs predicted calculation | unit | `pytest tests/test_paper_trade_analytics.py::TestRiskReward -x` | ❌ Wave 0 |
| AN-08 | Profit factor and EV | unit | `pytest tests/test_paper_trade_analytics.py::TestProfitFactor -x` | ❌ Wave 0 |
| AN-09 | Sector analysis joins ticker.industry correctly | unit | `pytest tests/test_paper_trade_analytics.py::TestSector -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_paper_trade_analytics.py tests/test_paper_trade_api.py -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x --timeout=60`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_paper_trade_api.py` — covers PT-09 + all API endpoint tests
- [ ] `tests/test_paper_trade_analytics.py` — covers AN-01 through AN-09 analytics computation
- [ ] Framework install: none needed — pytest already available

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user local app, no auth |
| V3 Session Management | no | Stateless API |
| V4 Access Control | no | Single-user, all endpoints public |
| V5 Input Validation | yes | Pydantic Field validators (gt=0, pattern, min_length, ge/le) |
| V6 Cryptography | no | No sensitive data encryption needed |

### Known Threat Patterns for FastAPI + PostgreSQL

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via raw strings | Tampering | SQLAlchemy ORM (parameterized queries) — never use raw SQL strings |
| Excessive resource consumption | DoS | Query limits (limit=200 max), pagination |
| Invalid enum values in requests | Tampering | Pydantic regex pattern validators |
| Integer overflow in position_size_pct | Tampering | Pydantic ge=1, le=100 constraints |

## Open Questions

1. **Confidence bracket boundary**
   - What we know: CONTEXT.md says 1-3/4-6/7-10, REQUIREMENTS.md says 1-4/5-7/8-10
   - What's unclear: Which is the intended bracket definition
   - Recommendation: Use CONTEXT.md (1-3/4-6/7-10) as it's the phase-specific authoritative document with "Research-Backed Constraints" heading

2. **Ticker resolution for manual follow**
   - What we know: PT-09 accepts `symbol` string, need to resolve to `ticker_id`
   - What's unclear: Whether to 404 on unknown symbols or create generic entries
   - Recommendation: 404 (match existing `_get_ticker_by_symbol` pattern from analysis.py)

3. **Analytics date range filter**
   - What we know: CONTEXT doesn't specify date filtering on analytics endpoints
   - What's unclear: Whether all analytics should support optional `?from_date=&to_date=` params
   - Recommendation: Add optional date params to all analytics endpoints — cheap to implement, valuable for time-windowed analysis

## Sources

### Primary (HIGH confidence)
- `backend/app/api/portfolio.py` — Router pattern with session-per-request [VERIFIED: codebase]
- `backend/app/api/analysis.py` — Read-only query endpoint patterns [VERIFIED: codebase]
- `backend/app/api/router.py` — Router registration (1 import + 1 include_router) [VERIFIED: codebase]
- `backend/app/schemas/portfolio.py` — Pydantic response model patterns [VERIFIED: codebase]
- `backend/app/services/portfolio_service.py` — Service layer with session injection [VERIFIED: codebase]
- `backend/app/models/paper_trade.py` — PaperTrade model with TradeStatus enum [VERIFIED: codebase]
- `backend/app/models/simulation_config.py` — SimulationConfig single-row model [VERIFIED: codebase]
- `backend/app/models/ticker.py` — Ticker with `industry` field for sector JOIN [VERIFIED: codebase]
- `backend/app/services/paper_trade_service.py` — calculate_position_size, calculate_pnl [VERIFIED: codebase]
- `backend/app/database.py` — async_session factory pattern [VERIFIED: codebase]
- FastAPI 0.135.3, SQLAlchemy 2.0.49, Pydantic 2.13.0, pytest 8.4.2 [VERIFIED: pip]

### Secondary (MEDIUM confidence)
- `.planning/research/ARCHITECTURE.md` — Analytics SQL patterns (Flow 4) [VERIFIED: planning docs]
- `.planning/phases/24-api-analytics-engine/24-CONTEXT.md` — Endpoint list + bracket definitions [VERIFIED: planning docs]

### Tertiary (LOW confidence)
- Max drawdown algorithm — standard finance peak-to-trough [ASSUMED: textbook]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all verified via pip, zero new deps
- Architecture: HIGH — exact patterns from existing codebase verified
- Pitfalls: HIGH — derived from model inspection + analytics domain knowledge

**Research date:** 2025-01-27
**Valid until:** 2025-02-27 (stable — no new dependencies or moving targets)

# Phase 22: Paper Trade Foundation - Research

**Researched:** 2026-04-21
**Domain:** SQLAlchemy data modeling, state machines, financial P&L calculation
**Confidence:** HIGH

## Summary

Phase 22 creates the foundational data layer for paper trading: two new SQLAlchemy models (`PaperTrade`, `SimulationConfig`), an Alembic migration, a state machine for trade lifecycle, P&L calculation logic handling partial take-profit scenarios, and position sizing that respects VN exchange 100-share lot rules. All business logic is pure Python with no external dependencies beyond the existing stack.

The codebase has mature, well-established patterns from 21 prior phases. The Trade model, Lot model, and portfolio service provide direct templates for the paper trade model and business logic. The AIAnalysis model with its `raw_response` JSONB field and the `TickerTradingSignal` Pydantic schema provide the exact data structure that paper trades will reference (linking `ai_analyses.id` where `analysis_type = 'trading_signal'`).

**Primary recommendation:** Build PaperTrade model following Trade/Lot model patterns (Mapped[], Numeric(12,2), BigInteger PK), implement state machine as a pure Python class with explicit transition validation, and write P&L calculation as a standalone service class with comprehensive unit tests. No new dependencies needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
All implementation choices are at the agent's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key constraints from research:
- State machine: PENDING → ACTIVE → PARTIAL_TP → CLOSED (sub-states: CLOSED_TP2, CLOSED_SL, CLOSED_TIMEOUT, CLOSED_MANUAL)
- Partial TP: 50% at TP1, move SL to entry (breakeven), remaining 50% targets TP2
- Entry at D+1 open price (prevent lookahead bias)
- SL wins on ambiguous bars (conservative fill when both SL and TP breach same day)
- Position sizing rounds to 100-share lots per VN exchange rules
- Exclude score=0 (invalid) signals from auto-tracking
- P&L in both VND absolute and % of entry
- Use Numeric(12,2) for prices following existing Trade model pattern
- Use Mapped[] + mapped_column() following existing SQLAlchemy 2.0 patterns
- Separate table from real trades (paper_trades, NOT reusing trades table)
- SimulationConfig: initial_capital, auto_track_enabled, min_confidence_threshold

### Agent's Discretion
All implementation choices — pure infrastructure phase.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PT-02 | Paper trade có lifecycle đầy đủ: PENDING → ACTIVE → PARTIAL_TP → CLOSED (TP2/SL/TIMEOUT) | State machine enum + transition validation class; model has `status` column with PostgreSQL ENUM |
| PT-03 | Khi giá chạm TP1, tự động chốt 50% vị thế và dời SL về entry (breakeven) | P&L service with `apply_partial_tp()` method; model tracks `quantity`, `closed_quantity`, `adjusted_sl`; percentage math tested |
| PT-05 | Vốn giả lập tùy chỉnh, position sizing theo AI recommendation, round 100-share lots | SimulationConfig model + `calculate_position_size()` pure function; 100-lot rounding with floor division |
| PT-07 | Tính P&L mỗi lệnh (VND + %) bao gồm partial TP — entry tại open ngày D+1 (tránh lookahead bias) | P&L calculation service handles two-leg trades (TP1 leg + remaining leg); returns both VND and % |
</phase_requirements>

## Standard Stack

### Core (Already Installed — No New Dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.49 | ORM for PaperTrade + SimulationConfig models | Already in use, Mapped[] pattern established [VERIFIED: `python -c "import sqlalchemy; print(sqlalchemy.__version__)"` → 2.0.49] |
| Alembic | 1.18.4 | Migration 013 for paper_trades + simulation_config tables | Already in use, sequential numbering pattern established [VERIFIED: `python -c "import alembic; print(alembic.__version__)"` → 1.18.4] |
| Pydantic | ~2.13 | Schemas for paper trade API responses (Phase 24 prep) | Already in use for all schemas [VERIFIED: in requirements.txt via pydantic-settings] |
| pytest | 8.4.2 | Unit tests for state machine and P&L logic | Already in use, `pytest.ini` configured with asyncio_mode=auto [VERIFIED: `python -m pytest --version` → 8.4.2] |

### No New Dependencies Required

This phase is pure data modeling + business logic. The existing stack covers everything needed:
- `enum.Enum` (stdlib) for status enums
- `decimal.Decimal` (stdlib) for precise financial math
- `math.floor` (stdlib) for lot rounding

**Installation:** None — no new packages.

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── app/
│   ├── models/
│   │   ├── paper_trade.py          # PaperTrade SQLAlchemy model + enums
│   │   └── simulation_config.py    # SimulationConfig SQLAlchemy model
│   ├── services/
│   │   └── paper_trade_service.py  # State machine + P&L + position sizing
│   └── schemas/
│       └── paper_trade.py          # Pydantic schemas (prep for Phase 24 API)
├── alembic/
│   └── versions/
│       └── 013_paper_trade_tables.py
└── tests/
    ├── test_paper_trade_model.py       # Enum + model field tests
    ├── test_paper_trade_state_machine.py  # State transition tests
    ├── test_paper_trade_pnl.py         # P&L calculation tests
    └── test_position_sizing.py         # Lot rounding tests
```

### Pattern 1: SQLAlchemy Model with PostgreSQL ENUM

**What:** PaperTrade model following the exact Trade model pattern with added PostgreSQL ENUM for status
**When to use:** When status column has a fixed set of values that must be enforced at DB level
**Example:**
```python
# Source: Existing ai_analysis.py AnalysisType enum pattern [VERIFIED: codebase]
import enum
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy import (
    Integer, BigInteger, String, Numeric, Date, Float,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP
from app.models import Base


class TradeStatus(str, enum.Enum):
    """Paper trade lifecycle states."""
    PENDING = "pending"         # Signal created, awaiting D+1 open
    ACTIVE = "active"           # Entry filled at D+1 open
    PARTIAL_TP = "partial_tp"   # TP1 hit, 50% closed, SL moved to entry
    CLOSED_TP2 = "closed_tp2"   # Remaining 50% hit TP2
    CLOSED_SL = "closed_sl"     # Hit stop loss (initial or breakeven)
    CLOSED_TIMEOUT = "closed_timeout"  # Exceeded timeframe limit
    CLOSED_MANUAL = "closed_manual"    # User manually closed


class TradeDirection(str, enum.Enum):
    """Trade direction — mirrors Direction enum from schemas/analysis.py."""
    LONG = "long"
    BEARISH = "bearish"


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    ai_analysis_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ai_analyses.id"), nullable=True  # NULL for manual follows
    )
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
    # Prices
    entry_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    stop_loss: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    take_profit_1: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    take_profit_2: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # Adjusted SL after partial TP (moves to entry = breakeven)
    adjusted_stop_loss: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Sizing
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)  # Total shares (100-lot rounded)
    closed_quantity: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    # P&L fields (computed when closing)
    realized_pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    realized_pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Exit tracking
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    partial_exit_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    # Dates
    signal_date: Mapped[date] = mapped_column(Date, nullable=False)  # When signal was generated
    entry_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # D+1 when entry fills
    closed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Metadata from signal
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)  # AI confidence 1-10
    timeframe: Mapped[str] = mapped_column(String(20), nullable=False)  # swing / position
    position_size_pct: Mapped[int] = mapped_column(Integer, nullable=False)  # AI recommended %
    risk_reward_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

### Pattern 2: State Machine as Service Method

**What:** State transitions validated in a service class, not in the model itself
**When to use:** When transition logic involves side effects (P&L calculation, field updates)
**Example:**
```python
# Source: Pattern derived from portfolio_service.py [VERIFIED: codebase]
from decimal import Decimal

# Valid state transitions
VALID_TRANSITIONS: dict[TradeStatus, set[TradeStatus]] = {
    TradeStatus.PENDING: {TradeStatus.ACTIVE, TradeStatus.CLOSED_MANUAL},
    TradeStatus.ACTIVE: {TradeStatus.PARTIAL_TP, TradeStatus.CLOSED_SL,
                         TradeStatus.CLOSED_TIMEOUT, TradeStatus.CLOSED_MANUAL},
    TradeStatus.PARTIAL_TP: {TradeStatus.CLOSED_TP2, TradeStatus.CLOSED_SL,
                              TradeStatus.CLOSED_TIMEOUT, TradeStatus.CLOSED_MANUAL},
    TradeStatus.CLOSED_TP2: set(),
    TradeStatus.CLOSED_SL: set(),
    TradeStatus.CLOSED_TIMEOUT: set(),
    TradeStatus.CLOSED_MANUAL: set(),
}


def validate_transition(current: TradeStatus, target: TradeStatus) -> bool:
    """Check if a state transition is valid."""
    return target in VALID_TRANSITIONS.get(current, set())
```

### Pattern 3: SimulationConfig as Single-Row Table

**What:** Configuration table that always has exactly one row (single-user app)
**When to use:** App-wide settings for paper trading simulation
**Example:**
```python
# Source: Pattern from config.py Settings + single-user constraint [VERIFIED: codebase]
class SimulationConfig(Base):
    __tablename__ = "simulation_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, server_default="1")
    initial_capital: Mapped[Decimal] = mapped_column(
        Numeric(16, 2), nullable=False, server_default="100000000"  # 100M VND default
    )
    auto_track_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    min_confidence_threshold: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="5"  # Only track signals with confidence >= 5
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

### Anti-Patterns to Avoid
- **Hand-rolling state machine with if/elif chains:** Use a transition map (dict) for O(1) validation and easy testing
- **Float arithmetic for VND prices:** Use `Decimal` everywhere — VND amounts can be large (100M+) and rounding errors accumulate
- **Storing P&L in model __init__:** P&L is computed when trade closes, not at creation time — keep columns nullable until computed
- **Coupling state transitions to DB session:** State machine validation should be pure Python (no async/DB), testable without mocking

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Decimal precision | Custom float rounding | `decimal.Decimal` with `Numeric(12,2)` | Float accumulates errors on VND amounts (thousands) |
| PostgreSQL ENUM | String + CHECK constraint | `sqlalchemy.Enum` with `native_enum=True` | DB-level type safety, matches existing AnalysisType pattern |
| State machine framework | Install `transitions` or `statemachine` | Plain dict + validation function | Only 7 states, 10 transitions — a library is overkill |
| 100-lot rounding | Complex modulo logic | `(shares // 100) * 100` | One-liner, no edge cases worth a helper |

**Key insight:** This phase is pure data modeling + arithmetic. No external libraries needed. The complexity is in getting the P&L math right for two-leg partial TP trades, not in framework choices.

## Common Pitfalls

### Pitfall 1: Incorrect Partial TP P&L Calculation
**What goes wrong:** Treating partial TP as a simple average exit instead of two separate legs
**Why it happens:** The 50% at TP1 and 50% at TP2/SL are two independent P&L events with different exit prices
**How to avoid:** Calculate P&L for each leg separately:
- Leg 1: `(tp1_price - entry_price) × closed_quantity` (always positive for LONG)
- Leg 2: `(exit_price - entry_price) × remaining_quantity` (can be negative)
- Total: `leg1_pnl + leg2_pnl`
- Percentage: `total_pnl / (entry_price × total_quantity) × 100`
**Warning signs:** P&L for a trade that hit TP1 then SL shows a loss — this means legs weren't computed separately

### Pitfall 2: BEARISH Direction P&L Sign Inversion
**What goes wrong:** BEARISH trades need inverted P&L (profit when price falls below entry)
**Why it happens:** VN market has no short selling — BEARISH tracks prediction accuracy, but P&L must still reflect the direction correctly
**How to avoid:** For BEARISH direction: `pnl = (entry_price - exit_price) × quantity`. Also for BEARISH: SL is ABOVE entry, TPs are BELOW entry — validate these relationships in the model
**Warning signs:** All BEARISH trades show losses even when prediction was correct

### Pitfall 3: Position Sizing Rounding to Zero
**What goes wrong:** `(capital × pct / 100 / price) // 100 * 100` can produce 0 for expensive stocks or small allocations
**Why it happens:** If AI recommends 3% allocation on 100M VND capital for a 150,000 VND stock: `3M / 150K = 20 shares → 0 lots`
**How to avoid:** Floor to 100-share lots but enforce minimum 100 shares if allocation would produce > 0 from raw division. Return 0 only if capital truly can't afford 100 shares at that price
**Warning signs:** Paper trades created with quantity=0

### Pitfall 4: PostgreSQL ENUM Must Be Created Before Table
**What goes wrong:** Migration fails with "type does not exist" error
**Why it happens:** PostgreSQL native ENUMs must be `CREATE TYPE ... AS ENUM (...)` before the table that references them
**How to avoid:** In migration: (1) CREATE TYPE trade_status ..., (2) CREATE TYPE trade_direction ..., (3) CREATE TABLE paper_trades. See migration 012 pattern for enum handling
**Warning signs:** `alembic upgrade head` fails

### Pitfall 5: Forgetting `values_callable` in SAEnum
**What goes wrong:** SQLAlchemy generates incorrect ENUM values (uses enum names instead of values)
**Why it happens:** Without `values_callable`, SQLAlchemy uses `PENDING` instead of `pending` as the ENUM value
**How to avoid:** Always include `values_callable=lambda e: [m.value for m in e]` — matches the existing `AnalysisType` pattern in `ai_analysis.py`
**Warning signs:** Status column contains uppercase values while Python enum uses lowercase

### Pitfall 6: `adjusted_stop_loss` Not Used After Partial TP
**What goes wrong:** After TP1 is hit, the remaining position's SL check still uses original SL instead of breakeven
**Why it happens:** The `adjusted_stop_loss` field is set but never consulted in the check logic
**How to avoid:** The effective SL for any position check should be: `trade.adjusted_stop_loss if trade.adjusted_stop_loss is not None else trade.stop_loss`. Encapsulate this in a property or helper
**Warning signs:** Trades in PARTIAL_TP state get stopped out at original SL instead of breakeven

## Code Examples

### P&L Calculation Service
```python
# Source: Derived from portfolio_service.py FIFO P&L pattern [VERIFIED: codebase]
from decimal import Decimal


def calculate_pnl(
    direction: str,       # "long" or "bearish"
    entry_price: Decimal,
    quantity: int,
    partial_exit_price: Decimal | None,  # TP1 price (if partial TP happened)
    closed_quantity: int,                # Shares closed at TP1
    exit_price: Decimal,                 # Final exit price
) -> tuple[Decimal, float]:
    """Calculate total P&L for a paper trade including partial TP.

    Returns (pnl_vnd, pnl_pct) tuple.
    """
    remaining = quantity - closed_quantity

    if direction == "long":
        # Leg 1: partial TP (if any)
        leg1 = (partial_exit_price - entry_price) * closed_quantity if closed_quantity > 0 and partial_exit_price else Decimal("0")
        # Leg 2: remaining position
        leg2 = (exit_price - entry_price) * remaining
    else:
        # BEARISH: inverted — profit when price drops
        leg1 = (entry_price - partial_exit_price) * closed_quantity if closed_quantity > 0 and partial_exit_price else Decimal("0")
        leg2 = (entry_price - exit_price) * remaining

    total_pnl = leg1 + leg2
    total_cost = entry_price * quantity
    pnl_pct = float(total_pnl / total_cost * 100) if total_cost > 0 else 0.0

    return total_pnl, round(pnl_pct, 2)
```

### Position Sizing with 100-Lot Rounding
```python
# Source: VN exchange rules — 100-share lots [CITED: CONTEXT.md]
from decimal import Decimal


def calculate_position_size(
    capital: Decimal,
    allocation_pct: int,   # AI recommended % (1-100)
    entry_price: Decimal,
) -> int:
    """Calculate position size in shares, rounded to 100-share lots.

    Returns 0 if capital can't afford even 100 shares.
    """
    allocated = capital * allocation_pct / 100
    raw_shares = int(allocated / entry_price)
    lot_rounded = (raw_shares // 100) * 100

    # Minimum 100 shares if raw calculation > 0
    if lot_rounded == 0 and raw_shares >= 1:
        # Check if we can actually afford 100 shares
        if capital * allocation_pct / 100 >= entry_price * 100:
            lot_rounded = 100

    return lot_rounded
```

### State Machine Transition with Side Effects
```python
# Source: Pattern from portfolio_service.py record_trade [VERIFIED: codebase]
def apply_partial_tp(trade: "PaperTrade", tp1_price: Decimal) -> None:
    """Apply partial take-profit: close 50%, move SL to breakeven.

    Mutates trade in-place. Caller must commit session.
    """
    if trade.status != TradeStatus.ACTIVE:
        raise ValueError(f"Cannot apply partial TP from status {trade.status}")

    half_qty = trade.quantity // 2
    # Ensure even split on 100-lot boundary
    half_qty = (half_qty // 100) * 100
    if half_qty == 0:
        half_qty = trade.quantity  # If quantity is 100, close all at TP1

    trade.status = TradeStatus.PARTIAL_TP
    trade.closed_quantity = half_qty
    trade.partial_exit_price = tp1_price
    trade.adjusted_stop_loss = trade.entry_price  # Breakeven
```

### Alembic Migration Pattern
```python
# Source: migration 007_portfolio_tables.py + 012_trading_signal_type.py [VERIFIED: codebase]
"""Add paper_trades and simulation_config tables.

Revision ID: 013
Revises: 012
"""
def upgrade() -> None:
    # Create PostgreSQL ENUMs first
    op.execute("""
        CREATE TYPE trade_status AS ENUM (
            'pending', 'active', 'partial_tp',
            'closed_tp2', 'closed_sl', 'closed_timeout', 'closed_manual'
        )
    """)
    op.execute("""
        CREATE TYPE trade_direction AS ENUM ('long', 'bearish')
    """)

    # Then create table referencing those types
    op.execute("""
        CREATE TABLE paper_trades (
            id BIGSERIAL PRIMARY KEY,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            ai_analysis_id BIGINT REFERENCES ai_analyses(id),
            direction trade_direction NOT NULL,
            status trade_status NOT NULL DEFAULT 'pending',
            entry_price NUMERIC(12,2) NOT NULL,
            -- ... rest of columns
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    # Indexes for Phase 23 queries
    op.execute("CREATE INDEX idx_paper_trades_status ON paper_trades (status)")
    op.execute("CREATE INDEX idx_paper_trades_ticker ON paper_trades (ticker_id)")

    # SimulationConfig: single-row config table
    op.execute("""
        CREATE TABLE simulation_config (
            id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            initial_capital NUMERIC(16,2) NOT NULL DEFAULT 100000000,
            auto_track_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            min_confidence_threshold INTEGER NOT NULL DEFAULT 5
                CHECK (min_confidence_threshold BETWEEN 1 AND 10),
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    # Insert default config row
    op.execute("""
        INSERT INTO simulation_config (id) VALUES (1)
        ON CONFLICT (id) DO NOTHING
    """)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `Column(Enum(...))` (SA 1.x) | `mapped_column(SAEnum(...))` with `Mapped[]` | SQLAlchemy 2.0 (Jan 2023) | Type-safe column definitions, IDE autocomplete |
| String status columns | Native PostgreSQL ENUM types | Project convention | DB-level validation, smaller storage |
| `onupdate=datetime.utcnow` | `onupdate=func.now()` | Project convention | Server-side timestamp, timezone-aware |

**Deprecated/outdated:**
- `declarative_base()` function: Replaced by `DeclarativeBase` class (already in use) [VERIFIED: `app/models/__init__.py`]
- `Column()` + `relationship()` legacy: Replaced by `Mapped[]` + `mapped_column()` (already in use) [VERIFIED: all model files]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | 100M VND is a reasonable default for initial_capital | Pattern 3: SimulationConfig | Low — user can change via settings; just affects default |
| A2 | min_confidence_threshold default of 5 is appropriate | Pattern 3: SimulationConfig | Low — configurable; 5 is middle of 1-10 scale |
| A3 | `id = 1 CHECK (id = 1)` pattern is suitable for single-row config | Pattern 3: SimulationConfig | Low — standard PostgreSQL pattern for singleton config tables |
| A4 | Numeric(14,2) is sufficient for realized_pnl (max ~99 trillion VND) | Pattern 1: PaperTrade model | Very low — personal portfolio won't approach this limit |
| A5 | Half quantity at TP1 should also round to 100-lot boundary | Code Examples: apply_partial_tp | Medium — if total qty is 200, half is exactly 100 (clean). But 300 → 100 closes, 200 remains. Need to decide: round half up or down to nearest 100 |

## Open Questions

1. **Half-quantity lot rounding at partial TP**
   - What we know: Total quantity is always 100-lot rounded. When 50% closes at TP1, half might not be 100-lot clean (e.g., 300 shares → 150 → rounds to 100)
   - What's unclear: Should we round DOWN to nearest 100 (conservative, close less) or UP (close more)?
   - Recommendation: Round DOWN — matches conservative principle (SL wins on ambiguous bars). If only 100 shares total, close all at TP1 (special case)

2. **BEARISH trade P&L semantics**
   - What we know: VN has no short selling. BEARISH tracks prediction accuracy per STATE.md
   - What's unclear: Should BEARISH P&L be synthetic (as if shorted) or just track "would have avoided loss"?
   - Recommendation: Use synthetic short P&L (entry - exit) for consistent analytics. STATE.md says "BEARISH tracks prediction accuracy, not synthetic short P&L" but for P&L calculation purposes, a directional calculation is needed to produce a meaningful number. Track it as prediction accuracy with inverted math.

3. **paper_trades.ai_analysis_id nullable for manual follows**
   - What we know: PT-09 (Phase 24) allows manual follow with custom entry/SL/TP
   - What's unclear: Should this field be nullable now or wait for Phase 24?
   - Recommendation: Make it nullable now — avoids a migration later and costs nothing

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + pytest-asyncio |
| Config file | `backend/pytest.ini` (asyncio_mode=auto) |
| Quick run command | `cd backend && python -m pytest tests/test_paper_trade_*.py tests/test_position_sizing.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PT-02 | State machine: valid transitions succeed, invalid transitions raise error | unit | `pytest tests/test_paper_trade_state_machine.py -x` | ❌ Wave 0 |
| PT-02 | All 7 statuses exist in TradeStatus enum | unit | `pytest tests/test_paper_trade_model.py -x` | ❌ Wave 0 |
| PT-03 | apply_partial_tp closes 50%, moves SL to breakeven | unit | `pytest tests/test_paper_trade_pnl.py::test_apply_partial_tp -x` | ❌ Wave 0 |
| PT-03 | Half-quantity rounds to 100-lot boundary | unit | `pytest tests/test_paper_trade_pnl.py::test_partial_tp_lot_rounding -x` | ❌ Wave 0 |
| PT-05 | Position sizing rounds to 100-share lots | unit | `pytest tests/test_position_sizing.py -x` | ❌ Wave 0 |
| PT-05 | Position sizing returns 0 when capital insufficient | unit | `pytest tests/test_position_sizing.py::test_insufficient_capital -x` | ❌ Wave 0 |
| PT-05 | SimulationConfig has initial_capital, auto_track, min_confidence | unit | `pytest tests/test_paper_trade_model.py::test_simulation_config_fields -x` | ❌ Wave 0 |
| PT-07 | P&L calculation: LONG with no partial TP | unit | `pytest tests/test_paper_trade_pnl.py::test_long_full_exit -x` | ❌ Wave 0 |
| PT-07 | P&L calculation: LONG with partial TP (TP1 + TP2) | unit | `pytest tests/test_paper_trade_pnl.py::test_long_partial_tp_then_tp2 -x` | ❌ Wave 0 |
| PT-07 | P&L calculation: LONG with partial TP (TP1 + SL) | unit | `pytest tests/test_paper_trade_pnl.py::test_long_partial_tp_then_sl -x` | ❌ Wave 0 |
| PT-07 | P&L calculation: BEARISH direction inverted | unit | `pytest tests/test_paper_trade_pnl.py::test_bearish_pnl -x` | ❌ Wave 0 |
| PT-07 | P&L returns both VND and percentage | unit | `pytest tests/test_paper_trade_pnl.py::test_pnl_returns_vnd_and_pct -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_paper_trade_*.py tests/test_position_sizing.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_paper_trade_model.py` — covers PT-02 enum, PT-05 SimulationConfig fields
- [ ] `tests/test_paper_trade_state_machine.py` — covers PT-02 transitions
- [ ] `tests/test_paper_trade_pnl.py` — covers PT-03 partial TP, PT-07 P&L calculation
- [ ] `tests/test_position_sizing.py` — covers PT-05 lot rounding

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user app, no auth |
| V3 Session Management | no | N/A |
| V4 Access Control | no | Single-user app |
| V5 Input Validation | yes | Pydantic Field validators + DB CHECK constraints |
| V6 Cryptography | no | No secrets in this phase |

### Known Threat Patterns for SQLAlchemy/PostgreSQL

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via raw string | Tampering | Use parameterized queries — Alembic `op.execute()` with literals is safe since it's DDL only run by admin |
| Invalid state transitions | Tampering | Transition validation dict — reject invalid transitions before DB write |
| Numeric overflow in P&L | Integrity | Numeric(14,2) handles up to 99 trillion VND — sufficient for personal use |

## Sources

### Primary (HIGH confidence)
- `backend/app/models/trade.py` — Trade model pattern with Mapped[], Numeric(12,2), ForeignKey [VERIFIED: codebase]
- `backend/app/models/ai_analysis.py` — AIAnalysis with SAEnum, JSONB, values_callable pattern [VERIFIED: codebase]
- `backend/app/models/__init__.py` — Base class + model registration pattern [VERIFIED: codebase]
- `backend/app/models/lot.py` — Lot model with ForeignKey chain pattern [VERIFIED: codebase]
- `backend/alembic/versions/007_portfolio_tables.py` — Table creation migration pattern [VERIFIED: codebase]
- `backend/alembic/versions/012_trading_signal_type.py` — ENUM modification migration pattern [VERIFIED: codebase]
- `backend/app/services/portfolio_service.py` — Service class with session injection pattern [VERIFIED: codebase]
- `backend/app/schemas/analysis.py` — Direction, Timeframe, TradingPlanDetail schemas [VERIFIED: codebase]
- `backend/tests/test_trading_signal_validation.py` — Pure unit test pattern (no DB, no async) [VERIFIED: codebase]
- SQLAlchemy 2.0.49, Alembic 1.18.4, pytest 8.4.2 — versions verified via Python import

### Secondary (MEDIUM confidence)
- VN exchange 100-share lot rule — common knowledge confirmed by CONTEXT.md constraint [CITED: CONTEXT.md]
- SimulationConfig 100M VND default — reasonable for personal VN stock trading [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all verified installed
- Architecture: HIGH — follows 12 existing migrations and 13 model files exactly
- State machine design: HIGH — 7 states / 10 transitions, well-defined in CONTEXT.md
- P&L calculation: HIGH — arithmetic is straightforward, two-leg partial TP is well-specified
- Pitfalls: HIGH — based on actual codebase patterns and financial math principles

**Research date:** 2026-04-21
**Valid until:** 2026-05-21 (stable — no external dependency changes expected)

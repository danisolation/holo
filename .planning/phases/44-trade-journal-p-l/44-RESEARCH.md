# Phase 44: Trade Journal & P&L - Research

**Researched:** 2026-04-23
**Domain:** Trade journaling with FIFO P&L calculation, VN market fee structure, SQLAlchemy async, FastAPI REST, React form + table UI
**Confidence:** HIGH

## Summary

Phase 44 builds a trade journaling feature: a `trades` table + `lots` table with FIFO P&L matching, backed by 4 REST endpoints, and a React `/journal` page with a trade entry dialog, sortable/filterable data table, and stats cards. The architecture is straightforward — it mirrors existing patterns from Phase 43 (service class, Pydantic schemas, react-hook-form + zod, React Query hooks, shadcn UI). No new Python packages are needed; no new frontend packages are needed (react-hook-form, zod, @hookform/resolvers, cmdk all already installed). The one meaningful complexity is the FIFO lot matching algorithm and its reversal on delete, which must be transactional to preserve data integrity.

**Primary recommendation:** Follow the Phase 43 service-class pattern exactly. Keep FIFO logic in pure Python functions (module-level) for testability. The migration is #020. All UI components are defined in the UI-SPEC — implement them against the existing shadcn component set with no new installs.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Trade form fields: ticker (autocomplete from tickers table), side (BUY/SELL), price, quantity, trade_date (default today), user_notes (optional)
- Fees auto-calculated from UserRiskProfile.broker_fee_pct (default 0.15%) on both BUY and SELL sides + mandatory 0.1% sales tax on SELL only
- User can override auto-calculated fees with actual fees if broker charges differently
- Quantity must be multiple of 100 (HOSE lot size) — form validates this
- Trade date cannot be in the future; default to today
- Separate `trades` and `lots` tables — BUY creates lots, SELL consumes lots via FIFO matching
- FIFO matching: when SELL, consume oldest open lots for that ticker first (by buy_date ASC, then lot id ASC)
- Realized P&L per SELL trade: Σ((sell_price - lot_buy_price) × matched_quantity) - total_fees
- Total fees on a matched sell = buy-side broker fee + sell-side broker fee + sell tax (0.1%)
- Display both gross P&L (price diff only) and net P&L (after all fees/tax)
- Unrealized P&L shown for open lots using latest DailyPrice close — calculated on-the-fly, not stored
- If SELL quantity exceeds available lots, reject the trade with error message
- Optional `daily_pick_id` FK on trades table — links to daily_picks when user followed AI recommendation
- When user selects a ticker that matches a recent daily pick (last 7 days), auto-suggest the link with a checkbox "Theo gợi ý AI"
- Link is informational only — no enforcement
- `trades` table: id (BigSerial), ticker_id (FK), daily_pick_id (nullable FK), side (BUY/SELL), quantity, price (Numeric 12,2), broker_fee (Numeric 12,2 auto-calc), sell_tax (Numeric 12,2, 0 for BUY), total_fee (computed), trade_date, user_notes (Text nullable), created_at
- `lots` table: id (BigSerial), trade_id (FK), ticker_id (FK), buy_price, quantity, remaining_quantity, buy_date, created_at
- Index on lots(ticker_id, remaining_quantity) WHERE remaining_quantity > 0 for fast FIFO lookup
- Migration 020: create both tables with indexes and constraints
- New route `/journal` with navbar entry "Nhật ký" (after "Huấn luyện")
- API endpoints: POST /api/trades, GET /api/trades (list with pagination + filters), GET /api/trades/stats, GET /api/trades/{id}
- Journal page layout: trade entry form (dialog/sheet) + trades table with sortable/filterable columns
- Color coding: green for profitable, red for loss, neutral for open BUY
- Use react-hook-form + zod for trade form validation

### Agent's Discretion
- Lot matching edge cases (partial fills, splits) — keep simple FIFO, no partial lot splitting beyond what's needed
- Stats endpoint aggregation period — default to all-time, add date range filter if straightforward
- Trade edit/delete — support delete only (with lot reversal), no edit to keep FIFO integrity clean

### Deferred Ideas (OUT OF SCOPE)
- Trade edit (lot reversal + replay complexity)
- CSV import from broker exports
- Broker-specific fee schedules
- Intraday timestamps (only track trade_date)
- Dividend income tracking
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| JRNL-01 | User nhập lệnh mua/bán thực tế (mã, giá, số lượng, ngày, phí) vào app | Trade model + POST /api/trades endpoint + TradeEntryDialog form with zod validation. Ticker autocomplete reuses existing useTickers() + Command component. Fee auto-calc from UserRiskProfile.broker_fee_pct. |
| JRNL-02 | App tự tính P&L theo FIFO, bao gồm phí môi giới (0.15%) và thuế bán (0.1%) theo quy định VN | FIFO lot matching algorithm in TradeService. BUY creates lots, SELL consumes oldest lots. Realized P&L = Σ((sell_price - buy_price) × qty) - fees. Stats endpoint aggregates. |
| JRNL-03 | Khi log trade, user có thể link đến daily pick tương ứng để theo dõi "có follow AI không?" | Optional daily_pick_id FK on trades table. Frontend auto-suggests link when ticker matches a recent daily pick (last 7 days). |
</phase_requirements>

## Standard Stack

### Core (already installed — no new packages)

**Backend:**
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | ~2.0.49 | ORM for trades + lots models | Already used for all models. Mapped columns, async sessions. [VERIFIED: requirements.txt] |
| Alembic | ~1.18 | Migration 020 | Standard migration tool already in use. [VERIFIED: requirements.txt] |
| Pydantic | ~2.13 | Request/response schemas | FastAPI integration, BaseModel with Field validators. [VERIFIED: requirements.txt via pydantic-settings] |
| FastAPI | ~0.135 | REST endpoints | Existing API framework. [VERIFIED: requirements.txt] |
| asyncpg | ~0.31 | Async PostgreSQL driver | Used by all existing DB operations. [VERIFIED: requirements.txt] |

**Frontend:**
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| react-hook-form | 7.73.1 | Trade entry form management | Already installed, used in ProfileSettingsCard. [VERIFIED: node_modules] |
| zod | 4.3.6 | Form schema validation | Already installed, z.object() pattern. [VERIFIED: node_modules] |
| @hookform/resolvers | 5.2.2 | zodResolver bridge | Already installed, supports zod v4. [VERIFIED: node_modules] |
| @tanstack/react-query | 5.99.0 | Data fetching + cache invalidation | useQuery + useMutation pattern established. [VERIFIED: node_modules] |
| @tanstack/react-table | 8.21.3 | Sortable, filterable data table | Already installed for stock listings. [VERIFIED: node_modules] |
| cmdk | 1.1.1 | Ticker autocomplete (Command component) | Already installed, used in TickerSearch. [VERIFIED: node_modules] |
| date-fns | 4.1.0 | Date formatting | Already installed, formatDateVN pattern. [VERIFIED: node_modules] |
| lucide-react | ~1.8.0 | Icons (Plus, Trash2, Sparkles, BookOpen, etc.) | Standard icon set. [VERIFIED: package.json] |

### No New Packages Needed

Zero new npm or pip installs. Every library needed is already in the project. [VERIFIED: package.json and requirements.txt]

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @tanstack/react-table | Manual HTML table | Lose built-in sorting, pagination, column definitions. Not worth it. |
| Input type="date" | react-day-picker | react-day-picker not installed. Native date input is good enough for simple date selection per UI-SPEC. |
| Command (cmdk) | Custom autocomplete | Already have the pattern working in TickerSearch. Reuse it. |

## Architecture Patterns

### Backend: New Files

```
backend/
├── app/
│   ├── api/
│   │   └── trades.py          # NEW — router for /trades endpoints
│   ├── models/
│   │   ├── trade.py           # NEW — Trade model
│   │   └── lot.py             # NEW — Lot model
│   ├── schemas/
│   │   └── trades.py          # NEW — Pydantic schemas
│   ├── services/
│   │   └── trade_service.py   # NEW — TradeService class + pure FIFO functions
│   └── api/
│       └── router.py          # MODIFY — add trades_router
├── alembic/versions/
│   └── 020_trade_journal_tables.py  # NEW — migration
└── tests/
    └── test_trade_service.py  # NEW — FIFO, fee calc, validation tests
```

### Frontend: New Files

```
frontend/src/
├── app/
│   └── journal/
│       └── page.tsx           # NEW — /journal route
├── components/
│   ├── trade-entry-dialog.tsx # NEW — form dialog
│   ├── trades-table.tsx       # NEW — data table
│   ├── trade-stats-cards.tsx  # NEW — 3-card stats row
│   ├── trade-filters.tsx      # NEW — ticker + side filter bar
│   └── delete-trade-dialog.tsx # NEW — delete confirmation
├── lib/
│   ├── api.ts                 # MODIFY — add trade types + fetch functions
│   └── hooks.ts               # MODIFY — add useTrades, useTradeStats, useCreateTrade, useDeleteTrade
└── components/
    └── navbar.tsx             # MODIFY — add "Nhật ký" link after "Huấn luyện"
```

### Pattern 1: Service Class with Pure Functions (follow PickService)
**What:** Module-level pure functions for FIFO logic + fee calculation (unit-testable without DB). Service class wraps async DB operations.
**When to use:** Always for business logic that involves computation.
**Example:**
```python
# Source: Existing pattern from backend/app/services/pick_service.py [VERIFIED: codebase]

# Pure functions at module level
def calculate_broker_fee(price: Decimal, quantity: int, broker_fee_pct: Decimal) -> Decimal:
    """Broker fee = price × quantity × broker_fee_pct / 100."""
    return (price * quantity * broker_fee_pct / Decimal("100")).quantize(Decimal("0.01"))

def calculate_sell_tax(price: Decimal, quantity: int) -> Decimal:
    """VN mandatory sell tax = 0.1% of transaction value."""
    return (price * quantity * Decimal("0.001")).quantize(Decimal("0.01"))

def fifo_match_lots(lots: list[dict], sell_quantity: int) -> list[dict]:
    """FIFO matching: consume oldest lots first. Returns list of matched allocations.
    
    Each allocation: {lot_id, buy_price, matched_quantity}
    Raises ValueError if insufficient lots.
    """
    remaining = sell_quantity
    matches = []
    for lot in lots:  # Already sorted by buy_date ASC, id ASC
        if remaining <= 0:
            break
        match_qty = min(lot["remaining_quantity"], remaining)
        matches.append({
            "lot_id": lot["id"],
            "buy_price": lot["buy_price"],
            "matched_quantity": match_qty,
        })
        remaining -= match_qty
    if remaining > 0:
        raise ValueError(f"Insufficient lots: need {sell_quantity}, available {sell_quantity - remaining}")
    return matches

def calculate_realized_pnl(
    sell_price: Decimal,
    matches: list[dict],
    sell_broker_fee: Decimal,
    sell_tax: Decimal,
    buy_broker_fees: Decimal,
) -> tuple[Decimal, Decimal]:
    """Returns (gross_pnl, net_pnl).
    
    gross_pnl = Σ((sell_price - buy_price) × matched_qty)
    net_pnl = gross_pnl - sell_broker_fee - sell_tax - buy_broker_fees
    """
    gross = sum(
        (sell_price - Decimal(str(m["buy_price"]))) * m["matched_quantity"]
        for m in matches
    )
    net = gross - sell_broker_fee - sell_tax - buy_broker_fees
    return (gross, net)

# Service class for DB operations
class TradeService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_trade(self, data: TradeCreate) -> Trade:
        # 1. Validate ticker exists
        # 2. Get broker_fee_pct from UserRiskProfile
        # 3. Calculate fees
        # 4. If SELL: FIFO match lots (within transaction)
        # 5. Create trade record
        # 6. If BUY: create lot record
        # 7. If SELL: update lot remaining quantities
        # 8. Commit
        ...
```

### Pattern 2: API Endpoint with Session (follow picks.py)
**What:** Router endpoints using `async with async_session()` context manager.
**When to use:** All API endpoints.
**Example:**
```python
# Source: Existing pattern from backend/app/api/picks.py [VERIFIED: codebase]
router = APIRouter(tags=["trades"])

@router.post("/trades", response_model=TradeResponse, status_code=201)
async def create_trade(data: TradeCreate):
    async with async_session() as session:
        service = TradeService(session)
        trade = await service.create_trade(data)
        return trade
```

### Pattern 3: React Query Mutations (follow useUpdateProfile)
**What:** useMutation with cache invalidation of related queries.
**When to use:** POST/DELETE operations.
**Example:**
```typescript
// Source: Existing pattern from frontend/src/lib/hooks.ts [VERIFIED: codebase]
export function useCreateTrade() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TradeCreate) => createTrade(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trades"] });
      queryClient.invalidateQueries({ queryKey: ["trades", "stats"] });
    },
  });
}
```

### Pattern 4: react-hook-form + zod (follow ProfileSettingsCard)
**What:** Form with `zodResolver`, field registration, watch for computed values, error display.
**When to use:** Trade entry form.
**Example:**
```typescript
// Source: Existing pattern from frontend/src/components/profile-settings-card.tsx [VERIFIED: codebase]
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

const tradeSchema = z.object({
  ticker_id: z.number().positive("Chọn mã chứng khoán"),
  side: z.enum(["BUY", "SELL"]),
  price: z.number().positive("Giá phải lớn hơn 0"),
  quantity: z.number().positive().refine(v => v % 100 === 0, "Số lượng phải là bội số của 100"),
  trade_date: z.string().refine(v => new Date(v) <= new Date(), "Ngày giao dịch không được trong tương lai"),
  user_notes: z.string().max(500).optional(),
  daily_pick_id: z.number().nullable().optional(),
  broker_fee_override: z.number().optional(),
  sell_tax_override: z.number().optional(),
});
```

### Pattern 5: Ticker Autocomplete (reuse TickerSearch pattern)
**What:** Popover + Command component for ticker selection within the trade form.
**When to use:** Trade entry form ticker field.
**Example:**
```typescript
// Source: Existing pattern from frontend/src/components/ticker-search.tsx [VERIFIED: codebase]
// Uses: Popover + Command + CommandInput + CommandList + CommandItem
// Data: useTickers() hook — already fetches all active tickers with 5min staleTime
```

### Anti-Patterns to Avoid
- **Storing computed P&L in lots table:** Unrealized P&L changes daily. Calculate on-the-fly from DailyPrice.close. [DECIDED in CONTEXT.md]
- **Allowing trade edits:** Would require lot reversal + replay. FIFO integrity is fragile. Delete-and-recreate is safer. [DECIDED in CONTEXT.md]
- **Floating point for money:** Always use `Decimal` / `Numeric(12,2)` in backend. Frontend receives as `number` (JSON) which is fine for display but backend does all calculations in Decimal. [ASSUMED — standard financial computing practice]
- **Non-transactional SELL:** FIFO lot matching + lot updates + trade creation MUST be in a single database transaction. If any step fails, rollback everything. [ASSUMED — data integrity requirement]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Form validation | Custom validation logic | zod schemas + react-hook-form | Already installed, handles async validation, field-level errors, accessibility. [VERIFIED: installed] |
| Data table sorting/pagination | Manual sort/page state | @tanstack/react-table | Already installed, provides column definitions, sort state, pagination state. [VERIFIED: installed] |
| Ticker autocomplete | Custom dropdown with keyboard nav | cmdk Command component | Already installed, handles fuzzy search, keyboard navigation, accessibility. [VERIFIED: installed] |
| VND formatting | Regex-based formatting | `formatVND()` from lib/format.ts | Already exists, uses Intl.NumberFormat. [VERIFIED: codebase] |
| Date formatting | Manual date string parsing | `formatDateVN()` from lib/format.ts | Already exists. [VERIFIED: codebase] |
| Cache invalidation | Manual refetch | React Query's invalidateQueries | Already the standard pattern. Invalidate `["trades"]` + `["trades", "stats"]` on mutation success. [VERIFIED: codebase] |

## Common Pitfalls

### Pitfall 1: FIFO Partial Lot Consumption
**What goes wrong:** A SELL of 300 shares may consume lot A (200 remaining) fully and lot B (500 remaining) partially. The partial lot must have its `remaining_quantity` decremented, not deleted.
**Why it happens:** Naive implementation might delete consumed lots entirely.
**How to avoid:** Always update `remaining_quantity` on matched lots. Only consider lots with `remaining_quantity > 0`. The partial index `WHERE remaining_quantity > 0` ensures fast lookups.
**Warning signs:** Lot remaining_quantity goes negative, or lots with remaining_quantity = 0 still appear in FIFO queries.

### Pitfall 2: Delete Reversal — Restoring Lots
**What goes wrong:** Deleting a SELL trade must restore the consumed lot quantities. Deleting a BUY trade must delete the associated lot (but only if the lot hasn't been partially consumed by a SELL).
**Why it happens:** Two-direction dependency between trades and lots.
**How to avoid:** 
- DELETE SELL: Find all lot_matches for this sell trade, add matched_quantity back to each lot's remaining_quantity.
- DELETE BUY: Check if the associated lot's remaining_quantity < quantity (i.e., some was consumed). If consumed, reject the delete with an error ("Cannot delete — this buy has been partially matched by SELL trades").
**Warning signs:** Deleting a trade and seeing orphaned or incorrect lot quantities.

### Pitfall 3: Transaction Isolation for FIFO Matching
**What goes wrong:** Two concurrent SELL trades for the same ticker could consume the same lots if not properly serialized.
**Why it happens:** Race condition in lot consumption.
**How to avoid:** Use `SELECT ... FOR UPDATE` on the lots being matched. Since this is a single-user app, this is low-risk but good practice. Alternatively, the `async with async_session()` pattern with commit/rollback handles this naturally.
**Warning signs:** Lot remaining_quantity going negative, P&L calculations being wrong.

### Pitfall 4: Decimal Precision in Fee Calculations
**What goes wrong:** Using Python `float` for fee calculations introduces rounding errors. VND amounts should never have fractional đồng.
**Why it happens:** Default Python arithmetic uses float.
**How to avoid:** All backend fee/price calculations use `Decimal`. Quantize results to `Decimal("0.01")` (VN stock prices are quoted to 2 decimal places for some, but VND has no fractional currency — round broker_fee and sell_tax to whole numbers with `Decimal("1")` or keep 2 decimals per DB schema).
**Warning signs:** Fee calculations differ by 1-2 VND from expected values.

### Pitfall 5: Lot Matching Needs a Junction Table (or Denormalized Storage)
**What goes wrong:** When a SELL consumes multiple lots with different buy prices, the P&L calculation needs to know which lots were matched and how many shares from each.
**Why it happens:** The CONTEXT.md design doesn't explicitly mention a junction/match table.
**How to avoid:** Two approaches:
1. **Store gross_pnl and net_pnl directly on the trade record** — calculate at SELL time, store the result. No need to re-derive from lot matches later. This is simpler and recommended.
2. **Create a lot_matches junction table** — `(sell_trade_id, lot_id, matched_quantity)`. Needed if you want to show per-lot P&L breakdown.

**Recommendation:** Store `gross_pnl` and `net_pnl` as columns on the `trades` table (null for BUY trades). This avoids needing a junction table while preserving the computed P&L for display. For delete reversal, a simple `lot_matches` junction table is cleaner — it records which lots a SELL consumed so they can be restored.

### Pitfall 6: Zod v4 Import Compatibility
**What goes wrong:** Zod v4 changed some APIs from v3 (e.g., `z.coerce` is different, enum handling changed).
**Why it happens:** The project has zod 4.3.6 installed.
**How to avoid:** Use `import { z } from "zod"` — this is the correct import for zod v4. The `.refine()`, `.enum()`, `.object()`, `.number()`, `.string()` APIs are stable across v3→v4. The existing ProfileSettingsCard pattern confirms compatibility. [VERIFIED: codebase uses this pattern successfully]
**Warning signs:** TypeScript errors from zod, or `zodResolver` throwing at runtime.

## Code Examples

### Migration 020: Create trades + lots tables
```python
# Source: Pattern from backend/alembic/versions/019_daily_picks_tables.py [VERIFIED: codebase]
"""Create trades and lots tables for trade journal.

Revision ID: 020
Revises: 019
"""
from alembic import op
import sqlalchemy as sa

revision = "020"
down_revision = "019"

def upgrade() -> None:
    op.create_table(
        "trades",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("ticker_id", sa.Integer, sa.ForeignKey("tickers.id"), nullable=False),
        sa.Column("daily_pick_id", sa.BigInteger, sa.ForeignKey("daily_picks.id"), nullable=True),
        sa.Column("side", sa.String(4), nullable=False),  # "BUY" or "SELL"
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("broker_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("sell_tax", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total_fee", sa.Numeric(12, 2), nullable=False),
        sa.Column("gross_pnl", sa.Numeric(14, 2), nullable=True),  # NULL for BUY
        sa.Column("net_pnl", sa.Numeric(14, 2), nullable=True),    # NULL for BUY
        sa.Column("trade_date", sa.Date, nullable=False),
        sa.Column("user_notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_trades_ticker_date", "trades", ["ticker_id", "trade_date"])
    op.create_index("ix_trades_trade_date", "trades", ["trade_date"])

    op.create_table(
        "lots",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("trade_id", sa.BigInteger, sa.ForeignKey("trades.id"), nullable=False),
        sa.Column("ticker_id", sa.Integer, sa.ForeignKey("tickers.id"), nullable=False),
        sa.Column("buy_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity", sa.Integer, nullable=False),
        sa.Column("remaining_quantity", sa.Integer, nullable=False),
        sa.Column("buy_date", sa.Date, nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    # Partial index for fast FIFO lookup — only lots with remaining shares
    op.create_index(
        "ix_lots_fifo_lookup",
        "lots",
        ["ticker_id", "buy_date", "id"],
        postgresql_where=sa.text("remaining_quantity > 0"),
    )

    # Junction table for SELL → lot matches (enables delete reversal)
    op.create_table(
        "lot_matches",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("sell_trade_id", sa.BigInteger, sa.ForeignKey("trades.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lot_id", sa.BigInteger, sa.ForeignKey("lots.id"), nullable=False),
        sa.Column("matched_quantity", sa.Integer, nullable=False),
    )
    op.create_index("ix_lot_matches_sell_trade", "lot_matches", ["sell_trade_id"])

def downgrade() -> None:
    op.drop_table("lot_matches")
    op.drop_table("lots")
    op.drop_table("trades")
```

### Trade Model
```python
# Source: Pattern from backend/app/models/daily_pick.py [VERIFIED: codebase]
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Integer, String, Text, Date, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP
from app.models import Base

class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    daily_pick_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("daily_picks.id"), nullable=True)
    side: Mapped[str] = mapped_column(String(4), nullable=False)  # "BUY" or "SELL"
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    broker_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sell_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, server_default="0")
    total_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    gross_pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    net_pnl: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    user_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
```

### Pydantic Schemas
```python
# Source: Pattern from backend/app/schemas/picks.py [VERIFIED: codebase]
from datetime import date
from pydantic import BaseModel, Field

class TradeCreate(BaseModel):
    ticker_symbol: str = Field(..., description="Ticker symbol e.g. VNM")
    side: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0)
    trade_date: date
    user_notes: str | None = Field(None, max_length=500)
    daily_pick_id: int | None = None
    broker_fee_override: float | None = None
    sell_tax_override: float | None = None

class TradeResponse(BaseModel):
    id: int
    ticker_symbol: str
    ticker_name: str
    daily_pick_id: int | None
    side: str
    quantity: int
    price: float
    broker_fee: float
    sell_tax: float
    total_fee: float
    gross_pnl: float | None
    net_pnl: float | None
    trade_date: str
    user_notes: str | None
    created_at: str

class TradeStatsResponse(BaseModel):
    total_trades: int
    realized_gross_pnl: float
    realized_net_pnl: float
    open_positions: int  # count of tickers with remaining lots > 0

class TradesListResponse(BaseModel):
    trades: list[TradeResponse]
    total: int
    page: int
    page_size: int
```

### Frontend API Types + Fetch Functions
```typescript
// Source: Pattern from frontend/src/lib/api.ts [VERIFIED: codebase]
export interface TradeResponse {
  id: number;
  ticker_symbol: string;
  ticker_name: string;
  daily_pick_id: number | null;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  broker_fee: number;
  sell_tax: number;
  total_fee: number;
  gross_pnl: number | null;
  net_pnl: number | null;
  trade_date: string;
  user_notes: string | null;
  created_at: string;
}

export interface TradeStatsResponse {
  total_trades: number;
  realized_gross_pnl: number;
  realized_net_pnl: number;
  open_positions: number;
}

export interface TradesListResponse {
  trades: TradeResponse[];
  total: number;
  page: number;
  page_size: number;
}

export interface TradeCreate {
  ticker_symbol: string;
  side: "BUY" | "SELL";
  quantity: number;
  price: number;
  trade_date: string;
  user_notes?: string;
  daily_pick_id?: number | null;
  broker_fee_override?: number;
  sell_tax_override?: number;
}

export async function fetchTrades(params?: {
  page?: number;
  ticker?: string;
  side?: string;
  sort?: string;
  order?: string;
}): Promise<TradesListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.ticker) searchParams.set("ticker", params.ticker);
  if (params?.side) searchParams.set("side", params.side);
  if (params?.sort) searchParams.set("sort", params.sort);
  if (params?.order) searchParams.set("order", params.order);
  const qs = searchParams.toString();
  return apiFetch<TradesListResponse>(`/trades${qs ? `?${qs}` : ""}`);
}

export async function fetchTradeStats(): Promise<TradeStatsResponse> {
  return apiFetch<TradeStatsResponse>("/trades/stats");
}

export async function createTrade(data: TradeCreate): Promise<TradeResponse> {
  return apiFetch<TradeResponse>("/trades", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteTrade(id: number): Promise<void> {
  await apiFetch<void>(`/trades/${id}`, { method: "DELETE" });
}
```

### FIFO Fee Calculation — VN Market Rules
```python
# VN market fee structure [VERIFIED: CONTEXT.md decision]
# 
# BUY side:  broker_fee = price × quantity × broker_fee_pct / 100
# SELL side: broker_fee = price × quantity × broker_fee_pct / 100
#            sell_tax   = price × quantity × 0.1 / 100 (mandatory)
# 
# Default broker_fee_pct = 0.15% (from UserRiskProfile)
# 
# For P&L calculation on a SELL:
#   Realized P&L includes both the original BUY fees and the SELL fees.
#   gross_pnl = Σ((sell_price - buy_price) × matched_qty)
#   net_pnl = gross_pnl - sell_broker_fee - sell_tax - Σ(buy_broker_fee_per_lot)
#
# Note: buy_broker_fee_per_lot needs to be proportionally allocated from the
# original BUY trade's broker_fee based on matched_quantity / original_quantity.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Migrations 007 + 013 (portfolio_tables, paper_trade_tables) | Dropped in migration 018 | 2026-04-23 (v7.0 cleanup) | Phase 44 builds fresh trades/lots tables with improvements (daily_pick_id FK, auto-fee calc, gross/net P&L storage) |
| Old paper trading had inline P&L | Store gross_pnl + net_pnl on trade record | Phase 44 | Avoids re-computing from lot history for every table render |

## Assumptions Log

> List all claims tagged `[ASSUMED]` in this research.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | All backend fee/price calculations should use Decimal, not float | Common Pitfalls | VND amounts could have rounding errors. LOW risk — standard practice. |
| A2 | FIFO lot matching + trade creation must be in a single DB transaction | Common Pitfalls | Data inconsistency if partial commit. LOW risk — standard practice. |
| A3 | A `lot_matches` junction table is needed for clean delete reversal | Code Examples | Without it, delete reversal is harder. Could store matched lot info as JSON on trade instead. MEDIUM risk. |

## Open Questions

1. **Buy Fee Allocation for Net P&L**
   - What we know: Net P&L includes buy-side broker fees. The original BUY trade has a single broker_fee for the entire quantity.
   - What's unclear: When a SELL partially consumes a BUY lot, how to allocate the original BUY broker fee proportionally.
   - Recommendation: Proportional allocation: `buy_fee_for_match = original_buy_trade.broker_fee × (matched_qty / original_buy_trade.quantity)`. This is the standard FIFO approach. Store the proportional buy fee in the lot_matches table or compute at SELL time from the lot's associated trade.

2. **Stats Aggregation Period**
   - What we know: CONTEXT.md says "default to all-time, add date range filter if straightforward" (agent's discretion).
   - Recommendation: Default GET /api/trades/stats to all-time. Add optional `?from=&to=` query params for date range filtering. Keep it simple — Phase 45 can add more advanced analytics.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/test_trade_service.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| JRNL-01 | Trade creation with fee auto-calc | unit | `pytest tests/test_trade_service.py::TestTradeCreation -x` | ❌ Wave 0 |
| JRNL-01 | Quantity must be multiple of 100 | unit | `pytest tests/test_trade_service.py::TestTradeValidation -x` | ❌ Wave 0 |
| JRNL-01 | Trade date cannot be future | unit | `pytest tests/test_trade_service.py::TestTradeValidation -x` | ❌ Wave 0 |
| JRNL-02 | FIFO lot matching (simple) | unit | `pytest tests/test_trade_service.py::TestFIFOMatching -x` | ❌ Wave 0 |
| JRNL-02 | FIFO lot matching (partial consumption) | unit | `pytest tests/test_trade_service.py::TestFIFOMatching -x` | ❌ Wave 0 |
| JRNL-02 | P&L calculation with fees | unit | `pytest tests/test_trade_service.py::TestPnLCalculation -x` | ❌ Wave 0 |
| JRNL-02 | SELL exceeds available lots → reject | unit | `pytest tests/test_trade_service.py::TestFIFOMatching -x` | ❌ Wave 0 |
| JRNL-02 | Fee auto-calculation (broker + sell tax) | unit | `pytest tests/test_trade_service.py::TestFeeCalculation -x` | ❌ Wave 0 |
| JRNL-03 | Pick link: daily_pick_id stored on trade | unit | `pytest tests/test_trade_service.py::TestPickLink -x` | ❌ Wave 0 |
| ALL | Trade delete with lot reversal | unit | `pytest tests/test_trade_service.py::TestTradeDelete -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_trade_service.py -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_trade_service.py` — covers JRNL-01, JRNL-02, JRNL-03
- [ ] Pure functions: `calculate_broker_fee`, `calculate_sell_tax`, `fifo_match_lots`, `calculate_realized_pnl`
- [ ] Framework install: Already installed (pytest + pytest-asyncio in requirements.txt)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Single-user app, no auth |
| V3 Session Management | No | No sessions |
| V4 Access Control | No | Single user |
| V5 Input Validation | Yes | Pydantic schemas (backend) + zod (frontend) — validates ticker exists, quantity > 0 & multiple of 100, price > 0, date not future, side in BUY/SELL |
| V6 Cryptography | No | No encryption needed |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via ticker filter | Tampering | SQLAlchemy parameterized queries (never raw SQL with user input) |
| Invalid quantity/price values | Tampering | Pydantic validation on backend (never trust frontend-only validation) |
| Overselling (SELL > available lots) | Tampering | Backend FIFO check rejects insufficient lots before any DB write |
| Negative fee injection | Tampering | Pydantic `Field(ge=0)` on fee override fields |

## Sources

### Primary (HIGH confidence)
- Codebase files verified directly:
  - `backend/app/models/daily_pick.py` — DailyPick model structure
  - `backend/app/models/user_risk_profile.py` — UserRiskProfile with broker_fee_pct
  - `backend/app/api/picks.py` — API endpoint pattern
  - `backend/app/services/pick_service.py` — Service class pattern
  - `backend/app/schemas/picks.py` — Pydantic schema pattern
  - `backend/app/models/__init__.py` — Model export pattern
  - `backend/app/api/router.py` — Router registration pattern
  - `backend/app/database.py` — async_session pattern
  - `backend/alembic/versions/019_daily_picks_tables.py` — Migration pattern
  - `frontend/src/lib/hooks.ts` — React Query hook patterns
  - `frontend/src/lib/api.ts` — apiFetch utility + type patterns
  - `frontend/src/components/profile-settings-card.tsx` — react-hook-form + zod pattern
  - `frontend/src/components/ticker-search.tsx` — Command autocomplete pattern
  - `frontend/src/components/navbar.tsx` — NAV_LINKS array for new entry
  - `frontend/package.json` — All frontend deps confirmed installed
  - `backend/requirements.txt` — All backend deps confirmed
  - `.planning/phases/44-trade-journal-p-l/44-CONTEXT.md` — All decisions
  - `.planning/phases/44-trade-journal-p-l/44-UI-SPEC.md` — Complete UI contract

### Secondary (MEDIUM confidence)
- VN market fee structure (0.15% broker, 0.1% sell tax) — confirmed in CONTEXT.md decisions and UserRiskProfile model

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified as already installed, no new dependencies
- Architecture: HIGH — direct extension of established Phase 43 patterns
- Pitfalls: HIGH — FIFO matching is well-understood algorithm, edge cases documented
- Data model: HIGH — explicitly designed in CONTEXT.md with all columns specified
- UI: HIGH — complete UI-SPEC exists with component-level specifications

**Research date:** 2026-04-23
**Valid until:** 2026-05-23 (stable — no external API changes expected)

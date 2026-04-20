# Phase 18: Support & Resistance Levels - Research

**Researched:** 2026-04-20
**Domain:** Financial indicator computation (pivot points, Fibonacci retracement), backend/frontend full-stack
**Confidence:** HIGH

## Summary

Phase 18 adds 9 new computed columns (5 pivot point levels + 4 Fibonacci retracement levels) to the existing `technical_indicators` table, following the exact same patterns established in Phase 17. The backend work is straightforward pandas computation using `.shift(1)` for pivot points and `.rolling(20).max()/.min()` for Fibonacci levels, integrated into the existing `_compute_indicators()` method. The frontend introduces a single new `SupportResistanceCard` component rendering a two-column data card (not a chart), placed between the indicator accordion and the separator on the ticker detail page.

This is a highly pattern-matched phase — every layer (migration, model, schema, service, API endpoint, frontend type, component) has a direct precedent from Phase 17. The computation is pure arithmetic on pandas Series with no external library dependencies beyond what's already imported. The main complexity is the Fibonacci swing high/low derivation on the frontend for display purposes, which is a solvable math problem with a verified formula.

**Primary recommendation:** Follow the Phase 17 pattern exactly — migration 011 adds 9 nullable Numeric(12,4) columns, model/schema/API endpoint get 9 new fields, `_compute_indicators()` returns 27 Series (18 existing + 9 new), and a new `SupportResistanceCard` component renders the latest S/R values as a structured data card.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Classic (Floor) Pivot Point formula: PP = (H+L+C)/3, S1 = 2*PP-H, R1 = 2*PP-L, S2 = PP-(H-L), R2 = PP+(H-L)
- Pivot points use previous day's H/L/C (1-day lookback via `.shift(1)`)
- Store 5 pivot values: pivot_point, support_1, support_2, resistance_1, resistance_2
- Fibonacci: 20-day rolling window, swing_high = max(high) over 20 days, swing_low = min(low) over 20 days
- Fibonacci levels: 23.6%, 38.2%, 50%, 61.8% using formula `level = swing_low + (swing_high - swing_low) * pct`
- Store 4 Fibonacci values: fib_236, fib_382, fib_500, fib_618
- Add 9 new columns to existing technical_indicators table
- Migration number: 011 (continues from 010)
- Column precision: Numeric(12,4) — matches existing indicator columns
- All columns nullable (warm-up: pivot needs 1 prior day, Fibonacci needs 20 days)
- Add `_compute_support_resistance()` private method to IndicatorService
- Call from `_compute_indicators()` alongside existing indicators
- Frontend: data card/table, NOT chart sub-charts
- Vietnamese labels: "Hỗ trợ 1", "Hỗ trợ 2", "Kháng cự 1", "Kháng cự 2", "Điểm xoay"
- Fibonacci labels: "Fib 23.6%", "Fib 38.2%", "Fib 50%", "Fib 61.8%"
- Price formatting with VN comma separator (toLocaleString('vi-VN'))

### Agent's Discretion
- Card layout details (grid columns, spacing) — resolved in UI-SPEC: two-column grid
- Color coding for support vs resistance levels — resolved in UI-SPEC: green=#26a69a, red=#ef5350
- Whether to show swing high/low values alongside Fibonacci — resolved in UI-SPEC: YES, derived from fib levels
- Empty state text when no S/R data available — resolved in UI-SPEC

### Deferred Ideas (OUT OF SCOPE)
- Woodie/Camarilla/DeMark pivot variants — only Classic pivot for now
- Multi-timeframe S/R (weekly, monthly pivots) — daily only for v3.0
- Automatic swing point detection with zig-zag indicator — simple rolling max/min for now
- Chart overlay lines for S/R on candlestick chart — handled in Phase 21
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SIG-04 | User can view support/resistance levels (pivot points) for any ticker | Backend: 5 pivot columns in migration 011, computation in `_compute_support_resistance()`, served via existing `/api/analysis/{symbol}/indicators`. Frontend: SupportResistanceCard left column with R2/R1/PP/S1/S2 |
| SIG-05 | User can view Fibonacci retracement levels for any ticker | Backend: 4 fib columns in migration 011, 20-day rolling computation. Frontend: SupportResistanceCard right column with Fib 61.8%/50%/38.2%/23.6% + derived swing high/low |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | (already installed) | `.shift(1)`, `.rolling(20).max()/.min()` for S/R computation | Already used by IndicatorService; all computation is native pandas ops |
| SQLAlchemy | (already installed) | Model columns, migration | Existing ORM; 9 new `Mapped[Decimal \| None]` columns |
| Alembic | (already installed) | Migration 011 | Existing migration framework; `op.add_column()` pattern from 010 |
| Pydantic | (already installed) | IndicatorResponse schema extension | Add 9 `float \| None` fields to existing schema |
| React / Next.js | (already installed) | SupportResistanceCard component | New "use client" component following existing patterns |
| shadcn v4 | (already installed) | Card, Badge, Skeleton, Separator | All already installed — zero new shadcn components |

### Supporting
No new libraries needed. All computation uses pandas built-in methods (`.shift()`, `.rolling().max()`, `.rolling().min()`, arithmetic operators).

### Alternatives Considered
None — the computation is pure arithmetic, no library choices to make.

**Installation:** None required. All dependencies already present.

## Architecture Patterns

### Backend Changes — Same Layer Pattern as Phase 17

```
backend/
├── alembic/versions/
│   └── 011_support_resistance_levels.py  # NEW: migration adding 9 columns
├── app/models/
│   └── technical_indicator.py            # MODIFY: add 9 mapped columns
├── app/schemas/
│   └── analysis.py                       # MODIFY: add 9 fields to IndicatorResponse
├── app/services/
│   └── indicator_service.py              # MODIFY: add _compute_support_resistance(), update _compute_indicators()
├── app/api/
│   └── analysis.py                       # MODIFY: add 9 field mappings in get_ticker_indicators()
└── tests/
    └── test_indicator_service.py         # MODIFY: add S/R computation tests
```

### Frontend Changes

```
frontend/src/
├── lib/
│   └── api.ts                            # MODIFY: add 9 fields to IndicatorData interface
├── components/
│   └── support-resistance-card.tsx       # NEW: SupportResistanceCard component
└── app/ticker/[symbol]/
    └── page.tsx                          # MODIFY: import and place SupportResistanceCard
```

### Pattern 1: Computation Method Extraction
**What:** Extract S/R computation into a separate private method `_compute_support_resistance()` that returns a dict of 9 Series, called from `_compute_indicators()`
**When to use:** When adding a logically distinct group of indicators to the existing pipeline
**Why:** Keeps `_compute_indicators()` readable — it already has 18 indicators across 3 libraries
**Example:**
```python
# Source: [VERIFIED: existing indicator_service.py pattern]
def _compute_support_resistance(
    self, close: pd.Series, high: pd.Series, low: pd.Series
) -> dict[str, pd.Series]:
    """Compute pivot points and Fibonacci retracement levels."""
    # Pivot Points — Classic (Floor) formula using previous day's values
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)
    pp = (prev_high + prev_low + prev_close) / 3
    
    return {
        "pivot_point": pp,
        "support_1": 2 * pp - prev_high,
        "support_2": pp - (prev_high - prev_low),
        "resistance_1": 2 * pp - prev_low,
        "resistance_2": pp + (prev_high - prev_low),
        # Fibonacci — 20-day rolling window
        "fib_236": swing_low + fib_range * 0.236,
        "fib_382": swing_low + fib_range * 0.382,
        "fib_500": swing_low + fib_range * 0.5,
        "fib_618": swing_low + fib_range * 0.618,
    }
```

### Pattern 2: Migration — ADD COLUMN Only
**What:** Migration 011 adds 9 nullable columns with `op.add_column()`, no data migration needed
**Example:**
```python
# Source: [VERIFIED: backend/alembic/versions/010_enhanced_indicators.py]
def upgrade() -> None:
    op.add_column("technical_indicators", sa.Column("pivot_point", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("support_1", sa.Numeric(12, 4), nullable=True))
    # ... 7 more columns

def downgrade() -> None:
    op.drop_column("technical_indicators", "fib_618")
    # ... 8 more columns (reverse order)
```

### Pattern 3: API Field Mapping — Explicit Float Conversion
**What:** Each new column gets `float(row.field) if row.field is not None else None` in the API endpoint
**Example:**
```python
# Source: [VERIFIED: backend/app/api/analysis.py lines 214-237]
IndicatorResponse(
    # ... existing fields ...
    pivot_point=float(row.pivot_point) if row.pivot_point is not None else None,
    support_1=float(row.support_1) if row.support_1 is not None else None,
    # ... 7 more fields
)
```

### Pattern 4: Frontend Data Card (Not Chart)
**What:** A single `SupportResistanceCard` component receives `indicatorData[]`, extracts latest row's S/R fields, renders a two-column Card with Badge-styled price values
**When to use:** For discrete price levels that don't need time-series visualization
**Example:**
```tsx
// Source: [VERIFIED: UI-SPEC pattern, existing analysis-card.tsx patterns]
const latest = indicatorData
  .filter(d => d.pivot_point != null)
  .sort((a, b) => b.date.localeCompare(a.date))[0];
```

### Anti-Patterns to Avoid
- **Don't add S/R as chart sub-panes:** These are discrete price levels, not time-series data. The UI-SPEC explicitly says "NOT chart sub-charts"
- **Don't create a new API endpoint:** The existing `/api/analysis/{symbol}/indicators` endpoint already serves all indicator data; just add fields to it
- **Don't use external pivot/fibonacci libraries:** These are trivial arithmetic operations; adding a library would be over-engineering

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Price formatting | Custom VN formatter | `toLocaleString('vi-VN')` | Browser-native, handles thousands separator correctly |
| Decimal→float conversion | Manual parsing | Existing `_safe_decimal()` → Pydantic `float \| None` | Pattern already handles NaN→None→null chain |
| Column upsert | Custom SQL | Existing `on_conflict_do_update` with `stmt.excluded[k]` | Auto-includes new columns via dict comprehension |

**Key insight:** The entire upsert mechanism in `compute_for_ticker()` (lines 125-131) auto-adapts to new columns because it builds the SET clause from `bulk_rows[0].keys()`. Adding 9 new keys to the indicator dict is sufficient.

## Common Pitfalls

### Pitfall 1: Pivot Point Off-by-One (shift direction)
**What goes wrong:** Pivot points calculated from same day's H/L/C instead of previous day's
**Why it happens:** Forgetting `.shift(1)` or shifting in wrong direction
**How to avoid:** Always use `high.shift(1)`, `low.shift(1)`, `close.shift(1)` — this produces NaN for row 0 (correct behavior: no prior day available)
**Warning signs:** Pivot point equals `(H+L+C)/3` for the same row's data instead of previous row
**Verification:** [VERIFIED: pandas `.shift(1)` tested — produces NaN at index 0, uses previous day's value at index 1+]

### Pitfall 2: Fibonacci Warm-Up Mismatch
**What goes wrong:** Fibonacci levels appear as NaN for 19 rows while pivot points appear from row 1
**Why it happens:** Rolling(20) needs 19 prior values; shift(1) only needs 1. This is EXPECTED behavior, not a bug
**How to avoid:** Both the model (nullable columns) and frontend (partial data state) already handle this
**Warning signs:** N/A — this is correct behavior. The frontend UI-SPEC defines a "Partial Data State" for exactly this case

### Pitfall 3: Missing Fields in API Endpoint Mapping
**What goes wrong:** New columns exist in DB but return `null` in API response
**Why it happens:** The `get_ticker_indicators()` endpoint manually maps each field (lines 214-237) — new fields must be added explicitly
**How to avoid:** Add all 9 new field mappings in the IndicatorResponse constructor. Don't rely on auto-mapping; the endpoint uses explicit field-by-field conversion
**Warning signs:** Frontend receives `undefined` for S/R fields despite data existing in database

### Pitfall 4: Test Count Assertion Breaks
**What goes wrong:** Existing test `test_returns_18_indicators` fails because indicator count changes from 18 to 27
**Why it happens:** The test asserts `expected_keys` with exactly 18 keys
**How to avoid:** Update the test to expect 27 keys (18 existing + 9 new). Update test docstring "18 indicators" → "27 indicators"
**Warning signs:** `AssertionError: assert set(...) == expected_keys` in test output

### Pitfall 5: Swing High/Low Frontend Derivation Precision
**What goes wrong:** Derived swing_high/swing_low values show floating-point artifacts (e.g., 119.00000000000001)
**Why it happens:** JavaScript floating-point arithmetic
**How to avoid:** Apply `Math.round()` or `.toFixed()` before formatting with `toLocaleString('vi-VN')`
**Verification:** [VERIFIED: derivation formula tested — `swing_low = (fib_236 * 0.5 - fib_500 * 0.236) / (0.5 - 0.236)`, `swing_high = swing_low + (fib_500 - swing_low) / 0.5` — produces exact matches]

### Pitfall 6: Forgetting to Merge S/R Dict into Main Indicators Dict
**What goes wrong:** S/R columns exist in DB and model but never get populated
**Why it happens:** Creating `_compute_support_resistance()` but forgetting to merge its return value into the indicators dict in `_compute_indicators()`
**How to avoid:** After calling `_compute_support_resistance()`, use `indicators.update(sr_indicators)` before returning
**Warning signs:** All 9 S/R columns remain NULL in database after computation

## Code Examples

### Backend: `_compute_support_resistance()` Method
```python
# Source: [Derived from CONTEXT.md formulas + verified pandas behavior]
def _compute_support_resistance(
    self, close: pd.Series, high: pd.Series, low: pd.Series
) -> dict[str, pd.Series]:
    """Compute pivot points (Classic) and Fibonacci retracement levels.
    
    Pivot Points use previous day's H/L/C (shift(1)).
    Fibonacci uses 20-day rolling window for swing high/low.
    """
    # --- Classic Pivot Points ---
    prev_high = high.shift(1)
    prev_low = low.shift(1)
    prev_close = close.shift(1)
    pp = (prev_high + prev_low + prev_close) / 3
    s1 = 2 * pp - prev_high
    r1 = 2 * pp - prev_low
    s2 = pp - (prev_high - prev_low)
    r2 = pp + (prev_high - prev_low)

    # --- Fibonacci Retracement ---
    swing_high = high.rolling(20).max()
    swing_low = low.rolling(20).min()
    fib_range = swing_high - swing_low
    fib_236 = swing_low + fib_range * 0.236
    fib_382 = swing_low + fib_range * 0.382
    fib_500 = swing_low + fib_range * 0.5
    fib_618 = swing_low + fib_range * 0.618

    return {
        "pivot_point": pp,
        "support_1": s1,
        "support_2": s2,
        "resistance_1": r1,
        "resistance_2": r2,
        "fib_236": fib_236,
        "fib_382": fib_382,
        "fib_500": fib_500,
        "fib_618": fib_618,
    }
```

### Backend: Integration into `_compute_indicators()`
```python
# Source: [VERIFIED: existing _compute_indicators pattern at line 133-184]
# At end of _compute_indicators(), before the return statement:
indicators = {
    # ... existing 18 indicators ...
}

# Support & Resistance [Phase 18]
sr = self._compute_support_resistance(close, high, low)
indicators.update(sr)

return indicators
```

### Migration 011
```python
# Source: [VERIFIED: 010_enhanced_indicators.py pattern]
revision: str = "011"
down_revision: Union[str, None] = "010"

def upgrade() -> None:
    # Pivot Points
    op.add_column("technical_indicators", sa.Column("pivot_point", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("support_1", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("support_2", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("resistance_1", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("resistance_2", sa.Numeric(12, 4), nullable=True))
    # Fibonacci Retracement
    op.add_column("technical_indicators", sa.Column("fib_236", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("fib_382", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("fib_500", sa.Numeric(12, 4), nullable=True))
    op.add_column("technical_indicators", sa.Column("fib_618", sa.Numeric(12, 4), nullable=True))

def downgrade() -> None:
    op.drop_column("technical_indicators", "fib_618")
    op.drop_column("technical_indicators", "fib_500")
    op.drop_column("technical_indicators", "fib_382")
    op.drop_column("technical_indicators", "fib_236")
    op.drop_column("technical_indicators", "resistance_2")
    op.drop_column("technical_indicators", "resistance_1")
    op.drop_column("technical_indicators", "support_2")
    op.drop_column("technical_indicators", "support_1")
    op.drop_column("technical_indicators", "pivot_point")
```

### Frontend: Swing High/Low Derivation from Fib Levels
```typescript
// Source: [VERIFIED: mathematical derivation tested in Python — exact match]
// Given: fib_236, fib_382, fib_500, fib_618 (from API)
// Derive swing_low and swing_high:
const swingLow = (fib_236 * 0.5 - fib_500 * 0.236) / (0.5 - 0.236);
const swingHigh = swingLow + (fib_500 - swingLow) / 0.5;
```

### Frontend: SupportResistanceCard Skeleton
```tsx
// Source: [VERIFIED: UI-SPEC layout contract + existing Card/Badge usage patterns]
"use client";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import type { IndicatorData } from "@/lib/api";

interface SupportResistanceCardProps {
  indicatorData: IndicatorData[];
}

export function SupportResistanceCard({ indicatorData }: SupportResistanceCardProps) {
  const latest = indicatorData
    .filter(d => d.pivot_point != null)
    .sort((a, b) => b.date.localeCompare(a.date))[0];

  if (!latest) {
    // Empty state
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-sm text-muted-foreground">
            Chưa đủ dữ liệu để tính hỗ trợ & kháng cự
          </p>
          <p className="text-xs text-muted-foreground/60 mt-1">
            Cần ít nhất 20 ngày giao dịch
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Hỗ trợ & Kháng cự</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Left: Pivot Points */}
          {/* Right: Fibonacci */}
        </div>
      </CardContent>
    </Card>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate S/R endpoint | Extend existing indicators endpoint | This phase | No new API routes needed, single fetch for all data |
| Chart-based S/R display | Data card display | This phase (locked decision) | Simpler, appropriate for discrete values |

**Not applicable:** These are stable financial formulas (Classic Pivot Points, Fibonacci retracement). No "state of the art" evolution — the math hasn't changed.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| — | — | — | — |

**All claims in this research were verified or cited — no user confirmation needed.** Every computation formula was verified with actual pandas execution. The UI-SPEC provides the complete frontend contract. All existing code patterns were read directly from the codebase.

## Open Questions

None. All implementation details are fully specified between CONTEXT.md, UI-SPEC.md, and the existing code patterns.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/test_indicator_service.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SIG-04 | Pivot point computation produces 5 correct Series with proper warm-up | unit | `cd backend && python -m pytest tests/test_indicator_service.py::TestComputeSupportResistance -x` | ❌ Wave 0 |
| SIG-04 | IndicatorResponse schema includes 5 pivot fields | unit | `cd backend && python -m pytest tests/test_indicator_service.py::TestIndicatorResponseSchema -x` | ✅ (extend existing) |
| SIG-05 | Fibonacci computation produces 4 correct Series with 19-row NaN warm-up | unit | `cd backend && python -m pytest tests/test_indicator_service.py::TestComputeSupportResistance -x` | ❌ Wave 0 |
| SIG-04+05 | _compute_indicators returns 27 indicator Series (18+9) | unit | `cd backend && python -m pytest tests/test_indicator_service.py::TestComputeIndicators::test_returns_27_indicators -x` | ✅ (update existing test) |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_indicator_service.py -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `TestComputeSupportResistance` test class — covers SIG-04, SIG-05 computation correctness
- [ ] Update `test_returns_18_indicators` → `test_returns_27_indicators` with 9 new keys
- [ ] Update `TestIndicatorResponseSchema::test_indicator_response_has_new_fields` with 9 new field names

## Security Domain

Not applicable for this phase. No new endpoints, no user input handling, no authentication changes, no data exposure changes. The 9 new columns are served through the same existing `/api/analysis/{symbol}/indicators` endpoint with the same access controls (none — public data). All computation is server-side on pre-validated price data.

## Sources

### Primary (HIGH confidence)
- `backend/app/services/indicator_service.py` — Existing computation pipeline, `_compute_indicators()` method signature and pattern
- `backend/app/models/technical_indicator.py` — Existing 18 column definitions with Numeric(12,4) precision
- `backend/app/schemas/analysis.py` — IndicatorResponse with 18 `float | None` fields
- `backend/app/api/analysis.py` — get_ticker_indicators() explicit field mapping pattern (lines 214-237)
- `backend/alembic/versions/010_enhanced_indicators.py` — Migration pattern for adding columns
- `backend/tests/test_indicator_service.py` — Test patterns: pure computation tests, schema validation
- `frontend/src/lib/api.ts` — IndicatorData interface with 18 fields
- `frontend/src/app/ticker/[symbol]/page.tsx` — Page section ordering, indicatorData prop passing
- `frontend/src/components/indicator-chart.tsx` — Receives `IndicatorData[]`, existing component integration
- `frontend/src/components/analysis-card.tsx` — Color constants (#26a69a, #ef5350), Badge usage
- `.planning/phases/18-support-resistance-levels/18-UI-SPEC.md` — Complete frontend layout contract
- `.planning/phases/18-support-resistance-levels/18-CONTEXT.md` — Locked implementation decisions

### Verified via Execution (HIGH confidence)
- pandas `.shift(1)` behavior — produces NaN at index 0, previous day's value at index 1+
- pandas `.rolling(20).max()/.min()` — produces NaN for first 19 rows (0-18), first value at index 19
- Fibonacci formulas — verified: `swing_low + (swing_high - swing_low) * pct` produces correct values
- Swing high/low derivation — verified: `(fib_236 * 0.5 - fib_500 * 0.236) / (0.5 - 0.236)` produces exact match

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new libraries, all existing dependencies
- Architecture: HIGH — exact pattern repetition from Phase 17
- Pitfalls: HIGH — verified computation edge cases via actual pandas execution
- Frontend: HIGH — complete UI-SPEC contract with verified math

**Research date:** 2026-04-20
**Valid until:** 2026-05-20 (stable — financial formulas don't change, code patterns locked)

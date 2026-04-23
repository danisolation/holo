---
phase: 46-behavior-tracking-adaptive-strategy
reviewed: 2026-04-23T18:30:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - backend/alembic/versions/022_behavior_tracking_tables.py
  - backend/app/models/behavior_event.py
  - backend/app/models/habit_detection.py
  - backend/app/models/risk_suggestion.py
  - backend/app/models/sector_preference.py
  - backend/app/schemas/behavior.py
  - backend/app/services/behavior_service.py
  - backend/app/api/behavior.py
  - backend/tests/test_behavior_service.py
  - backend/app/models/__init__.py
  - backend/app/api/router.py
  - backend/app/scheduler/jobs.py
  - backend/app/scheduler/manager.py
  - backend/app/services/pick_service.py
  - frontend/src/lib/use-behavior-tracking.ts
  - frontend/src/components/risk-suggestion-banner.tsx
  - frontend/src/components/habit-detection-card.tsx
  - frontend/src/components/viewing-stats-card.tsx
  - frontend/src/components/sector-preferences-card.tsx
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
  - frontend/src/app/ticker/[symbol]/page.tsx
  - frontend/src/components/ticker-search.tsx
  - frontend/src/app/coach/page.tsx
findings:
  critical: 0
  warning: 5
  info: 2
  total: 7
status: issues_found
---

# Phase 46: Code Review Report

**Reviewed:** 2026-04-23T18:30:00Z
**Depth:** standard
**Files Reviewed:** 24
**Status:** issues_found

## Summary

Phase 46 adds behavior tracking (viewing events, habit detection, risk suggestions, sector preferences) with a clean backend service + API layer, scheduled batch jobs, and four new frontend components on the coach page. Overall quality is solid — models, migration, schemas, and tests are well-structured. Pure computation functions are properly separated for testability. The scheduler integration follows existing patterns.

Key concerns: (1) two pure functions can crash on zero-price edge cases, (2) the weekly habit batch job creates duplicate detections on re-run, (3) a frontend/backend field name mismatch will silently drop metadata, (4) the impulsive trade detection query has no time bound, and (5) an unused import.

## Warnings

### WR-01: ZeroDivisionError in `detect_premature_profit_taking` when `sell_price=0`

**File:** `backend/app/services/behavior_service.py:47`
**Issue:** `rise_pct = ((max_after - sell_price) / sell_price) * 100` divides by `sell_price`. If `sell_price` is 0.0, this raises `ZeroDivisionError`. While a stock price of 0 is rare, defensive code in a pure function that's called from a batch job should not crash the entire weekly analysis.
**Fix:**
```python
def detect_premature_profit_taking(
    sell_price: float,
    prices_after_sell: list[float],
    threshold_pct: float = 5.0,
) -> bool:
    if not prices_after_sell or sell_price <= 0:
        return False
    max_after = max(prices_after_sell)
    rise_pct = ((max_after - sell_price) / sell_price) * 100
    return rise_pct > threshold_pct
```

### WR-02: ZeroDivisionError in `detect_holding_losers` when `buy_price=0`

**File:** `backend/app/services/behavior_service.py:70`
**Issue:** `loss_pct = ((buy_price - current_price) / buy_price) * 100` divides by `buy_price`. Same ZeroDivisionError risk as WR-01.
**Fix:**
```python
def detect_holding_losers(
    buy_price: float,
    current_price: float,
    days_held: int,
    loss_threshold_pct: float = 10.0,
    min_days: int = 5,
) -> bool:
    if buy_price <= 0:
        return False
    loss_pct = ((buy_price - current_price) / buy_price) * 100
    return loss_pct > loss_threshold_pct and days_held > min_days
```

### WR-03: Duplicate habit detections created on weekly batch re-run

**File:** `backend/app/services/behavior_service.py:339-353`
**Issue:** `detect_all_habits()` inserts new `HabitDetection` rows for every detected pattern without checking if a detection already exists for the same `(habit_type, trade_id)` pair. If the weekly batch job runs twice (e.g., manual retry, scheduler glitch), it creates exact duplicate rows. This inflates habit counts shown on the coach dashboard.
**Fix:** Either (a) clear existing detections before inserting (idempotent re-run, matching pick_service pattern), or (b) check for existing `(habit_type, trade_id)` before inserting:
```python
# Option A: Delete existing detections for this batch run (idempotent)
await self.session.execute(
    delete(HabitDetection).where(
        HabitDetection.detected_at >= func.current_date()
    )
)

# Option B: Check before insert per detection
for habit_type, detections in habits_found.items():
    for det in detections:
        existing = await self.session.execute(
            select(HabitDetection.id).where(
                HabitDetection.habit_type == habit_type,
                HabitDetection.trade_id == det["trade_id"],
            ).limit(1)
        )
        if existing.scalar_one_or_none() is not None:
            continue  # Already detected
        detection = HabitDetection(...)
        self.session.add(detection)
```
Option A is simpler and matches the existing idempotent pattern in `pick_service.py:541-543`.

### WR-04: Frontend/Backend field name mismatch for event metadata

**File:** `frontend/src/lib/api.ts:684` vs `backend/app/schemas/behavior.py:9`
**Issue:** The frontend TypeScript interface names the field `event_metadata`:
```typescript
export interface BehaviorEventCreate {
  event_metadata?: Record<string, unknown>;  // line 684
}
```
But the backend Pydantic schema expects `metadata`:
```python
class BehaviorEventCreate(BaseModel):
    metadata: dict | None = None  # line 9
```
If any frontend code sends `event_metadata` in the JSON body, Pydantic will silently ignore the unknown field. Currently no caller passes metadata, but this mismatch will cause a silent data loss bug the first time someone does.
**Fix:** Rename the frontend field to match the backend:
```typescript
export interface BehaviorEventCreate {
  event_type: "ticker_view" | "search_click" | "pick_click";
  ticker_symbol?: string;
  metadata?: Record<string, unknown>;  // Match backend schema
}
```

### WR-05: Unbounded query loads all BUY trades for impulsive trade detection

**File:** `backend/app/services/behavior_service.py:312-316`
**Issue:** The impulsive trade detection query fetches ALL `BUY` trades in the entire database with no date filter:
```python
buy_trades_result = await self.session.execute(
    select(Trade, Ticker.symbol)
    .join(Ticker, Trade.ticker_id == Ticker.id)
    .where(Trade.side == "BUY")
)
```
This also fetches ALL `NewsArticle` rows for those tickers (line 321-324). As the trade journal grows, this becomes increasingly expensive AND re-detects habits for trades that were already analyzed in previous weeks. The premature profit-taking detection (line 226-232) has a `cutoff_date` filter — this one should too.
**Fix:** Add a time-bound filter matching the premature sell pattern:
```python
buy_trades_result = await self.session.execute(
    select(Trade, Ticker.symbol)
    .join(Ticker, Trade.ticker_id == Ticker.id)
    .where(Trade.side == "BUY")
    .where(Trade.trade_date >= cutoff_date)  # Reuse existing cutoff
)
```
This also bounds the news query to relevant trades and avoids duplicate detections for old trades (complementing WR-03).

## Info

### IN-01: Unused import `literal_column`

**File:** `backend/app/services/behavior_service.py:281`
**Issue:** `from sqlalchemy import literal_column` is imported inside `detect_all_habits()` but never referenced. Likely a leftover from drafting the `DISTINCT ON` query for latest prices.
**Fix:** Remove the unused import:
```python
# Delete this line:
from sqlalchemy import literal_column
```

### IN-02: Module-level `sentTimestamps` Map grows unbounded

**File:** `frontend/src/lib/use-behavior-tracking.ts:8`
**Issue:** `const sentTimestamps = new Map<string, number>()` is module-level and never cleaned up. In a long-lived SPA session where the user browses many tickers, keys accumulate. For a personal-use app with limited tickers (~400) this is negligible, but a periodic cleanup (e.g., removing entries older than `DEBOUNCE_MS`) would be more correct.
**Fix:** Add cleanup on each check:
```typescript
const now = Date.now();
// Cleanup old entries
for (const [k, ts] of sentTimestamps) {
  if (now - ts > DEBOUNCE_MS) sentTimestamps.delete(k);
}
```

---

_Reviewed: 2026-04-23T18:30:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

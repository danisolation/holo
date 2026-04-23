---
phase: 43-daily-picks-engine
reviewed: 2025-07-18T18:45:00Z
depth: standard
files_reviewed: 18
files_reviewed_list:
  - backend/alembic/versions/019_daily_picks_tables.py
  - backend/app/api/picks.py
  - backend/app/api/router.py
  - backend/app/models/__init__.py
  - backend/app/models/daily_pick.py
  - backend/app/models/user_risk_profile.py
  - backend/app/scheduler/jobs.py
  - backend/app/scheduler/manager.py
  - backend/app/schemas/picks.py
  - backend/app/services/pick_service.py
  - backend/tests/test_pick_service.py
  - frontend/package.json
  - frontend/src/app/coach/page.tsx
  - frontend/src/components/almost-selected-list.tsx
  - frontend/src/components/navbar.tsx
  - frontend/src/components/pick-card.tsx
  - frontend/src/components/profile-settings-card.tsx
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
findings:
  critical: 0
  warning: 3
  info: 4
  total: 7
status: issues_found
---

# Phase 43: Code Review Report

**Reviewed:** 2025-07-18T18:45:00Z
**Depth:** standard
**Files Reviewed:** 18
**Status:** issues_found

## Summary

Phase 43 introduces a daily picks engine: backend service that scores trading signals into ranked picks with position sizing and Vietnamese explanations, plus a frontend coach page for viewing picks and managing a risk profile. Overall well-structured—clean separation of pure computation functions for testability, good use of Pydantic schemas with validation, and solid UI with loading/error/empty states.

Three warnings found: a semantic mismatch that causes incorrect position sizing on recomputation, a division-by-zero guard missing in a pure function, and a floating-point equality comparison in the frontend. Four informational items on code hygiene.

## Warnings

### WR-01: Position size recomputation uses wrong percentage value

**File:** `backend/app/services/pick_service.py:466` and `backend/app/services/pick_service.py:530-531`
**Issue:** In `generate_daily_picks()`, line 466 stores the *computed capital percentage* (`position_size_pct_computed`, i.e., what % of capital the position actually represents after lot rounding) into `DailyPick.position_size_pct`. Later in `get_today_picks()`, line 530-531 reads this value back and passes it to `compute_position_sizing()` as the `position_pct` parameter (the AI's *recommended allocation percentage*). These are semantically different values. For example, if the AI recommended 8% allocation but lot rounding pushed actual usage to 12%, the recomputation will use 12% as the allocation target—yielding a larger position than the AI intended.
**Fix:** Store the original trading plan `position_size_pct` in the DB column (or add a separate column). Change line 466:
```python
# Before (stores computed capital_pct):
position_size_pct=Decimal(str(p.get("position_size_pct_computed", 0))),

# After (stores original AI recommendation):
position_size_pct=Decimal(str(p.get("position_size_pct", 10))),
```

### WR-02: ZeroDivisionError in compute_position_sizing when capital is 0

**File:** `backend/app/services/pick_service.py:113`
**Issue:** `capital_pct = round(total_vnd / capital * 100, 1)` will raise `ZeroDivisionError` if `capital` is 0. While the Pydantic schema enforces `capital > 0` on the API boundary, `compute_position_sizing` is a standalone pure function that could be called from other code paths (tests, scripts, scheduler jobs) without that validation layer.
**Fix:** Add a guard at the top of the function:
```python
def compute_position_sizing(capital: int, entry_price: float, position_pct: int) -> dict:
    if capital <= 0 or entry_price <= 0:
        return {"shares": 0, "total_vnd": 0, "capital_pct": 0.0}
    # ... rest of function
```

### WR-03: Floating-point exact equality comparison for P&L display

**File:** `frontend/src/components/pick-card.tsx:145`
**Issue:** `pnlPct !== null && pnlPct === 0` uses strict equality on a float computed as `((currentPrice - entry_price) / entry_price) * 100`. Due to floating-point arithmetic, this will almost never be exactly `0`—the "flat" badge will never render and the display will fall through to showing nothing (no badge for tiny rounding artifacts like ±0.0000001%).
**Fix:** Use an epsilon comparison:
```tsx
{pnlPct != null && Math.abs(pnlPct) < 0.05 && (
  <Badge variant="outline">— 0.0%</Badge>
)}
```
And add `Math.abs(pnlPct) >= 0.05` guards to the positive/negative branches above to avoid double-rendering.

## Info

### IN-01: Unused import

**File:** `backend/app/api/picks.py:2`
**Issue:** `from datetime import date` is imported but never used in this module. All date handling is inside `PickService`.
**Fix:** Remove the import line.

### IN-02: Redundant exception types in catch clause

**File:** `backend/app/services/pick_service.py:437`
**Issue:** `except (ClientError, ServerError, Exception) as e:` — since `Exception` is the base class of both `ClientError` and `ServerError`, listing them is redundant. The intent (non-critical failure) is fine, but the code reads as if there are distinct handlers.
**Fix:** Simplify to just `except Exception as e:` or, better, keep only the specific types and add a comment:
```python
except (ClientError, ServerError) as e:
    logger.warning(f"Gemini explanation failed (picks still valid): {e}")
except Exception as e:
    logger.warning(f"Unexpected error generating explanations (picks still valid): {e}")
```

### IN-03: Fragile text-splitting for Gemini explanations

**File:** `backend/app/services/pick_service.py:421-435`
**Issue:** The logic splits Gemini's response by searching for symbol names in the text and slicing from one symbol mention to the next. If Gemini mentions another symbol within a section (e.g., "VNM tốt hơn FPT vì…"), the split boundary will be wrong, truncating VNM's explanation prematurely.
**Fix:** Consider a more robust approach: prompt Gemini to return JSON-keyed output or use numbered section delimiters (e.g., `### 1. VNM\n...`) and split on those markers.

### IN-04: Missing input validation on history endpoint days parameter

**File:** `backend/app/api/picks.py:25`
**Issue:** `get_pick_history(days: int = 30)` accepts any integer. While the service caps at 365, negative values like `days=-5` would compute `func.current_date() - (-5)` = a future date, returning an empty result. Not a security issue, but an unhandled edge case.
**Fix:** Add a `Query` constraint:
```python
from fastapi import Query

async def get_pick_history(days: int = Query(default=30, ge=1, le=365)):
```

---

_Reviewed: 2025-07-18T18:45:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

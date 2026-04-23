---
phase: 47-goals-weekly-reviews
reviewed: 2025-07-25T10:30:00Z
depth: standard
files_reviewed: 19
files_reviewed_list:
  - backend/alembic/versions/023_goals_weekly_reviews.py
  - backend/app/models/trading_goal.py
  - backend/app/models/weekly_prompt.py
  - backend/app/models/weekly_review.py
  - backend/app/schemas/goals.py
  - backend/app/services/goal_service.py
  - backend/app/api/goals.py
  - backend/tests/test_goal_service.py
  - backend/app/models/__init__.py
  - backend/app/api/router.py
  - backend/app/scheduler/jobs.py
  - backend/app/scheduler/manager.py
  - frontend/src/components/monthly-goal-card.tsx
  - frontend/src/components/set-goal-dialog.tsx
  - frontend/src/components/weekly-prompt-card.tsx
  - frontend/src/components/weekly-review-card.tsx
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
  - frontend/src/app/coach/page.tsx
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 47: Code Review Report

**Reviewed:** 2025-07-25T10:30:00Z
**Depth:** standard
**Files Reviewed:** 19
**Status:** issues_found

## Summary

Phase 47 adds monthly profit goal tracking, weekly risk tolerance prompts, and AI-generated weekly performance reviews. The implementation spans 3 new DB models, an Alembic migration, a comprehensive goal service with Gemini integration, a FastAPI router, React Query hooks, and 4 new frontend components.

**Overall quality is good.** The pure function extraction pattern (compute_goal_progress, clamp_risk_level, build_review_prompt, parse_review_response) with thorough unit tests is well-designed. The Gemini 3-stage fallback strategy is robust. Frontend components handle loading/error/empty states properly with good accessibility (aria labels, roles).

Key concerns: one potential data integrity bug where the scheduled review job could produce duplicate reviews, and several moderate issues around error handling and missing validation.

## Critical Issues

### CR-01: Duplicate Weekly Reviews — No Idempotency Guard

**File:** `backend/app/services/goal_service.py:432-528`
**Issue:** `generate_review()` creates a new `WeeklyReview` row every time it's called with no check for an existing review for the same `week_start`/`week_end` period. The scheduler in `manager.py` registers this job both as a cron job (Sunday 21:00, line 297) **and** as a chained job triggered after `weekly_behavior_analysis` (line 178). If `weekly_behavior_analysis` completes before 21:00, the chain fires `generate_weekly_review_triggered` first, and then the cron fires `generate_weekly_review` at 21:00 — producing a duplicate review for the same week.

Even with `replace_existing=True` on the chain job, the cron job is a separate job ID (`generate_weekly_review` vs `generate_weekly_review_triggered`) and will fire independently.

**Fix:**
```python
# In generate_review(), add idempotency check at the top:
async def generate_review(self) -> str:
    today = date.today()
    week_end = today
    week_start = today - timedelta(days=6)

    # Idempotency: skip if review already exists for this week
    existing = await self.session.execute(
        select(WeeklyReview).where(
            WeeklyReview.week_start == week_start,
            WeeklyReview.week_end == week_end,
        )
    )
    if existing.scalar_one_or_none():
        logger.info(f"Weekly review already exists for {week_start}-{week_end}, skipping")
        return "Already generated"

    # ... rest of method
```

## Warnings

### WR-01: KeyError Risk in `respond_to_prompt` When Response Is Invalid

**File:** `backend/app/services/goal_service.py:385-386`
**Issue:** The `delta_map[response]` lookup will raise `KeyError` if `response` is not in the map. While Pydantic validates at the API layer (`Literal["cautious", "unchanged", "aggressive"]`), the service method itself is public and could be called from other code paths (e.g., scheduler jobs, tests, or future internal callers) without Pydantic validation. A `KeyError` would produce an unhelpful 500 error.
**Fix:**
```python
delta = delta_map.get(response)
if delta is None:
    raise ValueError(f"Invalid response: {response}. Must be one of: cautious, unchanged, aggressive")
new_level = clamp_risk_level(prompt.risk_level_before or 3, delta)
```

### WR-02: `generate_review` Uses ticker_id Instead of ticker_symbol in Trade Data

**File:** `backend/app/services/goal_service.py:453`
**Issue:** The trade data sent to the Gemini prompt uses `str(t.ticker_id)` (a numeric database ID like "42") instead of the actual ticker symbol (like "VNM"). This means the AI sees meaningless numbers in the prompt instead of stock tickers, degrading the quality of the review narrative. The comment on line 453 acknowledges this: `"ticker_id — API layer can resolve to symbol"` — but it's not actually resolved here.
**Fix:**
```python
# Join with Ticker model to get symbol, or build a ticker_id→symbol lookup:
from app.models.ticker import Ticker

ticker_result = await self.session.execute(
    select(Ticker.id, Ticker.symbol)
)
ticker_map = {row.id: row.symbol for row in ticker_result}

trades_data = [
    {
        "ticker": ticker_map.get(t.ticker_id, str(t.ticker_id)),
        "side": t.side,
        "pnl": float(t.net_pnl) if t.net_pnl else 0,
    }
    for t in trades
]
```

### WR-03: Missing `updated_at` Auto-Update Trigger in Migration

**File:** `backend/alembic/versions/023_goals_weekly_reviews.py:32`
**Issue:** The `trading_goals` table has `updated_at` with `server_default=sa.func.now()`, but PostgreSQL `server_default` only applies on INSERT, not on UPDATE. The SQLAlchemy model (`trading_goal.py:25`) has `onupdate=func.now()` which works at the ORM level, but direct SQL updates (e.g., from a raw query, migration script, or psql) will not update the `updated_at` column. Consider adding a PostgreSQL trigger in the migration for full consistency, or accept that this only works via ORM (document the caveat).
**Fix:** This is acceptable if all updates go through the ORM. If you want DB-level consistency, add a trigger:
```python
op.execute("""
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = now();
        RETURN NEW;
    END;
    $$ language 'plpgsql';

    CREATE TRIGGER trading_goals_updated_at
        BEFORE UPDATE ON trading_goals
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
""")
```

### WR-04: `set_goal` Endpoint Returns Hardcoded `actual_pnl=0` and `progress_pct=0`

**File:** `backend/app/api/goals.py:39-49`
**Issue:** The `POST /goals` endpoint returns `actual_pnl=0, progress_pct=0, progress_color="red"` hardcoded, even when replacing an existing goal that may already have trades with non-zero P&L for the current month. A user updating their target mid-month would see a flash of `0` actual before the frontend re-fetches via `useCurrentGoal`. This is a data consistency issue at the API level — the response doesn't reflect reality.
**Fix:**
```python
# After commit, compute actual values like get_current_goal does:
actual_pnl = await service._compute_actual_pnl(goal.month, next_month)
progress = compute_goal_progress(float(actual_pnl), float(goal.target_pnl))
return GoalResponse(
    id=goal.id,
    target_pnl=float(goal.target_pnl),
    actual_pnl=float(actual_pnl),
    month=goal.month,
    status=goal.status,
    progress_pct=progress["percentage"],
    progress_color=progress["color"],
    created_at=goal.created_at,
    updated_at=goal.updated_at,
)
```

### WR-05: Duplicate `id` Attribute on Error Messages in SetGoalDialog

**File:** `frontend/src/components/set-goal-dialog.tsx:107-115`
**Issue:** Both the `error` and `serverError` `<p>` elements use the same `id="goal-input-error"`. When both error states are rendered simultaneously (unlikely but possible during race conditions), this creates duplicate DOM IDs which is invalid HTML and breaks `aria-describedby` association. Additionally, both error messages would be shown at once without distinction.
**Fix:**
```tsx
{error && (
  <p id="goal-input-error" className="text-xs text-destructive mt-1">
    {error}
  </p>
)}
{serverError && !error && (
  <p id="goal-input-error" className="text-xs text-destructive mt-1">
    {serverError}
  </p>
)}
```
Or use separate IDs and combine in `aria-describedby`.

## Info

### IN-01: `WeeklyReviewOutput` Schema Uses `dict` for Highlights

**File:** `backend/app/services/goal_service.py:36`
**Issue:** `highlights: dict` in the `WeeklyReviewOutput` Pydantic model is untyped. Using a more specific type would give better structured output enforcement from Gemini.
**Fix:**
```python
class ReviewHighlights(BaseModel):
    good: list[str] = []
    bad: list[str] = []

class WeeklyReviewOutput(BaseModel):
    summary_text: str
    highlights: ReviewHighlights
    suggestions: list[str]
```

### IN-02: `formatMonth` Uses Local Timezone Parsing

**File:** `frontend/src/components/monthly-goal-card.tsx:31-34`
**Issue:** `new Date(monthStr)` where `monthStr` is `"2026-04-01"` (date-only) is parsed as UTC midnight, but `getMonth()` uses local timezone. In UTC+7, this should be fine (UTC midnight + 7h = still April 1st), but in negative-offset timezones it could show the wrong month. Since this is a personal app used in Vietnam (UTC+7), this is not a real bug, just noting the pattern.
**Fix:** Parse explicitly: `const parts = monthStr.split("-"); return \`${parseInt(parts[1])}/${parts[0]}\`;`

### IN-03: Coach Page Section Heading Inconsistency

**File:** `frontend/src/app/coach/page.tsx:159`
**Issue:** The "Mục tiêu & Nhận xét" heading uses `text-base` while the adjacent "Phân tích hành vi" heading on line 168 uses `text-lg`. Minor visual inconsistency.
**Fix:** Use `text-lg` for both:
```tsx
<h2 className="text-lg font-bold">Mục tiêu & Nhận xét</h2>
```

---

_Reviewed: 2025-07-25T10:30:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

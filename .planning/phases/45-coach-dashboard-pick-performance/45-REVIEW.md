---
phase: 45-coach-dashboard-pick-performance
reviewed: 2026-04-23T11:15:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - backend/alembic/versions/021_pick_outcome_columns.py
  - backend/app/models/daily_pick.py
  - backend/app/services/pick_service.py
  - backend/app/schemas/picks.py
  - backend/app/api/picks.py
  - backend/app/scheduler/jobs.py
  - backend/app/scheduler/manager.py
  - backend/tests/test_pick_outcome.py
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
  - frontend/src/components/pick-performance-cards.tsx
  - frontend/src/components/pick-history-table.tsx
  - frontend/src/app/coach/page.tsx
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 45: Code Review Report

**Reviewed:** 2026-04-23T11:15:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 45 delivers pick outcome tracking (backend) and the unified coach dashboard (frontend). The implementation is solid overall — the pure `compute_pick_outcome` function has good test coverage (13 tests), the API endpoints are properly validated with status whitelisting and pagination caps, and the frontend components handle loading/error/empty states gracefully with accessibility considerations.

Three warnings found: (1) the scheduler job for outcome checking is missing the error handling and job tracking that every other job in the codebase follows, risking silent failures and lost progress; (2) `compute_pick_outcome` can divide by zero if a corrupt entry_price of 0 reaches the function; (3) the pick history filter bar is missing the "expired" filter option despite the backend and OutcomeBadge component both supporting it.

## Warnings

### WR-01: Scheduler Job Missing Error Handling and Job Execution Tracking

**File:** `backend/app/scheduler/jobs.py:595-607`
**Issue:** `daily_pick_outcome_check` is the only job in the codebase without `JobExecutionService` tracking, `try/except` error handling, or resilience patterns. Every other chained job (see `daily_pick_generation` at line 561, `daily_hnx_upcom_analysis` at line 533) creates an execution record, wraps work in try/except, and records success/failure. This job has none of that.

Consequences:
- No job execution record → the health dashboard can't show whether this job ran or when it last succeeded.
- If `compute_pick_outcomes()` raises on any single pick (e.g., unexpected null data), the entire batch fails, partial `days_held` updates are rolled back, and the exception propagates to APScheduler's `EVENT_JOB_ERROR` as a generic log line — no structured tracking.
- Since `compute_pick_outcomes()` commits all-or-nothing at line 880, a failure processing pick N means picks 1..N-1's updates are also lost.

**Fix:**
```python
async def daily_pick_outcome_check():
    """Check pending picks and update outcomes from DailyPrice data."""
    logger.info("=== DAILY PICK OUTCOME CHECK START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_pick_outcome_check")
        try:
            from app.services.pick_service import PickService

            service = PickService(session)
            result = await service.compute_pick_outcomes()
            await job_svc.complete(
                execution, status="success", result_summary=result
            )
            await session.commit()
            logger.info(f"=== DAILY PICK OUTCOME CHECK DONE: {result} ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"=== DAILY PICK OUTCOME CHECK FAILED: {e} ===")
            raise
```

### WR-02: Division by Zero Risk in compute_pick_outcome When entry_price Is 0

**File:** `backend/app/services/pick_service.py:68, 79, 91`
**Issue:** `compute_pick_outcome` computes `((close - entry_price) / entry_price) * 100` at three locations without checking that `entry_price != 0`. While the pick generation logic at line 415 filters `entry_price <= 0`, a corrupt database row or manual insert with `entry_price = 0` would cause a `ZeroDivisionError` that crashes the entire outcome batch (compounded by WR-01's lack of error handling).

**Fix:** Add a guard at the top of the function:
```python
def compute_pick_outcome(
    entry_price: float,
    stop_loss: float,
    take_profit_1: float,
    take_profit_2: float | None,
    daily_closes: list[tuple[date, float]],
    max_trading_days: int = 10,
) -> dict:
    if not daily_closes:
        return {"outcome": PickOutcome.PENDING, "days_held": 0, "actual_return_pct": None}

    if entry_price == 0:
        return {"outcome": PickOutcome.PENDING, "days_held": 0, "actual_return_pct": None}

    sorted_closes = sorted(daily_closes, key=lambda x: x[0])
    # ... rest of function
```

### WR-03: Missing "Expired" Filter in Pick History Table

**File:** `frontend/src/components/pick-history-table.tsx:75-80`
**Issue:** The `FILTER_OPTIONS` array defines 4 filters: "Tất cả" (all), "Thắng" (winner), "Thua" (loser), "Đang theo dõi" (pending) — but omits "Hết hạn" (expired). The backend API at `api/picks.py:20` supports `"expired"` in `_VALID_STATUSES`, the `OutcomeBadge` component at line 33-38 renders an expired badge ("Hết hạn"), and the CONTEXT.md spec (line 44) lists "Hết hạn" as a supported outcome badge. Users can see expired picks in the "all" view but cannot filter to show only expired picks.

**Fix:**
```tsx
const FILTER_OPTIONS = [
  { label: "Tất cả", value: "all" },
  { label: "Thắng", value: "winner" },
  { label: "Thua", value: "loser" },
  { label: "Hết hạn", value: "expired" },
  { label: "Đang theo dõi", value: "pending" },
] as const;
```

## Info

### IN-01: PENDING Return Dicts Missing hit_* Keys (Inconsistent Shape)

**File:** `backend/app/services/pick_service.py:54, 95-99`
**Issue:** The PENDING return paths at lines 54 and 95-99 only include `outcome`, `days_held`, and `actual_return_pct`, while LOSER/WINNER/EXPIRED paths include additional `hit_stop_loss`, `hit_take_profit_1`, `hit_take_profit_2` keys. The consumer at line 865-867 safely handles this via `.get()` with defaults, so there's no bug — but the inconsistent dict shape across return paths is a code smell that could trip up future callers.

**Fix:** Add the missing keys to both PENDING returns for a consistent contract:
```python
# Line 54
return {"outcome": PickOutcome.PENDING, "days_held": 0, "hit_stop_loss": False,
        "hit_take_profit_1": False, "hit_take_profit_2": False, "actual_return_pct": None}

# Line 95
return {"outcome": PickOutcome.PENDING, "days_held": len(sorted_closes), "hit_stop_loss": False,
        "hit_take_profit_1": False, "hit_take_profit_2": False, "actual_return_pct": None}
```

### IN-02: Streak Calculation Counts Per-Pick Not Per-Day

**File:** `backend/app/services/pick_service.py:782-801`
**Issue:** The streak query at line 785 orders by `pick_date DESC, rank ASC` and counts consecutive matching outcomes. On a day with multiple picks (e.g., 5 picks: 3 winners + 2 losers), the streak counts individual picks, not trading days. So 3 winning picks on one day + 2 on the previous day yields a streak of 5 — which could be misleading if the user interprets "streak" as consecutive *days*. This is a design ambiguity rather than a bug, but worth noting for future iteration.

**Fix:** No code change needed now. If per-day streak is desired later, add `DISTINCT ON (pick_date)` to the streak query and pick the "dominant" outcome per day.

---

_Reviewed: 2026-04-23T11:15:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

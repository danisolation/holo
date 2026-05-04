---
phase: 52-discovery-engine-schema
reviewed: 2025-07-23T19:30:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - backend/app/models/discovery_result.py
  - backend/alembic/versions/026_discovery_results.py
  - backend/app/services/discovery_service.py
  - backend/tests/test_discovery_service.py
  - backend/app/models/__init__.py
  - backend/app/scheduler/jobs.py
  - backend/app/scheduler/manager.py
findings:
  critical: 0
  warning: 2
  info: 3
  total: 5
status: issues_found
---

# Phase 52: Code Review Report

**Reviewed:** 2025-07-23T19:30:00Z
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

The discovery engine schema and scoring service are well-structured overall. The model, migration, service, job, and scheduler integration all follow established project patterns consistently. Scoring functions have clear boundary logic with proper None-handling. Tests cover boundary values well.

Two warnings found: a truthy-check bug in `score_adx` that mishandles zero-valued DI inputs, and timezone sensitivity with `date.today()` that could cause off-by-one date issues on UTC-configured servers. Three informational items flag misleading comments/docs and a minor transactional concern.

## Warnings

### WR-01: Truthy Check Instead of None Check in `score_adx`

**File:** `backend/app/services/discovery_service.py:53`
**Issue:** `if plus_di and minus_di:` uses Python truthiness, which treats `0.0` as falsy. If `plus_di` or `minus_di` is exactly `0.0` (a valid directional indicator value), the condition evaluates to `False` and falls through to `direction_bias = 0.5` instead of correctly comparing the two values. While a DI of exactly 0 is rare, it's a correctness bug — the intent is to check for data availability, not value truthiness.
**Fix:**
```python
if plus_di is not None and minus_di is not None:
    direction_bias = 1.0 if plus_di > minus_di else 0.3
else:
    direction_bias = 0.5
```

### WR-02: `date.today()` Is Timezone-Sensitive — May Cause Off-by-One Date on UTC Servers

**File:** `backend/app/services/discovery_service.py:135` (also lines 199, 276)
**Issue:** `date.today()` returns the date in the server's local timezone. The project scheduler is configured for `Asia/Ho_Chi_Minh` (UTC+7), but if the server or container runs in UTC (common on Render, AWS, etc.), `date.today()` at 22:00 UTC (05:00 Vietnam next day) returns yesterday's date in Vietnam time. This affects `score_date` (scores tagged to wrong date), cleanup cutoff (off by a day), and volume lookback window. The job chain runs after market close (~15:30 ICT = 08:30 UTC), so the risk is low during normal chained execution, but manual/ad-hoc runs at unusual hours could hit this.
**Fix:**
```python
from zoneinfo import ZoneInfo

# At the top of score_all_tickers or as a class method:
def _today_vn() -> date:
    """Current date in Vietnam timezone."""
    from datetime import datetime
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()

# Then replace all date.today() calls:
today = self._today_vn()  # line 135
cutoff = self._today_vn() - timedelta(days=self.RETENTION_DAYS)  # line 199
cutoff_date = self._today_vn() - timedelta(days=30)  # line 276
```

## Info

### IN-01: Misleading Comment on `dimensions_scored` Default

**File:** `backend/app/models/discovery_result.py:36`
**Issue:** Comment says "How many dimensions were scoreable (2-6)" but `server_default="0"`. The service enforces `MIN_DIMENSIONS = 2` before inserting, so 0 is never written in practice, but the comment range doesn't match the DB schema's allowed range. A reader might be confused about whether 0 or 1 are valid.
**Fix:** Change comment to:
```python
# How many dimensions were scoreable (0-6 at DB level; service enforces >= 2)
```

### IN-02: Docstring Says "20-day Average" but Lookback Is 30 Calendar Days

**File:** `backend/app/services/discovery_service.py:272-276`
**Issue:** The docstring says "Fetch 20-day average volume" but `cutoff_date` uses `timedelta(days=30)`. The intent is likely 30 calendar days ≈ 20 trading days, but the docstring is misleading for anyone reading the code.
**Fix:**
```python
async def _fetch_avg_volumes(self, ticker_ids: list[int]) -> dict[int, int | None]:
    """Fetch ~20-trading-day average volume (30 calendar day lookback) for all tickers."""
```

### IN-03: Cleanup Commits Independently from Scoring

**File:** `backend/app/services/discovery_service.py:203`
**Issue:** `_cleanup_old_results` calls `await self.session.commit()` independently, putting cleanup and scoring in separate transactions. If scoring fails after cleanup succeeds, old results are already deleted but new scores aren't written. This is not a real bug since cleanup is idempotent (only deletes data >14 days old), and a re-run will re-score. However, consolidating into a single transaction would be cleaner — the caller `score_all_tickers` already commits at line 187.
**Fix:** Remove the commit from `_cleanup_old_results` and let the caller manage the transaction:
```python
async def _cleanup_old_results(self) -> int:
    """Delete discovery results older than 14 days. Returns rows deleted."""
    cutoff = date.today() - timedelta(days=self.RETENTION_DAYS)
    stmt = delete(DiscoveryResult).where(DiscoveryResult.score_date < cutoff)
    result = await self.session.execute(stmt)
    return result.rowcount
    # Commit handled by caller (score_all_tickers)
```

---

_Reviewed: 2025-07-23T19:30:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

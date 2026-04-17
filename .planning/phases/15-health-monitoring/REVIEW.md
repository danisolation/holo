---
phase: 15-health-monitoring
reviewed: 2025-07-18T12:00:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - backend/app/models/gemini_usage.py
  - backend/app/services/gemini_usage_service.py
  - backend/app/services/health_alert_service.py
  - backend/app/services/ai_analysis_service.py
  - backend/app/services/health_service.py
  - backend/app/api/health.py
  - backend/app/schemas/health.py
  - backend/app/scheduler/manager.py
  - backend/app/scheduler/jobs.py
  - backend/app/telegram/formatter.py
  - backend/alembic/versions/009_gemini_usage_table.py
  - frontend/src/components/gemini-usage-card.tsx
  - frontend/src/components/pipeline-timeline.tsx
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
  - frontend/src/app/dashboard/health/page.tsx
  - backend/tests/test_gemini_usage.py
findings:
  critical: 0
  warning: 3
  info: 2
  total: 5
status: issues_found
---

# Phase 15: Code Review Report

**Reviewed:** 2025-07-18T12:00:00Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 15 adds three capabilities: (1) Gemini API usage tracking with a new model/service/endpoint, (2) pipeline execution timeline for Gantt-style visualization, and (3) proactive Telegram health alerts with cooldown logic. The implementation is generally solid — good separation of concerns, defensive error handling in `_record_usage`, proper HTML escaping in Telegram alerts, and comprehensive tests. Test coverage is strong across model, service, and endpoint layers.

Three warnings were found: a misleading stale-data alert message that claims a data age it hasn't verified, a confusing variable double-assignment in the error rate query, and a pre-existing null-safety gap in the AI analysis service that prevents the new usage recording from executing when `usage_metadata` is None. Two info items flag minor code quality patterns.

No critical or security issues were found.

## Warnings

### WR-01: Misleading Stale Data Alert Message

**File:** `backend/app/services/health_alert_service.py:108-114`
**Issue:** The `_check_stale_data` method triggers for any data source where `is_stale` is True (meaning age > `threshold_hours`), but the alert message reports `>threshold_hours * 2`. For example, a data source with a 48-hour threshold that is 50 hours old will generate an alert saying `>96h`, which is factually incorrect. The docstring says "Find data sources that are stale beyond 2× their threshold" but the code checks only `is_stale` (1× threshold).

**Fix:** Either implement the actual 2× check, or fix the message to reflect what's actually detected:

Option A — Fix the message to match behavior (recommended, simpler):
```python
stale_sources.append(
    f"{item['data_type']} (>{item['threshold_hours']}h)"
)
```

Option B — Implement actual 2× check as the docstring describes:
```python
async def _check_stale_data(self) -> list[str]:
    """Find data sources that are stale beyond 2× their threshold."""
    hs = HealthService(self.session)
    freshness = await hs.get_data_freshness()

    stale_sources = []
    now_utc = datetime.now(timezone.utc)
    for item in freshness:
        if item["latest"] is not None:
            from datetime import datetime as dt_mod
            latest = dt_mod.fromisoformat(item["latest"])
            if latest.tzinfo is None:
                latest = latest.replace(tzinfo=timezone.utc)
            age_hours = (now_utc - latest).total_seconds() / 3600
            double_threshold = item["threshold_hours"] * 2
            if age_hours > double_threshold:
                stale_sources.append(
                    f"{item['data_type']} (>{double_threshold}h)"
                )
    return stale_sources
```

### WR-02: Confusing Double Assignment With Misleading Variable Name

**File:** `backend/app/services/health_service.py:101`
**Issue:** The line `since = now_utc = datetime.now(timezone.utc) - timedelta(days=days)` creates a variable `now_utc` that is not the current time — it's the same past timestamp as `since`. While `now_utc` is unused and causes no runtime bug, the name is actively misleading and could cause future bugs if someone references `now_utc` expecting the current time (as is done elsewhere in this same file, e.g., line 69).

**Fix:** Remove the unused `now_utc` alias:
```python
since = datetime.now(timezone.utc) - timedelta(days=days)
```

### WR-03: `_record_usage` Unreachable When `usage_metadata` is None

**File:** `backend/app/services/ai_analysis_service.py:674-677` (and 704-707, 733-736, 762-765)
**Issue:** The new `_record_usage` method correctly handles `usage_metadata=None` via `getattr(response, "usage_metadata", None)`. However, the `logger.debug` call immediately before it (e.g., line 674-675) accesses `response.usage_metadata.total_token_count` directly, which will raise `AttributeError` if `response.usage_metadata` is None. This means `_record_usage` will never be called in that case — the exception propagates up the call stack and the usage row is lost.

This is a pre-existing pattern in the debug logging, but it now affects the new usage tracking functionality.

**Fix:** Guard the debug log the same way `_record_usage` does:
```python
response = await self._call_gemini(prompt, TechnicalBatchResponse, temp, sys_instr)
usage_meta = getattr(response, "usage_metadata", None)
if usage_meta:
    logger.debug(
        f"Gemini technical tokens: {usage_meta.total_token_count}"
    )
await self._record_usage("technical", len(ticker_data), response)
```

Apply the same pattern to lines 704-707 (fundamental), 733-736 (sentiment), and 762-765 (combined).

## Info

### IN-01: Hardcoded `max_overflow=3` Magic Number

**File:** `backend/app/api/health.py:67` and `backend/app/api/health.py:122`
**Issue:** The value `3` appears in two places — `DbPoolResponse(max_overflow=3)` and the `pool_available` formula `(3 - pool.overflow())`. While it matches the current `database.py` configuration, it's duplicated and would silently become wrong if the pool config changes.

**Fix:** Extract from the engine's pool or use a shared constant:
```python
# At module level or from config
from app.database import engine
# In the endpoint:
max_overflow = engine.pool._max_overflow  # SQLAlchemy internal
# Or define a constant alongside the database config
```

### IN-02: Dynamic SQL in `get_data_freshness` Uses f-string

**File:** `backend/app/services/health_service.py:73-74`
**Issue:** `text(f"SELECT MAX({col}) as latest FROM {table}")` uses f-string interpolation for table and column names. These come from the hardcoded `_FRESHNESS_SOURCES` tuple, so there is no injection risk today. However, this pattern is fragile — if someone later adds user-controlled values to `_FRESHNESS_SOURCES`, it becomes a SQL injection vector. Adding a comment or assertion documenting this safety assumption would help.

**Fix:** Add an inline comment for future maintainers:
```python
# SAFETY: table/col come from hardcoded _FRESHNESS_SOURCES — never user input
result = await self.session.execute(
    text(f"SELECT MAX({col}) as latest FROM {table}")
)
```

---

_Reviewed: 2025-07-18T12:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

---
phase: 14-corporate-actions-enhancements
reviewed: 2026-04-17T20:23:12Z
depth: standard
files_reviewed: 26
files_reviewed_list:
  - backend/app/models/corporate_event.py
  - backend/app/crawlers/corporate_event_crawler.py
  - backend/app/services/corporate_action_service.py
  - backend/app/services/exdate_alert_service.py
  - backend/app/services/price_service.py
  - backend/app/api/corporate_events.py
  - backend/app/api/tickers.py
  - backend/app/api/router.py
  - backend/app/scheduler/manager.py
  - backend/app/scheduler/jobs.py
  - backend/app/telegram/formatter.py
  - backend/alembic/versions/008_corporate_actions_enhancements.py
  - backend/tests/test_corporate_actions.py
  - backend/tests/test_corporate_actions_enhancements.py
  - backend/tests/test_exdate_alerts.py
  - backend/tests/test_corporate_events_api.py
  - backend/tests/test_scheduler.py
  - frontend/src/app/dashboard/corporate-events/page.tsx
  - frontend/src/components/corporate-events-calendar.tsx
  - frontend/src/components/dilution-badge.tsx
  - frontend/src/components/candlestick-chart.tsx
  - frontend/src/components/ui/popover.tsx
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
  - frontend/src/app/ticker/[symbol]/page.tsx
  - frontend/src/app/globals.css
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 14: Code Review Report

**Reviewed:** 2026-04-17T20:23:12Z
**Depth:** standard
**Files Reviewed:** 26
**Status:** issues_found

## Summary

Phase 14 adds corporate actions enhancements: RIGHTS_ISSUE event type, ex-date Telegram alerts, a corporate events calendar API/UI, and an adjusted/raw price toggle. The implementation is solid overall — clean architecture, proper deduplication patterns, comprehensive test coverage, and good input validation on the API.

Three warnings found: a timezone-sensitive date comparison in the alert service, inconsistent OHLC data when the adjusted price toggle is enabled, and dead code in the alert update path. Three info items for minor cleanups.

No critical security or data-loss issues found.

## Warnings

### WR-01: `date.today()` uses server timezone — alerts may fire on wrong day

**File:** `backend/app/services/exdate_alert_service.py:59`
**Issue:** `date.today()` returns the server's local date, not Vietnam time. The scheduler is configured with `timezone="Asia/Ho_Chi_Minh"`, but `date.today()` doesn't respect that. If the backend runs on a UTC server (e.g., cloud deployment), between 00:00–07:00 UTC (= 07:00–14:00 VN), `date.today()` returns the previous day in UTC while Vietnam is already in the next calendar day. This means ex-date alerts could check the wrong date window — missing alerts that should fire today or including alerts a day early.

**Fix:**
```python
# At top of file
from zoneinfo import ZoneInfo

# In check_upcoming_exdates (line 59)
today = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()
```

### WR-02: Adjusted price toggle produces invalid candlestick data

**File:** `backend/app/api/tickers.py:121-131`
**Issue:** When `adjusted=True`, the `close` field uses `adjusted_close` while `open`, `high`, `low` remain raw. After a large corporate event (e.g., stock dividend ratio=30 → factor=0.77), the adjusted close can be 23% below the raw close. This creates candlesticks where the close falls below the low — a visually impossible and misleading candle shape. The frontend chart at `candlestick-chart.tsx:100-108` renders these mixed values directly.

Example: pre-event candle raw OHLC = (100k, 105k, 95k, 100k). With 0.77 adjustment, chart sees (100k, 105k, 95k, 77k) — close below low.

**Fix:** Either adjust all OHLC values in `CorporateActionService` (not just close), or document this as a known limitation and add a note in the API response. The cleanest fix is to compute adjusted OHLC:
```python
# In corporate_action_service.py _compute_adjusted_prices:
# Change to select all OHLC columns and adjust them all
# Then in tickers.py, when adjusted=True, return all adjusted values
```

Alternatively, as a quick mitigation in the API response:
```python
# In tickers.py get_ticker_prices, when adjusted=True, 
# also adjust open/high/low by the same ratio
adj_ratio = float(p.adjusted_close / p.close) if p.adjusted_close and p.close else 1.0
open=float(p.open * adj_ratio) if adjusted and p.adjusted_close else float(p.open),
high=float(p.high * adj_ratio) if adjusted and p.adjusted_close else float(p.high),
low=float(p.low * adj_ratio) if adjusted and p.adjusted_close else float(p.low),
```

### WR-03: Dead SELECT query before UPDATE in alert dedup path

**File:** `backend/app/services/exdate_alert_service.py:148-151`
**Issue:** Lines 148-151 execute `select(CorporateEvent).where(CorporateEvent.id == event.id)` but the result is never assigned or used. This is a no-op database round-trip. The actual update happens on lines 154-158. This appears to be leftover debug code or an incomplete ORM pattern (perhaps originally intended to load the entity for attribute mutation, then switched to a raw UPDATE).

**Fix:** Remove lines 148-151:
```python
if sent:
    # Mark alert_sent=True (dedup — T-14-04 mitigation)
    from sqlalchemy import update
    await self.session.execute(
        update(CorporateEvent)
        .where(CorporateEvent.id == event.id)
        .values(alert_sent=True)
    )
    await self.session.commit()
    alerts_sent += 1
```

## Info

### IN-01: `from sqlalchemy import update` inside loop body

**File:** `backend/app/services/exdate_alert_service.py:153`
**Issue:** The `from sqlalchemy import update` import is inside the for-loop body (executed once per alert). While Python caches module imports so this doesn't cause repeated loading, it's unconventional and obscures the module's dependencies. The `update` function is already imported at line 153 on each iteration rather than once at the top.

**Fix:** Move to top of file with other sqlalchemy imports:
```python
from sqlalchemy import select, update, func as sa_func, case
```

### IN-02: `PriceData` TypeScript interface missing `adjusted_close` field

**File:** `frontend/src/lib/api.ts:15-22`
**Issue:** The backend `PriceResponse` includes `adjusted_close: float | None`, but the frontend `PriceData` interface omits it. The field is silently dropped during deserialization. While the price toggle works via the `adjusted` query param (the `close` field is already swapped), the frontend can't access the raw `adjusted_close` value for tooltips or comparison display.

**Fix:**
```typescript
export interface PriceData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjusted_close: number | null;  // Add this
}
```

### IN-03: API parameter `type` shadows Python built-in

**File:** `backend/app/api/corporate_events.py:41`
**Issue:** The query parameter `type: str | None = Query(None, ...)` shadows Python's built-in `type()` function within the endpoint function scope. Not a bug (the function doesn't need `type()`), but hinders readability and IDE warnings.

**Fix:** Rename to `event_type` with an alias:
```python
event_type: str | None = Query(None, alias="type", description="Filter by event type"),
```

---

_Reviewed: 2026-04-17T20:23:12Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

---
phase: 44-trade-journal-p-l
reviewed: 2026-04-23T17:30:00Z
depth: standard
files_reviewed: 17
files_reviewed_list:
  - backend/alembic/versions/020_trade_journal_tables.py
  - backend/app/models/trade.py
  - backend/app/models/lot.py
  - backend/app/models/lot_match.py
  - backend/app/models/__init__.py
  - backend/app/schemas/trades.py
  - backend/app/services/trade_service.py
  - backend/app/api/trades.py
  - backend/app/api/router.py
  - backend/tests/test_trade_service.py
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
  - frontend/src/components/navbar.tsx
  - frontend/src/components/trade-stats-cards.tsx
  - frontend/src/components/trade-filters.tsx
  - frontend/src/components/trades-table.tsx
  - frontend/src/components/delete-trade-dialog.tsx
  - frontend/src/components/trade-entry-dialog.tsx
  - frontend/src/app/journal/page.tsx
findings:
  critical: 1
  warning: 3
  info: 1
  total: 5
status: issues_found
---

# Phase 44: Code Review Report

**Reviewed:** 2026-04-23T17:30:00Z
**Depth:** standard
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 44 implements a trade journal with FIFO lot matching, VN market fee calculation, and a full-stack CRUD flow across 17 files. The backend architecture (migration, models, service, API) is well-structured with proper FIFO logic, decimal precision for financial calculations, and sort/order injection whitelist. The frontend components are clean with proper loading/error/empty states, zod validation, and controlled form state.

**One critical bug found:** The `apiFetch` utility calls `res.json()` unconditionally, but the DELETE endpoint returns HTTP 204 No Content (empty body). This causes the delete flow to always throw a JSON parse error in the frontend even when the backend deletion succeeds — effectively breaking trade deletion for users.

Three additional warnings cover: incorrect HTTP status code for not-found on delete, missing pagination bounds validation, and unhandled error in the delete confirmation UI flow.

## Critical Issues

### CR-01: `apiFetch` fails on 204 No Content — delete flow broken

**File:** `frontend/src/lib/api.ts:176`
**Issue:** `apiFetch<T>()` unconditionally calls `res.json()` on all successful (2xx) responses. The backend `DELETE /trades/{id}` returns HTTP 204 No Content with an empty body. Calling `.json()` on a 204 response throws `SyntaxError: Unexpected end of JSON input`. This means every successful trade deletion appears to fail in the frontend: the `useDeleteTrade` mutation rejects, the dialog stays open, and the user sees no confirmation — even though the trade was actually deleted on the backend. On page refresh, the trade is gone, creating a confusing UX.

**Fix:** Handle 204 (and other bodyless responses) before attempting JSON parse:
```typescript
async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "Unknown error");
    throw new ApiError(res.status, `${res.status} ${res.statusText}: ${body}`);
  }

  // 204 No Content — no body to parse
  if (res.status === 204) {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}
```

## Warnings

### WR-01: Delete endpoint returns 400 instead of 404 for non-existent trade

**File:** `backend/app/services/trade_service.py:453-454` and `backend/app/api/trades.py:92-93`
**Issue:** When `delete_trade` receives a non-existent `trade_id`, the service raises `ValueError("Trade not found: {trade_id}")`, which the API handler maps to HTTP 400. A "not found" condition should return HTTP 404 per REST conventions. Currently, both "not found" and "can't delete partially consumed lot" return 400, making it impossible for the frontend to distinguish between the two error cases.
**Fix:** Use separate exception handling in the API endpoint:
```python
@router.delete("/trades/{trade_id}", status_code=204)
async def delete_trade(trade_id: int):
    async with async_session() as session:
        service = TradeService(session)
        # Check existence first
        trade = await service.get_trade(trade_id)
        if trade is None:
            raise HTTPException(status_code=404, detail=f"Trade not found: {trade_id}")
        try:
            await service.delete_trade(trade_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
```

### WR-02: No bounds validation on `page` and `page_size` query parameters

**File:** `backend/app/api/trades.py:39-46`
**Issue:** The `page` parameter has no lower bound (page=0 or page=-1 produces negative offset at line 335 of trade_service.py), and `page_size` has no upper bound (page_size=1000000 dumps the entire table in one response). While this is a personal app, unbounded pagination can cause unexpected DB load and API behavior.
**Fix:** Add validation constraints:
```python
@router.get("/trades", response_model=TradesListResponse)
async def list_trades(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ticker: str | None = None,
    side: str | None = None,
    sort: str = "trade_date",
    order: str = "desc",
):
```

### WR-03: Missing error handling in delete confirmation flow

**File:** `frontend/src/app/journal/page.tsx:62-67`
**Issue:** `handleDeleteConfirm` calls `await deleteMutation.mutateAsync(deleteTarget.id)` without a try/catch. If the mutation rejects (network error, 400 from backend, or the CR-01 JSON parse error), the promise rejection is unhandled — the dialog stays open with no error feedback to the user. The `setDeleteDialogOpen(false)` and `setDeleteTarget(null)` lines never execute.
**Fix:** Wrap in try/catch with user-facing error feedback:
```typescript
async function handleDeleteConfirm() {
  if (!deleteTarget) return;
  try {
    await deleteMutation.mutateAsync(deleteTarget.id);
    setDeleteDialogOpen(false);
    setDeleteTarget(null);
  } catch {
    // Error is available via deleteMutation.error
    // Dialog stays open — user can retry or cancel
  }
}
```
Also consider displaying `deleteMutation.error` in the `DeleteTradeDialog` component.

## Info

### IN-01: LIKE wildcard characters not escaped in ticker filter

**File:** `backend/app/services/trade_service.py:319`
**Issue:** The ticker filter `Ticker.symbol.ilike(f"%{ticker}%")` doesn't escape `%` and `_` characters in user input. A user entering `%` as the ticker filter would match all tickers. While SQLAlchemy properly parameterizes the value (no SQL injection), the LIKE wildcards in user input could produce unexpected filter results. Very low risk for a personal app.
**Fix:** Escape LIKE special characters before interpolating:
```python
escaped = ticker.replace("%", r"\%").replace("_", r"\_")
base_query = base_query.where(Ticker.symbol.ilike(f"%{escaped}%"))
```

---

_Reviewed: 2026-04-23T17:30:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

---
phase: 54-sector-grouping-heatmap-rework
reviewed: 2025-07-18T12:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - backend/app/models/user_watchlist.py
  - backend/app/api/watchlist.py
  - backend/app/api/tickers.py
  - backend/app/schemas/watchlist.py
  - backend/tests/test_watchlist_sector.py
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
  - frontend/src/components/sector-combobox.tsx
  - frontend/src/components/watchlist-table.tsx
  - frontend/src/app/page.tsx
findings:
  critical: 0
  warning: 2
  info: 2
  total: 4
status: issues_found
---

# Phase 54: Code Review Report

**Reviewed:** 2025-07-18T12:00:00Z
**Depth:** standard
**Files Reviewed:** 9 (note: config listed `backend/app/routers/watchlist.py`, `backend/app/routers/tickers.py`, `frontend/src/hooks/use-watchlist.ts`, `frontend/src/components/watchlist/sector-combobox.tsx`, and `frontend/src/components/watchlist/watchlist-table.tsx` — these paths don't exist; the actual implementations live at `backend/app/api/watchlist.py`, `backend/app/api/tickers.py`, `frontend/src/lib/hooks.ts`, `frontend/src/components/sector-combobox.tsx`, and `frontend/src/components/watchlist-table.tsx` respectively)
**Status:** issues_found

## Summary

Phase 54 adds sector grouping to the watchlist: a `sector_group` column on `UserWatchlist`, a PATCH endpoint for updating it, auto-population from `Ticker.sector` on POST, a `GET /tickers/sectors` endpoint for sector suggestions, and frontend components (SectorCombobox, heatmap sector override).

Overall implementation is solid. The backend PATCH/POST/GET chain is clean, schemas have proper validation, and the frontend hooks correctly invalidate caches on mutation. Two functional warnings and two quality items were found. No security issues detected — SQLAlchemy parameterized queries prevent injection, symbol inputs are normalized, and the single-user no-auth model is consistent with project constraints.

## Warnings

### WR-01: `migrate_watchlist` skips `sector_group` auto-population (inconsistency with `add_to_watchlist`)

**File:** `backend/app/api/watchlist.py:178-184`
**Issue:** The `add_to_watchlist` endpoint (line 108-115) auto-populates `sector_group` from `Ticker.sector` when no sector is provided. However, `migrate_watchlist` creates entries with `sector_group=None` unconditionally. Users migrating from localStorage will have all their items missing sector tags until they manually assign each one (or re-add items individually).
**Fix:** Add the same Ticker.sector lookup inside the migration loop:
```python
for raw_symbol in body.symbols:
    symbol = raw_symbol.upper().strip()
    if not symbol or symbol in existing_symbols:
        continue
    # Auto-populate sector_group from Ticker.sector
    sector = None
    ticker_stmt = select(Ticker.sector).where(Ticker.symbol == symbol)
    ticker_result = await session.execute(ticker_stmt)
    ticker_sector = ticker_result.scalar_one_or_none()
    if ticker_sector:
        sector = ticker_sector
    entry = UserWatchlist(symbol=symbol, sector_group=sector)
    session.add(entry)
    existing_symbols.add(symbol)
```
Alternatively, batch the lookup with an `IN` query before the loop for efficiency.

### WR-02: Watchlist items not in market data silently disappear from table

**File:** `frontend/src/components/watchlist-table.tsx:49-55`
**Issue:** The `rows` computation joins `watchlistData` to `marketData` via symbol lookup (line 53-54). Any watchlist symbol that lacks a matching entry in market data (e.g., delisted ticker, ticker added before market data loads, or ticker not in HOSE active set) is silently filtered out. The user sees fewer rows than their actual watchlist count with no indication of missing items.
**Fix:** Include watchlist items even when market data is missing, using fallback values:
```typescript
const rows = useMemo(() => {
  if (!marketData || !watchlistData) return [];
  const marketMap = new Map(marketData.map((t) => [t.symbol, t]));
  return watchlistData.map((w) => {
    const market = marketMap.get(w.symbol);
    return market ?? {
      symbol: w.symbol,
      name: w.symbol,  // fallback — no name available
      sector: null,
      exchange: "HOSE",
      market_cap: null,
      last_price: null,
      change_pct: null,
    } as MarketTicker;
  });
}, [marketData, watchlistData]);
```
This ensures the delete button and sector combobox remain accessible for orphaned items.

## Info

### IN-01: Test mock side effects use fragile `setattr or setattr` idiom

**File:** `backend/tests/test_watchlist_sector.py:140-141, 167-168`
**Issue:** The mock `refresh` side effects chain two `setattr` calls using `or`:
```python
side_effect=lambda obj: setattr(obj, 'created_at', ...) or
                        setattr(obj, 'sector_group', ...)
```
This relies on `setattr` always returning `None` (falsy) so the `or` evaluates both operands. While technically correct, it's non-obvious and fragile — a reader unfamiliar with the pattern may not understand why `or` is used instead of a proper function body.
**Fix:** Use a named helper function or a multi-statement lambda wrapper:
```python
def mock_refresh(obj):
    obj.created_at = created_entry.created_at
    obj.sector_group = "Thực phẩm & Đồ uống"

mock_session.refresh = AsyncMock(side_effect=mock_refresh)
```

### IN-02: `useMemo` columns dependency array includes mutation objects

**File:** `frontend/src/components/watchlist-table.tsx:245`
**Issue:** The columns `useMemo` dependency array includes `removeMutation` and `updateSectorMutation`. These mutation objects update their internal state (e.g., `isPending`, `data`) on each mutation cycle, which can trigger unnecessary recomputation of the entire column definition array even when the column logic hasn't changed. With `@tanstack/react-query` v5 the mutation hook returns a new object reference on state changes.
**Fix:** Use `useCallback` for the mutation handlers and reference only the stable `.mutate` function, or extract mutation calls into stable refs:
```typescript
const handleRemove = useCallback((symbol: string) => {
  removeMutation.mutate(symbol);
}, [removeMutation.mutate]);
```
Then use `handleRemove` in the column cell renderer and exclude `removeMutation` from the deps array.

---

_Reviewed: 2025-07-18T12:00:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: standard_

---
phase: 13-portfolio-enhancements
reviewed: 2025-07-19T21:30:00Z
depth: deep
files_reviewed: 17
files_reviewed_list:
  - backend/app/api/portfolio.py
  - backend/app/schemas/portfolio.py
  - backend/app/services/csv_import_service.py
  - backend/app/services/portfolio_service.py
  - backend/tests/test_csv_import.py
  - backend/tests/test_portfolio.py
  - frontend/src/app/dashboard/portfolio/page.tsx
  - frontend/src/components/allocation-chart.tsx
  - frontend/src/components/csv-import-dialog.tsx
  - frontend/src/components/csv-preview-table.tsx
  - frontend/src/components/performance-chart.tsx
  - frontend/src/components/portfolio-summary.tsx
  - frontend/src/components/trade-delete-confirm.tsx
  - frontend/src/components/trade-edit-dialog.tsx
  - frontend/src/components/trade-history.tsx
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
findings:
  critical: 0
  high: 2
  medium: 2
  low: 2
  total: 6
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2025-07-19T21:30:00Z
**Depth:** deep (cross-file analysis, financial math verification, API contract tracing)
**Files Reviewed:** 17
**Status:** issues_found

## Summary

Phase 13 adds dividend income computation, performance/allocation charts, trade edit/delete with FIFO recalculation, and CSV import from VNDirect/SSI formats. The implementation is well-structured overall: FIFO recalculation logic is solid, the CSV format auto-detection and validation pipeline is thorough, frontend mutation hooks correctly invalidate all dependent queries, and the API endpoints have proper schema validation via Pydantic.

Two HIGH-severity issues were found: (1) dividend income uses current lot state instead of historical position at the record date, producing incorrect financial results when shares are sold after a dividend, and (2) CSV bulk import commits each trade individually via `record_trade()`, so partial failures leave the database in an inconsistent state. Two MEDIUM issues relate to defensive input handling.

## High Issues

### HIGH-01: Dividend income calculation uses current `remaining_quantity` instead of historical position

**File:** `backend/app/services/portfolio_service.py:266-278`
**Issue:** `get_dividend_income()` queries lots with `Lot.remaining_quantity > 0` and multiplies `event.dividend_amount * lot.remaining_quantity`. Both the filter and the multiplier use the **current** lot state, not the position held at the dividend's `record_date`. If shares are sold after a dividend record date, the dividend income is under-reported. If the lot is fully sold, it's excluded entirely — reporting zero dividend even though the investor held shares on the record date.

**Example:** BUY 200 VNM on Jan 1 → dividend record_date Jun 15 (1500₫/share) → SELL 200 on Aug 1. Correct dividend = 200 × 1500 = 300,000₫. Current code returns 0₫ (lot excluded because `remaining_quantity = 0`).

**Fix:** Compute the quantity held at each record_date by considering sells that occurred before that date. A minimal fix that improves accuracy:

```python
for event in events:
    # Find lots bought on or before record_date (regardless of current remaining)
    lots_stmt = (
        select(Lot)
        .where(
            Lot.ticker_id == ticker_id,
            Lot.buy_date <= event.record_date,
        )
    )
    lots_result = await self.session.execute(lots_stmt)
    lots = lots_result.scalars().all()

    # Compute total sold before record_date for this ticker
    sold_before_stmt = (
        select(func.coalesce(func.sum(Trade.quantity), 0))
        .where(
            Trade.ticker_id == ticker_id,
            Trade.side == "SELL",
            Trade.trade_date <= event.record_date,
        )
    )
    sold_result = await self.session.execute(sold_before_stmt)
    total_sold_before = int(sold_result.scalar_one())

    # FIFO: deduct sold shares from oldest lots first
    remaining_sold = total_sold_before
    for lot in sorted(lots, key=lambda l: (l.buy_date, l.id)):
        held = lot.quantity  # original quantity, not current remaining
        consumed = min(held, remaining_sold)
        held_on_record = held - consumed
        remaining_sold -= consumed
        total_income += event.dividend_amount * held_on_record
```

### HIGH-02: CSV import lacks atomicity — partial failures leave committed trades

**File:** `backend/app/services/csv_import_service.py:254-268` / `backend/app/services/portfolio_service.py:77`
**Issue:** `import_trades()` calls `portfolio_service.record_trade()` for each valid CSV row. `record_trade()` calls `self.session.commit()` after each individual trade (line 77). If the 30th trade out of 50 fails (e.g., a SELL exceeds available shares), the first 29 trades are already committed and cannot be rolled back. The user has no indication of which trades were imported and which weren't.

**Fix:** Remove the per-trade commit in `record_trade` when called from CSV import. Either:

(a) Add a `commit` parameter to `record_trade`:
```python
async def record_trade(self, ..., auto_commit: bool = True) -> dict:
    ...
    if auto_commit:
        await self.session.commit()
    else:
        await self.session.flush()
    ...
```

Then in `csv_import_service.py`:
```python
for row, preview in zip(rows, preview_rows):
    if preview.status == "error":
        continue
    await portfolio_service.record_trade(..., auto_commit=False)
    trades_imported += 1

# Single commit for all trades
await self.session.commit()
```

(b) Or wrap the entire import loop in a savepoint:
```python
async with self.session.begin_nested():
    for row, preview in zip(rows, preview_rows):
        ...
```

## Medium Issues

### MED-01: File content fully read into memory before size validation

**File:** `backend/app/api/portfolio.py:170-173`
**Issue:** The CSV import endpoint reads the entire file with `await file.read()` before checking `len(content) > 5MB`. While FastAPI's multipart parsing buffers the upload regardless, this pattern is a defense-in-depth gap. A client can POST large bodies without the multipart `Content-Length` being validated at the framework level.

**Fix:** Check `file.size` before reading (FastAPI UploadFile exposes the content-length header), or add an `app.add_middleware(...)` with max body size, or read in chunks:

```python
# Check declared size first (if available)
if file.size and file.size > 5 * 1024 * 1024:
    raise HTTPException(status_code=400, detail="File too large. Maximum 5MB.")

content = await file.read()

# Still validate actual size (defense-in-depth)
if len(content) > 5 * 1024 * 1024:
    raise HTTPException(status_code=400, detail="File too large. Maximum 5MB.")
```

### MED-02: VNDirect price column matching is overly greedy

**File:** `backend/app/services/csv_import_service.py:89`
**Issue:** The condition `"giá" in h` matches any header containing the Vietnamese word "giá" (price). If a VNDirect export includes additional columns like "Giá trị GD" (transaction value) or "Giá khớp lệnh" (matched price), the last matching column would overwrite the price mapping. Since headers are iterated sequentially, the final "giá"-containing column wins.

**Fix:** Use more specific matching and prioritize exact match:

```python
elif h == "giá" or h == "giá khớp":
    col_map["price"] = i
```

Or match with a boundary check:
```python
elif h in ("giá", "giá khớp", "giá khớp lệnh"):
    col_map["price"] = i
```

## Low Issues

### LOW-01: Fragile result handling in performance data price query

**File:** `backend/app/services/portfolio_service.py:320-331`
**Issue:** The query `select(DailyPrice)` with `.all()` returns Row tuples `(DailyPrice,)`, not bare ORM objects. The code compensates with `hasattr(row, "ticker_id")` branching and `row[0] if len(row) == 1` fallback. This is fragile and unnecessarily complex.

**Fix:** Use `.scalars().all()` to unwrap ORM objects directly:

```python
price_rows = prices_result.scalars().all()

for p in price_rows:
    price_lookup[(p.ticker_id, p.date)] = p.close
    all_dates.add(p.date)
```

### LOW-02: `useCallback` dependencies defeat memoization in CSVImportDialog

**File:** `frontend/src/components/csv-import-dialog.tsx:41-49`
**Issue:** `resetAll` is wrapped in `useCallback` with `[dryRunMutation, importMutation]` as dependencies. These mutation objects from `useMutation` change reference on every render, so the callback is recreated every render — the `useCallback` provides no memoization benefit.

**Fix:** Reference only the stable `.reset` methods, or remove `useCallback` since the function is only called on dialog close (no performance concern):

```typescript
const resetAll = () => {
  setStep(1);
  setFile(null);
  setFileSizeError(null);
  setDryRunResult(null);
  setImportError(null);
  dryRunMutation.reset();
  importMutation.reset();
};
```

## Notable Positives

- **FIFO recalculation** (`recalculate_lots`): Clean delete-and-replay approach with proper validation that SELL qty doesn't exceed available during replay (T-13-03 mitigation).
- **CSV validation pipeline**: Comprehensive per-row validation (symbol exists, qty > 0, price > 0, future date check, side check, duplicate detection). The dry-run preview pattern is user-friendly.
- **Mutation invalidation**: All mutation hooks (`useUpdateTrade`, `useDeleteTrade`, `useCSVImport`) correctly invalidate all five dependent query keys (holdings, summary, trades, performance, allocation).
- **MAX_CSV_ROWS = 1000** row limit (T-13-05) and 5MB file size limit (T-13-08) are good defense-in-depth measures.
- **Pydantic schema validation**: `TradeRequest` and `TradeUpdateRequest` use `gt=0`, `ge=0`, `min_length`, `pattern` constraints — solid server-side input validation.

---

_Reviewed: 2025-07-19T21:30:00Z_
_Reviewer: the agent (gsd-code-reviewer)_
_Depth: deep_

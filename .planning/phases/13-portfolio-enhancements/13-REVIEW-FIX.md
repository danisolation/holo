---
phase: 13-portfolio-enhancements
fixed_at: 2025-07-19T22:00:00Z
review_path: .planning/phases/13-portfolio-enhancements/13-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 13: Code Review Fix Report

**Fixed at:** 2025-07-19T22:00:00Z
**Source review:** .planning/phases/13-portfolio-enhancements/13-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (2 HIGH, 2 MEDIUM)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### HIGH-01: Dividend income calculation uses current `remaining_quantity` instead of historical position

**Files modified:** `backend/app/services/portfolio_service.py`, `backend/tests/test_portfolio.py`
**Commits:** `72ebbd6`, `bf620ec`
**Applied fix:** Rewrote `get_dividend_income()` to compute the historical position held at each dividend's `record_date`. Instead of filtering lots by `remaining_quantity > 0` and multiplying by current `remaining_quantity`, the method now:
1. Queries ALL lots bought on or before the record_date (regardless of current remaining)
2. Queries total SELL quantity for the ticker on or before the record_date
3. FIFO-deducts sold shares from oldest lots first to compute actual shares held on the record_date
4. Multiplies `dividend_amount × held_on_record` for each lot

This correctly handles the case where shares are sold after a dividend record date — the dividend income is still counted based on the position at record_date.

Updated 3 unit tests (`test_dividend_income_basic`, `test_dividend_income_multiple_events`, `test_dividend_income_skips_lots_bought_after_record_date`) to mock the additional `sold_before` query and use `lot.quantity` (original) instead of `lot.remaining_quantity`.

### HIGH-02: CSV import lacks atomicity — partial failures leave committed trades

**Files modified:** `backend/app/services/portfolio_service.py`, `backend/app/services/csv_import_service.py`
**Commit:** `4d1d181`
**Applied fix:** Added `auto_commit: bool = True` parameter to `record_trade()`. When `True` (default, preserving existing behavior for single-trade API calls), it commits after each trade. When `False`, it flushes instead — making the trade visible within the session but not committed.

In `csv_import_service.py`, `import_trades()` now:
1. Passes `auto_commit=False` to each `record_trade()` call
2. Wraps the entire loop in try/except
3. Issues a single `await self.session.commit()` after all trades succeed
4. On any failure, calls `await self.session.rollback()` and re-raises — ensuring atomicity

### MED-01: File content fully read into memory before size validation

**Files modified:** `backend/app/api/portfolio.py`
**Commit:** `5824eca`
**Applied fix:** Added an early check of `file.size` (FastAPI UploadFile's declared Content-Length) before reading file content into memory. If `file.size` exceeds 5MB, the request is rejected immediately without reading. The existing post-read `len(content)` check is preserved as defense-in-depth against spoofed Content-Length headers.

### MED-02: VNDirect price column matching is overly greedy

**Files modified:** `backend/app/services/csv_import_service.py`
**Commit:** `cbbc97f`
**Applied fix:** Replaced the greedy `"giá" in h` substring check with an exact-match whitelist: `h in ("giá", "giá khớp", "giá khớp lệnh")`. This prevents unrelated columns like "Giá trị GD" (transaction value) from overwriting the price column mapping.

## Verification

All 264 tests pass after all fixes applied (`python -m pytest tests/ -x -q` → 264 passed).

---

_Fixed: 2025-07-19T22:00:00Z_
_Fixer: the agent (gsd-code-fixer)_
_Iteration: 1_

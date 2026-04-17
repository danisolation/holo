---
phase: 12-multi-market-foundation
fixed_at: 2025-07-19T18:30:00Z
review_path: .planning/phases/12-multi-market-foundation/12-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 12: Code Review Fix Report

**Fixed at:** 2025-07-19  
**Source review:** `.planning/phases/12-multi-market-foundation/12-REVIEW.md`  
**Iteration:** 1

**Summary:**
- Findings in scope: 4
- Fixed: 4
- Skipped: 0

## Fixed Issues

### HIGH-01: On-demand analysis endpoint has no server-side rate limiting

**Files modified:** `backend/app/api/analysis.py`  
**Commit:** `632e295`  
**Applied fix:** Added a server-side 5-minute cooldown check in the `POST /{symbol}/analyze-now` endpoint. Before triggering background analysis, the handler queries `ai_analyses` for any record with `created_at >= now - 5 minutes` for the given ticker. If found, returns HTTP 429 with a descriptive message. Also added `datetime`, `timedelta`, `timezone` imports to the module.

### HIGH-02: `analyze_single_ticker` acquires lock 4 separate times — starvation risk

**Files modified:** `backend/app/services/ai_analysis_service.py`, `backend/tests/test_ai_analysis_tiered.py`  
**Commits:** `57b1d41`, `ed232de`  
**Applied fix:** Restructured `analyze_single_ticker` to acquire `_gemini_lock` once and call `run_technical_analysis`, `run_fundamental_analysis`, `run_sentiment_analysis`, and `run_combined_analysis` directly under that single lock acquisition — instead of calling `analyze_all_tickers` 4 times (which acquires/releases the lock each time). Updated the corresponding test to mock the 4 `run_*_analysis` methods directly, and updated the endpoint integration test to handle the new cooldown check's second `session.execute` call.

### MED-04: `fetch_and_sync_tickers` doesn't validate exchange parameter

**Files modified:** `backend/app/services/ticker_service.py`  
**Commit:** `1a491c4`  
**Applied fix:** Added an explicit validation check at the start of `fetch_and_sync_tickers` — if `exchange` is not in `EXCHANGE_MAX_TICKERS`, raises `ValueError` with a descriptive message listing valid exchanges. Replaced the `.get(exchange, 200)` fallback with a direct dict lookup `[exchange]` since the validation guarantees the key exists.

### LOW-01: Unused `import functools` in jobs.py

**Files modified:** `backend/app/scheduler/jobs.py`  
**Commit:** `55189c1`  
**Applied fix:** Removed the unused `import functools` line. Confirmed `functools` is imported independently in `manager.py` and is not referenced through `jobs.py`.

## Verification

All 222 tests pass after all fixes (`python -m pytest tests/ -x -q` — 0 failures).

---

_Fixed: 2025-07-19_  
_Fixer: the agent (gsd-code-fixer)_  
_Iteration: 1_

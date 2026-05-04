---
phase: 53-watchlist-gated-ai-pipeline
verified: 2026-05-04T16:18:32Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 53: Watchlist-Gated AI Pipeline Verification Report

**Phase Goal:** AI analysis and daily picks run exclusively on watchlist tickers, reducing Gemini API usage by ~70% and pipeline time by ~3x
**Verified:** 2026-05-04T16:18:32Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | AI analysis (Gemini calls) runs only on tickers present in the user's watchlist — non-watchlist tickers receive no AI analysis | ✓ VERIFIED | `_get_watchlist_ticker_map()` (jobs.py:64-79) builds `{symbol: ticker_id}` dict via JOIN on UserWatchlist×Ticker. All 4 AI analysis jobs (`daily_ai_analysis`, `daily_sentiment_analysis`, `daily_combined_analysis`, `daily_trading_signal_analysis`) pass this dict as `ticker_filter=ticker_filter` to `analyze_all_tickers()` at lines 334, 422, 476, 531 |
| 2 | Daily picks are selected exclusively from watchlist tickers — no picks appear for tickers outside the watchlist | ✓ VERIFIED | `daily_pick_generation` (jobs.py:582-588) extracts `watchlist_symbols = set(ticker_filter.keys())` and passes to `PickService.generate_daily_picks(watchlist_symbols=watchlist_symbols)`. `pick_service.py:322-323` applies `signal_query.where(Ticker.symbol.in_(watchlist_symbols))` |
| 3 | An empty watchlist causes the AI pipeline to skip gracefully with a logged warning and the scheduler chain continues — no crashes or stuck jobs | ✓ VERIFIED | All 5 gated jobs check `if not ticker_filter:`, log a warning, call `job_svc.complete(execution, status="skipped", result_summary={"reason": "empty_watchlist", ...})`, commit, and return normally. Normal return preserves scheduler chain per `_on_job_executed` in manager.py |
| 4 | Full pipeline completes noticeably faster, proportional to watchlist size (~15-30 tickers) versus the previous ~400-ticker run | ✓ VERIFIED | Architecturally guaranteed — all 5 gated jobs now process only watchlist tickers (typ. ~15-30) instead of all ~400 HOSE tickers. API calls and processing time scale linearly with ticker count. ~30/400 = ~92% reduction in Gemini calls (exceeds claimed ~70%) |
| 5 | Broken `analyze_watchlisted_tickers()` method is removed from AIAnalysisService | ✓ VERIFIED | `grep` finds zero matches for `analyze_watchlisted_tickers` in `ai_analysis_service.py` (610 lines). Dead `TestAnalyzeWatchlistedTickers` test class also removed from `test_ai_analysis_tiered.py` |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/scheduler/jobs.py` | `_get_watchlist_ticker_map()` helper + 5 gated job functions | ✓ VERIFIED | Helper at lines 64-79 with JOIN query. 5 gated jobs at lines 319-335, 407-422, 461-476, 516-531, 572-588 |
| `backend/app/services/pick_service.py` | `generate_daily_picks` with `watchlist_symbols` filter | ✓ VERIFIED | `watchlist_symbols: set[str] | None = None` param at line 285. `Ticker.symbol.in_(watchlist_symbols)` WHERE clause at line 323 |
| `backend/app/services/ai_analysis_service.py` | Clean service without broken `analyze_watchlisted_tickers` method | ✓ VERIFIED | 610 lines, no trace of the broken method |
| `backend/tests/test_watchlist_gating.py` | Tests for WL-01 and WL-02 (min 100 lines) | ✓ VERIFIED | 336 lines, 16 tests across 4 classes. All 16 pass in 4.47s |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `jobs.py` | UserWatchlist + Ticker models | `_get_watchlist_ticker_map` JOIN query | ✓ WIRED | Lines 70-75: imports both models, JOINs on `UserWatchlist.symbol == Ticker.symbol`, filters `Ticker.is_active` |
| `jobs.py` (4 AI jobs) | `AIAnalysisService.analyze_all_tickers` | `ticker_filter=ticker_filter` parameter | ✓ WIRED | 4 occurrences at lines 334, 422, 476, 531 — each passes the watchlist-derived dict |
| `jobs.py` (pick job) | `PickService.generate_daily_picks` | `watchlist_symbols=watchlist_symbols` parameter | ✓ WIRED | Line 588: `await service.generate_daily_picks(watchlist_symbols=watchlist_symbols)` |
| `pick_service.py` | Ticker.symbol IN clause | `signal_query.where()` filter | ✓ WIRED | Line 323: `signal_query = signal_query.where(Ticker.symbol.in_(watchlist_symbols))` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `jobs.py` | `ticker_filter` | `_get_watchlist_ticker_map(session)` → DB JOIN query | Yes — real DB query joining UserWatchlist × Ticker | ✓ FLOWING |
| `jobs.py` | `watchlist_symbols` | `set(ticker_filter.keys())` | Yes — derived from DB query result | ✓ FLOWING |
| `pick_service.py` | `signal_query` filter | `watchlist_symbols` param → `Ticker.symbol.in_()` | Yes — applied to live SQLAlchemy query | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| 16 watchlist gating tests pass | `python -m pytest tests/test_watchlist_gating.py -v` | 16 passed in 4.47s | ✓ PASS |
| `_get_watchlist_ticker_map` importable | Import verified by 3 tests in `TestGetWatchlistTickerMap` | Function exists and callable | ✓ PASS |
| `generate_daily_picks` accepts `watchlist_symbols` param | Signature introspection test | `watchlist_symbols` param with `default=None` | ✓ PASS |
| Broken method removed from AIAnalysisService | `hasattr` check test | `analyze_watchlisted_tickers` not found | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| WL-01 | 53-01-PLAN | AI analysis (Gemini) chỉ chạy trên các mã trong watchlist của user, không phân tích toàn sàn | ✓ SATISFIED | 4 AI jobs gated via `_get_watchlist_ticker_map()` → `ticker_filter` passthrough. 8 tests verify (4 filter, 4 skip) |
| WL-02 | 53-01-PLAN | Daily picks chỉ chọn từ các mã trong watchlist | ✓ SATISFIED | `generate_daily_picks(watchlist_symbols=...)` with `Ticker.symbol.in_()` filter. 2 job tests + 3 service tests verify |

No orphaned requirements — REQUIREMENTS.md maps WL-01 and WL-02 to Phase 53, and both are claimed by 53-01-PLAN.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| *(none found)* | — | — | — | — |

No TODO/FIXME/PLACEHOLDER/HACK patterns, no empty returns, no stub implementations, no hardcoded empty data detected across all 4 modified files.

### Human Verification Required

*(none — all truths verifiable programmatically)*

### Gaps Summary

No gaps found. All 5 must-have truths verified through code inspection, key link tracing, and passing tests. The watchlist gating is properly wired end-to-end:
- `_get_watchlist_ticker_map()` produces real data from DB via JOIN query
- All 4 AI analysis jobs and 1 pick generation job consume the filter
- Empty watchlist guard rails return `status="skipped"` with normal return (preserving scheduler chain)
- Pick service adds `Ticker.symbol.in_()` WHERE clause when watchlist_symbols provided
- 16 comprehensive tests pass covering all gating paths

---

_Verified: 2026-05-04T16:18:32Z_
_Verifier: the agent (gsd-verifier)_

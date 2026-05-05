---
phase: 58-ai-analysis-freshness
verified: 2026-05-06T18:30:00Z
status: human_needed
score: 3/3 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Verify freshness badges display correctly in watchlist table"
    expected: "Each ticker shows relative time (e.g. '2h ago', '18h ago') with muted gray for <12h and amber for ≥12h"
    why_human: "Visual styling and color distinction cannot be verified programmatically"
  - test: "Verify morning chain triggers at 8:30 AM and completes before 9:00 AM"
    expected: "After 8:30 AM ICT, watchlist tickers should have AI analysis updated with timestamps after 8:30 AM"
    why_human: "Requires running the scheduler at the correct time and observing real job execution"
---

# Phase 58: AI Analysis Freshness Verification Report

**Phase Goal:** AI analysis is fresh before market opens each trading day, and user can see how recent each analysis is
**Verified:** 2026-05-06T18:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | On weekday mornings by 9:00 AM ICT, watchlist tickers have AI analysis updated after 8:30 AM | ✓ VERIFIED | CronTrigger at hour=8, minute=30, day_of_week="mon-fri" in `manager.py:358-369`. Shortened chain routes price→indicators→AI→signals via `_on_job_executed` lines 75-103. All 4 morning jobs use watchlist gating via `_get_watchlist_ticker_map`. |
| 2 | Morning refresh completes within Gemini free tier limits (15 RPM) by running shortened chain | ✓ VERIFIED | Chain is price→indicators→AI→signals (4 steps). Skips discovery, news, sentiment, combined, picks, outcome check, loss check. AI service's existing 4s delay handles rate limiting. Watchlist gating limits scope to 10-30 tickers. |
| 3 | Dashboard shows freshness indicator per ticker with age and stale/fresh distinction | ✓ VERIFIED | `watchlist-table.tsx:38-58` has `getAnalysisFreshness()` helper computing relative time. Lines 249-271 render "AI" column with Clock icon, amber for stale (≥12h), muted-foreground for fresh (<12h), "Chưa có" for missing. `WatchlistItem.last_analysis_at` in `api.ts:101`. Backend serves `max_created_at` via subquery in `watchlist.py:42-49,60`. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/scheduler/manager.py` | Morning CronTrigger + chain routing | ✓ VERIFIED | CronTrigger at 8:30 AM Mon-Fri (line 358-369), chain routing in `_on_job_executed` (lines 75-103), 4 morning job names in `_JOB_NAMES` (lines 51-54) |
| `backend/app/scheduler/jobs.py` | Morning job functions | ✓ VERIFIED | `morning_price_crawl_hose` (line 806), `morning_indicator_compute` (line 815), `morning_ai_analysis` (line 846), `morning_trading_signal_analysis` (line 898) — all with proper job tracking, error handling, and watchlist gating |
| `backend/app/api/watchlist.py` | last_analysis_at in enriched response | ✓ VERIFIED | `latest_created` subquery with `MAX(created_at)` across all analysis types (lines 42-49), LEFT JOIN (lines 74-77), ISO timestamp in response (line 93) |
| `backend/app/schemas/watchlist.py` | last_analysis_at field | ✓ VERIFIED | `last_analysis_at: str \| None = None` on line 13 |
| `frontend/src/lib/api.ts` | WatchlistItem type with last_analysis_at | ✓ VERIFIED | `last_analysis_at: string \| null` on line 101 |
| `frontend/src/components/watchlist-table.tsx` | Freshness badge column | ✓ VERIFIED | `getAnalysisFreshness` helper (lines 38-58), "AI" column with Clock icon and amber/muted styling (lines 249-271) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `manager.py` | `jobs.py` | morning_price_crawl_hose CronTrigger → chain routing | ✓ WIRED | CronTrigger imports and registers `morning_price_crawl_hose`. `_on_job_executed` chains through all 4 morning steps with correct job IDs. |
| `watchlist.py` | `ai_analysis model` | MAX(created_at) JOIN for freshness | ✓ WIRED | `latest_created` subquery JOINs `AIAnalysis.ticker_id` with `MAX(created_at)`, result mapped to `last_analysis_at` in response. |
| `watchlist-table.tsx` | `api.ts` | WatchlistItem.last_analysis_at → freshness display | ✓ WIRED | Component accesses `watchItem?.last_analysis_at` (line 254), passes to `getAnalysisFreshness()`, renders with conditional styling. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `watchlist-table.tsx` | `watchItem?.last_analysis_at` | `useWatchlist()` → `GET /api/watchlist/` → `MAX(AIAnalysis.created_at)` | Yes — DB query via SQLAlchemy subquery | ✓ FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED (requires running server to test API endpoint)

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-----------|-------------|--------|----------|
| AI-01 | 58-01 | Morning refresh at 8:30 AM for watchlist tickers | ✓ SATISFIED | CronTrigger + 4 morning job functions with watchlist gating |
| AI-02 | 58-01 | Shortened chain respecting Gemini 15 RPM | ✓ SATISFIED | Chain: price→indicators→AI→signals (skips discovery/news/sentiment/combined/picks) |
| AI-03 | 58-02 | Dashboard freshness indicator per ticker | ✓ SATISFIED | "AI" column with relative time, amber/muted color coding, Clock icon |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No anti-patterns found | — | — |

### Human Verification Required

### 1. Freshness Badge Visual Check

**Test:** Navigate to watchlist page, verify "AI" column appears with proper styling
**Expected:** Each ticker shows Clock icon + relative time. Fresh (<12h) = gray, Stale (≥12h) = amber, Missing = "Chưa có" in amber
**Why human:** Visual styling, color contrast, and table layout need visual confirmation

### 2. Morning Chain Execution

**Test:** Wait for 8:30 AM ICT on a weekday, or manually trigger `morning_price_crawl_hose`, then verify chain completes
**Expected:** All 4 steps execute in sequence: price → indicators → AI → signals. Watchlist tickers get updated `last_analysis_at` timestamps
**Why human:** Requires real scheduler execution with Gemini API calls

### Gaps Summary

No code-level gaps found. All artifacts exist, are substantive, properly wired, and data flows from DB through API to frontend rendering. The morning chain is correctly registered, chains through 4 steps (skipping discovery/news/sentiment/combined/picks), and uses watchlist gating. The freshness indicator renders with proper visual distinction.

Human verification needed for: (1) visual appearance of freshness badges, (2) end-to-end morning chain execution at scheduled time.

---

_Verified: 2026-05-06T18:30:00Z_
_Verifier: the agent (gsd-verifier)_

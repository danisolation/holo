---
id: 260423-f6p
type: quick
title: "TIER 2 Batch A: staleTime tuning, GZip, analysis summary N+1, error states, pagination"
status: complete
completed: "2026-04-23T11:02:42Z"
duration: "3m 48s"
tasks_completed: 2
tasks_total: 2
files_modified:
  - backend/app/main.py
  - backend/app/api/analysis.py
  - frontend/src/lib/hooks.ts
  - frontend/src/lib/api.ts
  - frontend/src/app/ticker/[symbol]/page.tsx
commits:
  - hash: 54afb0e
    message: "perf(260423-f6p): GZip middleware, N+1 fix, pagination offsets"
  - hash: 16cd356
    message: "feat(260423-f6p): staleTime tuning, offset pagination, per-section error states"
key-decisions:
  - "GZip minimum_size=500 bytes to avoid compressing tiny JSON responses"
  - "ROW_NUMBER() window function for N+1 fix — single query returns latest per analysis type"
  - "Inline SectionError component rather than separate error-boundary — simpler, per-section retry"
  - "Vietnamese error text: 'Lỗi không xác định' / 'Thử lại' for consistency with existing UI"
---

# Quick Task 260423-f6p: TIER 2 Batch A Summary

Six targeted performance and UX improvements: GZip compression, N+1→1 query optimization, staleTime tuning to 60min for expensive AI hooks, offset pagination for news/indicators, and per-section error states with Vietnamese retry buttons.

## Task Completion

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Backend — GZip middleware, N+1 fix, pagination offsets | `54afb0e` | GZipMiddleware added after CORS; analysis summary query reduced from 5→1 using ROW_NUMBER() OVER PARTITION BY; offset param added to news + indicators endpoints |
| 2 | Frontend — staleTime tuning, API offset params, per-section error states | `16cd356` | useAnalysisSummary & useTradingSignal → 60min staleTime+gcTime; fetchIndicators/fetchTickerNews accept offset; SectionError component with retry on all 6 ticker page sections |

## Changes Detail

### Backend (Task 1)

**GZip Middleware** (`backend/app/main.py`):
- `GZipMiddleware(minimum_size=500)` added after CORSMiddleware — all JSON responses ≥500 bytes are gzip-compressed

**N+1 Query Fix** (`backend/app/api/analysis.py`):
- `get_analysis_summary()` previously ran 5 separate SELECT queries (one per AnalysisType) in a loop
- Replaced with single query using `ROW_NUMBER() OVER (PARTITION BY analysis_type ORDER BY analysis_date DESC)`, then filter `rn=1`
- Response format unchanged — same SummaryResponse with optional fields per analysis type

**Offset Pagination**:
- `get_ticker_indicators()`: added `offset: int = 0` parameter, applied `.offset(offset)` to query
- `get_ticker_news()`: added `offset: int = 0` parameter, applied `.offset(offset)` to query

### Frontend (Task 2)

**staleTime/gcTime Tuning** (`frontend/src/lib/hooks.ts`):
- `useAnalysisSummary`: 30min → 60min staleTime, added 60min gcTime
- `useTradingSignal`: 5min → 60min staleTime, added 60min gcTime
- `useIndicators`: kept at 5min (market-hours data, needs freshness)
- `usePrices`: kept at 5min (no change)

**Offset Pagination** (`frontend/src/lib/api.ts`, `frontend/src/lib/hooks.ts`):
- `fetchIndicators()` and `fetchTickerNews()` accept optional `offset` param, use URLSearchParams
- `useIndicators()` and `useTickerNews()` pass offset to API and include in queryKey

**Per-Section Error States** (`frontend/src/app/ticker/[symbol]/page.tsx`):
- Added `SectionError` inline component: displays error message + "Thử lại" retry button with RefreshCw icon
- Destructured `error` + `refetch` from: useIndicators, useAnalysisSummary, useTradingSignal, useTickerNews
- Error handling added to 6 sections: Indicators, Support & Resistance, Combined Recommendation, Trading Plan, Analysis Cards Grid, News

## Verification

- ✅ Backend loads: `from app.main import app` — OK
- ✅ Backend tests: 277 passed, 0 failed
- ✅ TypeScript: `npx tsc --noEmit` — clean compile, no errors

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

- ✅ All 5 modified files exist on disk
- ✅ Commit `54afb0e` found in git log
- ✅ Commit `16cd356` found in git log

**Self-Check: PASSED**

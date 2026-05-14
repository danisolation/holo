# Phase 97: AI Analysis Coverage Expansion - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

AI analysis runs automatically for all watchlist tickers daily with observable coverage metrics.

Requirements: AICOV-01, AICOV-02, AICOV-03
- AICOV-01: Hệ thống tự động chạy AI analysis cho tất cả ticker trong watchlist hàng ngày
- AICOV-02: Schedule auto-analysis vào 8:30 sáng mỗi ngày trading (UTC+7)
- AICOV-03: Dashboard hiển thị AI coverage stats (bao nhiêu ticker đã analyze / tổng watchlist)

</domain>

<decisions>
## Implementation Decisions

### Agent's Discretion
All implementation choices are at the agent's discretion. Key context:
- AI analysis already exists via unified pipeline (AIAnalysisService)
- Morning analysis chain already exists at 8:30 AM (morning_ai_refresh job in scheduler)
- Issue: analysis may not run for ALL watchlist tickers — needs verification and fix
- Frontend needs a coverage indicator component

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `backend/app/services/ai_analysis_service.py` — Unified AI analysis service
- `backend/app/scheduler/jobs.py` — Scheduler jobs including morning_ai_refresh
- `backend/app/api/analysis.py` — Analysis API endpoints
- `frontend/src/app/page.tsx` — Homepage/dashboard
- `frontend/src/lib/api.ts` — API client functions

### Known Context
- Gemini model: gemini-3-flash-preview (2.x quota exhausted)
- AI analysis runs LOCAL only (Gemini geo-blocked from Render Singapore)
- Existing morning_ai_refresh chain: price → indicators → AI → signals
- Watchlist currently has 11 tickers
- Analysis type is UNIFIED with Vietnamese signal names (mua/ban/giu)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — use existing patterns.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>

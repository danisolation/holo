# Phase 106: AI Peer Analysis - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Gemini AI generates contextual peer comparison analysis for any ticker, comparing it against sector peers on valuation, momentum, volume — producing structured Vietnamese insights with strengths/weaknesses. Accessible on-demand from ticker detail page.

Requirements: AIPEER-01, AIPEER-02, AIPEER-03

Success Criteria:
1. Gemini receives ticker metrics + sector peer metrics → structured Vietnamese analysis identifying relative strengths/weaknesses
2. AI explicitly compares ticker vs sector averages on key dimensions (valuation, momentum, volume), states outperform/underperform
3. AI peer analysis accessible from ticker detail page as panel/section, fetched on demand without blocking page load

</domain>

<decisions>
## Implementation Decisions

### Backend
- New PeerAnalysisService in backend/app/services/ using existing Gemini integration pattern
- Uses ScreenerService.get_peer_comparison() to fetch peer data as context for Gemini prompt
- Structured output from Gemini (JSON schema) matching a PeerAnalysis Pydantic model
- API endpoint: GET /api/market/peer-analysis/{symbol} — on-demand, not scheduled
- TTLCache 600s (peer analysis doesn't change rapidly)
- Uses existing _gemini_lock for RPM serialization (shared with other Gemini services)

### Gemini Prompt Design
- Vietnamese language output
- Structured: overall_verdict, strengths (list), weaknesses (list), peer_position (text), recommendation (text)
- Input: target ticker metrics + all peer metrics + sector averages
- Model: gemini-2.0-flash or gemini-2.5-flash (whichever is configured)

### Frontend
- New PeerAnalysisPanel component on ticker detail page
- Lazy-loaded on user click ("Phân tích so sánh ngành" button)
- Shows structured analysis with color-coded strengths/weaknesses
- Uses React Query with enabled: false until user triggers

### Agent's Discretion
All remaining choices at agent's discretion. Follow existing Gemini service patterns.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- backend/app/services/ai_analysis_service.py — Gemini integration pattern (_gemini_lock, model config, structured output)
- backend/app/services/screener_service.py — get_peer_comparison() returns PeerComparisonResponse
- backend/app/services/sector_intelligence_service.py — another Gemini service pattern
- backend/app/schemas/screener.py — PeerComparisonItem, PeerComparisonResponse
- frontend/src/lib/api.ts — fetchPeerComparison already exists
- frontend/src/lib/hooks.ts — usePeerComparison already exists
- frontend/src/app/ticker/[symbol]/page.tsx — ticker detail page to add panel

### Established Patterns  
- Gemini structured output via response_schema parameter
- AsyncSession dependency injection in services
- TTLCache for API response caching
- "use client" components with React Query hooks

### Integration Points
- ScreenerService provides peer data
- Ticker detail page hosts the new panel
- Gemini model from Settings.gemini_model

</code_context>

<specifics>
## Specific Ideas

None — follow existing Gemini service patterns.

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>

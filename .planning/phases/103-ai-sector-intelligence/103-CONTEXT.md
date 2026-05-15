# Phase 103: AI Sector Intelligence - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

AI-powered sector analysis using Gemini:
1. Sector strength/weakness analysis — Gemini receives breadth + flow data, outputs structured analysis
2. Rotation timing recommendation — which sectors attracting/losing money flow
3. Daily scheduled job — chained after price crawl in APScheduler
4. Display on sector page alongside charts

</domain>

<decisions>
## Implementation Decisions

### Service Architecture
- Create `SectorIntelligenceService` in `backend/app/services/sector_intelligence_service.py`
- Uses MarketBreadthService + SectorAnalysisService data as context for Gemini
- Follow existing GeminiClient pattern from `backend/app/services/analysis/gemini_client.py`
- Use structured output (Pydantic model) for Gemini response

### AI Prompt Design
- Input: sector performance (today/7D/30D), net flow, breadth metrics (A/D, MA breadth)
- Output: structured JSON with sector_analyses[] (name, strength, trend, recommendation)
- Vietnamese language output
- Use gemini-3-flash-preview model (same as unified analysis)

### Scheduler Integration
- New job: `daily_sector_analysis` chained after price crawl completion
- Follow existing EVENT_JOB_EXECUTED pattern in scheduler/manager.py
- Store result in new `sector_analyses` DB table (date, analysis JSON, created_at)

### API & Frontend
- GET /api/market/sector-analysis — returns latest AI sector analysis
- Display as card/panel on sector page with strength badges and recommendations
- Vietnamese labels

### Agent's Discretion
- Exact prompt wording
- DB table schema details
- Cache strategy for AI results
- Alembic migration details

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/analysis/gemini_client.py` — Gemini API wrapper with rate limiting
- `backend/app/services/analysis/prompts.py` — prompt template patterns
- `backend/app/scheduler/manager.py` — job chaining with EVENT_JOB_EXECUTED
- `backend/app/scheduler/jobs.py` — job function patterns
- Phase 100/101 services for breadth + sector data

### Established Patterns
- Gemini structured output: define Pydantic model, pass as response_schema
- _gemini_lock for RPM serialization
- Scheduler chaining: listener on EVENT_JOB_EXECUTED checking job.id

### Integration Points
- Scheduler: chain after price_crawl or indicator computation
- API: extend app/api/market.py router
- Frontend: add AI analysis panel to /market page
- New Alembic migration for sector_analyses table

</code_context>

<specifics>
## Specific Ideas

- Keep AI analysis concise — 2-3 sentences per sector
- Include overall market sentiment based on breadth
- Highlight top 3 strongest and weakest sectors

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

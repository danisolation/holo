# Phase 68: Gemini Quota Fix & Scoring Repair - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Switch rumor scoring Gemini model from gemini-2.5-flash-lite (20 RPD free tier) to gemini-2.0-flash (1500 RPD free tier). Verify scoring runs successfully and produces >0 scored tickers.

</domain>

<decisions>
## Implementation Decisions

### Agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Key change: update the model name used in RumorScoringService for Gemini API calls.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/services/rumor_scoring_service.py` — RumorScoringService with `score_all_tickers()` method
- `backend/app/config.py` — settings with Gemini model configuration
- `backend/app/services/analysis/gemini_client.py` — main Gemini client (may share model config)

### Established Patterns
- Gemini model name configured via settings or hardcoded in service
- Circuit breaker pattern (gemini_breaker) for rate limiting
- Batch scoring: 6 tickers per Gemini call

### Integration Points
- `backend/app/scheduler/jobs.py` — `daily_rumor_scoring()` triggers the service
- `backend/app/resilience.py` — circuit breaker state (was tripped due to 429s)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Change model, verify it works.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

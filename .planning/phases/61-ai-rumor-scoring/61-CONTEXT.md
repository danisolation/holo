# Phase 61 — AI Rumor Scoring: Smart Discuss Context

## Grey Areas Resolved

### Area 1: Service Architecture & Gemini Integration

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Service class pattern | `RumorScoringService` standalone class (NOT embedded in AIAnalysisService) | Separate concern — rumor scoring has different input/output schema than technical/fundamental analysis. Keeps AIAnalysisService unchanged. |
| 2 | Gemini client reuse | Reuse existing `GeminiClient._call_gemini_with_retry` pattern — create new instance with same `genai.Client` | Consistent retry/breaker pattern, shared API key config |
| 3 | Gemini model | Use `settings.gemini_model` (gemini-2.5-flash-lite) — same as other analyses | No need for different model for rumor scoring |
| 4 | Rate limiting | Acquire `_gemini_lock` before Gemini calls (same lock as AIAnalysisService) | Prevents RPM competition between analysis types running concurrently |
| 5 | Batch strategy | Group rumors by ticker, send ALL posts for one ticker in a single prompt | Gemini needs context of all posts together to assess patterns. ~20 posts × ~100 chars = ~2K tokens per ticker — well within limits |
| 6 | Structured output | Pydantic schema for response_schema (like existing analysis patterns) | Type-safe parsing, automatic validation |

### Area 2: Database Schema & Storage

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 7 | Table name | `rumor_scores` — one row per ticker per scoring date | Matches architecture research recommendation |
| 8 | Score columns | `credibility_score` (1-10), `impact_score` (1-10), `direction` (bullish/bearish/neutral) | Direct from requirements RUMOR-04, RUMOR-05 |
| 9 | Key claims storage | `key_claims` as JSONB array of strings | Flexible, queryable, avoids separate table for simple list (RUMOR-07) |
| 10 | Reasoning storage | `reasoning` as Text — Vietnamese explanation | Direct from RUMOR-08 |
| 11 | Dedup strategy | UniqueConstraint on (ticker_id, scored_date) — ON CONFLICT DO UPDATE | Re-scoring same ticker same day overwrites (latest is best) |
| 12 | Link to source posts | `post_ids` JSONB array — list of rumor.id values scored | Traceability without FK complexity |
| 13 | Unscored detection | Query rumors WHERE id NOT IN (any rumor_scores.post_ids for that ticker today) | Simple, no extra columns on rumors table |

### Area 3: Prompt Engineering & Scoring Logic

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 14 | Prompt language | Vietnamese system instruction + Vietnamese few-shot examples | All content is Vietnamese, Gemini handles it natively (RUMOR-08) |
| 15 | Engagement weighting | Include likes/replies/is_authentic in prompt context, let Gemini reason about credibility | Don't pre-compute weights — Gemini can assess "verified user with 50 likes" vs "anonymous with 0 likes" |
| 16 | Scoring rubric | Explicit 1-10 rubric in system instruction (like existing SCORING_RUBRIC pattern) | Consistent scoring across runs |
| 17 | Temperature | 0.2 (same as other analyses) — low creativity, high consistency | Scoring needs reproducibility |
| 18 | Empty ticker handling | If ticker has 0 unscored rumors, skip — don't call Gemini | Save RPM budget |

## Code Context

### Reusable Assets
- `backend/app/services/analysis/gemini_client.py` — GeminiClient with retry, breaker, structured output
- `backend/app/services/analysis/prompts.py` — SCORING_RUBRIC pattern, system instruction pattern
- `backend/app/services/analysis/storage.py` — AnalysisStorage upsert pattern
- `backend/app/models/rumor.py` — Rumor model (source data for scoring)
- `backend/app/config.py` — gemini_* settings
- `backend/app/resilience.py` — gemini_breaker

### Integration Points
- `_gemini_lock` in `ai_analysis_service.py` — must acquire before Gemini calls
- `gemini_breaker` in `resilience.py` — wraps all Gemini API calls
- `GeminiUsageService` — track token usage for RPM budgeting
- Scheduler jobs.py — will wire in Phase 63 (not this phase)

### Specifics
- Gemini structured output via `response_schema` parameter on `client.models.generate_content`
- Pydantic models define the schema, Gemini returns JSON matching it
- Existing pattern: system_instruction + few-shot + user prompt with data

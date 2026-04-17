# Phase 9: AI Prompt Improvements — Context

**Gathered:** 2026-04-18
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous smart discuss)

<domain>
## Phase Boundary

**Goal**: AI analysis produces more consistent, accurately calibrated recommendations with structured output reliability.

**In scope:**
- System instruction separation (persona in system_instruction, not user prompt)
- Few-shot examples for each analysis type
- Scoring rubric with explicit anchors (1-2 weak through 9-10 very strong)
- Technical analysis prompt includes latest close price and price-vs-SMA percentages
- Language consistency per analysis type (English for tech/fund, Vietnamese for combined/sentiment)
- Temperature tuning per analysis type
- Structured output retry at lower temperature before JSON parse fallback

**Out of scope:**
- Fine-tuning Gemini (explicit exclusion in REQUIREMENTS.md)
- Multi-model consensus (explicit exclusion)
- Changing the Gemini model (keep gemini-2.5-flash-lite)
- Changing batch size or rate limiting

</domain>

<decisions>
## Implementation Decisions

### D-09-01: System Instruction Separation
**Decision:** Move persona definition to `system_instruction` parameter in Gemini API call. User prompt contains only data + specific analysis request.
**Rationale:** Per AI-07 — Gemini's `system_instruction` parameter is the correct place for persona/role definition. Reduces prompt size and improves consistency.

### D-09-02: Few-Shot Examples
**Decision:** Add 1-2 few-shot examples per analysis type showing expected input → output format. Store examples as constants in the service module.
**Rationale:** Per AI-08 — few-shot examples anchor the model's output format and scoring distribution. Helps avoid always-moderate scoring bias.

### D-09-03: Scoring Rubric
**Decision:** Define explicit scoring rubric: 1-2 (very weak/negative), 3-4 (weak/slightly negative), 5-6 (moderate/neutral), 7-8 (strong/positive), 9-10 (very strong/very positive). Include in system instruction.
**Rationale:** Per AI-09 — without explicit anchors, models tend to cluster scores around 5-7.

### D-09-04: Technical Prompt Enhancement
**Decision:** Add latest close price and price-vs-SMA percentage distances to technical analysis input data.
**Rationale:** Per AI-10 — absolute price context helps the model reason about position relative to moving averages (e.g., "10% above SMA50" is more informative than raw values).

### D-09-05: Language Consistency
**Decision:** 
- Technical analysis: English
- Fundamental analysis: English
- Sentiment analysis: Vietnamese (CafeF titles are Vietnamese)
- Combined analysis: Vietnamese (final recommendation for VN user)
**Rationale:** Per AI-11 — match language to data source and audience.

### D-09-06: Temperature Tuning
**Decision:** 
- Technical analysis: temperature=0.1 (most deterministic — numbers-driven)
- Fundamental analysis: temperature=0.2 (slightly more interpretive)
- Sentiment analysis: temperature=0.3 (language understanding needs more creativity)
- Combined analysis: temperature=0.2 (reasoning across dimensions)
**Rationale:** Per AI-13 — lower temperature for quantitative analysis, slightly higher for language tasks.

### D-09-07: Structured Output Retry
**Decision:** On structured output failure (Gemini returns malformed JSON), retry once at temperature=0.05 before falling back to manual JSON parsing.
**Rationale:** Per AI-12 — lower temperature often fixes structured output issues. Two-phase fallback: lower temp retry → JSON parse.

</decisions>

<code_context>
## Existing Code Insights

- `AIAnalysisService` in `backend/app/services/ai_analysis_service.py` is the main file to modify
- Uses `google.genai` (new SDK) with `types.GenerateContentConfig(response_schema=...)` for structured output
- 4 analysis types: technical, fundamental, sentiment, combined
- Each has its own prompt builder method and response schema
- `_call_gemini_with_retry` handles retries via tenacity, wrapped with `gemini_breaker.call()`
- Prompts are currently inline strings — need to be refactored into structured format

</code_context>

<specifics>
## Specific Ideas

- Create a `prompts/` module with per-analysis-type prompt templates
- Or keep prompts in the service but add `_build_system_instruction()` method
- Few-shot examples should use realistic VN stock data (VNM, HPG, etc.)

</specifics>

<deferred>
## Deferred Ideas

- None — all AI-07 through AI-13 requirements are in scope

</deferred>

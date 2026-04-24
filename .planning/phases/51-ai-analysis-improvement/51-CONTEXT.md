# Phase 51: AI Analysis Improvement - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode — discuss skipped)

<domain>
## Phase Boundary

AI analysis output is longer, structured into clear sections, and rendered on the frontend with visual hierarchy — not a plain text block.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key research findings to incorporate:
- Current config in `backend/app/config.py`: batch_size=25 (regular), 15 (trading signals), thinking_budget=1024/2048, max_tokens=16384/32768
- Research recommends: increase reasoning caps (200→500 words), bump max_output_tokens, consider `gemini-2.5-flash` (non-lite) for combined/trading_signal
- Structured output via Pydantic models already proven with trading signals
- AI prompts are in `backend/app/ai/` directory — need to add section structure instructions
- Vietnamese section labels: tóm tắt, mức giá quan trọng, rủi ro, hành động cụ thể
- Frontend renders AI output — needs to parse sections and render with headings/visual hierarchy
- Reduce batch sizes to allow more tokens per ticker analysis

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `backend/app/config.py` — Settings class with batch_size, thinking_budget, max_tokens
- `backend/app/ai/` — AI analysis prompts and Gemini integration
- `frontend/src/` — components that render AI analysis output

### Established Patterns
- Google Gemini via `google-genai` SDK
- Pydantic models for structured AI output
- Markdown rendering on frontend

</code_context>

<specifics>
## Specific Ideas

- Vietnamese section headings in AI output: "Tóm tắt", "Mức giá quan trọng", "Rủi ro", "Hành động cụ thể"
- Each section should be clearly labeled and separated in the AI prompt instructions
- Frontend should render with visual hierarchy (headings, cards, or accordion)
- Reduce batch_size, increase max_tokens and thinking_budget for quality

</specifics>

<deferred>
## Deferred Ideas

- Model upgrade to gemini-2.5-flash (non-lite) — evaluate cost impact first
- Per-ticker analysis caching strategy — future optimization

</deferred>

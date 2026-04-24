---
phase: 51-ai-analysis-improvement
plan: 01
subsystem: backend-ai-analysis
tags: [ai, gemini, pydantic, prompts, config]
dependency_graph:
  requires: []
  provides: [structured-combined-schema, combined-token-limits, raw-response-api]
  affects: [frontend-analysis-rendering]
tech_stack:
  added: []
  patterns: [structured-pydantic-output, markdown-reasoning-concatenation]
key_files:
  created: []
  modified:
    - backend/app/config.py
    - backend/app/schemas/analysis.py
    - backend/app/services/analysis/prompts.py
    - backend/app/services/analysis/gemini_client.py
    - backend/app/services/ai_analysis_service.py
    - backend/app/api/analysis.py
decisions:
  - Batch size reduced 25→15 to match research finding on prompt length vs truncation tradeoff
  - Combined analysis reuses same token limits as trading_signal (32768/2048)
  - Reasoning column stores markdown-formatted concatenation of 4 sections for backward compatibility
  - raw_response exposed on summary endpoint for all analysis types, not just combined
metrics:
  duration: 2m 46s
  completed: "2026-04-24T15:10:42Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 6
---

# Phase 51 Plan 01: Structured Combined Analysis Backend Summary

Structured combined analysis with 4 Vietnamese sections (summary, key_levels, risks, action) replacing single explanation string, with reduced batch size and increased token/thinking limits for longer AI output.

## What Was Done

### Task 1: Config tuning + Pydantic schema + prompt restructuring
**Commit:** `140a959`

- **config.py**: Reduced `gemini_batch_size` from 25 to 15. Added `combined_thinking_budget=2048` and `combined_max_tokens=32768` settings.
- **schemas/analysis.py**: Replaced `explanation: str` field in `TickerCombinedAnalysis` with 4 structured fields: `summary`, `key_levels`, `risks`, `action` — each with Vietnamese descriptions guiding Gemini output.
- **prompts.py**: Rewrote `COMBINED_SYSTEM_INSTRUCTION` with detailed per-field instructions. Rewrote `COMBINED_FEW_SHOT` with a comprehensive multi-section example including concrete price levels and risk factors.

### Task 2: Gemini client token passing + service reasoning extraction + API raw_response
**Commit:** `0355725`

- **gemini_client.py**: Both `_call_gemini` invocations in `analyze_combined_batch` now pass `max_output_tokens=settings.combined_max_tokens` and `thinking_budget=settings.combined_thinking_budget`.
- **ai_analysis_service.py**: Updated combined reasoning extraction to concatenate 4 sections with markdown headers (`## Tóm tắt`, `## Mức giá quan trọng`, `## Rủi ro`, `## Hành động cụ thể`) for backward-compatible storage in the `reasoning` TEXT column.
- **api/analysis.py**: Added `raw_response=analysis.raw_response` to `get_combined_analysis` endpoint and `raw_response=row["raw_response"]` to `get_analysis_summary` endpoint.

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

| Check | Result |
|-------|--------|
| Schema fields = [ticker, recommendation, confidence, summary, key_levels, risks, action] | ✅ |
| gemini_batch_size = 15 | ✅ |
| combined_thinking_budget = 2048 | ✅ |
| combined_max_tokens = 32768 | ✅ |
| combined_max_tokens in gemini_client (2 occurrences) | ✅ |
| combined_thinking_budget in gemini_client (2 occurrences) | ✅ |
| raw_response in analysis.py (4 occurrences) | ✅ |
| Tóm tắt in ai_analysis_service.py | ✅ |
| No import errors | ✅ |

## Self-Check: PASSED

- [x] `backend/app/config.py` — FOUND
- [x] `backend/app/schemas/analysis.py` — FOUND
- [x] `backend/app/services/analysis/prompts.py` — FOUND
- [x] `backend/app/services/analysis/gemini_client.py` — FOUND
- [x] `backend/app/services/ai_analysis_service.py` — FOUND
- [x] `backend/app/api/analysis.py` — FOUND
- [x] Commit `140a959` — FOUND
- [x] Commit `0355725` — FOUND

---
phase: 61-ai-rumor-scoring
plan: 02
subsystem: backend
tags: [service, gemini, ai, rumor-scoring, upsert]
dependency_graph:
  requires: [61-01-rumor-score-model, 61-01-pydantic-schemas, 61-01-rumor-prompts]
  provides: [rumor-scoring-service]
  affects: [61-03-api-endpoint, 61-04-scheduler]
tech_stack:
  added: []
  patterns: [gemini-structured-output, asyncio-lock-serialization, sql-upsert-on-conflict, engagement-weighted-prompts]
key_files:
  created:
    - backend/app/services/rumor_scoring_service.py
    - backend/tests/test_rumor_scoring_service.py
  modified: []
decisions:
  - "Standalone service class (not embedded in AIAnalysisService) for separation of concerns"
  - "NOT EXISTS subquery for unscored detection (simpler than JSONB unnest of post_ids)"
  - "Ticker name mismatch fallback: use first score if Gemini returns different ticker name"
key-decisions:
  - "Standalone RumorScoringService with shared _gemini_lock for RPM serialization"
  - "NOT EXISTS subquery for efficient unscored ticker detection"
metrics:
  duration: ~3 min
  completed: "2026-05-05"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 61 Plan 02: RumorScoringService Implementation Summary

**One-liner:** RumorScoringService with engagement-weighted Vietnamese prompts, Gemini structured output via _gemini_lock serialization, and ON CONFLICT upsert storage — 12 unit tests passing.

## What Was Built

### Task 1: RumorScoringService Implementation
- **RumorScoringService** class in `backend/app/services/rumor_scoring_service.py` (254 lines)
- `score_all_tickers()` — orchestrates batch scoring with delay between tickers
- `score_ticker(ticker_id, ticker_symbol)` — queries rumors, builds prompt, calls Gemini with lock, stores result
- `_build_prompt()` — Vietnamese prompt with `[Xác thực ✓]`/`[Thường]` tags, likes/replies counts
- `_get_tickers_with_unscored_rumors()` — NOT EXISTS subquery to find tickers needing scoring
- `_store_score()` — INSERT ON CONFLICT upsert matching AnalysisStorage pattern
- Low-temp retry + manual JSON fallback for Gemini parse failures
- Ticker name mismatch fallback (use first score if name doesn't match)

### Task 2: Comprehensive Unit Tests
- **12 test functions** in `backend/tests/test_rumor_scoring_service.py` (310 lines)
- `TestBuildPrompt` (5 tests): engagement metrics, verified/regular tags, Vietnamese content, ticker header, few-shot
- `TestScoreTicker` (3 tests): success path, empty skip, lock acquisition verification
- `TestStoreScore` (2 tests): upsert SQL pattern, parameter correctness
- `TestScoreAllTickers` (2 tests): skip already scored, multiple ticker processing

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 323b332 | RumorScoringService with Gemini integration |
| 2 | fe59469 | Unit tests for RumorScoringService (12 tests) |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat | Mitigation |
|--------|-----------|
| T-61-03 (Tampering — Gemini response) | RumorBatchResponse Pydantic schema with Field(ge=1, le=10) validates scores; low-temp retry on parse failure |
| T-61-04 (DoS — RPM exhaustion) | _gemini_lock serializes access; skip tickers with 0 unscored rumors; gemini_delay_seconds between tickers |
| T-61-05 (Spoofing — prompt injection) | Accepted — structured output (response_schema) constrains Gemini output format |

## Self-Check: PASSED

- [x] `backend/app/services/rumor_scoring_service.py` exists (254 lines)
- [x] `backend/tests/test_rumor_scoring_service.py` exists (310 lines)
- [x] Commit 323b332 found
- [x] Commit fe59469 found
- [x] All 12 tests pass
- [x] Service imports successfully
- [x] `_gemini_lock` import from ai_analysis_service present
- [x] `INSERT INTO rumor_scores ... ON CONFLICT` upsert SQL present
- [x] `[Xác thực ✓]` engagement formatting in `_build_prompt` present

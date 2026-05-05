---
phase: 61-ai-rumor-scoring
plan: 01
subsystem: backend
tags: [model, migration, schema, prompts, ai]
dependency_graph:
  requires: [rumor-model-from-60]
  provides: [rumor-score-model, rumor-pydantic-schemas, rumor-prompt-constants]
  affects: [61-02-service]
tech_stack:
  added: []
  patterns: [pydantic-gemini-response-schema, vietnamese-prompt-engineering, jsonb-storage]
key_files:
  created:
    - backend/app/models/rumor_score.py
    - backend/alembic/versions/029_create_rumor_scores_table.py
    - backend/app/schemas/rumor.py
    - backend/app/services/analysis/rumor_prompts.py
  modified:
    - backend/app/models/__init__.py
decisions:
  - "JSONB for key_claims and post_ids — flexible list storage without separate tables"
  - "UniqueConstraint(ticker_id, scored_date) enables daily upsert pattern"
  - "Pydantic Field(ge=1, le=10) validates Gemini output at deserialization boundary (T-61-01)"
metrics:
  duration: ~3 min
  completed: "2026-05-05"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 61 Plan 01: RumorScore Data Layer & AI Contracts Summary

**One-liner:** RumorScore model with JSONB claims/post_ids, Pydantic Gemini response schemas with 1-10 validation, Vietnamese prompt constants with engagement-weighted rubric and few-shot example.

## What Was Built

### Task 1: RumorScore Model + Alembic Migration
- **RumorScore** SQLAlchemy model (`rumor_scores` table) with columns: `credibility_score`, `impact_score`, `direction`, `key_claims` (JSONB), `reasoning`, `post_ids` (JSONB), `model_version`, `scored_date`
- `UniqueConstraint("ticker_id", "scored_date")` for daily upsert
- Descending index on `(ticker_id, scored_date DESC)` for fast latest-score queries
- Alembic migration `029` with `revision="029"`, `down_revision="028"`
- Model registered in `app.models.__init__` with `__all__` export

### Task 2: Pydantic Schemas + Vietnamese Prompt Constants
- **RumorDirection** enum: `bullish`, `bearish`, `neutral`
- **TickerRumorScore**: `Field(ge=1, le=10)` on both scores — rejects invalid Gemini output at parse time (threat mitigation T-61-01)
- **RumorBatchResponse**: `scores: list[TickerRumorScore]` for batch Gemini calls
- **RUMOR_SYSTEM_INSTRUCTION**: Vietnamese system prompt referencing `is_authentic`, `likes`, `replies` for engagement weighting
- **RUMOR_SCORING_RUBRIC**: Full 1-10 scale with Vietnamese descriptions for credibility and impact
- **RUMOR_FEW_SHOT**: Example with verified user `[Xác thực ✓]` and engagement metrics
- **RUMOR_TEMPERATURE = 0.2**: Low creativity for consistent scoring

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 3d908f2 | RumorScore model + Alembic migration 029 |
| 2 | 035cde3 | Pydantic rumor schemas + Vietnamese prompt constants |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat | Mitigation |
|--------|-----------|
| T-61-01 (Tampering — Gemini response) | `Field(ge=1, le=10)` on credibility_score and impact_score; `RumorDirection` enum constrains direction to 3 values |
| T-61-02 (Information Disclosure — key_claims) | Accepted — public community posts, no PII beyond author names |

## Self-Check: PASSED

- [x] `backend/app/models/rumor_score.py` exists
- [x] `backend/alembic/versions/029_create_rumor_scores_table.py` exists
- [x] `backend/app/schemas/rumor.py` exists
- [x] `backend/app/services/analysis/rumor_prompts.py` exists
- [x] Commit 3d908f2 found
- [x] Commit 035cde3 found
- [x] All imports succeed
- [x] Score validation rejects out-of-range values

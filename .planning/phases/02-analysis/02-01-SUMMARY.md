---
phase: 02-analysis
plan: "01"
subsystem: analysis-foundation
tags: [models, schemas, migration, gemini, ta-library]
dependency_graph:
  requires: [01-01 (database schema, tickers/daily_prices/financials tables)]
  provides: [TechnicalIndicator ORM, AIAnalysis ORM, AnalysisType enum, Pydantic Gemini schemas, migration 002, ta + google-genai deps, Gemini config]
  affects: [02-02 (indicator service), 02-03 (AI analysis service)]
tech_stack:
  added: [ta 0.11.0, google-genai 1.73.1]
  patterns: [native_enum=False for SQLAlchemy Enum with raw DDL migration, Pydantic response_schema for Gemini structured output]
key_files:
  created:
    - backend/app/models/technical_indicator.py
    - backend/app/models/ai_analysis.py
    - backend/app/schemas/analysis.py
    - backend/alembic/versions/002_analysis_tables.py
  modified:
    - backend/requirements.txt
    - backend/.env.example
    - backend/app/config.py
    - backend/app/models/__init__.py
decisions:
  - "native_enum=False for AnalysisType SQLAlchemy Enum — avoids conflict with raw DDL migration that creates the PostgreSQL ENUM type separately"
  - "gemini_api_key defaults to empty string — allows app startup without key (non-analysis features work), analysis services check at runtime"
  - "gemini_delay_seconds=4.0 — minimum 4s for 15 RPM free tier rate limit safety"
metrics:
  duration: ~5m
  completed: 2026-04-15
  tasks_completed: 2
  tasks_total: 2
  files_created: 4
  files_modified: 4
---

# Phase 2 Plan 01: Analysis Data Foundation Summary

**One-liner:** ORM models (TechnicalIndicator, AIAnalysis), Alembic migration 002, Pydantic Gemini schemas, ta + google-genai dependencies, and Gemini config settings

## What Was Done

### Task 1: Dependencies, configuration, and Alembic migration 002
- Added `ta==0.11.0` and `google-genai>=1.73,<2` to `requirements.txt`
- Extended `Settings` class with 6 new fields: `gemini_api_key`, `gemini_model`, `gemini_batch_size`, `gemini_delay_seconds`, `gemini_max_retries`, `indicator_compute_days`
- Added all Gemini/indicator env vars to `.env.example` with documentation
- Created Alembic migration `002_analysis_tables.py` with:
  - `analysis_type` PostgreSQL ENUM (technical, fundamental, sentiment)
  - `technical_indicators` table with 12 indicator columns + unique constraint on (ticker_id, date)
  - `ai_analyses` table with signal/score/reasoning/JSONB + unique constraint on (ticker_id, analysis_type, analysis_date)
  - Appropriate indexes on both tables
- **Commit:** `5fb3a1f`

### Task 2: ORM models, Pydantic schemas, model registration
- Created `TechnicalIndicator` ORM model with 12 nullable `Decimal` indicator columns matching migration DDL
- Created `AIAnalysis` ORM model with `AnalysisType` enum using `native_enum=False` (stores as VARCHAR in ORM, PostgreSQL ENUM created by DDL migration)
- Registered both models in `app/models/__init__.py` (importable + Alembic-visible)
- Created `backend/app/schemas/analysis.py` with:
  - Gemini schemas: `TechnicalSignal`, `TickerTechnicalAnalysis`, `TechnicalBatchResponse`
  - Gemini schemas: `FundamentalHealth`, `TickerFundamentalAnalysis`, `FundamentalBatchResponse`
  - API schemas: `AnalysisResultResponse`, `AnalysisTriggerResponse`, `IndicatorResponse`
- **Commit:** `a10215b`

## Decisions Made

1. **`native_enum=False` for AnalysisType** — The PostgreSQL `analysis_type` ENUM is created by raw DDL in migration 002 (`CREATE TYPE analysis_type AS ENUM ...`). Using `native_enum=False` in SQLAlchemy stores values as VARCHAR in ORM mapping, avoiding duplicate ENUM creation conflicts. The DDL constraint is the source of truth.

2. **Empty string default for `gemini_api_key`** — Allows the application to start and serve non-analysis endpoints without a Gemini API key configured. Analysis services will check for a valid key at runtime before making API calls.

3. **4-second Gemini delay** — RESEARCH.md pitfall 2 identifies the free tier limit as 15 RPM. A 4-second delay provides safety margin (15 requests/60s = 1 per 4s).

## Deviations from Plan

### Migration Not Run Against Database

**Found during:** Task 1
**Issue:** No `.env` file with `DATABASE_URL` exists in the backend directory, so `alembic upgrade head` cannot connect to a database.
**Resolution:** Migration file is correctly written with proper revision chain (001 → 002). The migration will execute when `DATABASE_URL` is configured. This is expected — the migration file itself is the deliverable; running it requires user's database credentials.
**Impact:** None — the file is syntactically correct, importable, and has the correct revision chain verified programmatically.

## Verification Results

| Check | Result |
|-------|--------|
| `ta==0.11.0` importable | ✅ |
| `google-genai==1.73.1` importable | ✅ |
| Config has all 6 new settings | ✅ |
| `.env.example` has GEMINI_API_KEY | ✅ |
| Migration 002 revision chain (001→002) | ✅ |
| TechnicalIndicator model (12 indicator columns) | ✅ |
| AIAnalysis model (AnalysisType enum, JSONB) | ✅ |
| Models registered in `__init__.py` | ✅ |
| Pydantic schemas instantiation | ✅ |
| Existing tests pass (24/24) | ✅ |

## Known Stubs

None — all models, schemas, and configuration are fully wired with real types and constraints.

## Self-Check: PASSED

All 8 files verified present. Both commits (5fb3a1f, a10215b) verified in git log.

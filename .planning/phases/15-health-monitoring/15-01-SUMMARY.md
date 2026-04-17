---
phase: 15
plan: 15-01
title: "Gemini Usage Tracking — Model + Service + Migration"
subsystem: backend-health
tags: [gemini, usage-tracking, health-monitoring, api]
dependency_graph:
  requires: []
  provides: [gemini-usage-model, gemini-usage-service, gemini-usage-api]
  affects: [ai-analysis-service, health-api, health-schemas]
tech_stack:
  added: []
  patterns: [per-call-usage-tracking, daily-aggregation, free-tier-limit-constants]
key_files:
  created:
    - backend/app/models/gemini_usage.py
    - backend/app/services/gemini_usage_service.py
    - backend/alembic/versions/009_gemini_usage_table.py
    - backend/tests/test_gemini_usage.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/services/ai_analysis_service.py
    - backend/app/api/health.py
    - backend/app/schemas/health.py
decisions:
  - "Usage recording via _record_usage helper in each batch method (not in _call_gemini) to avoid counting retries"
  - "Graceful try/except in _record_usage — tracking never breaks analysis"
  - "Free-tier limits hardcoded as module constants in health.py (1500 RPD, 1M tokens/day)"
  - "Days param capped at 30 via min() in endpoint (not Query validator) for flexibility"
metrics:
  duration: "8m"
  completed: "2026-04-17"
  tasks: 3
  tests_added: 21
  tests_total: 334
---

# Phase 15 Plan 01: Gemini Usage Tracking — Model + Service + Migration Summary

**One-liner:** Per-call Gemini API token tracking with daily aggregation endpoint showing consumption vs 1500 RPD / 1M token free-tier limits.

## Tasks Completed

| # | Task | Commit | Test Count |
|---|------|--------|------------|
| 1 | GeminiUsage model + migration 009 | `b1a85a6` | 9 |
| 2 | GeminiUsageService + AI service recording hook | `c2d46b8` | 7 |
| 3 | GET /health/gemini-usage endpoint + schemas | `ea8f45c` | 5 |

## Implementation Details

### T-15-01: GeminiUsage Model + Migration
- `GeminiUsage` model: `id` (BigInteger PK), `analysis_type` (String 30), `batch_size` (Integer), `prompt_tokens`, `completion_tokens`, `total_tokens` (Integer), `model_name` (String 50), `created_at` (TIMESTAMP tz, server_default=now)
- Alembic migration 009: creates `gemini_usage` table with `idx_gemini_usage_created_at` index for daily aggregation queries
- Registered in `models/__init__.py` and `__all__`

### T-15-02: GeminiUsageService + Recording Hook
- `record_usage()`: inserts row, handles None usage_metadata gracefully (defaults to 0 tokens)
- `get_daily_usage(days)`: daily aggregates via GROUP BY cast(created_at, Date), ordered DESC
- `get_today_usage()`: per-analysis-type breakdown with totals for current UTC day
- `_record_usage()` helper added to all 4 batch methods (technical, fundamental, sentiment, combined)
- Wrapped in try/except so tracking failures never break AI analysis

### T-15-03: Gemini Usage API Endpoint
- `GET /health/gemini-usage?days=7` (default 7, max 30)
- Response: `GeminiUsageResponse` with `today` (requests, tokens, limits, breakdown) + `daily` history
- Free-tier constants: `GEMINI_FREE_TIER_RPD=1500`, `GEMINI_FREE_TIER_TOKENS=1,000,000`
- Pydantic schemas: `GeminiUsageTodayBreakdown`, `GeminiUsageToday`, `GeminiUsageDaily`, `GeminiUsageResponse`

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

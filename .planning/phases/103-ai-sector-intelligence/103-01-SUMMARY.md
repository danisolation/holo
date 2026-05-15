---
phase: 103-ai-sector-intelligence
plan: "01"
subsystem: ai-analysis
tags: [gemini, sector-intelligence, scheduler, api, frontend]
dependency_graph:
  requires:
    - "100-market-breadth (MarketBreadthService)"
    - "101-sector-analysis (SectorAnalysisService)"
    - "98-simulator (scheduler chain end)"
  provides:
    - "SectorIntelligenceService — AI sector analysis via Gemini"
    - "GET /api/market/sector-analysis — latest sector intelligence"
    - "SectorAIPanel — homepage sector AI display"
  affects:
    - "backend/app/scheduler/manager.py (chain extension)"
    - "backend/app/scheduler/jobs.py (new job)"
    - "frontend/src/app/page.tsx (new panel)"
tech_stack:
  added: []
  patterns:
    - "GeminiClient structured output for sector-level analysis"
    - "Scheduler job chaining (EVENT_JOB_EXECUTED)"
    - "TTLCache for API response caching"
key_files:
  created:
    - backend/app/models/sector_analysis.py
    - backend/alembic/versions/6ae2a74c3387_add_sector_analyses_table.py
    - backend/app/services/sector_intelligence_service.py
    - frontend/src/components/sector-ai-panel.tsx
  modified:
    - backend/app/models/__init__.py
    - backend/app/schemas/sector.py
    - backend/app/services/analysis/prompts.py
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
    - backend/app/api/market.py
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/page.tsx
decisions:
  - "Sector analysis stored as JSONB — full Gemini structured output preserved"
  - "One analysis per day (unique analysis_date) with upsert on re-run"
  - "10-min TTLCache on API endpoint (maxsize=1) for DoS mitigation"
  - "Panel placed after top movers on homepage, expandable sector details"
metrics:
  duration: "~12 min"
  completed: "2026-05-14"
  tasks_completed: 3
  tasks_total: 3
  test_results: "514 passed, 0 failed"
---

# Phase 103 Plan 01: AI Sector Intelligence Summary

Gemini-powered sector strength/weakness analysis with rotation timing, chained daily after simulator check, exposed via API, displayed on homepage with Vietnamese-language insights.

## What Was Built

### Task 1: DB Model, Migration, Schemas, Service, and Prompt
- **SectorAnalysis** SQLAlchemy model (`sector_analyses` table) with JSONB `analysis_json`, unique `analysis_date`, indexed for fast latest-query
- Alembic migration `6ae2a74c3387` creates table with date index
- Pydantic schemas: `SectorStrengthItem`, `SectorRotationTiming`, `SectorIntelligenceResponse`, `SectorAnalysisAPIResponse`
- **SectorIntelligenceService** gathers breadth + flow + performance data (30D perf, 7D flow, 7D breadth), builds Vietnamese prompt, calls Gemini via `GeminiClient._call_gemini()`, stores structured output
- `SECTOR_INTELLIGENCE_SYSTEM_INSTRUCTION` prompt added to prompts.py — Vietnamese macro analysis expert
- Commit: `6ac0a89`

### Task 2: Scheduler Job Chain and API Endpoint
- `daily_sector_intelligence` async job function with `JobExecutionService` tracking (start/complete/fail pattern)
- Scheduler chain extended: `daily_simulator_sl_tp_check → daily_sector_intelligence`
- `_JOB_NAMES` updated with sector intelligence entries
- `GET /api/market/sector-analysis` endpoint with 10-min `TTLCache` (maxsize=1), returns 404 when no analysis exists
- Commit: `289b1fe`

### Task 3: Frontend Sector AI Panel on Homepage
- TypeScript types and `fetchSectorAnalysis` API function in `api.ts`
- `useSectorAnalysis` hook with 10-min staleTime in `hooks.ts`
- `SectorAIPanel` component: market sentiment, top strong/weak badges (emerald/red), rotation recommendation, expandable sector detail list with strength/trend/flow indicators
- Handles loading (skeleton), empty state ("Chưa có phân tích ngành"), and error (returns null)
- Added to homepage after top movers section
- Commit: `bcac7f0`

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **JSONB storage**: Full Gemini structured output stored as-is — no normalization needed since it's read-only display data
2. **Upsert strategy**: Delete-then-insert for same-day re-runs (simpler than merge, matches existing patterns)
3. **Cache sizing**: maxsize=1 sufficient since endpoint always returns latest analysis only

## Self-Check: PASSED

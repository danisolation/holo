---
phase: 20-trading-plan-dashboard-panel
plan: 01
title: "Backend API + Frontend Data Layer"
one_liner: "Exposed raw_response JSONB via trading-signal endpoint and built typed frontend data layer (types, fetch, hook, ScoreBar export)"
completed: "2026-04-20T12:06:00Z"
duration: "2.7m"
tasks_completed: 2
tasks_total: 2
subsystem: "backend-api, frontend-data"
tags: [trading-signal, api-extension, react-query, typescript-types]
dependency_graph:
  requires: []
  provides: ["AnalysisResultResponse.raw_response", "TickerTradingSignal types", "fetchTradingSignal", "useTradingSignal", "ScoreBar export"]
  affects: ["20-02-PLAN (Trading Plan Panel component)"]
tech_stack:
  added: []
  patterns: ["Optional field backward-compat schema extension", "React Query hook with 404-to-null pattern"]
key_files:
  created: []
  modified:
    - backend/app/schemas/analysis.py
    - backend/app/api/analysis.py
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/components/analysis-card.tsx
key_decisions:
  - "raw_response: dict | None = None — backward-compatible, other endpoints return null"
  - "fetchTradingSignal extracts raw_response from AnalysisResult wrapper, returns TickerTradingSignal | null"
  - "useTradingSignal uses 5-min staleTime (matching indicator hooks, not 30-min analysis staleTime)"
  - "Direction values lowercase ('long', 'bearish') matching backend Python enum"
metrics:
  duration: "2.7m"
  completed: "2026-04-20"
  tasks: 2
  files: 5
requirements: [DISP-01]
---

# Phase 20 Plan 01: Backend API + Frontend Data Layer Summary

Exposed raw_response JSONB via trading-signal endpoint and built typed frontend data layer (types, fetch, hook, ScoreBar export)

## What Was Done

### Task 1: Backend — Expose raw_response in trading-signal endpoint
**Commit:** `6857d16`

- Added `raw_response: dict | None = None` field to `AnalysisResultResponse` in `backend/app/schemas/analysis.py`
- Added `raw_response=analysis.raw_response` to `get_trading_signal` handler in `backend/app/api/analysis.py`
- Backward-compatible: all other endpoints (technical, fundamental, sentiment, combined) return `raw_response: null` automatically
- All 424 backend tests pass

### Task 2: Frontend — Types, fetchTradingSignal, useTradingSignal hook, export ScoreBar
**Commit:** `9d82d9c`

- Exported `ScoreBar` component from `analysis-card.tsx` (single keyword change)
- Added `trading_signal?: AnalysisResult` to `AnalysisSummary` interface
- Added `TradingPlanDetail`, `DirectionAnalysis`, `TickerTradingSignal` interfaces
- Added `fetchTradingSignal()` function that extracts `raw_response` from API response, returns `TickerTradingSignal | null` (404 → null)
- Added `useTradingSignal()` React Query hook with 5-minute staleTime and `enabled: !!symbol` guard
- `next build` compiles successfully with zero type errors

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **raw_response backward-compat**: Using `None` default means zero changes needed for existing endpoints
2. **5-min staleTime**: Matches indicator hooks (not the 30-min analysis staleTime) since trading signals change daily
3. **Lowercase direction values**: `"long"` and `"bearish"` matching Python `Direction` enum `.value`

## Verification Results

| Check | Result |
|-------|--------|
| Python schema import + instantiation | ✅ PASS |
| Backend tests (424) | ✅ PASS |
| Frontend `next build` | ✅ Compiled successfully |
| ScoreBar exported | ✅ `export function ScoreBar` |
| fetchTradingSignal exported | ✅ in api.ts |
| useTradingSignal exported | ✅ in hooks.ts |

## Self-Check: PASSED

All 5 modified files verified. Both commits (6857d16, 9d82d9c) present. All exports confirmed via grep.

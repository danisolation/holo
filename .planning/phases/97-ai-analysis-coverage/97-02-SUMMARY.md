---
phase: 97-ai-analysis-coverage
plan: 02
subsystem: frontend
tags: [ai-analysis, coverage, dashboard, stats-card]
dependency_graph:
  requires: [coverage_endpoint]
  provides: [dashboard_coverage_card]
  affects: [homepage]
tech_stack:
  added: []
  patterns: [react-query-hook, stats-card-grid]
key_files:
  created: []
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/page.tsx
decisions:
  - Used Sparkles icon (violet) to differentiate AI card from market stats cards
  - 60s staleTime matching backend cache TTL for coverage endpoint
  - Grid changed from 4-col to 5-col to accommodate 5th card
metrics:
  duration: ~2min
  completed: 2025-07-14
  tasks: 2/2
  files: 3
---

# Phase 97 Plan 02: Add AI Coverage Stats Card to Dashboard Summary

AI coverage stats card added to homepage showing "X/Y AI phân tích" with violet Sparkles icon, fetching from GET /api/analysis/coverage via React Query hook.

## Task Completion

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add coverage API function and hook | 194b973 | api.ts, hooks.ts |
| 2 | Add AI coverage card to homepage dashboard | 194b973 | page.tsx |

## Changes Made

### Task 1: Coverage API Function and Hook
- **api.ts**: Added `AnalysisCoverage` interface (analyzed_today, total_watchlist, coverage_pct, last_run_at, failed_today) and `fetchAnalysisCoverage()` function
- **hooks.ts**: Added `useAnalysisCoverage` hook with 60s staleTime, imported `fetchAnalysisCoverage`

### Task 2: AI Coverage Card on Homepage
- **page.tsx**: Imported `Sparkles` from lucide-react and `useAnalysisCoverage` from hooks
- **page.tsx**: Called `useAnalysisCoverage()` hook in Home component
- **page.tsx**: Updated stats grid from `md:grid-cols-4` to `md:grid-cols-5` (both loading skeleton and data grid)
- **page.tsx**: Added 5th card with violet Sparkles icon showing `{analyzed_today}/{total_watchlist}` or "—" while loading

## Deviations from Plan

None - plan executed exactly as written.

## Verification

- ✅ `npx next build` compiles successfully (TypeScript clean, all pages generated)
- ✅ AnalysisCoverage interface matches backend CoverageResponse schema
- ✅ Coverage card shows graceful "—" fallback when data not loaded

---
phase: 51-ai-analysis-improvement
plan: 02
subsystem: frontend-analysis-rendering
tags: [frontend, react, structured-ui, vietnamese]
dependency_graph:
  requires: [structured-combined-schema, raw-response-api]
  provides: [structured-combined-card, structured-frontend-rendering]
  affects: [ticker-detail-page]
tech_stack:
  added: []
  patterns: [structured-section-rendering, type-safe-raw-response-parsing]
key_files:
  created: []
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/components/analysis-card.tsx
    - frontend/src/app/ticker/[symbol]/page.tsx
decisions:
  - Keep CombinedRecommendationCard for backward compat but replace usage in ticker page
  - getStructuredData validates all 4 fields as strings before rendering structured view
  - Fallback to plain reasoning text when raw_response absent or invalid
metrics:
  duration: 2m 30s
  completed: "2026-04-24T15:15:00Z"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 3
---

# Phase 51 Plan 02: Structured Combined Analysis Frontend Summary

StructuredCombinedCard rendering 4 Vietnamese sections (Tóm tắt, Mức giá quan trọng, Rủi ro, Hành động cụ thể) with icons, visual hierarchy, and type-safe raw_response parsing with plain-text fallback.

## What Was Done

### Task 1: Update AnalysisResult type + Build StructuredCombinedCard component
**Commit:** `d3859b9`

- **api.ts**: Added `raw_response?: Record<string, unknown> | null` to `AnalysisResult` interface. Created `StructuredCombinedData` interface with 4 string fields (summary, key_levels, risks, action).
- **analysis-card.tsx**: Added imports for `Separator`, `FileText`, `DollarSign`, `AlertTriangle`, `Zap` icons, and `StructuredCombinedData` type. Created `getStructuredData()` helper that validates all 4 fields exist and are strings before returning typed data (returns null otherwise). Defined `COMBINED_SECTIONS` config array with Vietnamese labels and icons. Built `StructuredCombinedCard` component that renders recommendation badge + confidence header, separator, 4 structured sections with icons when raw_response is valid, or falls back to plain `analysis.reasoning` text for old data.

### Task 2: Wire StructuredCombinedCard into ticker detail page
**Commit:** `a9206ed`

- **ticker/[symbol]/page.tsx**: Replaced `CombinedRecommendationCard` import with `StructuredCombinedCard`. Updated component usage at line 296 — drop-in replacement using same `CombinedCardProps` interface.

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

| Check | Result |
|-------|--------|
| TypeScript: zero errors | ✅ |
| StructuredCombinedCard in analysis-card.tsx AND ticker page | ✅ |
| CombinedRecommendationCard removed from ticker page | ✅ |
| raw_response in AnalysisResult interface | ✅ |
| StructuredCombinedData in api.ts | ✅ |
| Vietnamese section labels (Tóm tắt, Mức giá, Rủi ro, Hành động) | ✅ |
| getStructuredData validates fields as strings | ✅ |
| Fallback to analysis.reasoning preserved | ✅ |

## Self-Check: PASSED

- [x] `frontend/src/lib/api.ts` — FOUND
- [x] `frontend/src/components/analysis-card.tsx` — FOUND
- [x] `frontend/src/app/ticker/[symbol]/page.tsx` — FOUND
- [x] Commit `d3859b9` — FOUND
- [x] Commit `a9206ed` — FOUND

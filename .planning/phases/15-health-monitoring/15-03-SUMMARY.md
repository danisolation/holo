---
phase: 15
plan: 15-03
title: "Frontend — Gemini Usage Card + Pipeline Timeline"
subsystem: frontend-health
tags: [gemini-usage, pipeline-timeline, recharts, health-dashboard, ui]
dependency_graph:
  requires: [gemini-usage-api, pipeline-timeline-api]
  provides: [gemini-usage-card, pipeline-timeline-component]
  affects: [health-page]
tech_stack:
  added: []
  patterns: [progress-bar-color-thresholds, horizontal-bar-chart, date-navigation-selector, mini-area-trend-chart]
key_files:
  created:
    - frontend/src/components/gemini-usage-card.tsx
    - frontend/src/components/pipeline-timeline.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/dashboard/health/page.tsx
decisions:
  - "formatTokens helper with 1M/K thresholds for concise token display"
  - "hsl(var(--primary)) for Recharts fills to follow theme system"
  - "getLast7Dates computed client-side for date navigation buttons"
  - "font-bold replaced with font-semibold on health page heading per typography contract"
metrics:
  duration: "5m"
  completed: "2026-04-17"
  tasks: 4
  tests_added: 0
  tests_total: 358
---

# Phase 15 Plan 03: Frontend — Gemini Usage Card + Pipeline Timeline Summary

**One-liner:** GeminiUsageCard with color-threshold progress bars, 2×2 breakdown grid, and 7-day trend mini chart; PipelineTimeline with horizontal Recharts BarChart, Vietnamese job names, status-colored bars, and 7-day date navigation — both integrated into health dashboard layout.

## Tasks Completed

| # | Task | Commit | Key Files |
|---|------|--------|-----------|
| 1 | T-15-06: API types + fetch functions + hooks | `a3f7be7` | api.ts, hooks.ts |
| 2 | T-15-07: GeminiUsageCard component | `fb2be51` | gemini-usage-card.tsx |
| 3 | T-15-08: PipelineTimeline component | `669fb2f` | pipeline-timeline.tsx |
| 4 | T-15-09: Health page layout update | `77dd824` | health/page.tsx |

## Implementation Details

### T-15-06: API Types + Fetch Functions + Hooks
- **Types:** `GeminiUsageTodayBreakdown`, `GeminiUsageToday`, `GeminiUsageDaily`, `GeminiUsageResponse` for Gemini usage; `PipelineStep`, `PipelineRun`, `PipelineTimelineResponse` for timeline
- **Fetch functions:** `fetchGeminiUsage(days=7)` → `GET /api/health/gemini-usage?days=N`; `fetchPipelineTimeline(days=7)` → `GET /api/health/pipeline-timeline?days=N`
- **Hooks:** `useGeminiUsage(days)` and `usePipelineTimeline(days)` with 60s staleTime and 120s refetchInterval matching existing health hook patterns

### T-15-07: GeminiUsageCard Component
- **Header:** Bot icon + "Gemini API Usage (Hôm nay)" in 14px font-semibold
- **Progress bars:** 8px rounded-full, `bg-primary` <75%, `bg-yellow-500` 75–90%, `bg-red-500` >90%; accessible `role="progressbar"` with `aria-valuenow`/`aria-valuemin`/`aria-valuemax`
- **Token formatting:** `formatTokens()` — values ≥1M as "1.2M", ≥1K as "780K"
- **Breakdown:** 2×2 grid with Technical/Fundamental/Sentiment/Combined labels and request counts
- **7-day trend:** Recharts AreaChart height 48px, no axes, monotone interpolation, primary theme gradient fill
- **States:** Skeleton h-48 (loading), "Không thể tải Gemini usage." (error)

### T-15-08: PipelineTimeline Component
- **Header:** Timer icon + "Pipeline Timeline" in 14px font-semibold, CardAction with date selector
- **Date navigation:** 7 Button ghost/sm for last 7 days; today labeled "Hôm nay" with default variant highlight
- **Bar chart:** Recharts horizontal `BarChart` layout="vertical", YAxis with Vietnamese job names (12px), XAxis in seconds
- **Bar colors:** `hsl(var(--primary))` (success), `#eab308` (partial/yellow-500), `#ef4444` (failed/red-500)
- **Duration labels:** Custom `LabelList` content rendering formatted duration right of each bar
- **Footer:** "Tổng: Xm Xs" in text-xs font-semibold
- **States:** Skeleton h-64 (loading), "Chưa có dữ liệu pipeline cho ngày này." (empty)

### T-15-09: Health Page Layout Update
- Inserted `GeminiUsageCard` after `HealthStatusCards`, before the grid section
- Inserted `PipelineTimeline` after the grid section, before `ErrorRateChart`
- Fixed `font-bold` → `font-semibold` on page heading to comply with typography contract
- Layout order: Header → HealthStatusCards → GeminiUsageCard → Grid(DataFreshness + DbPool + JobTrigger) → PipelineTimeline → ErrorRateChart

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed font-bold to font-semibold on health page heading**
- **Found during:** Task T-15-09
- **Issue:** Existing health page heading used `font-bold` (weight 700), violating the UI-SPEC typography contract (only font-semibold/600 allowed)
- **Fix:** Changed `font-bold` to `font-semibold` on the h2 element
- **Files modified:** `frontend/src/app/dashboard/health/page.tsx`
- **Commit:** `77dd824`

## Verification

- TypeScript compiles with 0 errors (`npx tsc --noEmit`)
- No `font-bold` usage in any new or modified component files
- All components follow UI-SPEC typography: 12/14/18/24px sizes, font-semibold (600) only
- Progress bars have proper ARIA attributes for accessibility
- Color is never the sole indicator — text labels accompany all color coding

## Self-Check: PASSED

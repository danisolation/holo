---
phase: 47-goals-weekly-reviews
plan: 03
subsystem: frontend
tags: [react, next.js, shadcn, react-query, goals, weekly-reviews, coach-page]
requires:
  - phase: 47-goals-weekly-reviews
    plan: 02
    provides: "7 API endpoints at /api/goals/* for goals, prompts, reviews"
provides:
  - "3 TypeScript interfaces (GoalResponse, WeeklyPromptResponse, WeeklyReviewResponse) in api.ts"
  - "5 fetch functions for goals API endpoints in api.ts"
  - "5 React Query hooks (useCurrentGoal, useSetGoal, useWeeklyPrompt, useRespondWeeklyPrompt, useLatestReview) in hooks.ts"
  - "MonthlyGoalCard component with 3-color progress bar and 4 states"
  - "SetGoalDialog component with validation and loading/error states"
  - "WeeklyPromptCard component with conditional render and 3 response buttons"
  - "WeeklyReviewCard component with collapsible Vietnamese prose and highlights/suggestions"
  - "Coach page Section 5: Goals & Weekly Reviews between pick history and behavior insights"
affects: []
tech-stack:
  added: []
  patterns: ["Self-contained components fetch own data via hooks", "Conditional render for prompt card (no DOM when no pending)"]
key-files:
  created:
    - frontend/src/components/monthly-goal-card.tsx
    - frontend/src/components/set-goal-dialog.tsx
    - frontend/src/components/weekly-prompt-card.tsx
    - frontend/src/components/weekly-review-card.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/coach/page.tsx
key-decisions:
  - "Progress bar color computed client-side from progress_pct (3-tier: green>=100%, amber 50-99%, red<50%)"
  - "WeeklyReviewCard expanded by default for immediate value delivery"
  - "WeeklyPromptCard returns null (no DOM) when no pending prompt — matches Risk Banner pattern"
  - "SetGoalDialog resets form state on open via useEffect"
requirements-completed: [GOAL-01, GOAL-02, GOAL-03]
duration: 5min
completed: 2026-04-23
---

# Phase 47 Plan 03: Frontend Components & Coach Page Integration Summary

**4 new components (MonthlyGoalCard, SetGoalDialog, WeeklyPromptCard, WeeklyReviewCard), 3 API types, 5 fetch functions, 5 React Query hooks, and coach page Section 5 integration with Vietnamese copy per UI-SPEC**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-23T12:51:59Z
- **Completed:** 2026-04-23T12:56:28Z
- **Tasks:** 3 (2 auto + 1 checkpoint auto-approved)
- **Files modified:** 7

## Accomplishments

- 3 TypeScript interfaces matching backend Pydantic schemas (GoalResponse with progress_color, WeeklyPromptResponse, WeeklyReviewResponse with nested highlights)
- 5 fetch functions following existing apiFetch pattern (fetchCurrentGoal, setGoal, fetchWeeklyPrompt, respondWeeklyPrompt, fetchLatestReview)
- 5 React Query hooks with correct staleTime (5min for goals/prompts, 10min for reviews) and cache invalidation (["goals", "current"], ["goals", "weekly-prompt"], ["profile"])
- MonthlyGoalCard: 4 states (loading skeleton, error graceful degradation, no-goal empty state with CTA, goal-set with progress bar). Progress bar has role="progressbar" + aria attributes
- SetGoalDialog: client-side validation (100k min, 1B max per T-47-07), pre-fill for edit mode, loading/error states
- WeeklyPromptCard: conditional render (null when no pending prompt), 3 buttons with risk_level boundary guards (disable at 1 or 5), responding state with Loader2 on clicked button
- WeeklyReviewCard: expanded by default, collapsible with aria-expanded, Vietnamese prose + highlights (good in green, bad in red) + suggestions + stats footer
- Coach page Section 5 "Mục tiêu & Nhận xét" inserted between pick history and behavior insights
- `next build` passes with zero TypeScript/build errors

## Task Commits

1. **Task 1: API types, fetch functions, hooks, MonthlyGoalCard, SetGoalDialog** - `3da0aea` (feat)
2. **Task 2: WeeklyPromptCard, WeeklyReviewCard, coach page Section 5** - `9a074b7` (feat)
3. **Task 3: Checkpoint human-verify** - auto-approved (autonomous mode)

## Files Created/Modified

- `frontend/src/lib/api.ts` — Added GoalResponse, WeeklyPromptResponse, WeeklyReviewResponse interfaces + 5 fetch functions
- `frontend/src/lib/hooks.ts` — Added 5 React Query hooks: useCurrentGoal, useSetGoal, useWeeklyPrompt, useRespondWeeklyPrompt, useLatestReview
- `frontend/src/components/monthly-goal-card.tsx` — Self-contained MonthlyGoalCard with 3-color progress bar and SetGoalDialog integration
- `frontend/src/components/set-goal-dialog.tsx` — SetGoalDialog with validation, loading state, error handling, edit mode pre-fill
- `frontend/src/components/weekly-prompt-card.tsx` — Conditional WeeklyPromptCard with 3 response buttons and risk_level bounds
- `frontend/src/components/weekly-review-card.tsx` — Collapsible WeeklyReviewCard with Vietnamese prose, highlights, suggestions, stats footer
- `frontend/src/app/coach/page.tsx` — Section 5 "Mục tiêu & Nhận xét" with 3 new component imports, Section 6 rename

## Decisions Made

- **Progress bar color client-side**: Computed from progress_pct using 3-tier thresholds rather than relying solely on server-side progress_color field — allows consistent styling
- **WeeklyReviewCard expanded by default**: Agent's discretion resolved — expanded for immediate value delivery on page load
- **WeeklyPromptCard null render**: Returns null (no DOM) when no pending prompt, matching existing Risk Banner conditional pattern from Phase 46
- **SetGoalDialog form reset**: Uses useEffect on open/currentTarget to reset form state, preventing stale data between open/close cycles

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TypeScript closure narrowing in WeeklyPromptCard**
- **Found during:** Task 2 build verification
- **Issue:** TypeScript couldn't narrow `prompt` type inside `handleRespond` closure despite early return guard
- **Fix:** Added explicit `if (!prompt) return;` guard inside `handleRespond` function
- **Files modified:** frontend/src/components/weekly-prompt-card.tsx
- **Commit:** 9a074b7

## Self-Check: PASSED

All 7 files verified present. Both commit hashes (3da0aea, 9a074b7) confirmed in git log.

---
*Phase: 47-goals-weekly-reviews*
*Completed: 2026-04-23*

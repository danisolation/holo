---
phase: 47-goals-weekly-reviews
plan: 01
subsystem: database, api
tags: [sqlalchemy, alembic, pydantic, gemini, goals, weekly-reviews, tdd]
requires:
  - phase: 46-behavior-tracking
    provides: "HabitDetection model, BehaviorService pattern, UserRiskProfile, Trade model"
provides:
  - "Migration 023 with trading_goals, weekly_prompts, weekly_reviews tables"
  - "TradingGoal, WeeklyPrompt, WeeklyReview ORM models"
  - "Pydantic schemas for goals API (GoalCreate, GoalResponse, WeeklyPromptRespondRequest, WeeklyReviewResponse)"
  - "GoalService with pure functions (compute_goal_progress, clamp_risk_level, build_review_prompt, parse_review_response)"
  - "GoalService async methods for goal CRUD, weekly prompt CRUD, and Gemini review generation"
affects: [47-02-api-routes, 47-03-frontend, scheduler-jobs]
tech-stack:
  added: []
  patterns: ["3-stage Gemini fallback (parsed → low-temp retry → manual JSON parse)", "WeeklyReviewOutput Pydantic model for Gemini structured output"]
key-files:
  created:
    - backend/alembic/versions/023_goals_weekly_reviews.py
    - backend/app/models/trading_goal.py
    - backend/app/models/weekly_prompt.py
    - backend/app/models/weekly_review.py
    - backend/app/schemas/goals.py
    - backend/app/services/goal_service.py
    - backend/tests/test_goal_service.py
    - backend/tests/test_goal_schemas.py
  modified:
    - backend/app/models/__init__.py
key-decisions:
  - "Gemini review uses WeeklyReviewOutput Pydantic model for structured output (summary_text + highlights + suggestions)"
  - "3-stage Gemini fallback pattern matching gemini_client.py (parsed → low-temp retry → JSON parse)"
  - "build_review_prompt includes sector context (agent's discretion: yes, include for richer reviews)"
  - "GoalService takes optional api_key parameter matching PickService pattern"
patterns-established:
  - "GoalService follows BehaviorService pattern: module-level pure functions + async class"
  - "WeeklyReviewOutput as Pydantic BaseModel for Gemini response_schema"
requirements-completed: [GOAL-01, GOAL-02, GOAL-03]
duration: 5min
completed: 2026-04-23
---

# Phase 47 Plan 01: Backend Data Layer Summary

**Migration 023 (3 tables), ORM models, Pydantic schemas with validation, GoalService with pure functions + Gemini review generation, and 35 TDD unit tests**

## Performance

- **Duration:** 5 min
- **Started:** 2026-04-23T12:37:09Z
- **Completed:** 2026-04-23T12:42:29Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Migration 023 creates trading_goals, weekly_prompts, weekly_reviews tables with indexes
- 3 ORM models (TradingGoal, WeeklyPrompt, WeeklyReview) following mapped_column style
- Pydantic schemas with Field(gt=0, le=1B) for target_pnl and Literal["cautious","unchanged","aggressive"] for prompt response — mitigates T-47-01 and T-47-02
- GoalService with 4 pure functions + 10 async DB methods + Gemini review generation with 3-stage fallback
- 35 passing unit tests (10 schema + 25 pure function) covering all edge cases

## Task Commits

1. **Task 1: Migration 023, ORM models, Pydantic schemas** - `242c147` (feat)
2. **Task 2: GoalService pure functions + async methods + unit tests** - `9b5e757` (feat)

## Files Created/Modified

- `backend/alembic/versions/023_goals_weekly_reviews.py` — Migration: trading_goals, weekly_prompts, weekly_reviews tables with indexes
- `backend/app/models/trading_goal.py` — TradingGoal ORM model (target_pnl, month, status)
- `backend/app/models/weekly_prompt.py` — WeeklyPrompt ORM model (week_start, response, risk_level tracking)
- `backend/app/models/weekly_review.py` — WeeklyReview ORM model (summary_text, JSONB highlights/suggestions, trade stats)
- `backend/app/models/__init__.py` — Added TradingGoal, WeeklyPrompt, WeeklyReview imports and __all__
- `backend/app/schemas/goals.py` — 7 Pydantic schemas: GoalCreate, GoalResponse, GoalHistoryResponse, WeeklyPromptResponse, WeeklyPromptRespondRequest, WeeklyReviewResponse, WeeklyReviewHistoryResponse
- `backend/app/services/goal_service.py` — GoalService: 4 pure functions + 10 async methods + Gemini review generation
- `backend/tests/test_goal_service.py` — 25 pure function tests (progress, clamping, prompt building, response parsing)
- `backend/tests/test_goal_schemas.py` — 10 schema validation tests (target_pnl bounds, Literal response)

## Decisions Made

- **Gemini structured output schema**: Created WeeklyReviewOutput as Pydantic BaseModel (summary_text, highlights dict, suggestions list) for genai response_schema parameter
- **3-stage Gemini fallback**: Matches existing gemini_client.py pattern — response.parsed → low-temperature retry (0.1) → manual json.loads parse
- **Include sector context in reviews**: Agent's discretion resolved — yes, include sector preference data for richer coaching context
- **GoalService constructor**: Takes optional api_key matching PickService pattern — defaults to settings.gemini_api_key

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All models, schemas, and service logic ready for API endpoint wiring (Plan 02)
- GoalService exposes all methods needed by API routes: set_goal, get_current_goal, get_goal_history, get_pending_prompt, create_weekly_prompt, respond_to_prompt, get_latest_review, get_review_history, generate_review
- Scheduler jobs (create_weekly_risk_prompt, generate_weekly_review) can call GoalService methods directly

## Self-Check: PASSED

All 9 files verified present. Both commit hashes (242c147, 9b5e757) confirmed in git log.

---
*Phase: 47-goals-weekly-reviews*
*Completed: 2026-04-23*

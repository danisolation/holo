---
phase: 47-goals-weekly-reviews
plan: 02
subsystem: api, scheduler
tags: [fastapi, apscheduler, goals, weekly-prompts, weekly-reviews, gemini, chaining]
requires:
  - phase: 47-goals-weekly-reviews
    plan: 01
    provides: "GoalService, schemas, ORM models"
provides:
  - "7 API endpoints at /api/goals/* for goals, prompts, reviews"
  - "goals_router registered in main api_router"
  - "create_weekly_risk_prompt scheduler job (Monday 8:00 AM)"
  - "generate_weekly_review scheduler job (Sunday 21:00 + chained from weekly_behavior_analysis)"
affects: [47-03-frontend]
tech-stack:
  added: []
  patterns: ["async_session context manager per endpoint (no Depends)", "lazy GoalService import in scheduler jobs"]
key-files:
  created:
    - backend/app/api/goals.py
  modified:
    - backend/app/api/router.py
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
    - backend/tests/test_scheduler.py
key-decisions:
  - "GET endpoints return None (null JSON) instead of 404 for missing data — frontend shows empty state"
  - "Query params page/page_size validated with ge=1, le=100 via FastAPI Query"
  - "WeeklyPromptResponse maps prompt_type field defaulting to 'risk_tolerance' if None"
  - "Chaining from weekly_behavior_analysis triggers generate_weekly_review_triggered (separate ID from cron)"
duration: 4min
completed: 2026-04-23
---

# Phase 47 Plan 02: Backend API & Scheduler Summary

**7 goals API endpoints (POST/GET for goals, prompts, reviews), router registration, 2 scheduler jobs (Monday prompt + Sunday review), and weekly_behavior_analysis → generate_weekly_review chaining**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-23T19:45:37Z
- **Completed:** 2026-04-23T19:49:29Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- 7 API endpoints in `backend/app/api/goals.py` following behavior.py pattern
- POST /api/goals validates target_pnl > 0, le 1B via Pydantic (T-47-01)
- POST /api/goals/weekly-prompt/{id}/respond validates Literal response (T-47-02)
- GET /api/goals/history always sorted month DESC — no user-controlled sort (T-47-03)
- Both scheduler jobs use JobExecutionService for full audit trail (T-47-06)
- Chaining: weekly_behavior_analysis (Sun 20:00) → generate_weekly_review_triggered
- create_weekly_risk_prompt runs independently on Monday 8:00 AM cron
- 412 tests passing (0 failures, 0 regressions)

## Task Commits

1. **Task 1: Goals API endpoints + router registration** - `90c0877` (feat)
2. **Task 2: Scheduler jobs + manager registration + chaining** - `26cbcf2` (feat)
3. **Test fix: scheduler test job count** - `c019af7` (fix, Rule 1)

## Files Created/Modified

- `backend/app/api/goals.py` — 7 API endpoints: set goal, current goal, history, weekly prompt, respond, weekly review, review history
- `backend/app/api/router.py` — Added goals_router import and include_router
- `backend/app/scheduler/jobs.py` — 2 new async job functions: create_weekly_risk_prompt, generate_weekly_review
- `backend/app/scheduler/manager.py` — 3 _JOB_NAMES entries, chaining block, 2 cron registrations in configure_jobs
- `backend/tests/test_scheduler.py` — Updated job count assertion 8 → 10, added goal job ID assertions

## Decisions Made

- **None-not-404 pattern**: GET endpoints return None (null JSON) for missing goals/prompts/reviews — matches behavior.py pattern and lets frontend render empty states without error handling
- **Query param validation**: page (ge=1) and page_size (ge=1, le=100) validated via FastAPI Query defaults
- **Triggered job ID**: Chained review uses `generate_weekly_review_triggered` ID (distinct from cron `generate_weekly_review`) — matches existing pattern for daily chains
- **Lazy imports in jobs**: GoalService imported inside job functions to avoid circular imports — matches existing BehaviorService/PickService pattern

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated scheduler test job count**
- **Found during:** Task 2 verification
- **Issue:** test_configure_jobs_registers_six_jobs asserted 8 total jobs, but we added 2 new ones (now 10)
- **Fix:** Updated assertion to 10, added create_weekly_risk_prompt and generate_weekly_review job ID checks
- **Files modified:** backend/tests/test_scheduler.py
- **Commit:** c019af7

## Issues Encountered

None.

## Self-Check: PASSED

All 5 files verified present. All 3 commit hashes (90c0877, 26cbcf2, c019af7) confirmed in git log.

---
*Phase: 47-goals-weekly-reviews*
*Completed: 2026-04-23*

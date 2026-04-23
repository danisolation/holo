---
phase: 46-behavior-tracking-adaptive-strategy
plan: 02
subsystem: api, scheduler, services
tags: [fastapi, apscheduler, behavior-tracking, sector-bias, risk-management]

# Dependency graph
requires:
  - phase: 46-01
    provides: BehaviorService, 4 ORM models, Pydantic schemas
provides:
  - 6 REST API endpoints for behavior tracking
  - 2 scheduler jobs (weekly behavior analysis, daily consecutive loss check)
  - PickService sector bias integration in generate_daily_picks
affects: [46-03-frontend, pick-generation-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns: [scheduler-job-chaining, sector-bias-multiplier]

key-files:
  created:
    - backend/app/api/behavior.py
  modified:
    - backend/app/api/router.py
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
    - backend/app/services/pick_service.py
    - backend/app/services/behavior_service.py
    - backend/tests/test_scheduler.py

key-decisions:
  - "Added get_habit_detections() read method to BehaviorService (plan referenced it but missing from 46-01)"
  - "Sector bias uses select(SectorPreference).where(total_trades >= 3) inline in generate_daily_picks"
  - "daily_consecutive_loss_check chains from daily_pick_outcome_check (end of daily pipeline)"

patterns-established:
  - "Behavior API follows trades.py pattern: async_session context manager, service instantiation per request"
  - "Sector bias as multiplicative factor (1 + preference_score * 0.1) — bounded ±10% impact"

requirements-completed: [BEHV-01, BEHV-02, ADPT-01, ADPT-02]

# Metrics
duration: 4min
completed: 2026-04-23
---

# Phase 46 Plan 02: Backend API & Scheduler Summary

**6 behavior REST endpoints, 2 scheduler jobs (weekly habits + daily loss check), PickService sector bias multiplier — full backend wiring complete**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-23T18:43:19Z
- **Completed:** 2026-04-23T18:47:30Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- 6 API endpoints created following trades.py pattern (POST event, GET viewing-stats, GET habits, GET sector-preferences, GET risk-suggestion, POST risk-suggestion respond)
- behavior_router registered in api_router — all routes accessible at /api/behavior/*
- weekly_behavior_analysis job scheduled Sunday 20:00 (cron trigger, detect habits + refresh sector prefs)
- daily_consecutive_loss_check chains from daily_pick_outcome_check (extends daily pipeline)
- PickService Step 6.5: sector bias multiplier applied before sorting (min 3 trades, ±10% max impact)
- Full test suite 377 tests passing

## Task Commits

Each task was committed atomically:

1. **Task 1: API router with 6 behavior endpoints** - `10913ce` (feat)
2. **Task 2: Scheduler jobs + PickService sector bias integration** - `6594c80` (feat)

## Files Created/Modified
- `backend/app/api/behavior.py` — 6 API endpoints for behavior tracking (POST event, GET viewing-stats, habits, sector-prefs, risk-suggestion, POST respond)
- `backend/app/api/router.py` — Registered behavior_router in api_router
- `backend/app/services/behavior_service.py` — Added get_habit_detections() read method
- `backend/app/scheduler/jobs.py` — weekly_behavior_analysis + daily_consecutive_loss_check job functions
- `backend/app/scheduler/manager.py` — Job registration (cron + chaining + _JOB_NAMES)
- `backend/app/services/pick_service.py` — Sector bias Step 6.5 + Ticker.sector in signal query
- `backend/tests/test_scheduler.py` — Updated job count assertion to 8

## Decisions Made
- Added `get_habit_detections()` read method to BehaviorService — plan's GET /habits endpoint references this method but 46-01 only created the write path (detect_all_habits)
- Sector bias query uses inline `select(SectorPreference).where(total_trades >= 3)` — lightweight, no new service method needed
- daily_consecutive_loss_check chains at end of daily pipeline (after pick_outcome_check), not as standalone cron

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Missing get_habit_detections() method in BehaviorService**
- **Found during:** Task 1
- **Issue:** Plan specifies `service.get_habit_detections()` for GET /habits endpoint, but BehaviorService from 46-01 only has `detect_all_habits()` (write path)
- **Fix:** Added `get_habit_detections()` method that reads from habit_detections table, groups by habit_type, returns dict matching HabitDetectionsResponse schema
- **Files modified:** backend/app/services/behavior_service.py
- **Commit:** 10913ce

**2. [Rule 1 - Bug] Scheduler test expected 7 jobs, now 8**
- **Found during:** Task 2
- **Issue:** test_configure_jobs_registers_six_jobs asserted len(job_ids) == 7, now 8 with weekly_behavior_analysis
- **Fix:** Updated assertion to 8 and added weekly_behavior_analysis check
- **Files modified:** backend/tests/test_scheduler.py
- **Commit:** 6594c80

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Essential fixes for completeness. No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- All 6 API endpoints operational and tested via import verification
- Scheduler jobs registered and chained correctly
- PickService sector bias active for generate_daily_picks
- Frontend (Plan 03) can now call all /api/behavior/* endpoints
- Full test suite green (377 tests)

---
*Phase: 46-behavior-tracking-adaptive-strategy*
*Completed: 2026-04-23*

## Self-Check: PASSED

All 7 files verified present. Both task commits (10913ce, 6594c80) confirmed in git log.

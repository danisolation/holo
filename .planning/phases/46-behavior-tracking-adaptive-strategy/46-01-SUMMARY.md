---
phase: 46-behavior-tracking-adaptive-strategy
plan: 01
subsystem: database, services
tags: [sqlalchemy, alembic, pydantic, behavior-tracking, habit-detection, risk-management, sector-preferences]

# Dependency graph
requires:
  - phase: 44-trade-journal
    provides: Trade model with net_pnl, Lot model for open positions
  - phase: 45-pick-outcomes
    provides: DailyPick with pick_outcome, DailyPrice for post-sell analysis
provides:
  - 4 new DB tables (behavior_events, habit_detections, risk_suggestions, sector_preferences)
  - BehaviorService with 5 pure functions + 8 async DB methods
  - Pydantic schemas for all behavior API contracts
  - 54 unit tests (22 model/schema + 32 service)
affects: [46-02-api-scheduler, 46-03-frontend, pick-service-sector-bias]

# Tech tracking
tech-stack:
  added: []
  patterns: [centered-normalization-for-sector-bias, pure-function-habit-detection]

key-files:
  created:
    - backend/alembic/versions/022_behavior_tracking_tables.py
    - backend/app/models/behavior_event.py
    - backend/app/models/habit_detection.py
    - backend/app/models/risk_suggestion.py
    - backend/app/models/sector_preference.py
    - backend/app/schemas/behavior.py
    - backend/app/services/behavior_service.py
    - backend/tests/test_behavior_models.py
    - backend/tests/test_behavior_service.py
  modified:
    - backend/app/models/__init__.py

key-decisions:
  - "Renamed metadata to event_metadata (SQLAlchemy reserves 'metadata' attribute name)"
  - "Centered normalization for sector bias — subtract mean P&L so poor sectors get preference_score < 0"
  - "Impulsive trade detection uses Trade.created_at vs NewsArticle.published_at (not trade_date which is DATE only)"
  - "T-46-04 mitigation: validate suggestion status=pending before allowing risk response"

patterns-established:
  - "Centered normalization: subtract mean then divide by max_abs — produces values in [-1, 1] that naturally penalize below-average performers"
  - "Batch query for habit detection: collect all ticker_ids first, query DailyPrice in one shot, process in memory (Pitfall 6)"

requirements-completed: [BEHV-01, BEHV-02, ADPT-01, ADPT-02]

# Metrics
duration: 7min
completed: 2026-04-23
---

# Phase 46 Plan 01: Backend Data Layer Summary

**4 behavior tables via migration 022, BehaviorService with pure habit/risk/sector functions, 54 TDD unit tests — all backed by centered normalization for sector bias**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-23T11:32:17Z
- **Completed:** 2026-04-23T11:39:28Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Migration 022 creates 4 tables (behavior_events, habit_detections, risk_suggestions, sector_preferences) with proper FKs, indexes, defaults
- 5 pure functions for habit detection (premature sell, holding losers, impulsive trade), sector preference scoring, and consecutive loss checking
- BehaviorService class with 8 async DB methods (event logging, viewing stats, habit detection, risk suggestion management, sector preference computation)
- 54 unit tests passing (22 model/schema + 32 pure function tests), full suite 377 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration 022 + 4 ORM models + Pydantic schemas** - `41cc8a2` (feat)
2. **Task 2: BehaviorService pure functions + async methods + unit tests** - `8dd6bab` (feat)

## Files Created/Modified
- `backend/alembic/versions/022_behavior_tracking_tables.py` - Alembic migration for 4 behavior tables
- `backend/app/models/behavior_event.py` - BehaviorEvent ORM model (viewing/interaction events)
- `backend/app/models/habit_detection.py` - HabitDetection ORM model (trading habit patterns)
- `backend/app/models/risk_suggestion.py` - RiskSuggestion ORM model (risk level adjustments)
- `backend/app/models/sector_preference.py` - SectorPreference ORM model (sector performance tracking)
- `backend/app/models/__init__.py` - Registered 4 new models in __all__
- `backend/app/schemas/behavior.py` - 6 Pydantic schemas with regex validation
- `backend/app/services/behavior_service.py` - BehaviorService with 5 pure functions + 8 async methods
- `backend/tests/test_behavior_models.py` - 22 model/schema introspection tests
- `backend/tests/test_behavior_service.py` - 32 pure function unit tests

## Decisions Made
- Renamed `metadata` column to `event_metadata` — SQLAlchemy reserves `metadata` as a Declarative API attribute name
- Used centered normalization (subtract mean P&L) for sector preference scoring — this naturally penalizes poor sectors with preference_score < 0, addressing plan checker WARNING about sector bias formula
- Impulsive trade detection compares Trade.created_at (TIMESTAMP) with NewsArticle.published_at, per Pitfall 2 guidance
- Consecutive loss check orders by trade_date DESC, id DESC and filters side="SELL" only, per Pitfall 3

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Renamed metadata to event_metadata**
- **Found during:** Task 1 (ORM model creation)
- **Issue:** SQLAlchemy raises `InvalidRequestError: Attribute name 'metadata' is reserved when using the Declarative API`
- **Fix:** Renamed column attribute from `metadata` to `event_metadata` in model, migration, and tests
- **Files modified:** backend/app/models/behavior_event.py, backend/alembic/versions/022_behavior_tracking_tables.py, backend/tests/test_behavior_models.py
- **Verification:** All tests pass, migration applies cleanly
- **Committed in:** 41cc8a2 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix for SQLAlchemy compatibility. No scope creep.

## Issues Encountered
None beyond the metadata naming issue documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 4 tables created and migrated
- BehaviorService ready for API router integration (Plan 02)
- Pydantic schemas ready for endpoint request/response contracts
- Sector preference computation ready for PickService integration (Plan 03)
- Full test suite green (377 tests)

---
*Phase: 46-behavior-tracking-adaptive-strategy*
*Completed: 2026-04-23*

## Self-Check: PASSED

All 10 files verified present. Both task commits (41cc8a2, 8dd6bab) confirmed in git log.

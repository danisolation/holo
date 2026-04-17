---
phase: 06-resilience-foundation
plan: 01
subsystem: infra
tags: [circuit-breaker, sqlalchemy, alembic, postgresql, resilience]

requires:
  - phase: 05
    provides: core backend with models, crawlers, scheduler, telegram bot
provides:
  - JobExecution SQLAlchemy model for job tracking
  - FailedJob SQLAlchemy model for dead-letter queue
  - Alembic migration 005 creating both tables with indexes
  - AsyncCircuitBreaker class with 3-state machine
  - Three singleton circuit breaker instances (vnstock, cafef, gemini)
  - Config settings for circuit breaker thresholds and API timeouts
affects: [06-02, 06-03, 06-04]

tech-stack:
  added: []
  patterns: [async-circuit-breaker, dead-letter-queue, job-execution-tracking]

key-files:
  created:
    - backend/app/models/job_execution.py
    - backend/app/models/failed_job.py
    - backend/alembic/versions/005_resilience_tables.py
    - backend/app/resilience.py
    - backend/tests/test_circuit_breaker.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/config.py

key-decisions:
  - "Custom AsyncCircuitBreaker (~35 lines) instead of library — all 3 Python CB libraries have async bugs"
  - "Module-level singletons for per-API circuit breaker isolation"
  - "time.monotonic() for cooldown timing (not time.time()) — immune to system clock changes"
  - "JSONB column for result_summary — flexible schema for different job types"

patterns-established:
  - "Circuit breaker pattern: wrap external calls with breaker.call(func, *args) for automatic state management"
  - "Dead-letter queue pattern: FailedJob with retry_count, resolved_at for lifecycle tracking"
  - "Job execution tracking: JobExecution with JSONB result_summary for structured outcomes"

requirements-completed: [ERR-02, ERR-04, ERR-06]

duration: 8min
completed: 2026-04-17
---

# Plan 06-01: Resilience Foundation Summary

**AsyncCircuitBreaker with 3-state machine, JobExecution/FailedJob models, Alembic migration 005, and config settings for circuit breaker thresholds**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-17T04:00:00Z
- **Completed:** 2026-04-17T04:08:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- JobExecution model with JSONB result_summary for structured job outcome tracking
- FailedJob model (dead-letter queue) with retry_count and resolved_at lifecycle
- Alembic migration 005 creates both tables with indexes including partial index on unresolved items
- AsyncCircuitBreaker with CLOSED→OPEN→HALF_OPEN state machine, configurable thresholds
- Three singleton breaker instances (vnstock, cafef, gemini) reading from settings
- 10 unit tests covering all state transitions and edge cases — all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: DB models, migration, config** - `ce9ec24` (feat)
2. **Task 2: AsyncCircuitBreaker + unit tests** - `3b46325` (feat)

## Files Created/Modified
- `backend/app/models/job_execution.py` - JobExecution SQLAlchemy model
- `backend/app/models/failed_job.py` - FailedJob SQLAlchemy model (DLQ)
- `backend/app/models/__init__.py` - Added JobExecution, FailedJob imports
- `backend/alembic/versions/005_resilience_tables.py` - Migration creating both tables
- `backend/app/config.py` - Added circuit breaker + timeout settings
- `backend/app/resilience.py` - AsyncCircuitBreaker class + 3 singletons
- `backend/tests/test_circuit_breaker.py` - 10 unit tests for circuit breaker

## Decisions Made
- Used time.monotonic() for cooldown timing instead of time.time() — immune to clock changes
- Fixed test_half_open_failure_reopens to use time mock (monotonic resolution on Windows)

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
- test_half_open_failure_reopens initially failed due to same-tick monotonic() resolution on Windows — fixed by mocking time.monotonic in the test

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Circuit breaker singletons ready for integration into crawlers (Plan 06-03)
- Job tracking models ready for service layer (Plan 06-02)
- Config settings ready for all downstream plans

---
*Phase: 06-resilience-foundation*
*Completed: 2026-04-17*

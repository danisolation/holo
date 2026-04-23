---
phase: 43-daily-picks-engine
plan: "01"
title: "Daily Picks Data Layer"
subsystem: backend
tags: [models, schemas, migration, tests, daily-picks]
dependency_graph:
  requires: []
  provides: [DailyPick-model, UserRiskProfile-model, picks-schemas, migration-019, pick-test-scaffold]
  affects: [backend/app/models/__init__.py]
tech_stack:
  added: []
  patterns: [SQLAlchemy-mapped-column, Pydantic-BaseModel, Alembic-manual-migration]
key_files:
  created:
    - backend/app/models/daily_pick.py
    - backend/app/models/user_risk_profile.py
    - backend/alembic/versions/019_daily_picks_tables.py
    - backend/app/schemas/picks.py
    - backend/tests/test_pick_service.py
  modified:
    - backend/app/models/__init__.py
key_decisions:
  - "PickStatus as str enum (picked/almost) stored in String(10) column, not PostgreSQL ENUM — simpler, no migration hassle"
  - "position_size_vnd as BigInteger for VND amounts up to trillions"
  - "Manual Alembic migration with INSERT for default risk profile row"
metrics:
  duration: "3m 1s"
  completed: "2026-04-23T08:41:52Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 5
  files_modified: 1
  test_functions: 17
---

# Phase 43 Plan 01: Daily Picks Data Layer Summary

Database foundation for Daily Picks Engine — DailyPick + UserRiskProfile SQLAlchemy models, Alembic migration 019 with default profile row, Pydantic API schemas with validation, and 17-test scaffold covering PICK-01 through PICK-07.

## Tasks Completed

### Task 1: Create DailyPick + UserRiskProfile models and migration
- **Commit:** e89026d
- **Files:** `daily_pick.py`, `user_risk_profile.py`, `__init__.py`, `019_daily_picks_tables.py`
- Created DailyPick model with 16 columns: pick_date, ticker_id, rank, composite_score, entry_price, stop_loss, take_profit_1/2, risk_reward, position_size_shares/vnd/pct, explanation, status, rejection_reason, created_at
- Created UserRiskProfile single-row table with defaults: capital=50M, risk_level=3, broker_fee_pct=0.15%
- Alembic migration 019 creates both tables, adds unique constraint, inserts default profile row
- Models registered in `__init__.py` with PickStatus enum exported

### Task 2: Create Pydantic schemas and test scaffold
- **Commit:** 40bb127
- **Files:** `picks.py` (schemas), `test_pick_service.py`
- DailyPickResponse, DailyPicksResponse, ProfileResponse, ProfileUpdate schemas
- Pydantic validation: `capital = Field(gt=0)`, `risk_level = Field(ge=1, le=5)` — mitigates T-43-01 (tampering)
- 17 test functions across 7 test classes covering all PICK requirements (01-07)
- Tests are RED — import from `app.services.pick_service` which Plan 02 will create

## Verification Results

- ✅ All model imports clean: `from app.models import DailyPick, PickStatus, UserRiskProfile`
- ✅ All schema imports clean: `from app.schemas.picks import DailyPickResponse, DailyPicksResponse, ProfileResponse, ProfileUpdate`
- ✅ Migration 019 exists with upgrade/downgrade
- ✅ 7 test classes, 17 test functions covering PICK-01 through PICK-07
- ✅ Existing test suite unbroken: 277 passed in 25s

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all models have complete column definitions, schemas have all fields, tests have concrete assertions.

## Self-Check: PASSED

- All 7 files verified present on disk
- Commits e89026d and 40bb127 verified in git log

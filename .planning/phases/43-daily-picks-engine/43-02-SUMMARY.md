---
phase: 43-daily-picks-engine
plan: "02"
title: "Daily Picks Engine & API"
subsystem: backend
tags: [services, api, scheduler, picks, gemini, tests]
dependency_graph:
  requires: [DailyPick-model, UserRiskProfile-model, picks-schemas, migration-019, pick-test-scaffold]
  provides: [PickService, picks-api-endpoints, pick-generation-job, pick-scheduler-chain]
  affects: [backend/app/api/router.py, backend/app/scheduler/jobs.py, backend/app/scheduler/manager.py]
tech_stack:
  added: []
  patterns: [module-level-pure-functions, async-service-class, genai-client, job-chaining]
key_files:
  created:
    - backend/app/services/pick_service.py
    - backend/app/api/picks.py
  modified:
    - backend/app/api/router.py
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
    - backend/tests/test_pick_service.py
key_decisions:
  - "Position sizing test data fixed: floor(4M/6M)=0 not 6, updated expectations to min 1 lot=100 shares"
  - "Gemini explanation uses aio.models.generate_content (async) with graceful fallback — picks valid without explanations"
  - "Pick history caps at 365 days per T-43-06 DoS mitigation"
  - "Combined score defaults to 5 when missing for a ticker (neutral fallback per RESEARCH.md Pitfall 3)"
metrics:
  duration: "4m 55s"
  completed: "2026-04-23T15:50:08Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 4
  test_functions: 17
---

# Phase 43 Plan 02: Daily Picks Engine & API Summary

PickService with 7 pure scoring functions + 5 async methods, 4 API endpoints (GET today/history, GET/PUT profile), scheduler job chaining after HNX/UPCOM analysis — all 17 tests from Plan 01 GREEN.

## Tasks Completed

### Task 1: Create PickService with all computation functions (TDD)
- **Commit:** 6bef3da
- **Files:** `pick_service.py` (created), `test_pick_service.py` (fixed)
- 7 pure computation functions at module level for testability:
  - `compute_composite_score`: confidence×0.4 + combined×0.3 + safety×0.3
  - `is_affordable`: 1-lot minimum check against capital
  - `compute_safety_score`: ATR/ADX/volume normalized to 0-10 scale
  - `extract_trading_plan`: JSONB → dict from long_analysis.trading_plan
  - `compute_position_sizing`: VN lot-aligned (100 shares), capped at 30%
  - `generate_rejection_reason`: Vietnamese explanation for almost-selected
  - `build_explanation_prompt`: Gemini prompt with pick data
- PickService class with 5 async methods: generate_daily_picks, get_today_picks, get_pick_history, get_or_create_profile, update_profile
- Fixed test_position_sizing_normal: floor(4M/6M)=0 not 6, expects 100 shares (min lot)
- All 17 tests pass GREEN

### Task 2: Create API router + scheduler job chain + register
- **Commit:** c94773c
- **Files:** `picks.py` (API, created), `router.py`, `jobs.py`, `manager.py` (modified)
- GET /api/picks/today → DailyPicksResponse with picks + almost_selected arrays
- GET /api/picks/history → past picked tickers (cap 365 days per T-43-06)
- GET /api/profile → ProfileResponse (capital, risk_level, broker_fee_pct)
- PUT /api/profile → validates with Pydantic ProfileUpdate, returns updated profile
- daily_pick_generation job chains after daily_hnx_upcom_analysis_triggered
- Router registered in api_router via include_router(picks_router)
- All 277 existing tests + 17 pick tests pass

## Verification Results

- ✅ All 17 pick service tests pass GREEN: `pytest tests/test_pick_service.py -v`
- ✅ API imports clean: `from app.api.picks import router`
- ✅ Scheduler job importable: `from app.scheduler.jobs import daily_pick_generation`
- ✅ Existing test suite unbroken: 277 passed in 25s
- ✅ Pick service tests: 17 passed in 1.6s

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed position sizing test expectations**
- **Found during:** Task 1
- **Issue:** test_position_sizing_normal expected 600 shares (floor(4M/6M)=6) but correct math is floor(4M/6M)=0, min 1 lot=100 shares
- **Fix:** Updated test assertions to expect shares=100, total_vnd=6M
- **Files modified:** backend/tests/test_pick_service.py
- **Commit:** 6bef3da

## Known Stubs

None — all computation functions have complete implementations, all async methods have full DB queries, Gemini integration has graceful fallback.

## Self-Check: PASSED

- All 6 files verified present on disk
- Commits 6bef3da and c94773c verified in git log

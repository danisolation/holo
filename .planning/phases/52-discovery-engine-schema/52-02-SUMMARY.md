---
phase: 52-discovery-engine-schema
plan: "02"
title: "Scheduler Integration & Unit Tests"
one_liner: "Wire DiscoveryService into daily job chain (indicators→discovery→AI) with 33 comprehensive unit tests"
completed: "2026-05-04T08:33:00Z"
duration: "~3 min"
tasks_completed: 2
tasks_total: 2
subsystem: backend
tags: [discovery, scheduler, job-chain, testing, integration]
dependency_graph:
  requires: [DiscoveryService, discovery_results_table, technical_indicators, scheduler-chain]
  provides: [daily_discovery_scoring_job, scheduler-chain-with-discovery, discovery-unit-tests]
  affects: [daily-pipeline-execution-order]
tech_stack:
  added: []
  patterns: [job-chaining-via-EVENT_JOB_EXECUTED, mock-patch-object-tests]
key_files:
  created: []
  modified:
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
    - backend/tests/test_discovery_service.py
key_decisions:
  - "Discovery scoring inserted between indicators and AI in chain — replaces old direct link"
  - "Job follows existing pattern: JobExecutionService + try/except + _determine_status"
  - "Test file uses patch.object on service methods for cleaner service-level tests"
metrics:
  duration: "~3 min"
  completed: "2026-05-04"
  tasks: 2
  files: 3
  tests_added: 33
---

# Phase 52 Plan 02: Scheduler Integration & Unit Tests Summary

Wire DiscoveryService into daily job chain (indicators→discovery→AI) with 33 comprehensive unit tests

## What Was Done

### Task 1: Add discovery scoring job and integrate into scheduler chain
- Added `daily_discovery_scoring()` async job function to `backend/app/scheduler/jobs.py` following existing resilience pattern (JobExecutionService, try/except, status determination)
- **REPLACED** old direct chain link `indicator_compute → ai_analysis` with two-step: `indicator_compute → discovery_scoring → ai_analysis`
- Registered `daily_discovery_scoring_triggered` and `daily_discovery_scoring_manual` in `_JOB_NAMES`
- Updated chain description log string to include `discovery_scoring`
- **Critical verification:** old "Chaining: daily_indicator_compute → daily_ai_analysis" string does NOT exist (replaced)
- **Commit:** `d64baf4`

### Task 2: Enhance unit tests for discovery scoring
- Replaced test file with comprehensive 33-test suite (up from 27 in Plan 01)
- Added boundary tests: RSI floor at 100→0, MACD clamping at ±5→capped, P/E exactly at 10→10
- Added edge cases: medium ROE (15%→7.0), very low ROE (<2%), weak trend ADX, volume cap
- Added service integration tests using `patch.object` pattern (cleaner mocking)
- All 33 tests pass in 3.64s
- **Commit:** `a0ff52f`

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `d64baf4` | feat(52-02): wire discovery scoring into scheduler chain |
| 2 | `a0ff52f` | test(52-02): enhance discovery scoring unit tests |

## Verification Results

```
✓ from app.scheduler.jobs import daily_discovery_scoring → OK
✓ _JOB_NAMES contains 'daily_discovery_scoring_triggered' and 'daily_discovery_scoring_manual'
✓ Old direct link count (indicator→AI): 0 (removed)
✓ New chain link (indicator→discovery): 1
✓ New chain link (discovery→AI): 1
✓ 33/33 tests pass (pytest exit code 0)
✓ Test file: 229 lines (>80 minimum)
```

## Chain Order (After This Plan)

```
daily_price_crawl_hose
  → daily_indicator_compute
    → daily_discovery_scoring  ← NEW
      → daily_ai_analysis
        → daily_news_crawl
          → daily_sentiment_analysis
            → daily_combined_analysis
              → daily_trading_signal_analysis
                → daily_pick_generation
                  → daily_pick_outcome_check
                    → daily_consecutive_loss_check
```

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

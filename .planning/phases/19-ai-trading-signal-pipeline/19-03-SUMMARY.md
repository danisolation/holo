---
phase: 19-ai-trading-signal-pipeline
plan: 03
subsystem: backend-scheduler-api
tags: [scheduler, api, pipeline-wiring, trading-signal]
dependency_graph:
  requires: [19-02]
  provides: [daily_trading_signal_analysis-job, trading-signal-api-endpoints]
  affects: [scheduler-chain, summary-response]
tech_stack:
  added: []
  patterns: [job-chaining, background-task-trigger, resilience-dlq]
key_files:
  created: []
  modified:
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
    - backend/app/api/analysis.py
    - backend/app/schemas/analysis.py
    - backend/tests/test_telegram.py
decisions:
  - "Chain order: combined → trading_signal → signal_alerts + hnx_upcom (trading signal inserted before alerts)"
  - "Updated existing chain test to verify new 2-hop chain (combined → trading_signal → alerts)"
metrics:
  duration: 4.2m
  completed: 2026-04-20T04:40:00Z
  tasks: 2
  files: 5
---

# Phase 19 Plan 03: Pipeline Wiring (Scheduler Job + API Endpoints) Summary

**One-liner:** Daily trading signal job chained after combined analysis with GET/POST API endpoints and updated summary response.

## What Was Done

### Task 1: Scheduler Job + Chain Update + Job Name Mapping
- Added `daily_trading_signal_analysis()` async job function in `jobs.py` following exact resilience pattern (DLQ, job tracking, raise on complete failure)
- Updated job chain in `manager.py`: combined → trading_signal → signal_alerts + hnx_upcom_analysis
- Added `daily_trading_signal_triggered` and `daily_trading_signal_manual` to `_JOB_NAMES` dict
- Updated chain description log to include `trading_signal` step
- **Commit:** ea34006

### Task 2: API Endpoints + Summary Response Update
- Added `GET /{symbol}/trading-signal` endpoint returning latest trading signal analysis
- Added `POST /trigger/trading-signal` endpoint for manual background trigger
- Updated `SummaryResponse` schema with `trading_signal: AnalysisResultResponse | None` field
- Updated summary endpoint loop to include `AnalysisType.TRADING_SIGNAL`
- **Commit:** f004e2d

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated chain test for new trading signal insertion**
- **Found during:** Test suite verification after Task 2
- **Issue:** `test_combined_chains_to_signal_alerts` expected old chain (combined → signal_alerts) but chain now goes combined → trading_signal → signal_alerts
- **Fix:** Replaced single test with two tests: `test_combined_chains_to_trading_signal` and `test_trading_signal_chains_to_signal_alerts`
- **Files modified:** backend/tests/test_telegram.py
- **Commit:** 1ab04b1

## Verification Results

- ✅ `daily_trading_signal_analysis` importable from jobs.py
- ✅ Chain: combined → trading_signal → signal_alerts verified in manager.py
- ✅ Job name mapping includes `daily_trading_signal_triggered` and `daily_trading_signal_manual`
- ✅ GET /analysis/{symbol}/trading-signal route registered
- ✅ POST /analysis/trigger/trading-signal route registered
- ✅ SummaryResponse has `trading_signal` field
- ✅ Full test suite: 424 passed, 0 failed

## Self-Check: PASSED

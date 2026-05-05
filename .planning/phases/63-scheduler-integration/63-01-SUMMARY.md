---
phase: 63-scheduler-integration
plan: 01
subsystem: backend/scheduler
tags: [scheduler, rumor-pipeline, job-chaining]
dependency_graph:
  requires: [60-01, 61-01]
  provides: [daily_rumor_crawl, daily_rumor_scoring, chain-wiring]
  affects: [scheduler/manager, scheduler/jobs, api/health]
tech_stack:
  added: []
  patterns: [apscheduler-job-chaining, dlq-failure-isolation]
key_files:
  created: []
  modified:
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
    - backend/app/api/health.py
decisions:
  - "Rumor jobs follow exact same pattern as daily_indicator_compute (async_session, JobExecutionService, DLQ, raise on complete failure)"
  - "ValueError catch in daily_rumor_scoring for missing GEMINI_API_KEY — skip gracefully like daily_ai_analysis"
  - "Chain replaced (not duplicated): trading_signal → rumor_crawl instead of trading_signal → pick_generation"
metrics:
  duration: ~3min
  completed: 2026-05-05
  tasks: 2/2
requirements: [RUMOR-03]
---

# Phase 63 Plan 01: Scheduler Integration Summary

**One-liner:** Wire daily_rumor_crawl and daily_rumor_scoring into APScheduler chain between trading_signal and pick_generation with DLQ failure isolation.

## What Was Done

### Task 1: Add job functions to jobs.py
- Added `daily_rumor_crawl()` — crawls Fireant posts via FireantCrawler, DLQ on failures, raises RuntimeError on complete failure
- Added `daily_rumor_scoring()` — scores rumors via RumorScoringService (Gemini AI), converts {symbol: bool} to standard result dict, ValueError catch for missing API key
- Both follow the established job pattern exactly: lazy imports, async_session, JobExecutionService start/complete/fail, _determine_status, _build_summary, _dlq_failures

### Task 2: Wire chain and manual triggers
- **Chain rewired in manager.py:** `trading_signal → rumor_crawl → rumor_scoring → pick_generation`
- Old `trading_signal → pick_generation` link replaced (not duplicated)
- Added 4 entries to `_JOB_NAMES`: daily_rumor_crawl_triggered, daily_rumor_crawl_manual, daily_rumor_scoring_triggered, daily_rumor_scoring_manual
- Added 2 entries to `JOB_TRIGGER_MAP` in health.py: rumor_crawl, rumor_scoring
- Both `_manual` and `_triggered` IDs chain forward correctly

## Chain Order (verified)

```
daily_price_crawl_hose → indicators → discovery_scoring → AI → news → sentiment → combined → trading_signal → rumor_crawl → rumor_scoring → pick_generation → pick_outcome_check → consecutive_loss_check
```

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 3f476f0 | Add daily_rumor_crawl and daily_rumor_scoring job functions |
| 2 | df9a29a | Wire rumor chain in manager.py and add manual triggers in health.py |

## Self-Check: PASSED

- [x] `backend/app/scheduler/jobs.py` — modified, both functions importable
- [x] `backend/app/scheduler/manager.py` — modified, chain wiring correct
- [x] `backend/app/api/health.py` — modified, trigger map entries present
- [x] Commit 3f476f0 exists
- [x] Commit df9a29a exists

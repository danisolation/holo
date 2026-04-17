---
phase: 15
plan: 15-02
title: "Pipeline Timeline API + Health Alerts"
subsystem: backend-health
tags: [pipeline-timeline, health-alerts, telegram, scheduler, gantt]
dependency_graph:
  requires: [gemini-usage-model, gemini-usage-service, gemini-usage-api]
  provides: [pipeline-timeline-api, health-alert-service, health-alert-scheduler]
  affects: [health-api, health-schemas, scheduler-manager, telegram-formatter]
tech_stack:
  added: []
  patterns: [date-grouping-timeline, cooldown-deduplication, never-raises-scheduler, vietnamese-alert-format]
key_files:
  created:
    - backend/app/services/health_alert_service.py
    - backend/tests/test_pipeline_timeline.py
    - backend/tests/test_health_alerts.py
  modified:
    - backend/app/api/health.py
    - backend/app/schemas/health.py
    - backend/app/services/health_service.py
    - backend/app/scheduler/manager.py
    - backend/app/scheduler/jobs.py
    - backend/app/telegram/formatter.py
    - backend/tests/test_scheduler.py
decisions:
  - "_JOB_NAMES_VN Vietnamese mapping at module level in health_service.py for timeline-specific display names"
  - "In-memory _last_alert_times dict for cooldown — reset on app restart is acceptable for single-user"
  - "health_alert_check never-raises pattern (try/except) to avoid polluting EVENT_JOB_ERROR listener"
  - "telegram_bot lazy import inside check_and_alert to avoid circular import at module level"
metrics:
  duration: "9m"
  completed: "2026-04-17"
  tasks: 2
  tests_added: 24
  tests_total: 358
---

# Phase 15 Plan 02: Pipeline Timeline API + Health Alerts Summary

**One-liner:** Pipeline timeline Gantt API with date-grouped runs + Vietnamese name mapping, plus proactive HealthAlertService with 4h-cooldown Telegram alerts for job failures, stale data, and pool exhaustion on a 30-min scheduler.

## Tasks Completed

| # | Task | Commit | Test Count |
|---|------|--------|------------|
| 1 | T-15-04: Pipeline timeline API endpoint (TDD) | `885adda` → `a217701` | 13 |
| 2 | T-15-05: Health alert service + scheduler job (TDD) | `7298dc5` → `aa51240` | 11 |

## Implementation Details

### T-15-04: Pipeline Timeline API Endpoint
- **Schemas:** `PipelineStep`, `PipelineRun`, `PipelineTimelineResponse` in `health.py`
- **Service:** `HealthService.get_pipeline_timeline(days)` queries `job_executions`, groups by `DATE(started_at)`, computes `duration_seconds` from `completed_at - started_at`, sums `total_seconds` per run
- **Vietnamese mapping:** `_JOB_NAMES_VN` dict with 8 pipeline job Vietnamese labels (e.g., "Crawl giá HOSE", "Tính chỉ báo KT")
- **Endpoint:** `GET /health/pipeline-timeline?days=7` (default 7, max 30 via `min()` cap)
- **Tests:** Structure validation, date grouping, duration computation, None duration for incomplete jobs, total_seconds summation, empty result, Vietnamese names, 6 API endpoint tests

### T-15-05: Health Alert Service + Scheduler Job
- **HealthAlertService** (`health_alert_service.py`):
  - `check_and_alert()`: runs 3 checks sequentially, sends Telegram alerts via `telegram_bot.send_message()`
  - `_check_job_failures()`: SQL `HAVING COUNT(*) >= 3` for same `job_id` failed in 24h
  - `_check_stale_data()`: leverages `HealthService.get_data_freshness()` and checks `is_stale` flag
  - `_check_pool_exhaustion()`: `engine.pool.checkedout() / pool.size() > 0.8`
- **Cooldown:** Module-level `_last_alert_times` dict, `COOLDOWN_HOURS = 4`, per alert type ("job_failures", "stale_data", "pool_exhaustion")
- **MessageFormatter.health_alert():** Vietnamese HTML with emoji severity (🔴 critical / 🟡 warning), item list, "/dashboard/health" link
- **Scheduler:** `health_alert_check` job runs `CronTrigger(minute="*/30")` — every 30min, all day, every day. Never-raises pattern with try/except + logging. Added to `_JOB_NAMES` mapping.
- **Tests:** Consecutive failure detection, no alert below threshold, stale data alert, cooldown prevention, cooldown expiry, pool exhaustion, 3 message format tests, job name mapping, scheduler registration

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing scheduler test for 7th job**
- **Found during:** Task T-15-05
- **Issue:** `test_configure_jobs_registers_six_jobs` in `test_scheduler.py` asserted exactly 6 jobs; health_alert_check is now the 7th
- **Fix:** Updated assertion to check 7 jobs and added `health_alert_check` to expected IDs
- **Files modified:** `backend/tests/test_scheduler.py`
- **Commit:** `aa51240`

## Self-Check: PASSED

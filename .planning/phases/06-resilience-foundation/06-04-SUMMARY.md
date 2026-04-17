# Plan 06-04 Summary: Job Refactoring + Resilience Tests

## Status: COMPLETE

## What Was Done

### Task 1: Refactored All 11 Job Functions
All job functions in `backend/app/scheduler/jobs.py` now include:

1. **Job execution tracking (D-13/D-14):** `JobExecutionService.start()` at beginning, `.complete()` or `.fail()` at end
2. **Failed ticker retry (D-06):** `daily_price_crawl` retries failed tickers via `_crawl_batch` with only failed symbols
3. **Dead-letter queue (D-08/D-09):** Permanently failed tickers sent to DLQ via `_dlq_failures` helper
4. **Graceful degradation (Pitfall 2):** Partial failure returns normally (chain continues); complete failure raises `RuntimeError` (chain breaks → `EVENT_JOB_ERROR` → Telegram alert)
5. **Alert jobs never raise:** `daily_signal_alert_check`, `daily_price_alert_check`, `daily_summary_send` track execution but catch all exceptions

Helper functions added:
- `_determine_status(result)` → "success" / "partial" / "failed"
- `_build_summary(result, retried, dlq_count)` → standardized JSONB summary
- `_dlq_failures(session, job_type, failed_symbols)` → batch DLQ insert
- `_merge_ai_failed_symbols(results)` / `_sum_ai_results(results)` → AI result aggregation

### Task 2: Created test_resilience.py (8 Tests)
- `test_retry_rebatch_failed_tickers` (ERR-01)
- `test_failed_items_added_to_dlq` (ERR-02)
- `test_retry_then_dlq` (ERR-07)
- `test_partial_failure_continues_chain` (ERR-03)
- `test_complete_failure_raises` (ERR-03)
- `test_job_execution_logged` (ERR-04)
- `test_complete_failure_sends_telegram` (ERR-05)
- `test_signal_alert_check_never_raises` (alert safety)

### Task 2b: Updated test_scheduler.py
- Added `_mock_job_svc()` helper for JobExecutionService mocking
- Updated all 8 job function tests to include `JobExecutionService` mock

## Commits
- `b8cd78f` — feat(06-04): refactor jobs with tracking, retry, DLQ + resilience tests

## Test Results
- 114/114 tests pass (106 existing + 8 new resilience tests)

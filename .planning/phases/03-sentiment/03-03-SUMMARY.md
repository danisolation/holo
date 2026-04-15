---
phase: 03-sentiment
plan: "03"
subsystem: scheduler-api-tests
tags: [scheduler, api, testing, sentiment, combined, cafef]
dependency_graph:
  requires: [03-01, 03-02]
  provides: [full-pipeline-chain, sentiment-api, combined-api, summary-api, phase3-tests]
  affects: [scheduler/jobs.py, scheduler/manager.py, api/analysis.py]
tech_stack:
  added: []
  patterns: [job-chaining-extension, background-task-triggers, summary-endpoint]
key_files:
  created:
    - backend/tests/test_cafef_crawler.py
  modified:
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
    - backend/app/api/analysis.py
    - backend/tests/test_ai_analysis_service.py
    - backend/tests/test_scheduler.py
    - backend/tests/test_api.py
decisions:
  - "Summary endpoint returns all 4 dimensions without 404 for missing — graceful partial data"
  - "Job chain IDs: _triggered (from chain) and _manual (from API) — matches Phase 2 pattern"
metrics:
  duration: 4m
  completed: 2026-04-15
  tasks: 2
  files: 7
---

# Phase 3 Plan 3: Scheduler Chain + API Endpoints + Tests Summary

Extended scheduler job chain from AI→news→sentiment→combined, added 6 API endpoints (3 triggers + sentiment/combined/summary results), and wrote 27 new tests covering CafeF parsing, prompt building, schema validation, chaining, and endpoint responses.

## What Was Done

### Task 1: Scheduler job chaining extension + API endpoints
- **jobs.py**: Added `daily_news_crawl`, `daily_sentiment_analysis`, `daily_combined_analysis` — same pattern as existing jobs (lazy imports, try/except, async_session)
- **manager.py**: Extended `_on_job_executed` with 3 new `elif` blocks for chain: AI → news → sentiment → combined. Both `_triggered` and `_manual` variants handled.
- **analysis.py**: Added 6 new endpoints:
  - `POST /trigger/news` — background CafeF crawl
  - `POST /trigger/sentiment` — background sentiment analysis
  - `POST /trigger/combined` — background combined analysis
  - `GET /{symbol}/sentiment` — latest sentiment result
  - `GET /{symbol}/combined` — latest combined result
  - `GET /{symbol}/summary` — all 4 dimensions in one response (no 404 for missing)

### Task 2: Comprehensive unit tests for Phase 3
- **test_cafef_crawler.py** (new): 8 tests — HTML parsing, date filtering, URL normalization, edge cases
- **test_ai_analysis_service.py** (+8 tests): TestSentimentPrompt (2), TestCombinedPrompt (2), TestSentimentSchema (4)
- **test_scheduler.py** (+8 tests): TestPhase3Chaining (5), TestPhase3JobFunctions (3)
- **test_api.py** (+3 tests): TestPhase3Endpoints (trigger/news, trigger/sentiment, trigger/combined)
- Full suite: **71 passed** (44 existing + 27 new), zero regressions

## Full Pipeline Chain

```
daily_price_crawl (cron Mon-Fri 15:30)
  → daily_indicator_compute_triggered
    → daily_ai_analysis_triggered
      → daily_news_crawl_triggered
        → daily_sentiment_triggered
          → daily_combined_triggered
```

## Decisions Made

1. **Summary endpoint partial data**: Returns whatever dimensions are available without 404 — better UX for tickers with incomplete analysis
2. **Job chain ID convention**: `_triggered` (from chain) and `_manual` (from API) — consistent with Phase 2 pattern

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- All 7 key files verified present
- Commit f66f59d (Task 1) verified
- Commit d6db35d (Task 2) verified
- 71/71 tests passing

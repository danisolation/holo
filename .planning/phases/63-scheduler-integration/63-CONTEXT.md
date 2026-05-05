# Phase 63 — Scheduler Integration: Smart Discuss Context

## Grey Areas Resolved

### Area 1: Chain Placement

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Chain insertion point | After `daily_trading_signal_triggered` → rumor_crawl → rumor_scoring → `daily_pick_generation` | Per architecture research — after trading_signal, before pick_generation. Rumor scores inform pick generation context. |
| 2 | Chain pattern | Same `_on_job_executed` event-driven chaining as all other jobs | Consistent with existing pattern in manager.py |
| 3 | Two-step chain | `daily_rumor_crawl_triggered` → `daily_rumor_scoring_triggered` | Crawl must complete before scoring (scoring reads from DB) |

### Area 2: Job Functions

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 4 | Job function pattern | Mirror existing jobs: `async def daily_rumor_crawl()` and `async def daily_rumor_scoring()` | Same `async_session()`, `JobExecutionService`, `_determine_status`, `_build_summary`, DLQ pattern |
| 5 | Failure isolation | Partial failure returns normally (chain continues), complete failure raises (chain breaks) — same as all other jobs | Per existing resilience pattern in jobs.py |
| 6 | Manual trigger job IDs | `daily_rumor_crawl_manual`, `daily_rumor_scoring_manual` — both chain forward | Allow manual trigger from API like other jobs |

### Area 3: Job Registration

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 7 | Job name mapping | Add to `_JOB_NAMES` dict in manager.py | Consistent with existing pattern |
| 8 | No cron schedule | Rumor jobs only run via chain trigger (not standalone cron) | They depend on prior chain steps completing |
| 9 | Manual API endpoint | Add `POST /api/system/run-rumor-crawl` and `POST /api/system/run-rumor-scoring` | Mirror existing manual trigger endpoints in system.py |

## Code Context

### Reusable Assets
- `backend/app/scheduler/jobs.py` — All existing job functions (pattern to mirror)
- `backend/app/scheduler/manager.py` — Chain logic in `_on_job_executed`, `_JOB_NAMES`
- `backend/app/api/system.py` — Manual trigger endpoints pattern
- `backend/app/crawlers/fireant_crawler.py` — FireantCrawler (Phase 60)
- `backend/app/services/rumor_scoring_service.py` — RumorScoringService (Phase 61)

### Integration Points
- `manager.py:168` — Currently `daily_trading_signal_triggered` chains to `daily_pick_generation`. Must insert rumor_crawl between them.
- `jobs.py` — Add `daily_rumor_crawl()` and `daily_rumor_scoring()` functions
- `system.py` — Add manual trigger endpoints

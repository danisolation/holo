# Phase 6: Resilience Foundation - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the existing data pipeline resilient: add error recovery with retry and circuit breakers, track all job executions in the database, implement a dead-letter queue for permanently failed items, and send Telegram notifications on critical failures. This phase does NOT add new features — it hardens what v1.0 built.

</domain>

<decisions>
## Implementation Decisions

### Circuit Breaker Behavior
- **D-01:** Custom `AsyncCircuitBreaker` class (~30 lines) — all 3 Python libraries (aiobreaker, pybreaker, circuitbreaker) have async bugs or are sync-only
- **D-02:** Per-API isolation — one breaker each for vnstock, CafeF, and Gemini. CafeF going down must not block price crawling.
- **D-03:** Moderate thresholds: 3 consecutive failures to trip, 2-minute cooldown before half-open probe
- **D-04:** Half-open recovery: after cooldown, probe with 1 request. If it succeeds → close circuit and resume. If it fails → stay open, reset cooldown timer.
- **D-05:** Circuit state stored in-memory (not DB) — single-process app, no need for shared state. Reset on restart is acceptable.

### Job Failure Handling
- **D-06:** Auto-retry failed tickers only — re-batch just the failures for one additional attempt. Don't re-process the 395+ successful tickers.
- **D-07:** Retry must stay INSIDE job functions, not wrap them — APScheduler's `EVENT_JOB_EXECUTED` listener is binary (success/fail). Wrapping with tenacity at job level breaks chaining.
- **D-08:** Dead-letter queue: DB table (`failed_jobs`) storing permanently failed items with job_type, ticker_id, error_message, retry_count, failed_at, resolved_at. Visible on health dashboard. Manual re-trigger possible later (Phase 10).
- **D-09:** After auto-retry fails, item goes to DLQ. No further automatic retries. User investigates via health dashboard.

### Failure Notifications
- **D-10:** Critical failures only sent to Telegram — complete job failure (e.g., entire price crawl failed) or circuit breaker opened. No alerts for partial failures (e.g., 5 tickers failed in a 400-ticker batch).
- **D-11:** Use existing `bot.send_message()` pattern — 2-retry with backoff, never raises. Failure notification failures are logged but don't cascade.
- **D-12:** Alert format: "⚠️ [Job Name] failed: [error summary]" or "🔴 Circuit open: [API name] — [N] consecutive failures"

### Job Tracking
- **D-13:** Per-job summary rows in `job_executions` table: job_id, started_at, completed_at, status (success/partial/failed), result_summary (JSONB with tickers_processed, tickers_failed, failed_symbols, duration_seconds).
- **D-14:** One row per job run — NOT per-ticker. DLQ handles individual failure details. ~10-15 rows per daily pipeline run is acceptable.
- **D-15:** Extend existing `_on_job_executed` listener in `manager.py` to write to DB after each job completes.

### Agent's Discretion
- Exact timeout values for external API calls (vnstock, CafeF httpx, Gemini) — choose sensible defaults (30s for data, 60s for AI)
- Whether to add explicit timeouts on `asyncio.to_thread()` calls wrapping vnstock
- JSONB schema for `result_summary` in job_executions — as long as it includes counts and failed symbols
- Whether circuit breaker state includes a `last_failure_time` for debugging

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scheduler & Job Chain
- `backend/app/scheduler/manager.py` — `_on_job_executed` listener, job registration, EVENT_JOB_EXECUTED chaining
- `backend/app/scheduler/jobs.py` — All job implementations, try/except patterns, alert jobs never-raise convention (D-3.4)

### Existing Retry Patterns
- `backend/app/crawlers/vnstock_crawler.py` — Tenacity `@retry` decorator with exponential backoff
- `backend/app/services/ai_analysis_service.py` — Manual batch retry loop (429/503 handling), `_gemini_lock`, `_run_batched_analysis()`
- `backend/app/services/price_service.py` — Rate-limit detection, per-ticker retry

### External API Calls
- `backend/app/crawlers/cafef_crawler.py` — httpx async client, `timeout=15`, per-ticker try/except
- `backend/app/services/ai_analysis_service.py` — `_call_gemini()` with tenacity, batch composition

### Telegram Notification
- `backend/app/telegram/bot.py` — `send_message()` with 2-retry, never-raises pattern
- `backend/app/telegram/formatter.py` — HTML message formatting

### Health Endpoints
- `backend/app/api/system.py` — Existing `/health` and `/scheduler/status` endpoints

### Database Models
- `backend/app/models/` — All existing models for reference when creating new tables

### Research
- `.planning/research/PITFALLS.md` — Critical pitfalls #1 (cascade), #3 (retry vs chain conflict), #5 (connection pool)
- `.planning/research/ARCHITECTURE.md` — Resilience layer design, new service patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tenacity` library already installed and used on vnstock/Gemini calls
- `bot.send_message()` with retry pattern — use directly for failure notifications
- `asyncio.to_thread()` pattern for wrapping sync vnstock calls
- `_gemini_lock` (asyncio.Lock) for serializing Gemini batches

### Established Patterns
- Services follow Service-Per-Domain with `AsyncSession` injection
- Jobs create own `async_session()` context — each job is isolated
- Config via `pydantic-settings` in `backend/app/config.py` — all retry/timeout values live here
- Alembic for migrations — new tables follow existing model patterns in `backend/app/models/`

### Integration Points
- `manager.py:_on_job_executed` — extend to log to `job_executions` table
- `jobs.py` — wrap each job function with circuit breaker + failure tracking
- `system.py` — extend health endpoint with per-job status from `job_executions`
- `config.py` — add circuit breaker thresholds, timeout values

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Key constraint: don't break the existing job chain mechanism.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-resilience-foundation*
*Context gathered: 2026-04-16*

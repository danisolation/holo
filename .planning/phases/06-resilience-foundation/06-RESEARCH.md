# Phase 6: Resilience Foundation - Research

**Researched:** 2025-07-18
**Domain:** Error recovery, circuit breakers, job tracking, dead-letter queues — Python async
**Confidence:** HIGH

## Summary

Phase 6 hardens the existing v1.0 data pipeline with error recovery, circuit breakers, job execution tracking, a dead-letter queue, and critical failure notifications via Telegram. No new features are added — this is purely resilience infrastructure.

The core challenge is integrating retry, circuit breaker, and DLQ patterns into the existing APScheduler job chain without breaking the `EVENT_JOB_EXECUTED`-based chaining in `manager.py`. APScheduler 3.11's event listeners are **synchronous** (`cb(event)`, not `await cb(event)`) [VERIFIED: APScheduler 3.11 source inspection], so async DB writes for job logging must be dispatched via `asyncio.get_event_loop().create_task()` or, more cleanly, performed inside each job function itself.

**Primary recommendation:** Implement a custom `AsyncCircuitBreaker` (~35 lines) in `app/resilience.py`, wrap external API calls with it, modify each job function to track execution + retry failed tickers internally, and add two new DB tables (`job_executions`, `failed_jobs`) via Alembic migration 005.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Custom `AsyncCircuitBreaker` class (~30 lines) — all 3 Python libraries (aiobreaker, pybreaker, circuitbreaker) have async bugs or are sync-only
- **D-02:** Per-API isolation — one breaker each for vnstock, CafeF, and Gemini. CafeF going down must not block price crawling.
- **D-03:** Moderate thresholds: 3 consecutive failures to trip, 2-minute cooldown before half-open probe
- **D-04:** Half-open recovery: after cooldown, probe with 1 request. If it succeeds → close circuit and resume. If it fails → stay open, reset cooldown timer.
- **D-05:** Circuit state stored in-memory (not DB) — single-process app, no need for shared state. Reset on restart is acceptable.
- **D-06:** Auto-retry failed tickers only — re-batch just the failures for one additional attempt. Don't re-process the 395+ successful tickers.
- **D-07:** Retry must stay INSIDE job functions, not wrap them — APScheduler's `EVENT_JOB_EXECUTED` listener is binary (success/fail). Wrapping with tenacity at job level breaks chaining.
- **D-08:** Dead-letter queue: DB table (`failed_jobs`) storing permanently failed items with job_type, ticker_id, error_message, retry_count, failed_at, resolved_at. Visible on health dashboard. Manual re-trigger possible later (Phase 10).
- **D-09:** After auto-retry fails, item goes to DLQ. No further automatic retries. User investigates via health dashboard.
- **D-10:** Critical failures only sent to Telegram — complete job failure (e.g., entire price crawl failed) or circuit breaker opened. No alerts for partial failures (e.g., 5 tickers failed in a 400-ticker batch).
- **D-11:** Use existing `bot.send_message()` pattern — 2-retry with backoff, never raises. Failure notification failures are logged but don't cascade.
- **D-12:** Alert format: "⚠️ [Job Name] failed: [error summary]" or "🔴 Circuit open: [API name] — [N] consecutive failures"
- **D-13:** Per-job summary rows in `job_executions` table: job_id, started_at, completed_at, status (success/partial/failed), result_summary (JSONB with tickers_processed, tickers_failed, failed_symbols, duration_seconds).
- **D-14:** One row per job run — NOT per-ticker. DLQ handles individual failure details. ~10-15 rows per daily pipeline run is acceptable.
- **D-15:** Extend existing `_on_job_executed` listener in `manager.py` to write to DB after each job completes.

### Agent's Discretion
- Exact timeout values for external API calls (vnstock, CafeF httpx, Gemini) — choose sensible defaults (30s for data, 60s for AI)
- Whether to add explicit timeouts on `asyncio.to_thread()` calls wrapping vnstock
- JSONB schema for `result_summary` in job_executions — as long as it includes counts and failed symbols
- Whether circuit breaker state includes a `last_failure_time` for debugging

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ERR-01 | Failed tickers in AI analysis batches are re-batched for one additional retry attempt | D-06 pattern: collect `failed_symbols` from batch, re-run `_run_batched_analysis()` on just those symbols. Existing `_run_batched_analysis` already returns `failed_symbols` list. |
| ERR-02 | Permanently failed items stored in dead letter table with error details and retry count | D-08: `failed_jobs` table schema defined. `DeadLetterService` class for insert/query. |
| ERR-03 | Partial pipeline failures allow remaining tickers to proceed (graceful degradation) | Existing pattern already supports this (e.g., `_crawl_batch` skips failed tickers). Phase 6 formalizes: jobs catch all per-ticker errors internally, only raise on catastrophic failure. |
| ERR-04 | Every scheduled job logs execution start/end, status, and result summary to `job_executions` table | D-13/D-14/D-15: `JobExecutionService` wraps job logic. Uses async DB session inside job function. |
| ERR-05 | Complete crawler failure triggers Telegram notification to user | D-10/D-11/D-12: After job completes with `status=failed` or circuit opens, send alert via `telegram_bot.send_message()`. |
| ERR-06 | Circuit breaker stops calling external APIs after N consecutive failures, auto-resets after cooldown | D-01 to D-05: `AsyncCircuitBreaker` class, 3 instances (vnstock, cafef, gemini), 3-failure threshold, 2-min cooldown, half-open probe. |
| ERR-07 | Failed jobs are automatically retried once after 30-minute delay (max 3 retries) | **Modified by D-06/D-07/D-09:** Retry happens INSIDE job functions for failed tickers only (one immediate re-batch), not at scheduler level. After retry fails → DLQ, no further automatic retries. The "30-minute delay" from the original requirement is superseded by inline re-batching. |
</phase_requirements>

## Standard Stack

### Core (Already Installed — No New Dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| APScheduler | 3.11.2 | Job scheduling + chaining | Already in use. EVENT_JOB_EXECUTED/EVENT_JOB_ERROR listeners for chaining + logging. [VERIFIED: installed 3.11.2] |
| SQLAlchemy | 2.0.49 | ORM for new tables | Already in use. JSONB column type for result_summary. [VERIFIED: installed 2.0.49] |
| Alembic | ≥1.18 | Migration for new tables | Already in use. Migration 005 for job_executions + failed_jobs. [VERIFIED: requirements.txt] |
| tenacity | 9.1.4 | Existing retry on vnstock/Gemini | Already in use. Keep as-is — circuit breaker wraps AROUND tenacity retries. [VERIFIED: installed 9.1.4] |
| loguru | 0.7.x | Logging | Already in use everywhere. [VERIFIED: requirements.txt] |
| python-telegram-bot | 22.7 | Failure notifications | Already in use. `telegram_bot.send_message()` for critical alerts. [VERIFIED: requirements.txt] |

### No New Dependencies Required

Per STATE.md decision: "Zero new backend libraries — existing stack covers all requirements." The `AsyncCircuitBreaker` is custom code (~35 lines), not a library. [VERIFIED: CONTEXT.md D-01]

### Alternatives Considered

| Instead of | Could Use | Why Not |
|------------|-----------|---------|
| Custom AsyncCircuitBreaker | aiobreaker | Tornado-legacy, no native asyncio. [VERIFIED: D-01 rationale from CONTEXT.md] |
| Custom AsyncCircuitBreaker | pybreaker | Sync-only, blocking in async context. [VERIFIED: D-01 rationale from CONTEXT.md] |
| Custom AsyncCircuitBreaker | circuitbreaker | Sync-only decorator pattern. [VERIFIED: D-01 rationale from CONTEXT.md] |
| DB dead-letter table | Redis queue | Overkill for single-user. No Redis infra. [VERIFIED: STATE.md] |

## Architecture Patterns

### Recommended New File Structure
```
backend/app/
├── resilience.py              # NEW: AsyncCircuitBreaker class + per-API instances
├── services/
│   ├── job_execution_service.py  # NEW: job_executions table CRUD
│   └── dead_letter_service.py    # NEW: failed_jobs table CRUD
├── models/
│   ├── job_execution.py       # NEW: JobExecution model
│   └── failed_job.py          # NEW: FailedJob model
├── scheduler/
│   ├── manager.py             # MODIFIED: add EVENT_JOB_ERROR listener, async job logging
│   └── jobs.py                # MODIFIED: wrap each job with tracking + retry + DLQ
├── config.py                  # MODIFIED: add circuit breaker + timeout settings
└── telegram/
    └── formatter.py           # MODIFIED: add failure alert formatting methods
```

### Pattern 1: AsyncCircuitBreaker (Custom, ~35 Lines)
**What:** Three-state circuit breaker (CLOSED → OPEN → HALF_OPEN) using `time.monotonic()` for timing.
**When to use:** Wrap every external API call (vnstock, CafeF, Gemini).
**Key design decisions:**
- Uses `time.monotonic()` not `time.time()` (immune to system clock changes) [ASSUMED]
- Include `last_failure_time` for debugging (agent's discretion — recommend YES)
- State property lazily transitions OPEN → HALF_OPEN on cooldown expiry
- `call()` method is async, wraps the actual async function call
- On HALF_OPEN success → CLOSED, on HALF_OPEN failure → OPEN (reset timer per D-04)

**Example:**
```python
# app/resilience.py — verified pattern from CONTEXT.md D-01 through D-05
import asyncio
import time
from enum import Enum
from loguru import logger

class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitOpenError(Exception):
    """Raised when circuit is open and call is rejected."""
    def __init__(self, name: str, fail_count: int):
        self.name = name
        self.fail_count = fail_count
        super().__init__(f"Circuit '{name}' is open after {fail_count} consecutive failures")

class AsyncCircuitBreaker:
    def __init__(self, name: str, fail_max: int = 3, reset_timeout: float = 120.0):
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self._state = CircuitState.CLOSED
        self._fail_count = 0
        self._last_failure_time: float | None = None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and self._last_failure_time is not None:
            if time.monotonic() - self._last_failure_time >= self.reset_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info(f"Circuit '{self.name}' transitioning to HALF_OPEN (cooldown expired)")
        return self._state

    async def call(self, func, *args, **kwargs):
        current = self.state
        if current == CircuitState.OPEN:
            raise CircuitOpenError(self.name, self._fail_count)
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except CircuitOpenError:
            raise  # Don't count circuit errors as failures
        except Exception:
            self._on_failure()
            raise

    def _on_success(self):
        if self._state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit '{self.name}' HALF_OPEN probe succeeded — closing circuit")
        self._fail_count = 0
        self._state = CircuitState.CLOSED

    def _on_failure(self):
        self._fail_count += 1
        self._last_failure_time = time.monotonic()
        if self._fail_count >= self.fail_max:
            self._state = CircuitState.OPEN
            logger.warning(f"Circuit '{self.name}' OPENED after {self._fail_count} consecutive failures")

# Module-level singletons — per D-02
vnstock_breaker = AsyncCircuitBreaker("vnstock", fail_max=3, reset_timeout=120.0)
cafef_breaker = AsyncCircuitBreaker("cafef", fail_max=3, reset_timeout=120.0)
gemini_breaker = AsyncCircuitBreaker("gemini", fail_max=3, reset_timeout=120.0)
```

### Pattern 2: Job Execution Tracking (Inside Job Functions)
**What:** Each job function creates a `JobExecution` record at start, updates on completion.
**Why inside job (not listener):** APScheduler 3.11 listeners are **synchronous** — `_dispatch_event` calls `cb(event)` without await. [VERIFIED: APScheduler source inspection]. Async DB writes from a sync listener require `asyncio.get_event_loop().create_task()` which is fragile. Cleaner to log inside the async job function itself.
**Listener role for D-15:** The listener can still be extended to fire Telegram notifications (sync-compatible via `asyncio.ensure_future`), but primary job logging happens in the job body.

**Example:**
```python
# In scheduler/jobs.py — revised job pattern
async def daily_price_crawl():
    logger.info("=== DAILY PRICE CRAWL START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_price_crawl")
        try:
            crawler = VnstockCrawler()
            service = PriceService(session, crawler)
            result = await service.crawl_daily()

            # Retry failed tickers (D-06: one re-batch attempt)
            if result["failed_symbols"]:
                logger.info(f"Retrying {len(result['failed_symbols'])} failed tickers...")
                retry_result = await service.crawl_specific(result["failed_symbols"])
                # Merge results
                result["success"] += retry_result["success"]
                result["failed"] = retry_result["failed"]
                result["failed_symbols"] = retry_result["failed_symbols"]

            # DLQ permanently failed tickers (D-08/D-09)
            if result["failed_symbols"]:
                dlq_svc = DeadLetterService(session)
                for symbol in result["failed_symbols"]:
                    await dlq_svc.add("daily_price_crawl", symbol, "Persistent failure after retry")

            status = "success" if result["failed"] == 0 else "partial" if result["success"] > 0 else "failed"
            await job_svc.complete(execution, status=status, result_summary=result)
            logger.info(f"=== DAILY PRICE CRAWL COMPLETE: {result} ===")

            if status == "failed":
                # Send Telegram notification for complete failure (D-10)
                await _notify_critical_failure("Daily Price Crawl", "All tickers failed")
                raise RuntimeError("Complete crawl failure")  # Break chain

        except Exception as e:
            await job_svc.fail(execution, error=str(e))
            logger.error(f"=== DAILY PRICE CRAWL FAILED: {e} ===")
            raise
```

### Pattern 3: Circuit Breaker Integration Points
**What:** Wrap the lowest-level async API calls, BELOW tenacity retries.
**Why below tenacity:** Tenacity retries individual call failures. Circuit breaker monitors the aggregate failure pattern ACROSS retries. If tenacity exhausts retries and raises, that counts as one circuit breaker failure. After 3 such exhaustions → circuit opens. [VERIFIED: existing tenacity on VnstockCrawler, existing manual retry in ai_analysis_service.py]

**Integration map:**

| API | Current Call Site | Circuit Breaker | Tenacity |
|-----|------------------|-----------------|----------|
| vnstock (VCI) | `VnstockCrawler.fetch_ohlcv()` etc. | `vnstock_breaker` wraps the `asyncio.to_thread()` call | Existing `@retry` stays (3 attempts) |
| CafeF | `CafeFCrawler._fetch_news()` | `cafef_breaker` wraps the `client.get()` call | No existing tenacity (single try per ticker) |
| Gemini | `AIAnalysisService._call_gemini()` | `gemini_breaker` wraps the `generate_content` call | Existing `@retry` stays (2 attempts on ServerError) |

**Example integration for VnstockCrawler:**
```python
# In vnstock_crawler.py
from app.resilience import vnstock_breaker

@retry(stop=stop_after_attempt(settings.crawl_max_retries), ...)
async def fetch_ohlcv(self, symbol: str, start: str, end: str | None = None) -> pd.DataFrame:
    def _fetch():
        quote = Quote(symbol)
        return quote.history(start=start, end=end, interval='1D')
    # Circuit breaker wraps the actual call
    return await vnstock_breaker.call(asyncio.to_thread, _fetch)
```

### Pattern 4: Telegram Failure Notifications
**What:** Fire-and-forget async notification on critical failures.
**When:** Complete job failure OR circuit breaker opens.
**Integration:** From `_on_job_error` listener (EVENT_JOB_ERROR) and from circuit breaker `_on_failure` when transitioning to OPEN.

**Example:**
```python
# In scheduler/manager.py
from app.telegram.bot import telegram_bot

def _on_job_error(event: events.JobExecutionEvent):
    """Send Telegram notification on complete job failure (D-10)."""
    job_name = event.job_id.replace("_", " ").title()
    error_msg = str(event.exception)[:200] if event.exception else "Unknown error"
    message = f"⚠️ <b>{job_name}</b> failed:\n<code>{error_msg}</code>"
    # Fire-and-forget async send from sync listener
    asyncio.ensure_future(telegram_bot.send_message(message))

# Register alongside existing listener
scheduler.add_listener(_on_job_error, events.EVENT_JOB_ERROR)
```

### Anti-Patterns to Avoid

- **Wrapping job functions with tenacity at scheduler level:** APScheduler sees initial failure, fires EVENT_JOB_ERROR before retry completes. Chain breaks. D-07 explicitly forbids this. [VERIFIED: PITFALLS.md Pitfall 3]
- **Circuit breaker per request/per ticker:** Creates new instances with no shared state — circuit never opens. Must be module-level singletons. [VERIFIED: ARCHITECTURE.md Anti-Pattern 3]
- **Swallowing ALL exceptions in jobs (never raising):** If a job catches everything and returns normally even on complete failure, the chain continues to process stale/missing data. Jobs SHOULD raise on catastrophic failure to break the chain. [VERIFIED: PITFALLS.md Pitfall 3]
- **Parsing logs for error metrics:** Use explicit counters/DB records. Logs are for humans, `job_executions` table is for code. [VERIFIED: PITFALLS.md Integration Gotcha: loguru + health metrics]
- **Async DB writes from sync APScheduler listeners:** `_dispatch_event` calls `cb(event)` synchronously. Using `asyncio.ensure_future()` works for fire-and-forget (Telegram notifications) but is unreliable for must-complete DB writes. Do DB writes in the job body instead. [VERIFIED: APScheduler source inspection]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Retry with backoff | Custom retry loops | tenacity (already installed) | Edge cases: jitter, max delay, retry filtering. Already in use on vnstock/Gemini. |
| JSON serialization for JSONB | Custom dict-to-JSON | SQLAlchemy's JSONB column type | Already handles serialization/deserialization. Used in `ai_analyses.raw_response`. |
| Telegram message sending with retry | Custom HTTP calls | `telegram_bot.send_message()` | Already has 2-retry with backoff, never-raises. D-11. |
| Job ID → human name mapping | Regex on job_id strings | Simple dict lookup | `{"daily_price_crawl": "Daily Price Crawl", ...}` — maintainable, clear. |

## Common Pitfalls

### Pitfall 1: Circuit Breaker + Tenacity Double-Counting Failures
**What goes wrong:** If circuit breaker wraps ABOVE tenacity, each tenacity retry attempt counts as a separate circuit breaker failure. 3 retries × 1 failure = circuit opens after just 1 actual API outage.
**Why it happens:** Tenacity retries happen before raising to the caller. If the circuit breaker sees each retry attempt as a failure, it trips prematurely.
**How to avoid:** Circuit breaker wraps the INNERMOST async call (inside tenacity). Tenacity retries the circuit-breaker-wrapped call. One tenacity `@retry` exhaustion = one circuit breaker failure count. 3 exhaustions = circuit opens. Alternatively, place circuit breaker OUTSIDE tenacity and count only the final exception (after retries exhausted). The OUTSIDE approach is simpler: tenacity handles transient failures, circuit breaker handles persistent ones.
**Warning signs:** Circuit opens after a single transient API glitch that would have been handled by tenacity alone.

**Recommended approach:** Circuit breaker OUTSIDE tenacity:
```python
# tenacity retries the raw call 3 times
# If all 3 fail, tenacity raises
# Circuit breaker counts that as 1 failure
# After 3 such sequences (9 raw failures), circuit opens
async def fetch_ohlcv(self, symbol, start, end):
    return await vnstock_breaker.call(self._fetch_ohlcv_with_retry, symbol, start, end)

@retry(stop=stop_after_attempt(3), ...)
async def _fetch_ohlcv_with_retry(self, symbol, start, end):
    return await asyncio.to_thread(self._fetch_sync, symbol, start, end)
```

### Pitfall 2: Job Chain Breaks on Partial Failure
**What goes wrong:** Current jobs raise on ANY failure (line 29 of jobs.py: `raise`). Even 1 failed ticker out of 400 causes the job to raise → `EVENT_JOB_ERROR` fires → chain breaks → no indicators, no AI analysis, no summary.
**Why it happens:** Jobs were designed in v1.0 to be all-or-nothing. Phase 6 needs graceful degradation.
**How to avoid:** Jobs must return normally (not raise) on partial failure. Only raise on complete/catastrophic failure. The chain continues for partial failures. Status tracking distinguishes `success` vs `partial` vs `failed`.
**Warning signs:** Chain stops completely; downstream jobs (indicators, AI, alerts) never run after a single ticker failure.

### Pitfall 3: EVENT_JOB_EXECUTED Listener Becomes a Bottleneck
**What goes wrong:** The `_on_job_executed` listener (sync) tries to do too much: chaining + DB logging + Telegram notifications. DB writes block the event loop; Telegram calls block the event loop.
**Why it happens:** Developers keep adding responsibilities to the single listener.
**How to avoid:** Split concerns:
1. `_on_job_executed` — chaining ONLY (existing, keep sync)
2. `_on_job_error` — Telegram notifications (new, sync with `asyncio.ensure_future`)
3. Job body — DB logging (async, inside job function)

### Pitfall 4: DLQ Table Grows Unbounded
**What goes wrong:** Failed items accumulate in `failed_jobs`. No cleanup mechanism.
**Why it happens:** D-09 says no automatic retries after DLQ. Items stay forever.
**How to avoid:** Add `resolved_at` column (D-08 already specifies this). Phase 10 health dashboard can show/resolve items. Add a periodic cleanup: delete resolved items older than 30 days. Not in this phase — just ensure the schema supports it.

### Pitfall 5: asyncio.ensure_future() in Sync Listener May Be Silently Dropped
**What goes wrong:** `asyncio.ensure_future()` requires a running event loop on the current thread. If called from a wrong context, the coroutine is never executed.
**Why it happens:** APScheduler 3.x's AsyncIOScheduler runs in the asyncio event loop, so `asyncio.ensure_future()` SHOULD work in listeners. But edge cases exist (e.g., during shutdown).
**How to avoid:** Use `asyncio.get_event_loop().create_task()` which is equivalent but more explicit. Add try/except around it. For critical notifications, also log the alert content so it's not lost even if Telegram send fails.

### Pitfall 6: Job Function Refactoring Breaks Existing Tests
**What goes wrong:** All 20 scheduler tests mock at specific import paths. Changing job function signatures or adding new imports breaks mocks.
**Why it happens:** Tests use `patch("app.scheduler.jobs.async_session")` etc.
**How to avoid:** Maintain backward-compatible function signatures. Add new parameters with defaults. Update tests incrementally — new tests for resilience behavior, update existing tests for changed internals.

## Code Examples

### Database Model: job_executions
```python
# app/models/job_execution.py
# Source: CONTEXT.md D-13, D-14
from datetime import datetime
from sqlalchemy import Integer, BigInteger, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP
from app.models import Base

class JobExecution(Base):
    __tablename__ = "job_executions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success, partial, failed
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
```

### Database Model: failed_jobs (DLQ)
```python
# app/models/failed_job.py
# Source: CONTEXT.md D-08
from datetime import datetime
from sqlalchemy import Integer, BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP
from app.models import Base

class FailedJob(Base):
    __tablename__ = "failed_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ticker_symbol: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    failed_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
```

### Alembic Migration Pattern (005)
```python
# alembic/versions/005_resilience_tables.py
# Follow existing migration pattern from 004_telegram_tables.py
def upgrade() -> None:
    op.execute("""
        CREATE TABLE job_executions (
            id BIGSERIAL PRIMARY KEY,
            job_id VARCHAR(100) NOT NULL,
            started_at TIMESTAMPTZ NOT NULL,
            completed_at TIMESTAMPTZ,
            status VARCHAR(20) NOT NULL,
            result_summary JSONB,
            error_message TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_job_executions_job_id ON job_executions (job_id)")
    op.execute("CREATE INDEX idx_job_executions_started_at ON job_executions (started_at DESC)")

    op.execute("""
        CREATE TABLE failed_jobs (
            id BIGSERIAL PRIMARY KEY,
            job_type VARCHAR(100) NOT NULL,
            ticker_symbol VARCHAR(10),
            error_message TEXT NOT NULL,
            retry_count INTEGER NOT NULL DEFAULT 1,
            failed_at TIMESTAMPTZ NOT NULL,
            resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX idx_failed_jobs_job_type ON failed_jobs (job_type)")
    op.execute("CREATE INDEX idx_failed_jobs_unresolved ON failed_jobs (resolved_at) WHERE resolved_at IS NULL")
```

### JSONB Schema for result_summary
```json
{
  "tickers_processed": 395,
  "tickers_failed": 5,
  "tickers_skipped": 0,
  "failed_symbols": ["ABC", "DEF", "GHI", "JKL", "MNO"],
  "duration_seconds": 782.4,
  "retried_count": 5,
  "dlq_count": 3
}
```

### Config Additions
```python
# In app/config.py — new settings for Phase 6
# Circuit breaker (D-03)
circuit_breaker_fail_max: int = 3
circuit_breaker_reset_timeout: float = 120.0  # 2 minutes

# Timeouts (Agent's discretion: 30s data, 60s AI)
vnstock_timeout: float = 30.0
cafef_timeout: float = 15.0  # Keep existing (already 15s in CafeFCrawler)
gemini_timeout: float = 60.0
```

### Telegram Failure Alert Formatting
```python
# In app/telegram/formatter.py — new methods
@staticmethod
def job_failure_alert(job_name: str, error_summary: str) -> str:
    """Format critical job failure notification (D-12)."""
    return (
        f"⚠️ <b>JOB FAILED</b>\n\n"
        f"<b>{job_name}</b>\n"
        f"<code>{error_summary[:300]}</code>"
    )

@staticmethod
def circuit_open_alert(api_name: str, fail_count: int) -> str:
    """Format circuit breaker open notification (D-12)."""
    return (
        f"🔴 <b>CIRCUIT OPEN</b>\n\n"
        f"<b>{api_name}</b> — {fail_count} consecutive failures\n"
        f"Auto-reset after 2 minutes"
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| APScheduler 3.x sync listeners | Still sync in 3.11.2 | N/A | Must use asyncio.ensure_future() for async work in listeners |
| pybreaker for circuit breaking | Custom async implementation | Decision D-01 | No external dependency, native asyncio support |
| Wrapping jobs with retry at scheduler level | Retry inside job functions | Decision D-07 | Preserves EVENT_JOB_EXECUTED chaining |

**Deprecated/outdated:**
- APScheduler 4.x was never released to PyPI. [VERIFIED: STATE.md, pip index check]
- aiobreaker last release 2020 — Tornado-based, not asyncio-native. [ASSUMED]

## Critical Integration Analysis

### How Job Chaining Works (Must Not Break)

```
APScheduler 3.11 event flow:
1. Job function returns normally → EVENT_JOB_EXECUTED fires (event.exception = None)
2. Job function raises → EVENT_JOB_ERROR fires (event.exception = the error)
3. _on_job_executed listener only registered for EVENT_JOB_EXECUTED (line 173)
4. Listener checks event.exception (defensive, always None for this event)
5. Listener chains next job via scheduler.add_job()
```

**Phase 6 change:** Jobs return normally on partial failure (chain continues). Jobs raise only on catastrophic failure (chain breaks). New EVENT_JOB_ERROR listener sends Telegram alert.

**event.retval availability:** `JobExecutionEvent.retval` contains the job function's return value. [VERIFIED: APScheduler source inspection]. Jobs currently don't return values (implicit None). After Phase 6, they'll return result dicts. The existing `_on_job_executed` listener ignores retval — this is backward-compatible.

### Existing Retry/Error Patterns (Must Integrate, Not Replace)

| Location | Current Pattern | Phase 6 Change |
|----------|----------------|-----------------|
| `VnstockCrawler.fetch_*()` | tenacity `@retry` 3 attempts, exponential backoff | Add circuit breaker OUTSIDE tenacity |
| `PriceService._crawl_batch()` | Per-ticker try/except, rate-limit 60s wait | Add retry re-batch for failed_symbols + DLQ |
| `AIAnalysisService._run_batched_analysis()` | Per-batch retry loop (5 attempts for 429), per-ticker store | Add re-batch for failed_symbols + DLQ |
| `AIAnalysisService._call_gemini()` | tenacity `@retry` 2 attempts on ServerError | Add circuit breaker OUTSIDE tenacity |
| `CafeFCrawler.crawl_all_tickers()` | Per-ticker try/except, no retry | Add circuit breaker on _fetch_news + DLQ |
| `jobs.py` all job functions | try/except → log + raise | Wrap with job tracking + return normally on partial |

### Circuit Breaker Placement Decision

**Option A: Circuit breaker INSIDE tenacity (wraps raw call)**
- Each tenacity retry hits the circuit breaker
- 3 retries × 3 tickers = 9 circuit breaker calls before opening
- Pro: Fine-grained failure tracking
- Con: Circuit opens slowly; tenacity already handles transient errors

**Option B: Circuit breaker OUTSIDE tenacity (wraps retried call)** ← **RECOMMENDED**
- Tenacity retries internally, raises on exhaustion
- Circuit breaker counts only final failures (after all retries exhausted)
- 3 final failures = circuit opens
- Pro: Clean separation — tenacity handles transient, circuit handles persistent
- Con: Slightly delayed circuit opening (waits for retry exhaustion)

Option B is cleaner because it respects the existing tenacity patterns and only trips on genuinely persistent failures.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `time.monotonic()` is the correct timer for circuit breaker cooldown (immune to system clock changes) | Architecture Pattern 1 | Low — `time.time()` would also work for 2-min cooldown, just less robust |
| A2 | aiobreaker last release was ~2020, Tornado-based | State of the Art | Low — the decision to use custom is already locked (D-01) |
| A3 | `asyncio.ensure_future()` works correctly in APScheduler 3.x sync listeners because AsyncIOScheduler runs within the asyncio event loop | Pitfall 5 | Medium — if it doesn't work, Telegram notifications from listener would silently fail. Fallback: log the alert content. |

## Open Questions

1. **`asyncio.to_thread()` timeout for vnstock calls**
   - What we know: vnstock calls are sync, wrapped via `asyncio.to_thread()`. No explicit timeout.
   - What's unclear: Can `asyncio.to_thread()` be timed out with `asyncio.wait_for()`? Or does that leave the thread running?
   - Recommendation: Use `asyncio.wait_for(asyncio.to_thread(...), timeout=30)`. The thread continues running but the caller gets a TimeoutError. The circuit breaker counts it as a failure. This is acceptable for single-user (thread leak is bounded by batch processing rate).

2. **Re-batch pattern for AI analysis**
   - What we know: `_run_batched_analysis()` returns `failed_symbols`. We need to re-batch just those.
   - What's unclear: The method takes `ticker_data` dict, not symbol list. Need to retain the context data for retry.
   - Recommendation: After first pass, filter `ticker_data` to only failed symbols, call `_run_batched_analysis()` again. The method already handles arbitrary subsets.

3. **Should `_on_job_executed` be split into two listeners?**
   - What we know: Currently handles chaining. D-15 says extend it for DB logging.
   - What's unclear: Adding async DB writes to a sync listener is fragile.
   - Recommendation: Keep `_on_job_executed` for chaining only. Do DB logging inside job functions. Use a new `_on_job_error` listener for Telegram alerts.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24.x |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && .venv\Scripts\python.exe -m pytest tests/ -x -q` |
| Full suite command | `cd backend && .venv\Scripts\python.exe -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ERR-01 | Failed tickers re-batched for one retry | unit | `pytest tests/test_resilience.py::test_retry_rebatch_failed_tickers -x` | ❌ Wave 0 |
| ERR-02 | Permanently failed items in DLQ table | unit | `pytest tests/test_resilience.py::test_failed_items_added_to_dlq -x` | ❌ Wave 0 |
| ERR-03 | Partial failures don't break pipeline | unit | `pytest tests/test_resilience.py::test_partial_failure_continues_chain -x` | ❌ Wave 0 |
| ERR-04 | Job execution logged to DB | unit | `pytest tests/test_resilience.py::test_job_execution_logged -x` | ❌ Wave 0 |
| ERR-05 | Complete failure triggers Telegram | unit | `pytest tests/test_resilience.py::test_complete_failure_sends_telegram -x` | ❌ Wave 0 |
| ERR-06 | Circuit breaker opens/closes correctly | unit | `pytest tests/test_circuit_breaker.py -x` | ❌ Wave 0 |
| ERR-07 | Failed tickers retried once then DLQ'd | unit | `pytest tests/test_resilience.py::test_retry_then_dlq -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && .venv\Scripts\python.exe -m pytest tests/ -x -q`
- **Per wave merge:** `cd backend && .venv\Scripts\python.exe -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_circuit_breaker.py` — covers ERR-06 (circuit breaker state machine)
- [ ] `tests/test_resilience.py` — covers ERR-01 through ERR-05, ERR-07 (job tracking, DLQ, retry, notifications)
- [ ] Update `tests/test_scheduler.py` — existing 20 tests must still pass after job function refactoring

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — single-user, no auth |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A — single-user |
| V5 Input Validation | Yes (minimal) | Pydantic models for API schemas, SQLAlchemy parameterized queries |
| V6 Cryptography | No | N/A — no crypto in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| DLQ data exposure (error messages may contain API keys in stack traces) | Information Disclosure | Truncate error_message to 500 chars, strip known secret patterns before storing |
| Telegram message injection via error strings | Tampering | HTML-escape all dynamic content in Telegram messages (already using HTML parse_mode) |
| Uncontrolled circuit breaker reset (attacker triggers half-open probe) | Denial of Service | Not applicable — single-user, in-memory state, no external interface to circuit breaker |

## Sources

### Primary (HIGH confidence)
- APScheduler 3.11.2 source code — event dispatch, listener mechanism, JobExecutionEvent attributes [VERIFIED: local installation inspection]
- Existing codebase: `manager.py`, `jobs.py`, `ai_analysis_service.py`, `price_service.py`, `cafef_crawler.py`, `vnstock_crawler.py`, `bot.py` [VERIFIED: direct code reading]
- CONTEXT.md decisions D-01 through D-15 [VERIFIED: file content]
- `.planning/research/PITFALLS.md` — Pitfall 3 (retry + chain conflict) [VERIFIED: file content]
- `.planning/research/ARCHITECTURE.md` — Resilience layer design, error recovery flow [VERIFIED: file content]

### Secondary (MEDIUM confidence)
- APScheduler 3.x documentation on event types (EVENT_JOB_EXECUTED vs EVENT_JOB_ERROR semantics) [VERIFIED: source code constants]

### Tertiary (LOW confidence)
- aiobreaker/pybreaker async limitations claim from CONTEXT.md D-01 rationale [ASSUMED: from user's research during discuss phase]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all verified installed
- Architecture: HIGH — patterns directly derived from existing code + locked decisions
- Pitfalls: HIGH — grounded in APScheduler source inspection + existing codebase analysis
- Circuit breaker design: HIGH — simple state machine, well-understood pattern
- Integration points: HIGH — every integration point verified against actual code

**Research date:** 2025-07-18
**Valid until:** 2025-08-18 (stable — no fast-moving dependencies)

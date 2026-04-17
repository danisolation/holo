# Phase 6: Resilience Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 06-resilience-foundation
**Areas discussed:** Circuit breaker behavior, Job failure handling, Failure notification scope, Job tracking granularity

---

## Circuit Breaker Behavior

### Q1: How quickly should the circuit breaker trip?

| Option | Description | Selected |
|--------|-------------|----------|
| Conservative (5 failures, 5-min cooldown) | Tolerant of transient issues, slow to trip | |
| Moderate (3 failures, 2-min cooldown) | Good balance for APIs that rarely go down | ✓ |
| Aggressive (2 failures, 1-min cooldown) | Fail fast, retry soon | |

**User's choice:** Moderate (3 failures, 2-min cooldown)

### Q2: Circuit breaker scope

| Option | Description | Selected |
|--------|-------------|----------|
| Per-API (vnstock, CafeF, Gemini) | Isolates failures, CafeF down doesn't block prices | ✓ |
| Per-job | Simpler, but bundles unrelated calls | |
| Global | Simplest, but too coarse | |

**User's choice:** Per-API isolation

### Q3: Recovery strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Half-open probe | Try 1 request after cooldown, if succeeds → close | ✓ |
| Timer-only reset | Close after cooldown, hope for best | |
| Manual reset only | Stay open until user triggers from dashboard | |

**User's choice:** Half-open probe (standard pattern, auto-recovers)

---

## Job Failure Handling

### Q4: Retry strategy for failed tickers

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-retry failed tickers only | Re-batch failures, run once more | ✓ |
| Auto-retry entire job | Simpler but re-does all 400 tickers | |
| No auto-retry | Manual trigger from health dashboard only | |

**User's choice:** Auto-retry failed tickers only

### Q5: Dead-letter queue persistence

| Option | Description | Selected |
|--------|-------------|----------|
| DB table + health dashboard | Queryable, visible, can manually re-trigger | ✓ |
| Log file only | Simpler, but harder to query and act on | |
| Store + auto-retry after 30 min | Most automated | |

**User's choice:** Store in DB table + show on health dashboard

---

## Failure Notification Scope

### Q6: What triggers a Telegram alert?

| Option | Description | Selected |
|--------|-------------|----------|
| Critical failures only | Complete job failure or circuit open | ✓ |
| All failures | Including partial (e.g., 5 tickers failed) | |
| Critical + daily health summary | One end-of-day message with any issues | |

**User's choice:** Critical failures only — low noise, only when seriously broken

---

## Job Tracking Granularity

### Q7: job_executions detail level

| Option | Description | Selected |
|--------|-------------|----------|
| Per-job summary | 1 row per job run with JSONB stats | ✓ |
| Per-job + per-ticker detail | Summary row + DLQ for failures | |
| Per-ticker granularity | 400 rows per crawl run | |

**User's choice:** Per-job summary (compact, fast queries, enough for health dashboard)

---

## Agent's Discretion

- Exact timeout values for external API calls
- JSONB schema for result_summary
- Whether circuit breaker state includes last_failure_time
- Whether to add explicit timeouts on asyncio.to_thread() calls

## Deferred Ideas

None — discussion stayed within phase scope

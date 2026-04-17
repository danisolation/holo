# Phase 15: Health & Monitoring — Implementation Decisions

## Phase Goal
System health monitoring covers API usage budgets, pipeline performance visualization, and proactive Telegram alerts.

## Requirements
- **HEALTH-08**: Health dashboard shows Gemini API usage (tokens consumed, requests made) vs free tier limits
- **HEALTH-09**: Health dashboard shows pipeline execution timeline with per-step duration visualization
- **HEALTH-10**: System sends Telegram notification when health checks detect sustained errors or stale data

## Existing Infrastructure
- **HealthService** (`backend/app/services/health_service.py`): job statuses, data freshness, error rates
- **Health API** (`backend/app/api/health.py`): /health/jobs, /health/data-freshness, /health/errors, /health/db-pool, /health/trigger, /health/summary
- **Health Frontend** (`frontend/src/app/dashboard/health/page.tsx`): HealthStatusCards, DataFreshnessTable, ErrorRateChart, DbPoolStatus, JobTriggerButtons
- **JobExecution model**: job_id, started_at, completed_at, status, result_summary, error_message
- **AI service** already logs `response.usage_metadata.total_token_count` per batch call
- **Telegram MessageFormatter**: existing message formatting infrastructure
- **APScheduler**: in-process scheduler for all cron jobs

## Implementation Decisions

### D-15-01: Gemini Usage Tracking Storage
**Decision:** New `gemini_usage` table with columns: id, analysis_type, batch_size, prompt_tokens, completion_tokens, total_tokens, model_name, created_at. Each Gemini API call inserts one row. Dashboard aggregates by day.
**Rationale:** The AI service already has `response.usage_metadata` available. Storing per-call lets us show breakdowns by analysis type. Simple table, no schema changes to existing models.

### D-15-02: Free Tier Limits Display
**Decision:** Hardcode Gemini 2.0 Flash free tier limits in config: 15 RPM, 1,500 RPD, 1M tokens/day. Dashboard shows usage vs limits as progress bars. Config-driven so limits update easily.
**Rationale:** Free tier limits change rarely. Config is simpler than an API call to Google. Visual progress bars give instant understanding of budget consumption.

### D-15-03: Pipeline Timeline Visualization
**Decision:** Horizontal bar chart (Gantt-style) using Recharts BarChart with custom bars. X-axis = time, each bar = a job step's duration. Data source = job_executions table (started_at, completed_at). Group by daily pipeline run.
**Rationale:** Recharts already in the project. Gantt-style gives immediate visual of which steps are slow. No new backend data needed — just query job_executions with proper sorting.

### D-15-04: Timeline Grouping
**Decision:** Group pipeline steps by date. Show the most recent pipeline run prominently with option to view last 7 days. Each date shows all jobs that ran (crawl → indicators → AI → news → sentiment → combined).
**Rationale:** Pipeline runs once daily. Grouping by date is natural. Recent run is most actionable.

### D-15-05: Telegram Health Alerts
**Decision:** New `health_alert_check` scheduler job running every 30 minutes. Checks: (1) any job failed 3+ consecutive times, (2) any data source stale beyond 2x threshold, (3) DB pool exhaustion >80%. Sends Telegram alert with summary. Cooldown: 4 hours between alerts to prevent spam.
**Rationale:** 30-minute check interval catches issues quickly. 3 consecutive failures avoids alerting on transient errors. 4-hour cooldown prevents alert fatigue. Reuses existing HealthService methods.

### D-15-06: Alert Deduplication
**Decision:** In-memory dict tracking last alert time per alert type. Reset on app restart (acceptable for single-user). Types: "job_failures", "stale_data", "pool_exhaustion".
**Rationale:** Simple, no DB overhead. App restart clears cooldowns which is fine — if the app restarted, user wants to know about any issues.

### D-15-07: Health Alert Message Format
**Decision:** Vietnamese HTML message with severity emoji (🔴 critical, 🟡 warning). Lists affected jobs/sources. Include /health deep link to dashboard.
**Rationale:** Consistent with existing Telegram message style. Vietnamese matches the app's UI language.

### D-15-08: Pipeline Timeline API
**Decision:** New GET /health/pipeline-timeline?days=7 endpoint. Returns array of daily runs, each with ordered job steps and their start/end/duration/status. Frontend renders as Gantt chart.
**Rationale:** Separating the API from existing /health/jobs allows optimized query (ordered by time, grouped by date) without changing existing endpoint behavior.

### D-15-09: Gemini Usage API
**Decision:** New GET /health/gemini-usage?days=7 endpoint. Returns daily aggregates: total_tokens, total_requests, breakdown by analysis_type. Plus today's progress vs limits.
**Rationale:** Frontend needs pre-aggregated data. Daily granularity matches free-tier tracking (RPD = requests per day). Today's progress is the key metric.

## Out of Scope
- Real-time WebSocket for health updates (Phase 16 handles WebSocket)
- Prometheus/Grafana integration (explicitly out of scope per REQUIREMENTS.md)
- Email alerts (Telegram is the sole notification channel)
- Historical usage analytics beyond 7 days (can extend later)

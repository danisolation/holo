# Phase 10: System Health Dashboard — Context

**Gathered:** 2026-04-18
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous smart discuss)

<domain>
## Phase Boundary

**Goal**: User can monitor system health, data freshness, and error rates from a dedicated dashboard page.

**In scope:**
- Health API endpoints: data freshness, job status, error rates, DB pool, manual triggers
- Frontend health page at `/dashboard/health`
- Color-coded job status cards (green/yellow/red)
- Error rate per job over last 7 days
- Manual trigger buttons for crawl, indicators, AI analysis
- Database connection pool status display

**Out of scope:**
- Grafana/Prometheus integration (explicit exclusion)
- Gemini API usage tracker (HEALTH-08, v2.0)
- Pipeline execution timeline (HEALTH-09, v2.0)
- Telegram health notifications (HEALTH-10, v2.0)

</domain>

<decisions>
## Implementation Decisions

### D-10-01: Health API Design
**Decision:** New API router at `/api/system/health` with endpoints:
- `GET /health` — Overall health summary
- `GET /health/jobs` — Job status with last run results
- `GET /health/data-freshness` — Last update timestamps per data type
- `GET /health/errors` — Error rates per job (7 days)
- `GET /health/db-pool` — Connection pool stats
- `POST /health/trigger/{job_name}` — Manual job trigger
**Rationale:** Extends existing system API (backend/app/api/system.py). RESTful under /system prefix.

### D-10-02: Data Freshness Tracking
**Decision:** Query latest timestamps from daily_prices, financials, news_articles, ai_analyses, technical_indicators. Flag stale data if older than expected (prices > 1 business day, financials > 1 week, etc.).
**Rationale:** Uses existing data — no new tables needed. Just aggregation queries.

### D-10-03: Job Status from job_executions
**Decision:** Use job_executions table (from Phase 6) to compute last run result, error count, and status color.
- Green: last run success
- Yellow: last run partial
- Red: last run failed or no runs in expected window
**Rationale:** Phase 6 already tracks all job executions. Just need aggregation queries.

### D-10-04: Manual Job Triggers
**Decision:** POST endpoint adds job to scheduler with immediate run. Uses same job functions from scheduler/jobs.py.
**Rationale:** Per HEALTH-07. Reuses existing job infrastructure.

### D-10-05: Frontend Health Page
**Decision:** New page at `/dashboard/health` with:
- Status cards grid for each job (colored by status)
- Data freshness table with stale flags
- Error rate mini-charts (7-day sparklines using Recharts)
- Trigger buttons with confirmation dialog
**Rationale:** Matches existing dashboard layout. Uses shadcn/ui cards + tables.

</decisions>

<code_context>
## Existing Code Insights

- `backend/app/api/system.py` has existing system endpoints (scheduler status, etc.)
- `job_executions` table from Phase 6 tracks all job runs with status and timestamps
- Frontend dashboard uses sidebar navigation — need to add "Health" nav item
- shadcn/ui components available for cards, tables, buttons, dialogs

</code_context>

<deferred>
## Deferred Ideas

- Gemini API usage tracker (HEALTH-08)
- Pipeline execution timeline Gantt chart (HEALTH-09)
- Telegram health notifications (HEALTH-10)

</deferred>

# Phase 58: AI Analysis Freshness - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning
**Mode:** Auto-generated (scheduler + frontend — patterns clear from codebase)

<domain>
## Phase Boundary

Add a morning AI refresh job (8:30 AM Mon-Fri) that runs a shortened pipeline chain for watchlist tickers only. Add freshness indicator to the frontend showing age of last AI analysis per ticker.

Backend: New CronTrigger + shortened job chain in APScheduler.
Frontend: Freshness badge on dashboard/ticker views showing "Xh ago" with stale/fresh visual.

</domain>

<decisions>
## Implementation Decisions

### Morning Refresh Chain
- Add new CronTrigger at 8:30 AM (Mon-Fri, Asia/Ho_Chi_Minh) that starts a shortened chain
- Shortened chain: price_crawl → indicators → AI analysis → trading_signals (skip discovery, news, sentiment)
- Scope to watchlist tickers only (query user_watchlist table) to stay within Gemini 15 RPM
- Chain via existing _on_job_executed event listener pattern using distinct job IDs (e.g., "morning_price_crawl", "morning_indicator_compute", etc.)

### Freshness Indicator (Frontend)
- Backend: Add `last_analysis_at` field to analysis summary API response (max created_at from ai_analyses for each ticker)
- Frontend: Show relative time badge ("2h ago", "18h ago") with color coding:
  - Fresh (< 12h): green/muted text
  - Stale (≥ 12h): amber/warning badge
- Display on dashboard ticker cards and ticker detail page

### the agent's Discretion
- Exact morning job function names and implementation
- How to query watchlist tickers efficiently for morning scope
- Freshness badge exact styling within existing Tailwind/shadcn patterns
- Whether to use a separate morning chain listener or extend existing _on_job_executed

</decisions>

<code_context>
## Existing Code Insights

### Scheduler Pattern
- `backend/app/scheduler/manager.py` — CronTrigger + _on_job_executed chaining pattern
- `backend/app/scheduler/jobs.py` — All job functions (daily_price_crawl_for_exchange, daily_ai_analysis, etc.)
- Chaining: EVENT_JOB_EXECUTED listener matches job_id, triggers next job via scheduler.add_job()
- Each chain step has distinct job IDs with _triggered suffix

### AI Analysis Model
- `backend/app/models/ai_analysis.py` — has `created_at` timestamp (TIMESTAMP with timezone)
- `analysis_date` (Date) + `analysis_type` + `ticker_id` form unique constraint
- Types: technical, fundamental, news_sentiment, combined, trading_signal

### Integration Points
- `configure_jobs()` in manager.py — add new morning CronTrigger
- `_on_job_executed()` in manager.py — add morning chain routing
- Analysis API endpoints — add last_analysis_at to response
- Frontend dashboard components — add freshness badge

</code_context>

<specifics>
## Specific Ideas

- Morning chain should use distinct job IDs (morning_ prefix) so _on_job_executed can differentiate from daily chain
- The 4s delay between Gemini batches is already in the AI analysis job — no change needed
- Watchlist typically has 10-30 tickers → well within 15 RPM Gemini limit for morning run

</specifics>

<deferred>
## Deferred Ideas

- Manual "refresh now" button per ticker (v12.0+)
- Intraday mid-session analysis during market hours (v12.0+)
- AI confidence scoring visible in UI (v12.0+)

</deferred>

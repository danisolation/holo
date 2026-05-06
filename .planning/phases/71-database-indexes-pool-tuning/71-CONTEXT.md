# Phase 71: Database Indexes & Pool Tuning - Context

**Gathered:** 2026-05-06
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Database queries hit indexes on hot paths and connection pool handles concurrent load without exhaustion. Add composite indexes on 7 hot tables (daily_prices, technical_indicators, ai_analyses, daily_picks, weekly_reviews, job_executions, community_posts) for common query patterns. Tune DB connection pool (pool_size, max_overflow, pool_recycle).

Requirements: DB-IDX-01, DB-POOL-01

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

</decisions>

<code_context>
## Existing Code Insights

- `app/database.py` — current pool settings: pool_size=5, max_overflow=3
- `app/models/` — SQLAlchemy models with UniqueConstraint but limited explicit indexes
- Hot query patterns: ticker_id + date DESC, ticker_id + analysis_type + analysis_date, job_id + started_at, pick_date DESC
- Alembic migrations in `alembic/versions/`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>

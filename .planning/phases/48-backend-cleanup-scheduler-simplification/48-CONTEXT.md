# Phase 48: Backend Cleanup & Scheduler Simplification - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure/cleanup phase — discuss skipped)

<domain>
## Phase Boundary

All dead features are fully removed — corporate events, HNX/UPCOM support, and telegram dependency — and the scheduler pipeline is simplified to a reliable HOSE-only chain.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure/cleanup phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key research findings to incorporate:
- Scheduler chain triggers from `daily_price_crawl_upcom` completion (manager.py). Must rewire to HOSE BEFORE removing UPCOM jobs.
- Corporate events + HNX/UPCOM removal are coupled via UPCOM chain trigger that also spawns `daily_corporate_action_check`.
- Safe removal order: frontend → API → scheduler → model → DB (reverse dependency order).
- Two localStorage persistence traps: `holo-watchlist` and `holo-exchange-filter` (zustand/persist). Clear exchange filter persisted state.

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `backend/app/scheduler/manager.py` — scheduler chain with UPCOM trigger (critical)
- `backend/app/api/router.py` — API route registration
- `backend/app/models/` — SQLAlchemy models
- `frontend/src/app/dashboard/corporate-events/` — corporate events page
- `backend/requirements.txt` — contains `python-telegram-bot==22.7` (dead dep)

### Established Patterns
- Alembic for all DB migrations
- APScheduler with job chaining via EVENT_JOB_EXECUTED
- Frontend uses Next.js App Router with folder-based routing

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure/cleanup phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure/cleanup phase.

</deferred>

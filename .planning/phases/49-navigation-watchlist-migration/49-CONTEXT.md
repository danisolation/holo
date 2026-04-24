# Phase 49: Navigation & Watchlist Migration - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode — discuss skipped)

<domain>
## Phase Boundary

User has a clean, simplified navigation and a server-backed watchlist that persists across devices and shows AI signal data alongside each ticker.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key research findings to incorporate:
- Navigation reduction: 7→4-5 items. Merge overlapping pages, add redirects for old routes.
- Watchlist migration: localStorage (zustand/persist with key `holo-watchlist`) → PostgreSQL table + REST API + React Query hooks.
- Old `user_watchlist` table may exist from Telegram-era — check and reuse or clean up.
- Auto-migration: on first visit, read localStorage watchlist, POST to API, clear localStorage after success.
- AI signal display: each watchlist ticker shows latest signal score + buy/sell/hold recommendation from existing trading_signals data.
- Use existing patterns: Alembic for DB migration, FastAPI endpoints, React Query hooks, shadcn/ui components.

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `frontend/src/components/navbar.tsx` — current navigation (now has fewer items after Phase 48 cleanup)
- `frontend/src/lib/store.ts` — zustand store with watchlist (localStorage persist key: `holo-watchlist`)
- `frontend/src/app/watchlist/page.tsx` — current watchlist page
- `frontend/src/components/watchlist-table.tsx` — watchlist table component
- `backend/app/models/` — SQLAlchemy models
- `backend/app/api/` — FastAPI route modules

### Established Patterns
- Alembic for all DB migrations
- FastAPI with async SQLAlchemy for API endpoints
- React Query (TanStack) for data fetching
- zustand for client state
- shadcn/ui for UI components

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond ROADMAP success criteria. Refer to phase description.

</specifics>

<deferred>
## Deferred Ideas

- Watchlist-based alerts (notify when watchlist ticker has new signal) — future requirement
- Open position monitoring dashboard — future requirement

</deferred>

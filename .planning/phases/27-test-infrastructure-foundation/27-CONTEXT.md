# Phase 27: Test Infrastructure & Foundation - Context

**Gathered:** 2025-07-20
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase)

<domain>
## Phase Boundary

E2E test infrastructure is fully operational — Playwright configured, both servers auto-start/stop, test selectors stable, seed fixtures ready. This phase sets up the entire testing foundation that all subsequent test phases depend on.

Requirements: INFRA-01, INFRA-02, INFRA-03, INFRA-04, INFRA-05

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure phase. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key research findings to consider:
- Playwright `webServer` array supports dual servers (FastAPI :8001 + Next.js :3000)
- HOLO_TEST_MODE env guard must prevent APScheduler and Telegram bot from starting
- Windows venv path: `.venv/Scripts/python` (not `.venv/bin/python`)
- Chromium-only (no WebKit on Windows)
- data-testid attributes on navbar, tabs, forms, tables, chart containers
- Test fixtures should seed minimal data (tickers, prices, analysis) for read-only tests

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `backend/app/main.py` — FastAPI lifespan with APScheduler + Telegram bot startup
- `backend/app/scheduler/manager.py` — Scheduler initialization
- `backend/app/core/config.py` — Settings/config via pydantic-settings
- `frontend/src/components/navbar.tsx` — Main navigation
- `frontend/src/app/dashboard/paper-trading/page.tsx` — Tab-based dashboard
- `frontend/package.json` — Frontend dependencies

### Established Patterns
- pydantic-settings for backend config (.env file)
- Next.js rewrites for API proxying to backend
- shadcn/ui components with Tailwind CSS

### Integration Points
- Backend starts on port 8000 (production) — use 8001 for test to avoid conflict
- Frontend starts on port 3000
- API proxy: `/api/*` → `http://localhost:8000/api/*`

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure phase. Refer to ROADMAP phase description and success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — infrastructure phase.

</deferred>

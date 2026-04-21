# Phase 28: Page Smoke Tests & API Health Checks - Context

**Gathered:** 2025-07-20
**Status:** Ready for planning
**Mode:** Auto-generated (testing phase — patterns established in Phase 27)

<domain>
## Phase Boundary

Every application route loads without crashing and every API endpoint responds with correct status codes and response shapes. This phase writes the actual smoke + API tests using the infrastructure from Phase 27.

Requirements: SMOKE-01, SMOKE-02, SMOKE-03, SMOKE-04, API-01, API-02, API-03, API-04

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion — testing phase with established patterns from Phase 27. Use test helpers and API helpers already created.

Key guidelines from research:
- Assert on STRUCTURE, not VALUES (prices/volumes change daily)
- Playwright API tests = integration smoke tests only (560 pytest tests cover edge cases)
- Use data-testid attributes from Phase 27 for element selection
- Use ApiHelpers class from `e2e/fixtures/api-helpers.ts`
- Use test helpers from `e2e/fixtures/test-helpers.ts` (APP_ROUTES, navigateAndWait, etc.)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (from Phase 27)
- `frontend/e2e/fixtures/api-helpers.ts` — ApiHelpers class with typed API methods
- `frontend/e2e/fixtures/test-helpers.ts` — APP_ROUTES, navigateAndWait, expectNavbarVisible, TEST_TICKER
- `frontend/playwright.config.ts` — Dual webServer config already working
- 17 data-testid attributes across 7 frontend components

### Routes to Test
/, /watchlist, /dashboard, /dashboard/paper-trading, /dashboard/portfolio, /dashboard/health, /dashboard/corporate-events, /ticker/[symbol]

### API Endpoints
- GET /api/health
- GET /api/tickers
- GET /api/tickers/{symbol}/prices
- GET /api/analysis/{symbol}/summary
- GET /api/paper-trading/config
- GET /api/paper-trading/trades
- GET /api/paper-trading/analytics/summary
- GET /api/watchlist
- Plus 18 paper trading endpoints total

</code_context>

<specifics>
## Specific Ideas

No specific requirements — testing phase. Refer to ROADMAP success criteria.

</specifics>

<deferred>
## Deferred Ideas

None — testing phase.

</deferred>

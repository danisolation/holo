# Phase 29: User Interaction Tests - Context

**Gathered:** 2025-07-20
**Status:** Ready for planning
**Mode:** Auto-generated (testing phase)

<domain>
## Phase Boundary

Forms, tables, tabs, and interactive UI controls respond correctly to user input and persist state where expected. Tests verify real user interactions — clicking, typing, sorting, filtering, tab switching.

Requirements: INTERACT-01, INTERACT-02, INTERACT-03, INTERACT-04, INTERACT-05

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion. Use existing test infrastructure from Phase 27 and patterns from Phase 28.

Key guidelines:
- Use data-testid selectors established in Phase 27
- Paper trading settings form: submit and verify persistence via page reload
- Trade table: test sorting by P&L, status, date + filtering by direction, status
- Watchlist: add/remove operations via API or UI + verify persistence
- Tab switching: verify content changes on each tab click
- Ticker detail: test tab navigation and chart control interactions

</decisions>

<code_context>
## Existing Code Insights

### Available data-testid attributes
- `pt-tabs`, `pt-tab-overview`, `pt-tab-trades`, `pt-tab-analytics`, `pt-tab-calendar`, `pt-tab-settings`
- `pt-settings-form`, `pt-settings-submit`
- `pt-trades-table`
- `pt-analytics-content`
- `watchlist-page`, `watchlist-table`
- `ticker-page`, `ticker-chart`

### Test Infrastructure
- `frontend/e2e/fixtures/api-helpers.ts` — ApiHelpers
- `frontend/e2e/fixtures/test-helpers.ts` — helpers + APP_ROUTES

</code_context>

<specifics>
No specific requirements — testing phase.
</specifics>

<deferred>
None.
</deferred>

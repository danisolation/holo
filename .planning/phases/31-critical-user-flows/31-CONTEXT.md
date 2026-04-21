# Phase 31: Critical User Flows - Context

**Gathered:** 2025-07-20
**Status:** Ready for planning
**Mode:** Auto-generated (testing phase)

<domain>
## Phase Boundary

Multi-page end-to-end user journeys complete successfully — proving the application works as a cohesive whole. Tests simulate real user workflows spanning multiple pages.

Requirements: FLOW-01, FLOW-02, FLOW-03, FLOW-04

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All choices at agent's discretion. Key guidelines:
- Each flow test navigates across multiple pages
- Use API helpers to verify backend state changes
- Don't assert specific prices/values — structure only
- Handle potential empty states gracefully

</decisions>

<code_context>
## Existing Test Infrastructure
- All data-testid attributes from Phase 27
- API helpers from Phase 27
- Test helpers (navigateAndWait, expectNavbarVisible, APP_ROUTES, TEST_TICKER)
- Page smoke tests from Phase 28 prove all routes load
- Interaction tests from Phase 29 prove individual controls work

</code_context>

<specifics>
No specific requirements.
</specifics>

<deferred>
None.
</deferred>

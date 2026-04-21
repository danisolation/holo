# Phase 30: Visual Regression Testing - Context

**Gathered:** 2025-07-20
**Status:** Ready for planning
**Mode:** Auto-generated (testing phase)

<domain>
## Phase Boundary

Screenshot baselines capture key page states, chart rendering is verified via canvas checks, and layout holds on mobile viewports. Visual regression testing ensures UI doesn't break silently.

Requirements: VIS-01, VIS-02, VIS-03, VIS-04

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All choices at agent's discretion. Key research findings:
- Use `toHaveScreenshot()` built into Playwright — no external tools needed
- MUST mask dynamic data areas (prices, timestamps, percentages) to avoid false positives
- Canvas charts (lightweight-charts) invisible to DOM — screenshot-only verification
- Use `animations: 'disabled'` to prevent flaky diffs from CSS transitions
- Recharts renders SVG — some elements ARE queryable via DOM
- Wait for data load + network idle before screenshots
- Mobile viewport: 375px width for responsive tests
- Generate baselines on first run, compare on subsequent runs

</decisions>

<code_context>
## Existing Code Insights

### Chart Components
- Candlestick chart via lightweight-charts → `<canvas>` element
- Analytics charts via Recharts → `<svg>` elements
- Chart container has `data-testid="ticker-chart"`

### Dynamic Data Areas to Mask
- Stock prices (change daily)
- Timestamps / "last updated" indicators
- Percentage changes
- Volume numbers

</code_context>

<specifics>
No specific requirements — testing phase.
</specifics>

<deferred>
None.
</deferred>

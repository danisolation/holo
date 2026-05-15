# Phase 108: Dual Portfolio UI + AI Rationale - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Two-tab portfolio switcher on simulator page. Each tab shows its own summary, positions, trades. AI tab shows pending signals with Gemini rationale. Trade history displays rationale text.

Requirements: DUAL-01, RAT-01, RAT-02

Success Criteria:
1. Two top-level tabs "AI Portfolio" / "User Portfolio" — each with own summary, positions, trade history
2. AI tab shows pending signals with rationale text explaining Gemini's reasoning
3. Trade history displays rationale alongside trade details (ticker, side, price, P&L)
4. Manual trade form only in User tab; AI tab is auto-executed only

</domain>

<decisions>
## Implementation Decisions

### UI Layout
- Replace current single-view simulator page with 2-tab layout (shadcn Tabs)
- Each tab reuses existing components (portfolio summary, positions, trade history, equity chart)
- Tab state managed via URL param or useState
- AI tab: no manual trade form, shows pending signals + rationale
- User tab: manual trade form, no pending signals

### AI Rationale
- Backend: extend DailyPick or SimulatorTrade model with rationale field from Gemini
- OR: fetch rationale from existing AIAnalysis.reasoning for the ticker
- Frontend: display rationale as expandable text in pending signals and trade history
- Rationale generated during AI analysis pipeline (already has reasoning field)

### Data Fetching
- Existing hooks need portfolio_type param added
- New hook for fetching both portfolio summaries (for tab badges)

### Agent's Discretion
All remaining UI/UX choices at agent's discretion. Follow existing simulator page patterns.

</decisions>

<code_context>
## Existing Code Insights

### Key Files (updated by Phase 107)
- backend/app/api/simulator.py — all endpoints now accept portfolio_type param
- backend/app/services/simulator_service.py — all methods accept portfolio_name param
- backend/app/schemas/simulator.py — schemas with portfolio_type fields
- frontend/src/app/simulator/page.tsx — current simulator page (single view)
- frontend/src/components/simulator/ — existing components (trade-history, equity-chart, etc.)
- frontend/src/lib/api.ts — simulator fetch functions
- frontend/src/lib/hooks.ts — simulator hooks

### New from Phase 107
- GET /simulator/portfolios — returns both portfolio summaries
- All GET endpoints accept portfolio_type query param
- POST /trades accepts portfolio_type body param

</code_context>

<specifics>
No specific requirements — follow existing simulator page patterns.
</specifics>

<deferred>
None.
</deferred>

# Phase 109: AI Review + Performance Comparison - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Gemini reviews portfolio or individual trades on demand. Equity overlay chart compares AI vs User. Metrics comparison table shows win rate, avg P&L, max drawdown side-by-side.

Requirements: REVIEW-01, REVIEW-02, COMP-01, COMP-02

Success Criteria:
1. User clicks "AI Review" on portfolio → Gemini Vietnamese analysis (strengths, weaknesses, suggestions)
2. User clicks "AI Review" on specific closed trade → Gemini analysis (entry/exit optimal?, improvements, patterns)
3. Equity chart overlays AI + User portfolio lines on same time axis, color-coded
4. Metrics table shows side-by-side: win rate, avg P&L, total P&L, max drawdown, trade count

</domain>

<decisions>
## Implementation Decisions

### Backend — AI Review Service
- New SimulatorReviewService using Gemini structured output
- Portfolio review: fetches positions + recent trades + stats → sends to Gemini → structured response
- Trade review: fetches specific trade details + ticker context → sends to Gemini → structured response
- API endpoints: POST /simulator/review/portfolio, POST /simulator/review/trade/{trade_id}
- Uses existing _gemini_lock for RPM serialization
- TTLCache 300s for portfolio review (same portfolio state)

### Backend — Performance Comparison
- New endpoint: GET /simulator/comparison — returns both portfolios' equity histories + stats side-by-side
- Reuses existing get_equity_history() and get_stats() per portfolio

### Frontend
- AI Review: button on portfolio summary card → modal/panel with Gemini analysis
- Trade Review: button on each closed trade row → expandable analysis panel
- Comparison: new tab or section with overlaid Recharts LineChart + metrics table
- Vietnamese labels throughout

### Agent's Discretion
All remaining details at agent's discretion.

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- backend/app/services/simulator_service.py — get_stats(), get_equity_history() accept portfolio_name
- backend/app/services/ai_analysis_service.py — Gemini structured output pattern
- backend/app/services/peer_analysis_service.py — another Gemini service (simpler pattern)
- backend/app/api/simulator.py — updated with portfolio_type params (Phase 107)
- frontend/src/app/simulator/page.tsx — 2-tab layout (Phase 108)
- frontend/src/components/simulator/ — all components accept portfolioType
- frontend/src/lib/api.ts — simulator fetch functions with portfolioType
- frontend/src/lib/hooks.ts — simulator hooks

### Patterns
- Gemini: _gemini_lock, settings.gemini_model, structured output
- Frontend: "use client", React Query hooks, shadcn/ui components
- Charts: Recharts LineChart, ResponsiveContainer

</code_context>

<specifics>
None.
</specifics>

<deferred>
None.
</deferred>

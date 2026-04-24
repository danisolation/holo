# Phase 50: Coach Page Restructure & Trade Flow - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode — discuss skipped)

<domain>
## Phase Boundary

The Coach page is interactive and action-oriented — user can record trades directly from AI picks with one click and sees clear next steps after every trade.

</domain>

<decisions>
## Implementation Decisions

### the agent's Discretion
All implementation choices are at the agent's discretion. Use ROADMAP phase goal, success criteria, and codebase conventions to guide decisions.

Key context to incorporate:
- Pick cards need "Ghi nhận giao dịch" button → opens trade entry dialog pre-filled with ticker, entry price, SL, TP from the pick data.
- Coach page currently uses single long scroll — restructure to tab-based layout (Picks / Nhật ký / Mục tiêu).
- After recording trade → show open position with SL/TP monitoring + clear next steps guidance.
- Use existing patterns: shadcn/ui Tabs component, existing trade journal model/API, React Query hooks.
- Coach page already exists at `frontend/src/app/coach/page.tsx`.
- Trade journal and paper trading models already exist in backend from v4.0/v8.0 milestones.

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `frontend/src/app/coach/page.tsx` — current coach page (long scroll)
- `frontend/src/components/` — existing components (pick cards, trade journal)
- `backend/app/models/` — trade journal, paper trading models
- `backend/app/api/` — existing trade/journal API endpoints

### Established Patterns
- shadcn/ui components (Tabs, Dialog, Button, Card)
- React Query for data fetching
- FastAPI REST endpoints
- Pydantic schemas for validation

</code_context>

<specifics>
## Specific Ideas

- Vietnamese UI labels: "Ghi nhận giao dịch", "Nhật ký", "Mục tiêu"
- Pre-fill dialog from pick data (ticker, entry_price, stop_loss, take_profit)
- After trade: show position card with SL/TP levels and "what to do next" guidance

</specifics>

<deferred>
## Deferred Ideas

- Post-trade AI guidance (automated AI suggestions for open positions) — future requirement
- Real-time SL/TP monitoring with alerts — future requirement

</deferred>

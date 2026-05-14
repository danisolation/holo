# Phase 99: Performance & UX Polish - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped)

<domain>
## Phase Boundary

Polish the frontend UX: add loading skeleton states, improve mobile responsiveness, add page transition animations, and redesign the dashboard homepage for better information density.

Requirements: UX-01, UX-02, UX-03, UX-04
- UX-01: Loading skeleton states cho tất cả data-fetching components
- UX-02: Mobile responsive polish (sidebar, tables, charts)
- UX-03: Page transition animations (smooth route changes)
- UX-04: Dashboard homepage redesign (better layout, info density)

</domain>

<decisions>
## Implementation Decisions

### Agent's Discretion
All implementation choices are at the agent's discretion. Key context:
- Frontend: Next.js 16, TypeScript, Tailwind CSS, shadcn/ui
- Charts: lightweight-charts (candlestick), Recharts (stats)
- State: zustand, @tanstack/react-query
- Current homepage: 5-card stats grid + ticker table
- Simulator page: Tabs with multiple panels
- All UI text in Vietnamese

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `frontend/src/app/page.tsx` — Homepage dashboard
- `frontend/src/app/simulator/page.tsx` — Simulator page with tabs
- `frontend/src/app/layout.tsx` — Root layout with sidebar
- `frontend/src/components/` — Shared components
- `frontend/src/lib/hooks.ts` — React Query hooks
- `frontend/src/lib/api.ts` — API fetch functions
- `frontend/tailwind.config.ts` — Tailwind config

### Dependencies Available
- shadcn/ui Skeleton component (may need to add)
- framer-motion for animations (may need to install)
- Tailwind responsive utilities (sm:, md:, lg:)

</code_context>

<specifics>
## Specific Ideas

- Skeleton: Use shadcn/ui Skeleton component pattern
- Mobile: Collapsible sidebar, horizontal scroll for tables, responsive chart containers
- Transitions: framer-motion or CSS transitions for route changes
- Homepage redesign: Better card layout, market summary section, quick actions

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>

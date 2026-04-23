---
phase: 46-behavior-tracking-adaptive-strategy
plan: 03
subsystem: frontend
tags: [react, next.js, react-query, behavior-tracking, shadcn-ui, lucide-react]

# Dependency graph
requires:
  - phase: 46-02
    provides: 6 REST API endpoints at /api/behavior/*
provides:
  - useBehaviorTracking hook for passive event logging
  - 4 self-contained behavior components (RiskSuggestionBanner, HabitDetectionCard, ViewingStatsCard, SectorPreferencesCard)
  - 5 React Query hooks for behavior data fetching
  - Complete coach page integration with behavior insights section
affects: [coach-page-ux, ticker-detail-page, ticker-search, pick-card]

# Tech tracking
tech-stack:
  added: []
  patterns: [fire-and-forget-behavior-tracking, module-scope-debounce-map, self-contained-card-components]

key-files:
  created:
    - frontend/src/lib/use-behavior-tracking.ts
    - frontend/src/components/risk-suggestion-banner.tsx
    - frontend/src/components/habit-detection-card.tsx
    - frontend/src/components/viewing-stats-card.tsx
    - frontend/src/components/sector-preferences-card.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/ticker/[symbol]/page.tsx
    - frontend/src/components/ticker-search.tsx
    - frontend/src/components/pick-card.tsx
    - frontend/src/app/coach/page.tsx

key-decisions:
  - "Used event_metadata (not metadata) in BehaviorEventCreate type to match 46-01 backend deviation"
  - "Used apiFetch helper for GET endpoints but plain fetch for fire-and-forget POST (no error propagation needed)"
  - "Added onClick handler to PickCard for pick_click tracking (card had no prior click handler)"
  - "RiskSuggestionBanner checks suggestion.status === 'pending' in addition to null check for extra safety"

requirements-completed: [BEHV-01, BEHV-02, ADPT-01, ADPT-02]

# Metrics
duration: 4min
completed: 2026-04-23
---

# Phase 46 Plan 03: Frontend Behavior Tracking Summary

**useBehaviorTracking hook with 5-min debounce, 4 self-contained behavior cards (risk banner, habits, viewing stats, sectors), coach page integration with responsive layout — all Vietnamese copy per UI-SPEC**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-23T11:51:17Z
- **Completed:** 2026-04-23T11:55:44Z
- **Tasks:** 3 (2 auto + 1 checkpoint auto-approved)
- **Files modified:** 11

## Accomplishments
- 6 Phase 46 TypeScript interfaces + 6 fetch functions added to api.ts (using apiFetch pattern + plain fetch for fire-and-forget)
- 5 React Query hooks in hooks.ts: useRiskSuggestion (query), useRespondRiskSuggestion (mutation with cache invalidation), useHabitDetections, useViewingStats, useSectorPreferences
- useBehaviorTracking hook: module-scope Map debounce, 5-min per ticker, silent error swallow, integrated into ticker detail page, ticker search, and pick card
- RiskSuggestionBanner: conditional amber banner with accept/reject buttons, loading spinners per button, inline error text, removed on success via query invalidation
- HabitDetectionCard: habit badges with icons (TrendingDown/Clock/Zap), amber/blue colors, summary text for highest-count habit, CheckCircle empty state
- ViewingStatsCard: ordered list of top 10 tickers with rank, symbol, sector, view count, sector concentration warning in amber
- SectorPreferencesCard: ranked sectors with colored win rate and P&L, insufficient data note, BarChart3 empty state
- Coach page: risk banner as first child (above header), behavior insights section below pick history with section heading "Phân tích hành vi", responsive 2-col grid for viewing stats + sector prefs
- Next.js production build passes cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1: API types, fetch functions, hooks, and passive behavior tracking** - `34739a3` (feat)
2. **Task 2: 4 behavior components + coach page integration** - `a262723` (feat)
3. **Task 3: Verify behavior tracking UI on coach page** - auto-approved (checkpoint, no commit)

## Files Created/Modified
- `frontend/src/lib/api.ts` — 6 behavior interfaces + 6 fetch functions (event_metadata naming)
- `frontend/src/lib/hooks.ts` — 5 React Query hooks for behavior data
- `frontend/src/lib/use-behavior-tracking.ts` — Passive tracking hook with module-scope debounce Map
- `frontend/src/app/ticker/[symbol]/page.tsx` — Added useBehaviorTracking("ticker_view") call
- `frontend/src/components/ticker-search.tsx` — Added postBehaviorEvent("search_click") in handleSelect
- `frontend/src/components/pick-card.tsx` — Added onClick with postBehaviorEvent("pick_click")
- `frontend/src/components/risk-suggestion-banner.tsx` — Conditional amber risk banner with accept/reject
- `frontend/src/components/habit-detection-card.tsx` — Trading habits card with badges and summary
- `frontend/src/components/viewing-stats-card.tsx` — Top 10 viewed tickers with concentration warning
- `frontend/src/components/sector-preferences-card.tsx` — Ranked sectors with colored win rate and P&L
- `frontend/src/app/coach/page.tsx` — Risk banner + behavior insights section integration

## Decisions Made
- Used `event_metadata` (not `metadata`) in `BehaviorEventCreate` interface to match the 46-01 backend deviation where SQLAlchemy reserved `metadata`
- Used `apiFetch` helper for GET fetch functions (consistent error handling) but plain `fetch` for `postBehaviorEvent` (fire-and-forget, no error propagation)
- Added `onClick` handler to `PickCard` for pick_click tracking — the card had no prior click handler, so this is a new interaction
- `RiskSuggestionBanner` checks `suggestion.status === "pending"` in addition to null check as defense-in-depth (backend may return non-pending suggestions)

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None — no external service configuration required.

## Next Phase Readiness
- Phase 46 is now fully complete (data layer, API, scheduler, frontend)
- All 4 behavior tracking features are live on /coach page
- Passive tracking fires on ticker views, search clicks, and pick clicks
- Risk suggestion banner appears when pending and handles accept/reject flow
- Ready for Phase 47 (weekly reviews and goals)

---
*Phase: 46-behavior-tracking-adaptive-strategy*
*Completed: 2026-04-23*

## Self-Check: PASSED

All 11 files verified present. Both task commits (34739a3, a262723) confirmed in git log. Next.js production build passes.

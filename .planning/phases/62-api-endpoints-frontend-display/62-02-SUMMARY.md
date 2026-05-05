---
phase: 62-api-endpoints-frontend-display
plan: 02
subsystem: frontend-rumor-display
tags: [react, tanstack-query, components, rumor-intelligence, shadcn-ui]
dependency_graph:
  requires: [rumor-api-endpoints]
  provides: [rumor-score-panel, rumor-feed, watchlist-rumor-badge]
  affects: [ticker-detail-page, watchlist-table]
tech_stack:
  added: []
  patterns: [react-query-hooks, card-component, empty-state-vietnamese, direction-badge-colors]
key_files:
  created:
    - frontend/src/components/rumor-score-panel.tsx
    - frontend/src/components/rumor-feed.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/ticker/[symbol]/page.tsx
    - frontend/src/components/watchlist-table.tsx
decisions:
  - RumorScorePanel shows empty state when credibility_score is null (graceful no-data handling)
  - Direction badge uses same green/red color scheme as existing signal badges (#26a69a/#ef5350)
  - Rumor section placed after news section on ticker page (per D-9 ordering)
  - Watchlist rumor column uses colored dot + count (minimal, not full badge)
metrics:
  duration: ~4min
  completed: 2026-05-05
---

# Phase 62 Plan 02: Frontend Rumor Display Summary

**One-liner:** React Query hooks + RumorScorePanel/RumorFeed components + watchlist rumor badge column connecting to Plan 01 backend endpoints

## What Was Built

### Task 1: API Types, Hooks, Components, Ticker Page Integration
- **Types**: `RumorPost`, `RumorScoreData`, `WatchlistRumorSummary` interfaces in api.ts
- **Fetch functions**: `fetchRumorScores(symbol)` and `fetchWatchlistRumors()` using existing `apiFetch` pattern
- **React Query hooks**: `useRumorScores` and `useWatchlistRumors` with 5-min staleTime
- **RumorScorePanel**: Card showing credibility/impact scores, direction badge (bullish/bearish/neutral), key claims list, reasoning text, scored date
- **RumorFeed**: Card showing chronological post list with author (verified badge), content (line-clamp-3), likes/replies counts, date
- **Ticker page**: Rumor section added after CafeF news section with loading skeleton, error retry, and data display
- Commit: `78fdb24`

### Task 2: Watchlist Table Rumor Badge Column
- Added "Tin đồn" column before freshness/actions columns
- Shows colored sentiment dot (green=bullish, red=bearish, yellow=neutral) + MessageCircle icon + rumor count
- Tickers with no rumors show "—" placeholder
- Uses `useWatchlistRumors` hook with `rumorSummary` in useMemo deps
- Commit: `a6a31d8`

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 78fdb24 | Add rumor API types, hooks, RumorScorePanel + RumorFeed components, ticker page integration |
| 2 | a6a31d8 | Add rumor badge column to watchlist table |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

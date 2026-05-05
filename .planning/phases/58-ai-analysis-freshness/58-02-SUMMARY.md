---
phase: 58-ai-analysis-freshness
plan: 02
subsystem: frontend-watchlist
tags: [freshness-indicator, watchlist-table, ai-analysis, ui]
dependency_graph:
  requires: [58-01 last_analysis_at API field, WatchlistItem type, watchlist-table.tsx]
  provides: [AI freshness column in watchlist table]
  affects: [frontend/src/lib/api.ts, frontend/src/components/watchlist-table.tsx]
tech_stack:
  added: []
  patterns: [relative time freshness badge with stale/fresh color coding]
key_files:
  created: []
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/components/watchlist-table.tsx
decisions:
  - "12h threshold for fresh vs stale, matching CONTEXT.md specification"
  - "Column header 'AI' kept short to preserve table layout on narrow screens"
  - "Vietnamese 'Chưa có' label for missing analysis to match app language"
metrics:
  duration: ~2m
  completed: 2026-05-06
  tasks: 2/2
---

# Phase 58 Plan 02: Watchlist Freshness Indicator Summary

AI freshness column added to watchlist table showing relative time of last analysis per ticker, with amber (stale ≥12h) / muted gray (fresh <12h) visual distinction via Clock icon badge.

## Completed Tasks

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Add freshness column to watchlist table | `e7756b0` | WatchlistItem.last_analysis_at field + getAnalysisFreshness helper + "AI" column with Clock icon |
| 2 | Visual verification checkpoint | — | Code complete; visual verification noted as needed |

## Implementation Details

### Task 1: Freshness Column

**api.ts changes:**
- Added `last_analysis_at: string | null` to `WatchlistItem` interface to match backend schema from Plan 01

**watchlist-table.tsx changes:**
- Added `Clock` icon import from lucide-react
- Added `getAnalysisFreshness()` helper function:
  - Converts ISO timestamp to relative time ("2m ago", "5h ago", "3d ago")
  - Returns `isStale: true` for ≥12h or missing timestamps
  - Returns `isStale: false` for <12h (fresh)
- Added "AI" column between signal and actions columns:
  - Clock icon + relative time text
  - Fresh (<12h): `text-muted-foreground` (gray)
  - Stale (≥12h): `text-amber-500 font-medium` (amber)
  - Missing: "Chưa có" in amber

### Task 2: Visual Checkpoint
- All code implemented and committed
- Visual verification requires running frontend + backend and checking watchlist page

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

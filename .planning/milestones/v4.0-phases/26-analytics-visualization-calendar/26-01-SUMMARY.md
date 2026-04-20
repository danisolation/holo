---
phase: 26-analytics-visualization-calendar
plan: 01
subsystem: paper-trading-analytics
tags: [analytics, streaks, timeframe, periodic, calendar, react-query, frontend-hooks]
dependency_graph:
  requires: [Phase 24 analytics service, Phase 25 frontend data layer]
  provides: [4 new analytics endpoints, 11 frontend fetch+hook combos, react-activity-calendar]
  affects: [Phase 26 Plan 02 UI components]
tech_stack:
  added: [react-activity-calendar@3.2.0]
  patterns: [per-trade streak iteration, SQL GROUP BY timeframe/period/date, Pydantic Query pattern validation]
key_files:
  created: []
  modified:
    - backend/app/services/paper_trade_analytics_service.py
    - backend/app/schemas/paper_trading.py
    - backend/app/api/paper_trading.py
    - backend/tests/test_paper_trade_analytics.py
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/package.json
    - frontend/package-lock.json
decisions:
  - "Streak logic: per-trade iteration ordered by (closed_date, id) ASC — pnl>0 is win, else loss"
  - "Periodic weekly uses isoyear + ISO week for correct year-boundary grouping"
  - "Periodic monthly uses to_char(YYYY-MM) for clean month labels"
  - "All 11 analytics hooks use 1-minute staleTime (consistent with existing summary hook)"
metrics:
  duration: "3 min"
  completed: "2026-04-20"
  tasks_completed: 2
  tasks_total: 2
  files_modified: 8
---

# Phase 26 Plan 01: Analytics Data Pipeline Summary

**Complete analytics data pipeline: 4 new backend endpoints + 11 frontend fetch/hooks + react-activity-calendar**

## Tasks Completed

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | Backend — 4 analytics service methods, schemas, endpoints, tests | `fe4956f` | 4 Pydantic schemas, 4 service methods, 4 API endpoints, 10 new tests (36 total pass) |
| 2 | Frontend — react-activity-calendar + TypeScript types, fetch, hooks | `9517501` | 13 interfaces, 11 fetch functions, 11 react-query hooks, npm package installed |

## What Was Built

### Backend (4 new endpoints)

1. **GET /analytics/streaks** → `StreakResponse` — current/longest win/loss streak counts via per-trade iteration
2. **GET /analytics/timeframe** → `list[TimeframeComparisonItem]` — swing vs position stats (GROUP BY timeframe)
3. **GET /analytics/periodic?period=weekly|monthly** → `list[PeriodicSummaryItem]` — aggregated by ISO week or month, limit 12
4. **GET /analytics/calendar** → `list[CalendarDataPoint]` — daily P&L + trade count for heatmap

### Frontend (11 fetch + hook combos)

7 existing Phase 24 endpoints now have typed fetch functions + react-query hooks:
- `usePaperEquityCurve`, `usePaperDrawdown`, `usePaperDirection`, `usePaperConfidence`, `usePaperRiskReward`, `usePaperProfitFactor`, `usePaperSector`

4 new Phase 26 endpoints:
- `usePaperStreaks`, `usePaperTimeframe`, `usePaperPeriodic(period)`, `usePaperCalendar`

### Dependencies
- `react-activity-calendar@3.2.0` installed in frontend for calendar heatmap visualization

## Verification Results

- ✅ Backend: 36/36 tests pass (`pytest tests/test_paper_trade_analytics.py`)
- ✅ Frontend: TypeScript compiles with zero errors (`tsc --noEmit`)
- ✅ react-activity-calendar@3.2.0 present in node_modules
- ✅ Period param validation: `Query(pattern="^(weekly|monthly)$")` rejects arbitrary input (T-26-01 mitigated)

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **Streak ordering:** `ORDER BY closed_date, id` ensures deterministic sequence when multiple trades close same day
2. **Periodic weekly label:** `isoyear-W-week` format (e.g., "2025-W03") handles year boundaries correctly
3. **sqlalchemy imports:** Added `String` and `extract` to service imports for periodic SQL expressions

## Self-Check: PASSED

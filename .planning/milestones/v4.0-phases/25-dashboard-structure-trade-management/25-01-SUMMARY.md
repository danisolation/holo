---
phase: 25-dashboard-structure-trade-management
plan: "01"
name: "Dashboard Structure & Data Layer"
subsystem: "paper-trading-ui"
tags: [frontend, react-query, dashboard, tabs, paper-trading, backend-filter]
dependency_graph:
  requires: [Phase 24 paper-trading API]
  provides: [paper-trading types, fetch functions, react-query hooks, dashboard page shell, overview tab]
  affects: [Plan 25-02 (trades table, settings form)]
tech_stack:
  added: []
  patterns: [react-query hooks, shadcn tabs, responsive card grid, TypeScript API interfaces]
key_files:
  created:
    - frontend/src/app/dashboard/paper-trading/page.tsx
    - frontend/src/components/paper-trading/pt-overview-tab.tsx
  modified:
    - backend/app/api/paper_trading.py
    - backend/app/services/paper_trade_analytics_service.py
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/components/navbar.tsx
decisions:
  - "Trades and Settings tabs show placeholder text — Plan 02 replaces with real components"
  - "Analytics and Calendar tabs disabled — Phase 26 scope"
  - "SimulationConfigUpdateRequest imported directly (no alias) for type clarity"
metrics:
  duration: "3 min"
  completed: "2026-04-20"
  tasks: 2
  files: 7
---

# Phase 25 Plan 01: Dashboard Structure & Data Layer Summary

**One-liner:** Backend symbol filter + full TypeScript data layer (types/fetch/hooks) + paper trading dashboard page with tabbed shell and overview summary cards.

## What Was Built

### Backend (2 files)
- **Symbol query param** on `GET /paper-trading/trades?symbol=VNM` — filters by ticker symbol using `.upper()` normalization and SQLAlchemy parameterized query
- Service method `list_trades` extended with `symbol` parameter; `count_query` gets Ticker join only when symbol filter is active

### Frontend Data Layer (2 files)
- **5 TypeScript interfaces** in `api.ts`: `PaperTradeResponse`, `PaperTradeListResponse`, `SimulationConfigResponse`, `SimulationConfigUpdateRequest`, `AnalyticsSummaryResponse`
- **5 fetch functions**: `fetchPaperTrades`, `closePaperTrade`, `fetchPaperConfig`, `updatePaperConfig`, `fetchPaperAnalyticsSummary`
- **5 react-query hooks** in `hooks.ts`: `usePaperTrades`, `usePaperConfig`, `usePaperAnalyticsSummary`, `useUpdatePaperConfig`, `useClosePaperTrade`

### Frontend UI (3 files)
- **Navbar**: "Paper Trading" link added between "Đầu tư" and "Sự kiện"
- **Dashboard page** at `/dashboard/paper-trading`: 5-tab interface (Tổng quan active, Lệnh, Phân tích disabled, Lịch disabled, Cài đặt)
- **PTOverviewTab**: 4 summary cards — Tỷ lệ thắng, Tổng P&L, Tổng lệnh, TB P&L/lệnh with loading skeletons, error state, and green/red color coding

## Commits

| # | Hash | Description |
|---|------|-------------|
| 1 | `c57d30b` | Backend symbol filter + frontend types, fetch functions, react-query hooks |
| 2 | `dfb8baa` | Paper trading nav link, dashboard page with tabs, overview tab |

## Verification

- `next build` passes with zero errors on both commits
- `/dashboard/paper-trading` route appears in build route manifest
- All 5 interfaces, 5 fetch functions, 5 hooks exported correctly

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| Trades tab placeholder "Đang tải bảng lệnh..." | `page.tsx` L39-41 | Plan 02 Task 1 replaces with PTTradesTable |
| Settings tab placeholder "Đang tải cài đặt..." | `page.tsx` L51-53 | Plan 02 Task 2 replaces with PTSettingsForm |
| Analytics tab "Sắp có — Phase 26" | `page.tsx` L45-47 | Phase 26 scope, tab disabled |
| Calendar tab "Sắp có — Phase 26" | `page.tsx` L48-50 | Phase 26 scope, tab disabled |

## Self-Check: PASSED

All 8 files verified on disk. Both commit hashes (c57d30b, dfb8baa) found in git log.

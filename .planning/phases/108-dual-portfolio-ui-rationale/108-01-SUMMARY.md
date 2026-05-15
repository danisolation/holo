---
phase: 108-dual-portfolio-ui-rationale
plan: 01
subsystem: simulator-frontend
tags: [dual-portfolio, ai-rationale, tabs, ui-refactor]
dependency_graph:
  requires: [dual-portfolio-backend, ai-portfolio-auto-trade, portfolio-type-api-param]
  provides: [dual-portfolio-ui, ai-rationale-display, portfolio-scoped-components]
  affects: [phase-109-performance-comparison]
tech_stack:
  added: []
  patterns: [portfolioType-prop-drilling, tab-scoped-data-fetching]
key_files:
  created: []
  modified:
    - backend/app/schemas/simulator.py
    - backend/app/services/auto_trade_service.py
    - backend/app/services/simulator_service.py
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/simulator/page.tsx
    - frontend/src/components/simulator/pending-signals.tsx
    - frontend/src/components/simulator/trade-history.tsx
    - frontend/src/components/simulator/equity-chart.tsx
    - frontend/src/components/simulator/pnl-timeline.tsx
    - frontend/src/components/simulator/ai-accuracy-panel.tsx
  deleted:
    - frontend/src/components/simulator/auto-trade-toggle.tsx
decisions:
  - "Removed AutoTradeToggle entirely — server-side auto-trade since Phase 107"
  - "Removed localStorage auto-mode state from PendingSignals (obsolete)"
  - "Top-level tabs use string values 'ai'/'user', sub-tabs use numeric values"
  - "Rationale displayed inline with line-clamp-2 hover expand pattern"
metrics:
  duration: ~6min
  completed: 2026-05-15
  tasks: 3/3
  files: 12
---

# Phase 108 Plan 01: Dual Portfolio UI + AI Rationale Summary

Two-tab AI/User portfolio layout with scoped data fetching and Gemini rationale text surfaced in pending signals and trade history.

## One-liner
Two-tab simulator page (AI Portfolio / Danh mục thủ công) with portfolio_type-scoped data and DailyPick.explanation displayed in signals + trades.

## What Was Done

### Task 1: Backend rationale fields + frontend API types and hooks
- Added `explanation: str | None` to `PendingSignalResponse` schema
- Added `rationale: str | None` to `SimulatorTradeResponse` schema
- `get_pending_signals()` now includes `pick.explanation` in response
- `list_trades()` joins DailyPick.explanation as rationale when `daily_pick_id` exists
- All 6 frontend fetch functions accept `portfolioType` param (portfolio, trades, stats, equity, pnl, reset)
- Added `PortfolioSummaryItem`, `PortfolioListResponse` types and `fetchPortfolios` function
- All 7 hooks updated with `portfolioType` in queryKey and queryFn
- Added `usePortfolios` hook
- **Commit:** `1467cb0`

### Task 2: Two-tab simulator page layout
- Completely rewrote simulator page with top-level `<Tabs>` for AI/User switching
- AI tab: pending signals, trade history, equity chart, P&L timeline, AI accuracy
- User tab: trade form, trade history, equity chart, P&L timeline, accuracy
- Portfolio summary + positions table render data scoped to `activePortfolio`
- Reset dialog shows which portfolio is being reset
- Deleted `auto-trade-toggle.tsx` (server-side auto-trade since Phase 107)
- Removed `AutoTradeToggle` import from page
- **Commit:** `837628f`

### Task 3: Wire portfolioType into components + display AI rationale
- `PendingSignals`: removed localStorage auto-mode state/banner, added 💡 explanation text with line-clamp-2 hover expand
- `TradeHistory`: accepts `portfolioType` prop, added "Lý do" column with rationale text
- `EquityChart`: accepts `portfolioType` prop, passes to `useEquityHistory`
- `PnlTimeline`: accepts `portfolioType` prop, passes to `usePnlTimeline`
- `AiAccuracyPanel`: accepts `portfolioType` prop, passes to `useSimulatorStats`
- **Commit:** `53c3182`

## Deviations from Plan

None — plan executed exactly as written.

## Test Results

- All 550 backend tests pass
- TypeScript compiles with zero errors

## Self-Check: PASSED

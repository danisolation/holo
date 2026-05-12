---
phase: 95-stock-trading-simulator
plan: "03"
subsystem: frontend
tags: [simulator, frontend, dashboard, trading, ui]
dependency_graph:
  requires: ["95-01", "95-02"]
  provides: ["/simulator page", "simulator UI components", "simulator hooks"]
  affects: ["frontend/src/lib/api.ts", "frontend/src/lib/hooks.ts"]
tech_stack:
  added: []
  patterns: ["TanStack Query hooks", "base-ui tabs", "localStorage toggle", "dialog confirmation"]
key_files:
  created:
    - frontend/src/app/simulator/page.tsx
    - frontend/src/components/simulator/portfolio-summary.tsx
    - frontend/src/components/simulator/positions-table.tsx
    - frontend/src/components/simulator/trade-form.tsx
    - frontend/src/components/simulator/trade-history.tsx
    - frontend/src/components/simulator/ai-accuracy-panel.tsx
    - frontend/src/components/simulator/auto-trade-toggle.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
decisions:
  - "Used inline success/error messages instead of sonner toast (sonner not installed)"
  - "Used custom switch button instead of shadcn Switch (not available in project)"
  - "Used base-ui tabs with numeric value props matching project tab component"
  - "Used apiFetch helper for all API calls instead of raw fetch for consistent error handling"
metrics:
  duration: "4m"
  completed: "2026-05-12T10:14:43Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 7
  files_modified: 2
---

# Phase 95 Plan 03: Simulator Frontend Summary

Complete /simulator page with portfolio dashboard, manual trade form, paginated trade history, AI vs manual accuracy panel, auto-trade toggle with localStorage, and portfolio reset with confirmation dialog — all UI text in Vietnamese.

## What Was Built

### Task 1: Simulator API Functions & Hooks
- Added 6 TypeScript interfaces to `api.ts`: SimulatorPositionResponse, SimulatorPortfolioResponse, SimulatorTradeCreate, SimulatorTradeResponse, SimulatorTradesListResponse, SimulatorStatsResponse
- Added 5 fetch functions using the project's `apiFetch` helper: fetchSimulatorPortfolio, createSimulatorTrade, fetchSimulatorTrades, fetchSimulatorStats, resetSimulatorPortfolio
- Added 5 TanStack Query hooks in `hooks.ts`: useSimulatorPortfolio (30s stale), useSimulatorTrades (30s), useSimulatorStats (60s), useCreateSimulatorTrade (mutation), useResetSimulator (mutation)

### Task 2: Simulator Page & Components
- **PortfolioSummary**: Card showing starting capital, cash, market value, total equity, total P&L (with %), realized P&L, unrealized P&L. Green/red color coding.
- **PositionsTable**: Table with ticker, name, quantity, avg price, current price, market value, unrealized P&L, %. Empty state message.
- **TradeForm**: Manual trade entry with ticker, BUY/SELL toggle buttons, quantity, price, date (default today), notes. Shows API errors and success messages.
- **TradeHistory**: Paginated table with source filter tabs (All/AI/Manual). Shows date, ticker, side badge, quantity, price, fees, tax, net P&L, source badge.
- **AiAccuracyPanel**: Side-by-side AI vs Manual comparison with win rate, avg return %, total P&L. Better performer highlighted with ring.
- **AutoTradeToggle**: Custom switch with localStorage persistence. Shows "Tự động"/"Thủ công" badge with description.
- **SimulatorPage**: Main page layout combining all components with reset dialog confirmation.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | 1783414 | feat(95-03): add simulator API types, fetch functions, and TanStack Query hooks |
| 2 | 695eb4a | feat(95-03): add simulator page with portfolio, trade form, history, AI panel, auto-toggle |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Used apiFetch instead of raw fetch for API functions**
- **Found during:** Task 1
- **Issue:** Plan suggested raw `fetch()` calls, but project uses `apiFetch` helper with consistent error handling
- **Fix:** Used `apiFetch` for all simulator API functions to match project patterns
- **Files modified:** frontend/src/lib/api.ts

**2. [Rule 3 - Blocking] Used inline messages instead of sonner toast**
- **Found during:** Task 2
- **Issue:** Plan referenced sonner toast for success messages, but sonner is not installed in the project
- **Fix:** Used state-based success/error messages in TradeForm component
- **Files modified:** frontend/src/components/simulator/trade-form.tsx

**3. [Rule 3 - Blocking] Created custom switch instead of shadcn Switch**
- **Found during:** Task 2
- **Issue:** Plan referenced shadcn Switch component, but switch.tsx doesn't exist in UI components
- **Fix:** Created accessible custom toggle button with role="switch" and aria-checked
- **Files modified:** frontend/src/components/simulator/auto-trade-toggle.tsx

## Verification

- ✅ All 7 component files created with correct content
- ✅ TypeScript compilation passes (no new errors; pre-existing coach/journal errors unchanged)
- ✅ All acceptance criteria patterns found via grep
- ✅ All UI text in Vietnamese

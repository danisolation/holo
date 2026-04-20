---
phase: 25-dashboard-structure-trade-management
plan: "02"
name: "Trade Table, Settings Form & Signal Outcomes"
subsystem: "paper-trading-ui"
tags: [frontend, react-table, paper-trading, settings, signal-outcomes, UI-05, UI-07, UI-08]
dependency_graph:
  requires: [Plan 25-01 (types, hooks, page shell)]
  provides: [trade list table, settings form, signal outcome history on ticker page]
  affects: [Phase 26 analytics/calendar tabs]
tech_stack:
  added: []
  patterns: [react-table ColumnDef, server-side filtering via queryKey, mutation with cache invalidation, useEffect sync pattern]
key_files:
  created:
    - frontend/src/components/paper-trading/pt-trades-table.tsx
    - frontend/src/components/paper-trading/pt-settings-form.tsx
    - frontend/src/components/paper-trading/pt-signal-outcomes.tsx
  modified:
    - frontend/src/app/dashboard/paper-trading/page.tsx
    - frontend/src/app/ticker/[symbol]/page.tsx
decisions:
  - "Direction filter uses server-side params (queryKey changes trigger re-fetch), not client-side filtering"
  - "Settings form uses useEffect sync to populate local state from config query, then mutates via PUT"
  - "PTSignalOutcomes returns null when no trades exist — non-intrusive on ticker pages"
  - "STATUS_LABEL map extracted to module-level const in pt-signal-outcomes for concise row rendering"
metrics:
  duration: "3 min"
  completed: "2026-04-20"
---

# Phase 25 Plan 02: Trade Table, Settings Form & Signal Outcomes Summary

@tanstack/react-table trade list with 10 sortable/filterable columns, settings form with capital/auto-track/confidence config via PUT mutation, and signal outcome history (✅/❌/⏳) on ticker detail pages

## Tasks Completed

### Task 1: Trade list table with sorting, filtering, and manual close (UI-07)
**Commit:** `2859916`

Created `pt-trades-table.tsx` following the existing `trade-history.tsx` pattern:
- 10 columns: signal_date, symbol, direction, entry_price, exit_price, realized_pnl, realized_pnl_pct, status, confidence, actions
- 4 sortable columns (date, entry, P&L, AI score) with ArrowUpDown icon toggle
- Server-side filtering: symbol text input (auto-uppercased) + direction button group (Tất cả/Long/Bearish)
- Status badges with Vietnamese labels and semantic colors for all 7 backend statuses (pending → closed_manual)
- "Đóng" button on active/partial_tp rows triggers useClosePaperTrade mutation with pending state disable
- Loading skeleton and empty state ("Chưa có lệnh paper trading nào")
- Footer shows total trade count
- Wired into `<TabsContent value="trades">` replacing placeholder

### Task 2: Settings form (UI-08) + Signal outcome history (UI-05)
**Commit:** `184c684`

**PTSettingsForm** (`pt-settings-form.tsx`):
- Loads current config via usePaperConfig, syncs to local state via useEffect
- Three fields: initial capital (number input, min 1M VND), auto-track toggle (Bật/Tắt button pair), min confidence threshold (1-10 with helper text)
- Save button triggers useUpdatePaperConfig mutation with Loader2 spinner during save
- Wired into `<TabsContent value="settings">` replacing placeholder

**PTSignalOutcomes** (`pt-signal-outcomes.tsx`):
- Shows 10 most recent paper trades for a given ticker symbol
- Each row: date, direction badge (LONG green / BEARISH red), status label, outcome icon
- Outcome logic: realized_pnl > 0 → ✅, realized_pnl ≤ 0 (not null) → ❌, null → ⏳
- Returns null when no trades exist — zero visual impact on tickers without paper trades
- Inserted after TradingPlanPanel section on ticker detail page

## Deviations from Plan

None — plan executed exactly as written.

## Verification

- `next build` passes with zero errors after each task
- All 5 files created/modified match plan artifacts
- All 3 must_have truths addressed:
  - ✅ Sortable/filterable trade table with all specified columns
  - ✅ Settings form loads from GET and persists via PUT
  - ✅ Signal outcomes on ticker page with ✅/❌/⏳ icons

## Self-Check: PASSED

All 5 created/modified files verified on disk. Both commits (2859916, 184c684) confirmed in git log. Min line counts met: pt-trades-table=316, pt-settings-form=119, pt-signal-outcomes=66. Key imports (PTTradesTable, PTSettingsForm, PTSignalOutcomes) confirmed in consuming pages.

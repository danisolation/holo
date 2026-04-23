---
phase: 45-coach-dashboard-pick-performance
plan: "02"
subsystem: frontend/coach-dashboard
tags: [performance-cards, pick-history, coach-page, dashboard, ui]
dependency_graph:
  requires: [GET /picks/performance, GET /picks/history, useDailyPicks, useTrades, TradesTable, PickCard]
  provides: [PickPerformanceCards, PickHistoryTable, unified coach page, usePickHistory, usePickPerformance]
  affects: [/coach route, frontend API types]
tech_stack:
  added: []
  patterns: [self-contained-hook-component, outcome-badge-mapping, graceful-error-degradation, conditional-section-rendering]
key_files:
  created:
    - frontend/src/components/pick-performance-cards.tsx
    - frontend/src/components/pick-history-table.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/coach/page.tsx
decisions:
  - "PickPerformanceCards and PickHistoryTable are self-contained (own hooks internally) — coach page just renders them"
  - "Open trades section conditionally rendered only when BUY trades exist — hidden entirely otherwise"
  - "Error state for performance cards shows dashes (graceful degradation) rather than blocking error card"
  - "Filter buttons use variant toggle (default/outline) with aria-pressed for accessibility"
metrics:
  duration: ~3 minutes
  completed: 2026-04-23T10:52:00Z
  tasks_completed: 3
  tasks_total: 3
  test_count: 0
  files_changed: 5
---

# Phase 45 Plan 02: Coach Dashboard Frontend Summary

Unified 4-section coach dashboard at /coach — performance cards (win rate, P&L, R:R, streak), today's picks (unchanged), open trades (BUY filter, hidden when empty), and paginated pick history table with outcome badges and status filters.

## Tasks Completed

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | API types + fetch functions + hooks + PickPerformanceCards + PickHistoryTable | 3944f6e | 3 new TS interfaces, 2 fetch functions, 2 hooks, 2 new components |
| 2 | Restructure coach page into 4-section dashboard | 006737d | Coach page from 80→160 lines with perf cards, open trades, pick history |
| 3 | Visual verification (auto-approved) | — | ⚡ Auto-approved: all 4 sections wired, TypeScript compiles clean |

## What Was Built

### API Types (api.ts)
- `PickPerformanceResponse` — win_rate, total_pnl, avg_risk_reward, current_streak, counts
- `PickHistoryItem` — pick with outcome data, has_trades boolean
- `PickHistoryResponse` — paginated list (items, total, page, per_page)
- `fetchPickHistory()` — paginated with page/per_page/status params (replaces old days-based version)
- `fetchPickPerformance()` — fetches aggregated performance stats

### Hooks (hooks.ts)
- `usePickHistory({ page, status })` — queryKey includes page + status, 5min staleTime, 20 per page
- `usePickPerformance()` — queryKey ["picks", "performance"], 5min staleTime

### PickPerformanceCards Component
- 4-card grid: `grid grid-cols-2 sm:grid-cols-4 gap-4`
- Card 1: Tỷ lệ thắng — green >50%, red <50%, muted =50%
- Card 2: Lãi/lỗ thực hiện — signed VND with color
- Card 3: TB tỷ lệ R:R — "1:{ratio}" in default foreground
- Card 4: Chuỗi hiện tại — 🔥 wins / ❄️ losses / "— Chưa có"
- Loading: 4 skeleton cards; Error: all dashes (graceful degradation)
- All cards have aria-label for screen reader accessibility

### PickHistoryTable Component
- Self-contained: manages own page/status state internally
- Filter bar: 4 toggle buttons (Tất cả, Thắng, Thua, Đang theo dõi) with aria-pressed
- Table: 10 columns (Ngày, Mã, #, Giá vào, Cắt lỗ, Chốt lời, Kết quả, Lãi/Lỗ, Ngày, GD)
- OutcomeBadge: winner=green, loser=red, expired=outline, pending=blue
- ReturnCell: colored percentage with sign prefix
- Traded indicator: Sparkles icon with sr-only text
- Pagination: nav with aria-label, Trước/Sau buttons, "Hiển thị X-Y / Z gợi ý"
- Loading: 5 skeleton rows; Empty: History icon + message; Error: retry button
- `overflow-x-auto` for mobile horizontal scroll

### Coach Page Restructure
- Section 0: Page header (unchanged)
- Section 1: `<PickPerformanceCards />` — new
- Section 2: Today's picks grid + almost-selected (unchanged logic)
- Section 3: Open trades — `useTrades({ side: "BUY" })`, hidden when empty, with delete dialog
- Section 4: `<PickHistoryTable />` — new
- All sections in `space-y-8` vertical scroll layout per UI spec

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- All 5 key files exist on disk ✓
- Commit 3944f6e (Task 1) verified ✓
- Commit 006737d (Task 2) verified ✓
- TypeScript compilation: 0 errors ✓

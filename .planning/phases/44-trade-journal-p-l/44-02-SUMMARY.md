---
phase: 44-trade-journal-p-l
plan: "02"
subsystem: frontend
tags: [trade-journal, react-query, components, data-layer]
dependency_graph:
  requires: [trade-api, fifo-matching]
  provides: [trade-hooks, trade-components, journal-navbar]
  affects: [journal-page-assembly, phase-45-analytics]
tech_stack:
  added: []
  patterns: [react-query-hooks, controlled-filter-props, sortable-table-headers]
key_files:
  created:
    - frontend/src/components/trade-stats-cards.tsx
    - frontend/src/components/trade-filters.tsx
    - frontend/src/components/trades-table.tsx
    - frontend/src/components/delete-trade-dialog.tsx
  modified:
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/components/navbar.tsx
decisions:
  - Sparkles icon wrapped in span for title tooltip (lucide icons lack title prop)
  - Invalidating queryKey ["trades"] cascades to both trades list and stats caches
  - ArrowUpDown icon on sortable columns for visual affordance
metrics:
  duration: 3m
  completed: 2026-04-23T09:58:23Z
  tasks_completed: 2
  tasks_total: 2
  test_count: 0
  test_status: no_tests_required
---

# Phase 44 Plan 02: Trade Journal Frontend — Data Layer & Display Components Summary

**One-liner:** 4 TypeScript interfaces, 4 fetch functions, 4 React Query hooks, 4 display components (stats cards, filters, sortable table, delete dialog), and navbar link — zero type errors

## What Was Built

### Frontend Data Layer (api.ts + hooks.ts)

**TypeScript Interfaces:**
- `TradeResponse` — full trade record with P&L fields, ticker info, pick link
- `TradeStatsResponse` — aggregate stats: total_trades, realized P&L, open positions
- `TradesListResponse` — paginated response wrapper with total/page/page_size
- `TradeCreate` — trade creation payload with optional fee overrides and pick link

**Fetch Functions:**
- `fetchTrades(params?)` — paginated list with ticker/side filters, sort/order params via URLSearchParams
- `fetchTradeStats()` — aggregate statistics endpoint
- `createTrade(data)` — POST with JSON body
- `deleteTrade(id)` — DELETE by trade ID

**React Query Hooks:**
- `useTrades(params?)` — queryKey includes all filter params for cache granularity, 30s staleTime
- `useTradeStats()` — queryKey `["trades", "stats"]`, 30s staleTime
- `useCreateTrade()` — invalidates `["trades"]` on success (cascades to list + stats)
- `useDeleteTrade()` — invalidates `["trades"]` on success (cascades to list + stats)

### Navbar Update
- Added `{ href: "/journal", label: "Nhật ký" }` between "Huấn luyện" and "Sự kiện"

### Display Components

**TradeStatsCards** (`trade-stats-cards.tsx`):
- 3-card grid (`grid-cols-1 sm:grid-cols-3 gap-4`) with Skeleton loading states
- Cards: Tổng giao dịch, Lãi/lỗ thực hiện (green/red colored), Vị thế đang mở
- Values in `font-mono text-2xl font-bold`, labels in `text-xs text-muted-foreground`
- P&L colors: `text-[#26a69a]` positive, `text-[#ef5350]` negative, `text-muted-foreground` zero

**TradeFilters** (`trade-filters.tsx`):
- Controlled component with ticker/side props and change callbacks
- Input placeholder "Tìm mã..." with 3 toggle buttons: Tất cả / MUA / BÁN
- `aria-pressed` on each filter button for accessibility

**TradesTable** (`trades-table.tsx`):
- 10-column sortable table: Ngày, Mã, Loại, SL, Giá, Phí, Lãi/Lỗ gộp, Lãi/Lỗ ròng, AI, Actions
- Sortable columns (trade_date, side, net_pnl) with `aria-sort` and ArrowUpDown icons
- BUY/SELL badges with semantic colors (`#26a69a`/`#ef5350`)
- P&L cells with ▲/▼ prefix characters for positive/negative values
- Sparkles icon for AI-linked trades, Trash2 icon button for delete
- Pagination: "Hiển thị {start}-{end} / {total} giao dịch" with Trước/Sau buttons
- Empty state: BookOpen icon + "Chưa có giao dịch nào" message
- Loading state: 5 Skeleton rows

**DeleteTradeDialog** (`delete-trade-dialog.tsx`):
- Dialog with "Xóa giao dịch?" title and trade details in description
- Destructive confirm button "Xóa lệnh" with Loader2 spinner when deleting
- Cancel button "Hủy", disabled state during deletion

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Sparkles icon title prop type error**
- **Found during:** Task 2
- **Issue:** lucide-react Sparkles component doesn't accept `title` prop (TS2322)
- **Fix:** Wrapped Sparkles in `<span title="Theo gợi ý AI">` for tooltip
- **Files modified:** frontend/src/components/trades-table.tsx
- **Commit:** a1939d5

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 3067e1a | API types, fetch functions, hooks, navbar link |
| 2 | a1939d5 | Stats cards, filters, table, delete dialog components |

## Self-Check: PASSED

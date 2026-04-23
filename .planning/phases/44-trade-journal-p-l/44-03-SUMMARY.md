---
phase: 44-trade-journal-p-l
plan: "03"
subsystem: frontend
tags: [trade-journal, form-dialog, journal-page, pick-link, fee-calc]
dependency_graph:
  requires: [trade-api, fifo-matching, trade-hooks, trade-components]
  provides: [trade-entry-dialog, journal-page, complete-trade-flow]
  affects: [phase-45-analytics]
tech_stack:
  added: []
  patterns: [popover-command-autocomplete, zod-reactive-form, controlled-dialog-state]
key_files:
  created:
    - frontend/src/components/trade-entry-dialog.tsx
    - frontend/src/app/journal/page.tsx
  modified:
    - frontend/src/components/trades-table.tsx
    - frontend/src/lib/api.ts
    - backend/app/schemas/picks.py
    - backend/app/services/pick_service.py
decisions:
  - Added id field to DailyPickResponse for pick linking (backend + frontend)
  - Used Popover + Command combo for ticker autocomplete (same pattern as TickerSearch)
  - Controlled pickLinkChecked state for auto-suggest + manual toggle of AI pick checkbox
  - Added onCreateFirst prop to TradesTable for empty state CTA button
metrics:
  duration: 5m
  completed: 2026-04-23T17:06:12Z
  tasks_completed: 3
  tasks_total: 3
  test_count: 16
  test_status: all_passing
---

# Phase 44 Plan 03: Trade Entry Dialog & Journal Page Assembly Summary

**One-liner:** Zod-validated trade entry form with Popover+Command ticker autocomplete, auto-calculated VN market fees, AI pick link auto-suggestion, and complete /journal page wiring 5 components with filter/sort/pagination state

## What Was Built

### TradeEntryDialog (`trade-entry-dialog.tsx`)

**Form validation (zod schema):**
- `ticker_symbol`: required string (min 1 char)
- `side`: enum BUY/SELL
- `price`: positive number ("Giá phải lớn hơn 0")
- `quantity`: positive, mod 100 refine ("Số lượng phải là bội số của 100")
- `trade_date`: string, not future refine ("Ngày giao dịch không được trong tương lai")
- `user_notes`: optional, max 500 chars
- `daily_pick_id`: nullable number (optional)
- `broker_fee_override` / `sell_tax_override`: optional min 0

**Form hooks:**
- `useCreateTrade()` — mutation for trade creation
- `useTickers()` — ticker list for autocomplete
- `useDailyPicks()` — pick matching for AI link suggestion
- `useProfile()` — broker_fee_pct for fee auto-calculation
- `useForm<TradeForm>({ resolver: zodResolver(tradeSchema) })`

**Ticker autocomplete:**
- Popover + Command pattern (same as TickerSearch component)
- Displays `font-mono font-bold` symbol + `text-muted-foreground` name
- Filters up to 50 tickers with `shouldFilter={true}`
- Empty state: "Không tìm thấy mã nào."

**Fee auto-calculation:**
- Broker fee: `price × quantity × broker_fee_pct / 100` (rounded)
- Sell tax: `price × quantity × 0.001` (rounded, SELL only)
- Total fee: broker + sell tax
- Override toggle: "Tự nhập phí (ghi đè tính tự động)" checkbox reveals manual inputs

**Pick link auto-suggestion:**
- Checks dailyPicksData (picks + almost_selected) for matching ticker_symbol
- Auto-checks checkbox with "Theo gợi ý AI — {symbol} #{rank} ({date})"
- User can uncheck; sets `daily_pick_id` accordingly

**Error handling:**
- ApiError displays inline error message
- Generic fallback: "Không thể lưu lệnh. Vui lòng thử lại."
- Loader2 spinner on submit button during mutation

**Dialog lifecycle:**
- Reset form, selectedTicker, feeOverrideEnabled, apiError on close
- Dialog width: `sm:max-w-lg` (overrides default `sm:max-w-sm`)

### JournalPage (`journal/page.tsx`)

**State management:**
- Filter state: ticker (string), side (string)
- Sort state: sort column (default "trade_date"), order (default "desc")
- Pagination: page (default 1), resets to 1 on filter change
- Dialogs: entryDialogOpen, deleteTarget, deleteDialogOpen

**Component wiring:**
- `TradeStatsCards` — self-fetching stats display
- `TradeFilters` — ticker/side filter with change callbacks
- `TradesTable` — sortable table with pagination, delete, and createFirst callbacks
- `TradeEntryDialog` — controlled open/close via state
- `DeleteTradeDialog` — controlled via deleteTarget + deleteDialogOpen state

**Error state:**
- AlertTriangle icon + "Không thể tải nhật ký" heading
- "Thử lại" button calls refetch()

**Delete flow:**
- Click trash icon → sets deleteTarget + opens dialog
- Confirm → mutateAsync(deleteTarget.id) → close dialog + clear target

### TradesTable Enhancement

- Added `onCreateFirst?: () => void` optional prop
- Empty state now renders "Ghi lệnh đầu tiên" button when callback provided

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] DailyPickResponse missing id field for pick linking**
- **Found during:** Task 1
- **Issue:** Backend `DailyPickResponse` Pydantic schema and frontend `DailyPickResponse` interface did not include `id` field, making it impossible to set `daily_pick_id` when linking trades to AI picks
- **Fix:** Added `id: int` to backend schema, `id=pick.id` to service construction, `id: number` to frontend interface
- **Files modified:** backend/app/schemas/picks.py, backend/app/services/pick_service.py, frontend/src/lib/api.ts
- **Commit:** c951058

## Threat Mitigations Applied

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-44-08 Tampering form data | Zod validates quantity (mod 100), price (positive), date (not future), fee overrides (≥ 0). Backend Pydantic validates independently. | ✅ Applied |
| T-44-09 Pick link injection | daily_pick_id is optional/informational. Invalid FK rejected by DB constraint. | ✅ Accepted (low risk) |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | c951058 | TradeEntryDialog with ticker autocomplete, fee calc, pick link + DailyPickResponse id fix |
| 2 | c3600c4 | JournalPage at /journal wiring all components + TradesTable onCreateFirst prop |
| 3 | — | Checkpoint auto-approved (autonomous mode), 16 backend tests pass |

## Self-Check: PASSED

All 6 files verified on disk. Both commit hashes (c951058, c3600c4) found in git log. trade-entry-dialog.tsx: 517 lines (min 150 ✓). journal/page.tsx: 143 lines (min 50 ✓). 16 backend tests passing.

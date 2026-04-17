---
phase: 13-portfolio-enhancements
plan: "05"
subsystem: portfolio-frontend
tags: [portfolio, trade-edit, trade-delete, csv-import, dialogs, frontend]
dependency_graph:
  requires: [useUpdateTrade, useDeleteTrade, useCSVDryRun, useCSVImport, TradeResponse, CSVDryRunResponse, CSVPreviewRow]
  provides: [TradeEditDialog, TradeDeleteConfirm, CSVImportDialog, CSVPreviewTable, TradeHistory_actions_column]
  affects: [trade-history.tsx, portfolio/page.tsx]
tech_stack:
  added: []
  patterns: [controlled-dialog-base-ui, multi-step-dialog, drag-drop-file-upload, color-coded-validation-table]
key_files:
  created:
    - frontend/src/components/trade-edit-dialog.tsx
    - frontend/src/components/trade-delete-confirm.tsx
    - frontend/src/components/csv-import-dialog.tsx
    - frontend/src/components/csv-preview-table.tsx
  modified:
    - frontend/src/components/trade-history.tsx
    - frontend/src/app/dashboard/portfolio/page.tsx
decisions:
  - "Removed useMemo from trade-history columns to support action button state setters — ≤50 rows, no perf concern"
  - "CSVImportDialog exported as default to match DialogTrigger render pattern with embedded trigger button"
  - "Client-side 5MB file size validation before upload (T-13-13 mitigation)"
  - "CSV preview table max-h-[360px] with overflow scroll (T-13-14 mitigation)"
metrics:
  duration: "3m"
  completed: "2026-04-17"
  tasks_completed: 3
  tasks_total: 3
  files_modified: 6
---

# Phase 13 Plan 05: Trade Edit/Delete & CSV Import Frontend Summary

TradeEditDialog with prefilled form + PUT mutation, TradeDeleteConfirm with destructive confirmation, CSVImportDialog 3-step flow (upload/preview/result), CSVPreviewTable with color-coded validation, and trade history Actions column with Pencil/Trash2 per row.

## One-liner

Trade edit/delete dialogs with FIFO recalculation messaging, 3-step CSV import dialog with drag-drop upload and validation preview table, and trade history action buttons.

## What Was Built

### Task 1: Trade Edit Dialog + Delete Confirmation + Trade History Actions

**TradeEditDialog** (`trade-edit-dialog.tsx`):
- Controlled dialog with `open`/`onOpenChange` props, prefilled from `TradeResponse`
- Symbol field readonly with `bg-muted cursor-not-allowed`
- Side toggle: "Mua" (green) / "Bán" (red) matching trade-form.tsx pattern
- All numeric inputs with `font-mono` class
- Submit via `useUpdateTrade` mutation → PUT /api/portfolio/trades/{id}
- Submit button color follows side: `bg-[#26a69a]` BUY / `bg-[#ef5350]` SELL
- Error display: `text-xs text-[#ef5350]` inline
- useEffect resets state when trade prop changes

**TradeDeleteConfirm** (`trade-delete-confirm.tsx`):
- Destructive confirmation dialog with trade summary card
- Summary: Badge (Mua/Bán) + symbol + quantity + formatted VND total + date
- Delete via `useDeleteTrade` mutation → DELETE /api/portfolio/trades/{id}
- `variant="destructive"` button with "Đang xóa..." loading state

**TradeHistory Update** (`trade-history.tsx`):
- Added Pencil + Trash2 icon imports from lucide-react
- New `editTrade` and `deleteTrade` state (TradeResponse | null)
- Actions column: `flex items-center gap-1` with ghost icon buttons
- Pencil button opens TradeEditDialog, Trash2 opens TradeDeleteConfirm
- Removed `useMemo` from columns (action buttons use state setters)
- Wrapped return in Fragment to render dialogs after Card

### Task 2: CSV Import Dialog + Preview Table + Page Header

**CSVPreviewTable** (`csv-preview-table.tsx`):
- Status icons: CheckCircle (green), AlertTriangle (amber), XCircle (red)
- Row backgrounds: transparent valid, `bg-[#f59e0b]/10` warning, `bg-[#ef5350]/10` error
- Border-left indicators: `border-[#f59e0b]` warning, `border-[#ef5350]` error
- Columns: Status, Row, Mã CK, Loại, SL, Giá, Ngày GD, Phí, Vấn đề
- Container: `max-h-[360px] overflow-y-auto`

**CSVImportDialog** (`csv-import-dialog.tsx`):
- 3-step flow with `step` state (1 | 2 | 3)
- **Step 1 (Upload):** Drag-drop zone with `FileUp` icon, click-to-select, 5MB validation
  - File info display with `FileText` icon + size + remove button
  - "Tiếp tục" button triggers dry-run, "Đang phân tích..." loading
- **Step 2 (Preview):** Summary bar with colored valid/warning/error counts
  - CSVPreviewTable with validation rows
  - "Quay lại" returns to Step 1, "Xác nhận nhập N giao dịch" disabled if errors
  - Import error banner with destructive styling
- **Step 3 (Result):** CheckCircle icon + success message + FIFO recalculation count
  - "Đóng" button closes and resets all state
- Trigger button: `variant="outline" size="sm"` with Upload icon + "Nhập CSV"

**Portfolio Page Update** (`page.tsx`):
- Header right section changed to flex container with gap-2
- CSVImportDialog placed before TradeForm (Nhập CSV | Thêm giao dịch)

### Task 3: Visual Verification Checkpoint

Auto-approved via programmatic verification:
- TypeScript: Zero errors
- All 4 new component files exist
- 19/19 structural artifact checks passed
- All key patterns verified: hooks, icons, Vietnamese labels, form fields

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `38ed35d` | feat(13-05): add trade edit dialog, delete confirmation, and history actions column |
| 2 | `2aa4de6` | feat(13-05): add CSV import dialog, preview table, and page header update |

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **Removed useMemo from trade-history columns** — Actions column cell uses `setEditTrade`/`setDeleteTrade` state setters; useMemo with empty deps would stale-close over them. ≤50 rows makes this safe.
2. **CSVImportDialog default export** — Matches the `DialogTrigger render` pattern where the trigger button is embedded inside the component (same as TradeForm).
3. **Client-side 5MB file validation** — T-13-13 threat mitigation: validates before upload to prevent unnecessary network transfer.
4. **CSV preview scroll container** — T-13-14 threat mitigation: `max-h-[360px] overflow-y-auto` prevents DOM explosion with large CSV files.

## Self-Check: PASSED

All 6 files exist. Both commits verified (38ed35d, 2aa4de6). All key artifacts confirmed present.

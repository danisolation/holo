---
phase: 13-portfolio-enhancements
plan: "02"
subsystem: portfolio-service
tags: [portfolio, fifo, trade-edit, csv-import, backend]
dependency_graph:
  requires: [portfolio_service, lots, trades, tickers]
  provides: [recalculate_lots, update_trade, delete_trade, CSVImportService, TradeUpdateRequest, CSVPreviewRow, CSVDryRunResponse, CSVImportResponse]
  affects: [portfolio_service, portfolio_schemas]
tech_stack:
  added: []
  patterns: [FIFO-replay-from-history, csv-format-autodetect, row-level-validation]
key_files:
  created:
    - backend/app/services/csv_import_service.py
    - backend/tests/test_csv_import.py
  modified:
    - backend/app/services/portfolio_service.py
    - backend/app/schemas/portfolio.py
    - backend/tests/test_portfolio.py
decisions:
  - "recalculate_lots replays all trades chronologically in memory, building lots from BUY and consuming FIFO from SELL"
  - "CSV import accepts PortfolioService as parameter for record_trade calls — no circular dependency"
  - "T-13-03 mitigated: ValueError raised if SELL exceeds available during FIFO replay"
  - "T-13-05 mitigated: MAX_CSV_ROWS=1000 constant enforced before validation"
metrics:
  duration: "5m"
  completed: "2026-04-17"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 25
  tests_total: 59
  files_modified: 5
---

# Phase 13 Plan 02: FIFO Recalculation, Trade Edit/Delete, CSV Import Summary

FIFO lot recalculation via trade-history replay, trade update/delete with automatic recalculation, and CSV import with VNDirect/SSI auto-detection and row-level validation.

## One-liner

FIFO lot rebuild via chronological trade replay, trade edit/delete triggering recalculation, CSV import with VNDirect/SSI auto-detect and per-row validation.

## What Was Built

### Task 1: FIFO Recalculation + Trade Edit/Delete (TDD)

**recalculate_lots(ticker_id)** — Deletes all lots for a ticker, queries all trades ordered by `trade_date ASC, id ASC`, replays BUY trades to create new Lot objects, replays SELL trades consuming lots FIFO (oldest first). Raises `ValueError` if sell quantity exceeds available during replay (T-13-03 mitigation). Flushes to persist changes.

**update_trade(trade_id, side, quantity, price, trade_date, fees)** — Looks up trade by ID (ValueError if not found), updates all fields via Decimal conversion, calls `recalculate_lots(trade.ticker_id)`, commits, returns trade dict with ticker symbol.

**delete_trade(trade_id)** — Looks up trade by ID (ValueError if not found), stores `ticker_id`, deletes trade, flushes, calls `recalculate_lots(ticker_id)`, commits, returns `{"deleted": True, "trade_id": ...}`.

**TradeUpdateRequest schema** — Pydantic model with `side` (BUY|SELL pattern), `quantity` (>0), `price` (>0), `trade_date`, `fees` (>=0, default 0).

**Tests (9):** BUY-only lots created, BUY+SELL FIFO consumption, no trades creates none, sell exceeds raises ValueError, update changes fields + recalculates, update not found raises, delete removes + recalculates, delete not found raises, delete SELL restores lots.

### Task 2: CSV Import Service (TDD)

**CSVImportService** — Full CSV import pipeline with:

- `detect_format(header)` — Returns "VNDirect" if headers contain "Mã CK"/"Mã chứng khoán" + "Khối lượng"/"KL". Returns "SSI" if headers contain "Symbol" + "Quantity". Otherwise "unknown".
- `parse_rows(content)` — Reads CSV string, detects format, maps columns. VNDirect: Mã CK→symbol, Loại GD (Mua/Bán)→BUY/SELL, DD/MM/YYYY→ISO date. SSI: direct English mapping with YYYY-MM-DD dates. Raises ValueError for unknown format.
- `validate_rows(rows)` — Batch queries ticker symbols, validates each row: symbol exists, quantity > 0, price > 0, side BUY/SELL, trade_date not future. Detects duplicates (same date+symbol+side+qty) as warnings.
- `dry_run(content)` — Parse + validate, returns CSVDryRunResponse with per-row status and valid/warning/error counts.
- `import_trades(content, portfolio_service)` — Parse, validate, call record_trade for valid rows. T-13-05: rejects > 1000 rows.

**New schemas** — `CSVPreviewRow(row_number, symbol, side, quantity, price, trade_date, fees, status, message)`, `CSVDryRunResponse(format_detected, rows, total_valid, total_warnings, total_errors)`, `CSVImportResponse(trades_imported, tickers_recalculated)`.

**Tests (16):** VNDirect format detection (2 variants), SSI detection, unknown detection, VNDirect parsing, SSI parsing, unknown raises, unknown symbol error, negative qty error, duplicate warning, future date error, invalid side error, dry_run counts, import records valid, import skips errors, rejects >1000 rows.

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | `ec40a96` | test(13-02): add failing tests for recalculate_lots, update_trade, delete_trade |
| 2 | `af6e369` | feat(13-02): implement recalculate_lots, update_trade, delete_trade with TradeUpdateRequest schema |
| 3 | `fc1c351` | test(13-02): add failing tests for CSV import service |
| 4 | `f5601f3` | feat(13-02): implement CSV import service with VNDirect/SSI format detection and validation |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Security] Added T-13-03 ValueError on SELL exceeds available during replay**
- **Found during:** Task 1
- **Issue:** Threat model T-13-03 requires rollback if sell quantity exceeds available during FIFO replay
- **Fix:** Added available-quantity check before FIFO consumption in recalculate_lots, raises ValueError
- **Files modified:** backend/app/services/portfolio_service.py
- **Commit:** af6e369

**2. [Rule 2 - Security] Added T-13-05 max 1000 rows enforcement**
- **Found during:** Task 2
- **Issue:** Threat model T-13-05 requires max 1000 rows per CSV file server-side
- **Fix:** Added MAX_CSV_ROWS constant and check in import_trades, with dedicated test
- **Files modified:** backend/app/services/csv_import_service.py, backend/tests/test_csv_import.py
- **Commit:** f5601f3

## Decisions Made

1. **recalculate_lots in-memory lot tracking** — Open lots tracked in a list during replay rather than querying DB mid-replay — avoids flush/query cycles and keeps replay atomic
2. **CSV import_trades accepts PortfolioService parameter** — Avoids circular import; caller passes the service instance for record_trade calls
3. **CSVImportService uses Python csv module** — Standard library handles quoting, escaping, Unicode (Vietnamese characters) correctly
4. **Duplicate detection is additive** — First occurrence is "valid", subsequent duplicates are "warning" (not error) — allows intentional duplicate trades

## Test Results

```
59 passed, 4 warnings in 4.32s
```

- 34 existing tests: all pass (FIFO, P&L, validation, recording, schema, router, dividend, performance, allocation)
- 9 new portfolio tests: all pass (recalculate_lots, update_trade, delete_trade)
- 16 new CSV import tests: all pass (format detection, parsing, validation, dry-run, import)

## Self-Check: PASSED

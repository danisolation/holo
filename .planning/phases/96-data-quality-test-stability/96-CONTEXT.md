# Phase 96: Data Quality & Test Stability - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning
**Mode:** Auto-generated (infrastructure phase — discuss skipped)

<domain>
## Phase Boundary

Test suite is green and simulator has comprehensive test coverage; data integrity issues are automatically detected.

Requirements: DQ-01, DQ-02, DQ-03, DQ-04
- DQ-01: Fix pre-existing test failures (test_weekly_financial_crawl_calls_service scheduler test)
- DQ-02: Thêm unit tests cho simulator service (buy, sell, SL/TP auto-close, fee calculation, FIFO matching)
- DQ-03: Thêm unit tests cho pick generation pipeline (signal filter, unified format, date range)
- DQ-04: Data integrity checks (phát hiện gaps trong daily_prices, duplicate entries, stale analysis)

</domain>

<decisions>
## Implementation Decisions

### Agent's Discretion
All implementation choices are at the agent's discretion — pure infrastructure/test phase. Use existing test patterns from the codebase.

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `backend/app/services/simulator_service.py` — Simulator business logic (buy, sell, FIFO, fees)
- `backend/app/services/pick_service.py` — Pick generation pipeline
- `backend/app/services/auto_trade_service.py` — Auto-trade execution
- `backend/tests/` — Existing test directory with 436+ tests

### Known Issues
- `test_weekly_financial_crawl_calls_service` has been failing pre-existing
- Price unit mismatch: DailyPrice.close in nghìn đồng (×1000 for VND)
- Pick service signal filter accepts both "long" and "mua"
- Analysis type filter accepts both TRADING_SIGNAL and UNIFIED

</code_context>

<specifics>
## Specific Ideas

No specific requirements — infrastructure/test phase.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

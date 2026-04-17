# Phase 13: Portfolio Enhancements - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Enhance the existing portfolio system (Phase 8) with dividend income tracking, visual analytics (performance line chart + allocation pie chart), trade edit/delete with FIFO recalculation, and CSV trade import. This phase builds entirely on the existing Trade/Lot/PortfolioService architecture.

</domain>

<decisions>
## Implementation Decisions

### Dividend Income Tracking
- Dividend crediting uses existing `CorporateEvent` table (Phase 7) with `event_type=CASH_DIVIDEND` and `record_date` matching against held lots — no new crawling needed, just a query joining lots held on record_date
- Dividend income shown as a new field in `HoldingResponse` and `PortfolioSummaryResponse` — `dividend_income: float` — separate from realized/unrealized P&L
- Dividend income computation: sum of `dividend_amount * remaining_quantity` for all CASH_DIVIDEND events where ticker has open lots on the record_date
- No automatic trade creation for stock dividends in this phase — stock dividend lots are a deferred enhancement (complex FIFO implications)

### Portfolio Visual Analytics
- Performance chart: daily portfolio value line chart using Recharts (already installed) — compute daily snapshots by joining holdings × DailyPrice for each date
- Performance data stored as a materialized view or cached API response (computed on-demand, cached for 1 hour) — no new table needed for MVP
- Allocation pie chart: two modes — by ticker (default) and by sector — using Recharts PieChart component
- Chart period selector: 1M / 3M / 6M / 1Y / All (default 3M) — consistent with existing chart patterns in ticker detail page
- Charts placed on the existing portfolio dashboard page (`/dashboard/portfolio`) below the summary cards

### Trade Edit/Delete & CSV Import
- Trade edit: PUT endpoint that updates the trade fields, then full FIFO recalculation for that ticker (delete all lots, replay all BUY trades chronologically, re-consume with SELL trades)
- Trade delete: DELETE endpoint with same full FIFO recalculation approach — ensures lot state is always consistent
- FIFO recalculation as a service method `recalculate_lots(ticker_id)` — replayable from trade history
- CSV import: support VNDirect and SSI export formats (auto-detect by header row) — parse to TradeRequest[] then batch-insert with dry-run mode
- Dry-run mode: validate all rows, return preview with errors/warnings, require explicit confirmation POST to commit
- CSV upload via multipart form POST `/api/portfolio/import` with query param `?dry_run=true|false`

### Agent's Discretion
- Specific Vietnamese column names for CSV parsing (symbol mapping, date format detection)
- Chart color palette for allocation pie (follow existing exchange color pattern or use distinct palette)
- Performance snapshot granularity (daily vs weekly for periods > 6M)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PortfolioService` in `backend/app/services/portfolio_service.py` — full FIFO lot management, P&L computation
- `Trade` model with side/quantity/price/fees/trade_date fields
- `Lot` model with FIFO tracking (remaining_quantity)
- `CorporateEvent` model with dividend_amount, record_date, event_type
- `PortfolioSummary` component in `frontend/src/components/portfolio-summary.tsx` — 4 stat cards
- Portfolio API at `/api/portfolio/` — trades CRUD, holdings, summary endpoints
- Recharts already installed for non-financial charts
- `usePortfolioSummary` hook exists in `frontend/src/lib/hooks.ts`

### Established Patterns
- Backend: FastAPI router + service class + Pydantic schemas
- Frontend: shadcn/ui Card components, react-query hooks, Vietnamese labels
- Portfolio page at `frontend/src/app/dashboard/portfolio/page.tsx`
- FIFO lot consumption in `_consume_lots_fifo()` method

### Integration Points
- New endpoints added to `backend/app/api/portfolio.py` router
- New schemas in `backend/app/schemas/portfolio.py`
- Frontend components added to portfolio page
- Dividend query joins `corporate_events` × `lots` tables

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing portfolio patterns from Phase 8.

</specifics>

<deferred>
## Deferred Ideas

- Stock dividend auto-crediting (creates new lots from STOCK_DIVIDEND events) — complex FIFO implications, defer to v3.0
- Portfolio comparison against VN-Index benchmark — requires index data pipeline
- Tax reporting / capital gains summary — requires Vietnamese tax rules

</deferred>

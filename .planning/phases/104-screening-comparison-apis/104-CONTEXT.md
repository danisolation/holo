# Phase 104: Screening & Comparison APIs - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Backend provides endpoints for filtering tickers by sector with multi-criteria sorting, peer comparison with ranked metrics, and sector detail with constituent ticker data.

Requirements: PEER-03, SCRN-02, SCRN-03

Success Criteria:
1. API endpoint accepts sector/industry filter plus optional criteria (min/max volume, % change range, P/E range) and returns matching tickers with their metric values
2. API endpoint supports sort-by on any returned metric column (volume, % change, P/E, close price) with ascending/descending order
3. Peer comparison API endpoint returns ranked metrics (P/E, volume, % change, market cap) for all tickers in a given sector, with the queried ticker highlighted
4. Sector detail API endpoint returns all tickers belonging to a sector with their latest price data and 7D/30D performance values

</domain>

<decisions>
## Implementation Decisions

### API Design
- Add endpoints to existing market router (backend/app/api/market.py)
- GET /api/market/screener — sector/industry/criteria filter with sort
- GET /api/market/sector/{sector_name} — sector detail with tickers
- GET /api/market/peers/{symbol} — peer comparison for a ticker
- Use query params for filters (sector, industry, min_volume, max_volume, min_change, max_change, sort_by, sort_order)
- Pagination via offset/limit (consistent with existing patterns)

### Service Layer
- Create ScreenerService in new file (not extend SectorAnalysisService — different concern)
- Reuse DailyPrice + Ticker joins from SectorAnalysisService pattern
- P/E data: use FinancialStatement.pe_ratio if available, else null
- Volume: from latest DailyPrice.volume
- % change: compute from DailyPrice close-to-close (1D, 7D, 30D)

### the agent's Discretion
All remaining implementation choices at agent's discretion. Follow existing patterns from sector_analysis_service.py and market.py.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SectorAnalysisService` — CTE+LAG pattern for sector performance (sector_analysis_service.py)
- `Ticker` model — has sector, industry, market_cap fields (models/ticker.py)
- `DailyPrice` model — has close, volume, date (models/daily_price.py)
- `FinancialStatement` model — may have PE ratio data
- `market.py` router — existing sector/breadth endpoints with TTLCache pattern
- ICB sector mapping in ticker_service.py — 11 sectors, 186 tickers enriched

### Established Patterns
- TTLCache for API responses (300s default)
- Pydantic response models in schemas/ directory
- SQLAlchemy async session via async_session()
- LAG window functions for prev_close computation

### Integration Points
- New endpoints added to existing market router
- Frontend will consume these APIs in Phase 105

</code_context>

<specifics>
## Specific Ideas

No specific requirements — follow ROADMAP success criteria and existing codebase patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

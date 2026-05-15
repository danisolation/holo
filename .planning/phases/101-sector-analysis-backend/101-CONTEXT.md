# Phase 101: Sector Analysis Backend - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Backend service + API endpoints for sector-level analysis:
1. Sector Performance — average % price change per sector for today/7D/30D periods
2. Sector Net Flow — net buying/selling volume per sector per day (volume × sign of price change)

All computed from existing Ticker.sector + DailyPrice tables. HOSE only (~186 tickers).

</domain>

<decisions>
## Implementation Decisions

### Service Architecture
- Create `SectorAnalysisService` in `backend/app/services/sector_analysis_service.py`
- Follow same pattern as MarketBreadthService: AsyncSession-based, pure computation
- Compute on-the-fly from DailyPrice + Ticker (no new DB table)
- TTLCache for caching (300s)

### API Design
- GET /api/market/sectors — sector performance summary (avg % change per sector, today/7D/30D)
- GET /api/market/sector-flow — net flow per sector per day
- Both support date range params (start_date, end_date)
- Add to same `market.py` router created in Phase 100

### Computation Details
- Sector Performance: For each sector, avg of (close_today - close_prev) / close_prev × 100 for each ticker
- 7D/30D: Same but comparing close_today vs close_N_days_ago
- Net Flow: For each day per sector, sum of (volume × sign(close - prev_close)) for each ticker
- Group by Ticker.sector field — handle null/empty sectors as "Khác" (Other)
- DailyPrice.close in nghìn đồng — ratios cancel out, no conversion needed

### Agent's Discretion
- Response format details
- Query optimization (window functions vs subqueries)
- Market cap weighting (optional, suggest equal weight for simplicity)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Ticker` model — has sector, industry, market_cap fields
- `DailyPrice` model — OHLCV with ticker_id FK
- `TickerService.get_ticker_id_map()` — all active tickers
- Phase 100 creates `app/api/market.py` router — reuse it

### Established Patterns  
- JOIN DailyPrice with Ticker for sector grouping
- Window functions used in pick_service.py for batch per-ticker queries
- Pydantic schemas for typed responses

### Integration Points
- Extend `app/api/market.py` router from Phase 100
- New schemas in `app/schemas/market.py` (created in Phase 100)

</code_context>

<specifics>
## Specific Ideas

- Use SQL GROUP BY Ticker.sector with AVG() for sector performance
- Window function LAG() for prev_close to compute daily change
- Consider returning sector list with ticker count per sector for frontend drill-down

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

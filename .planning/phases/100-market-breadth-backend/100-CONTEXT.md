# Phase 100: Market Breadth Backend - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Backend service + API endpoints for market breadth indicators:
1. A/D Line (Advance/Decline) — daily count of advancing vs declining HOSE tickers
2. MA Breadth — % stocks above MA50 and % above MA200
3. 52-Week Highs/Lows — daily count of new 52-week highs vs lows (rolling 252 trading days)

All computed from existing DailyPrice table (~186 HOSE tickers). No new DB tables needed — compute on-the-fly from price data.

</domain>

<decisions>
## Implementation Decisions

### Service Architecture
- Create `MarketBreadthService` in `backend/app/services/market_breadth_service.py`
- Follow same pattern as IndicatorService/DiscoveryService: AsyncSession-based, pure computation
- All breadth metrics computed on-the-fly from DailyPrice (no new DB table — cache in TTLCache)
- Return data for configurable date range (default 90 days)

### API Design
- GET /api/market/breadth — returns A/D line, MA breadth, highs/lows in one response
- Date range params: `start_date` and `end_date` (query params)
- Response: { ad_line: [...], ma_breadth: [...], highs_lows: [...] }

### Computation Details
- A/D: Compare each ticker's close today vs close previous day. Advancing = close > prev_close
- MA50/MA200: Compute SMA from DailyPrice.close for each ticker, check if current close > SMA
- 52-week: Rolling window of 252 trading days, check if today's close is max/min of window
- DailyPrice.close is in nghìn đồng (e.g., 26.9 = 26,900 VND) — consistent within comparison, no conversion needed

### Agent's Discretion
- TTL cache duration (suggest 300s like other cached endpoints)
- Error handling for tickers with insufficient history
- Query optimization strategy (batch vs per-ticker)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `IndicatorService` (indicator_service.py) — pattern for batch ticker computation with session
- `TickerService.get_ticker_id_map()` — returns all active tickers
- `DailyPrice` model — OHLCV data with ticker_id, date, close, high, low, volume
- `TechnicalIndicator` model — has sma_50, sma_200 already computed
- TTLCache pattern used in api/tickers.py, api/discovery.py

### Established Patterns
- Services take AsyncSession in constructor
- API routers use `Depends(get_db)` for session injection
- Pydantic schemas in `app/schemas/` for response models
- Router registered in `app/api/router.py`

### Integration Points
- New router: `app/api/market.py` → register in `app/api/router.py`
- Can leverage existing `technical_indicators` table for MA50/MA200 instead of recomputing

</code_context>

<specifics>
## Specific Ideas

- Use existing technical_indicators.sma_50 and sma_200 for MA breadth (already computed daily)
- A/D line and 52-week highs/lows need raw DailyPrice queries
- Consider batch SQL queries with window functions for efficiency

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

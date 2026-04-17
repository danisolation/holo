# Phase 7: Corporate Actions — Context

**Gathered:** 2025-07-18
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous smart discuss)

<domain>
## Phase Boundary

**Goal**: Historical prices accurately reflect stock splits, dividends, and bonus shares so charts and analysis use correct data.

**In scope:**
- Corporate event data model and migration
- Crawler for VCI corporate events (sự kiện doanh nghiệp)
- Adjustment factor computation for each event type
- Populating `adjusted_close` in `daily_prices` table
- Daily corporate action check + auto-adjustment
- Re-triggering indicator recompute after adjustment

**Out of scope:**
- Rights issues (quyền mua cổ phiếu) — too complex, deferred
- Corporate action UI page (events are backend-only, charts show adjusted prices)
- Manual corporate event entry

</domain>

<decisions>
## Implementation Decisions

### D-07-01: Data Source for Corporate Events
**Decision:** Use vnstock/VCI API for corporate event data.
**Rationale:** vnstock wraps VCI endpoints that provide sự kiện doanh nghiệp (corporate events) including dividends, bonuses, splits. Already in our stack — no new dependency needed.

### D-07-02: Event Type Classification
**Decision:** Four event types: CASH_DIVIDEND, STOCK_DIVIDEND, BONUS_SHARES, STOCK_SPLIT.
**Rationale:** These are the four types specified in CORP-05. Maps to VN market standard events.

### D-07-03: Adjustment Factor Approach
**Decision:** Cumulative backward adjustment factor per ticker. Each event produces a ratio (e.g., 2:1 split = 0.5). Multiply all prior close prices by the cumulative product of factors from that date forward.
**Rationale:** Standard financial data approach. VN market uses same math as international markets for splits/dividends. Working backward ensures most recent prices equal raw close.

### D-07-04: VN Market Dividend Formula
**Decision:** For cash dividends: `factor = (close_before - dividend_per_share) / close_before`. For stock dividends/bonus: `factor = 1 / (1 + ratio)`. For splits: `factor = 1 / split_ratio`.
**Rationale:** Standard formulas used by Bloomberg, VNDirect, and other VN market data providers.

### D-07-05: Adjustment Trigger
**Decision:** Daily check after price crawl. If new corporate events detected, recalculate adjusted_close for all affected tickers and trigger indicator recompute.
**Rationale:** Per CORP-04 — automated pipeline. Integrates into existing job chaining (after daily_price_crawl).

### D-07-06: Storage Pattern
**Decision:** Store events in `corporate_events` table. Compute `adjusted_close` by scanning all events for a ticker and applying cumulative factors to `daily_prices.adjusted_close`. Write directly to existing column.
**Rationale:** `adjusted_close` column already exists in `daily_prices` (added in Phase 1, currently NULL). No schema change needed for prices — only new table for events.

### D-07-07: Idempotent Recomputation
**Decision:** Full recompute from scratch on each adjustment run (scan all events, recalculate all adjusted_close). Don't try to incrementally update.
**Rationale:** For 400 tickers × ~500 trading days = 200K rows — fast enough with bulk UPDATE. Simpler and avoids edge cases with out-of-order event discovery.

</decisions>

<code_context>
## Existing Code Insights

- `daily_prices.adjusted_close` column exists (Numeric(12,2), nullable=True, currently all NULL)
- `VnstockCrawler` already has circuit breaker protection (Phase 6)
- Job chaining in `manager.py` chains after `daily_price_crawl` — can add corporate action check there
- `IndicatorService.compute_all_tickers()` exists for recomputing indicators after adjustment
- Alembic migration chain: 001 → 002 → 003 → 004 → 005 (Phase 6). Next = 006.
- vnstock `Listing` and `Quote` APIs are used. Need to explore vnstock's corporate events API.

</code_context>

<specifics>
## Specific Ideas

- vnstock's corporate event API may use `Stock(symbol).company.events()` or similar — research needed
- VCI endpoint for corporate events: `https://api-finfo.vndirect.com.vn/v4/corporate_events` — verify during research
- Consider caching adjustment factors per ticker to avoid recomputing on every API request

</specifics>

<deferred>
## Deferred Ideas

- Rights issues handling (complex pricing, rare for top 400 tickers)
- Corporate actions calendar UI page
- Historical backfill of corporate events (only track from implementation date forward)

</deferred>

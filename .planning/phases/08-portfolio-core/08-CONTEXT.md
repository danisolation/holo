# Phase 8: Portfolio Core — Context

**Gathered:** 2026-04-18
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous smart discuss)

<domain>
## Phase Boundary

**Goal**: User can track personal trades and see accurate FIFO-based P&L on all positions.

**In scope:**
- Trade model (buy/sell) with ticker, quantity, price, date, fees
- Lot model for FIFO tracking (each buy creates a lot, sell consumes lots FIFO)
- Portfolio service: FIFO cost basis, realized/unrealized P&L computation
- API endpoints: POST /trades (buy/sell), GET /portfolio, GET /portfolio/summary, GET /trades
- Frontend portfolio page: holdings table, P&L summary, trade entry form, trade history

**Out of scope:**
- Dividend income tracking on held positions (PORT-08, v2.0)
- Portfolio performance chart over time (PORT-09, v2.0)
- Portfolio allocation pie chart (PORT-10, v2.0)
- Trade edit/delete (PORT-11, v2.0)
- Broker CSV import (PORT-12, v2.0)
- Short selling — only long positions (buy then sell)
- Margin trading — cash trades only

</domain>

<decisions>
## Implementation Decisions

### D-08-01: Trade Data Model
**Decision:** Single `trades` table with columns: id, ticker_id, side (BUY/SELL), quantity, price, fees, trade_date, created_at. No separate orders table — this is manual trade logging, not order management.
**Rationale:** Simple trade log for a personal portfolio tracker. Single user, manual entry only.

### D-08-02: FIFO Lot Tracking
**Decision:** Explicit `lots` table: id, trade_id (FK to buy trade), ticker_id, buy_price, quantity, remaining_quantity, buy_date, created_at. Sells consume lots FIFO by updating remaining_quantity. When remaining_quantity = 0, lot is fully consumed.
**Rationale:** Explicit lot tracking enables accurate realized P&L per-trade. FIFO is the VN standard for individual investors. Alternative (weighted average cost) was explicitly excluded in REQUIREMENTS.md.

### D-08-03: P&L Computation
**Decision:** 
- **Realized P&L** = Sum of (sell_price - buy_price) × quantity for each consumed lot, minus fees
- **Unrealized P&L** = Sum of (latest_market_price - buy_price) × remaining_quantity for open lots
- **Total return %** = (realized + unrealized) / total_invested × 100
- Use latest `daily_prices.close` as market price for unrealized P&L.
**Rationale:** Standard financial P&L calculation. FIFO matching means each sell creates specific realized P&L entries.

### D-08-04: API Design
**Decision:** 
- `POST /api/portfolio/trades` — Record a trade (buy or sell)
- `GET /api/portfolio/holdings` — Current holdings with per-position P&L
- `GET /api/portfolio/summary` — Total invested, market value, total return
- `GET /api/portfolio/trades` — Trade history with sorting/filtering
**Rationale:** RESTful API under /portfolio prefix. Separate from /tickers namespace.

### D-08-05: Frontend Portfolio Page
**Decision:** New route at `/dashboard/portfolio` with 3 sections: (1) Summary cards (total invested, market value, total return), (2) Holdings table (ticker, qty, avg cost, market price, P&L, P&L%), (3) Trade history table with buy/sell form.
**Rationale:** Consistent with existing dashboard layout. Uses shadcn/ui tables and cards.

### D-08-06: Sell Validation
**Decision:** Sell quantity cannot exceed available shares for that ticker. If user tries to sell more than they own, return 400 error with clear message.
**Rationale:** Prevents negative positions. No short selling per scope constraint.

### D-08-07: Fee Handling
**Decision:** Fees stored per trade (optional, default 0). VN standard: 0.15% brokerage + 0.1% tax on sell. Fees are subtracted from P&L but NOT from cost basis.
**Rationale:** Simple fee tracking. User enters total fee amount (not computed) — different brokers charge different rates.

</decisions>

<code_context>
## Existing Code Insights

- Backend API router pattern: `backend/app/api/router.py` aggregates sub-routers
- Frontend dashboard exists at `/dashboard` with sidebar navigation
- Daily prices available for unrealized P&L via `DailyPrice.close`
- TickerService.get_ticker_id_map() returns {symbol: id}
- Alembic migration chain: 001-006. Next = 007.
- No existing portfolio/trade models or API endpoints

</code_context>

<specifics>
## Specific Ideas

- Use @tanstack/react-table for holdings and trade history tables (already in stack per STACK.md)
- Use lightweight-charts or a simple P&L bar chart for portfolio overview
- Trade entry could be a modal or inline form on the portfolio page
- Consider adding a quick trade button from the ticker detail page (/ticker/[symbol])

</specifics>

<deferred>
## Deferred Ideas

- Dividend income tracking on held positions (PORT-08)
- Portfolio performance chart (PORT-09)
- Trade edit/delete (PORT-11)
- Broker CSV import (PORT-12)
- Portfolio allocation pie chart (PORT-10)

</deferred>

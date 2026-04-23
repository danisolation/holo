# Phase 44: Trade Journal & P&L - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

User can log real buy/sell trades and see accurate profit/loss calculations with VN market fees and taxes, optionally linking trades to daily AI picks. This phase builds the trade journaling backend and frontend — performance analytics and pick tracking come in Phase 45.

</domain>

<decisions>
## Implementation Decisions

### Trade Entry (JRNL-01)
- Trade form fields: ticker (autocomplete from tickers table), side (BUY/SELL), price, quantity, trade_date (default today), user_notes (optional)
- Fees auto-calculated from UserRiskProfile.broker_fee_pct (default 0.15%) on both BUY and SELL sides + mandatory 0.1% sales tax on SELL only
- User can override auto-calculated fees with actual fees if broker charges differently
- Quantity must be multiple of 100 (HOSE lot size) — form validates this
- Trade date cannot be in the future; default to today

### FIFO P&L Calculation (JRNL-02)
- Separate `trades` and `lots` tables — BUY creates lots, SELL consumes lots via FIFO matching
- FIFO matching: when SELL, consume oldest open lots for that ticker first (by buy_date ASC, then lot id ASC)
- Realized P&L per SELL trade: Σ((sell_price - lot_buy_price) × matched_quantity) - total_fees
- Total fees on a matched sell = buy-side broker fee + sell-side broker fee + sell tax (0.1%)
- Display both gross P&L (price diff only) and net P&L (after all fees/tax)
- Unrealized P&L shown for open lots using latest DailyPrice close — calculated on-the-fly, not stored
- If SELL quantity exceeds available lots, reject the trade with error message

### Pick Linking (JRNL-03)
- Optional `daily_pick_id` FK on trades table — links to daily_picks when user followed AI recommendation
- When user selects a ticker that matches a recent daily pick (last 7 days), auto-suggest the link with a checkbox "Theo gợi ý AI"
- Link is informational only — no enforcement. User can trade tickers not in daily picks
- Pick link enables Phase 45 to track "follow rate" and AI recommendation accuracy

### Data Model
- `trades` table: id (BigSerial), ticker_id (FK), daily_pick_id (nullable FK), side (BUY/SELL), quantity, price (Numeric 12,2), broker_fee (Numeric 12,2 auto-calc), sell_tax (Numeric 12,2, 0 for BUY), total_fee (computed), trade_date, user_notes (Text nullable), created_at
- `lots` table: id (BigSerial), trade_id (FK), ticker_id (FK), buy_price, quantity, remaining_quantity, buy_date, created_at
- Index on lots(ticker_id, remaining_quantity) WHERE remaining_quantity > 0 for fast FIFO lookup
- Migration 020: create both tables with indexes and constraints

### Frontend & API
- New route `/journal` with navbar entry "Nhật ký" (after "Huấn luyện")
- API endpoints: POST /api/trades (create trade), GET /api/trades (list with pagination + filters), GET /api/trades/stats (summary: total trades, realized P&L, open positions count), GET /api/trades/{id} (single trade detail)
- Journal page layout: trade entry form (dialog/sheet) + trades table with columns: date, ticker, side, qty, price, fees, P&L, pick link icon
- Table sortable by date (default desc), filterable by ticker and side
- Color coding: green for profitable, red for loss, neutral for open BUY with no matching SELL yet
- Use react-hook-form + zod for trade form validation (already installed from Phase 43)

### Agent's Discretion
- Lot matching edge cases (partial fills, splits) — keep simple FIFO, no partial lot splitting beyond what's needed
- Stats endpoint aggregation period — default to all-time, add date range filter if straightforward
- Trade edit/delete — support delete only (with lot reversal), no edit to keep FIFO integrity clean

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `UserRiskProfile` model (Phase 43) — contains broker_fee_pct for auto-calculating trade fees
- `DailyPick` model (Phase 43) — FK target for pick linking
- `apiFetch<T>()` in frontend/src/lib/api.ts — standard fetch utility
- React Query hooks pattern in frontend/src/lib/hooks.ts — useQuery + useMutation
- react-hook-form + zod + @hookform/resolvers already in package.json (Phase 43)
- `TRADE_STATUS_CONFIG` in frontend/src/lib/constants.ts — has VN-localized trade status labels (adapt for journal)
- Service class pattern from PickService — session-based, async methods
- Pydantic schemas pattern from backend/app/schemas/picks.py

### Old Portfolio Code (Reference Only)
- Migrations 007 (portfolio_tables) and 013 (paper_trade_tables) created similar trades+lots structure — both dropped in migration 018
- Old schema was validated and worked; Phase 44 can use similar column structure with improvements (daily_pick_id FK, auto-fee calc)

### Integration Points
- `backend/app/api/router.py` — register new trades_router
- `backend/app/models/__init__.py` — export Trade, Lot models
- `frontend/src/components/navbar.tsx` — add "Nhật ký" link
- `frontend/src/lib/api.ts` — add trade fetch/create functions
- `frontend/src/lib/hooks.ts` — add useTrades, useCreateTrade, useTradeStats hooks

</code_context>

<deferred>
## Deferred Ideas

- **Trade edit**: Editing trades after creation would require lot reversal + replay — defer to future if needed
- **CSV import**: Bulk trade import from broker export — defer to future milestone
- **Broker-specific fee schedules**: Different brokers have different fee tiers — keep single broker_fee_pct for now
- **Intraday timestamps**: Only track trade_date (not time) — VN market has fixed sessions, time granularity not needed for journal
- **Dividend income tracking**: Out of scope — Phase 44 is pure buy/sell P&L
</deferred>

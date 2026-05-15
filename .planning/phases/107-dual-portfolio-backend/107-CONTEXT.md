# Phase 107: Dual Portfolio Backend - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Split the single simulator portfolio into 2 independent instances: "ai" (auto-trade from DailyPick signals) and "user" (manual trades). Each has own cash, positions, trades. All API endpoints accept portfolio_type param.

Requirements: DUAL-02, DUAL-03

Success Criteria:
1. Two portfolios in DB ("ai" + "user") with independent starting capital and cash
2. AutoTradeService always targets AI portfolio (no frontend dependency)
3. POST /simulator/trades routes to User portfolio by default, with portfolio_type param
4. GET endpoints accept portfolio_type ("ai"/"user") and return scoped data
5. Per-portfolio reset (independent)

</domain>

<decisions>
## Implementation Decisions

### Database Strategy
- SimulatorPortfolio already has `name` field — create 2 rows: name="ai" and name="user"
- Each starts with 100,000,000 VND (independent capital)
- SimulatorTrade.source already has "ai_auto" vs "manual" — align with portfolio routing
- SimulatorLot belongs to a portfolio via trade → portfolio linkage

### API Changes
- All existing GET endpoints add optional `portfolio_type` query param (default: "user" for backward compat)
- POST /trades: add optional `portfolio_type` param (default: "user")
- POST /reset: add required `portfolio_type` param
- New: GET /simulator/portfolios — list both portfolios with summary

### AutoTradeService Changes
- get_or_create_portfolio() → get_or_create_portfolio(name="ai")
- Remove any frontend toggle dependency — always auto-execute to AI portfolio
- execute_sell_signals() → scope to AI portfolio

### Migration
- Alembic migration: rename existing default portfolio to "ai", create "user" portfolio
- OR: keep existing as "user" (preserving manual trade history), create new "ai" portfolio

### Agent's Discretion
All remaining implementation details at agent's discretion.

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- backend/app/services/simulator_service.py — SimulatorService with portfolio CRUD, trade execution, stats
- backend/app/services/auto_trade_service.py — AutoTradeService executing DailyPick signals
- backend/app/models/simulator_portfolio.py — SimulatorPortfolio model (has name field)
- backend/app/models/simulator_trade.py — SimulatorTrade model (has source field: ai_auto/manual)
- backend/app/models/simulator_lot.py — SimulatorLot model (FIFO lots)
- backend/app/api/simulator.py — API endpoints
- backend/app/schemas/simulator.py — Pydantic schemas

### Patterns
- get_or_create_portfolio() creates single default portfolio
- Trade execution uses FIFO lot matching
- SL/TP check runs in scheduler
- Stats computed from trade history with source filter

</code_context>

<specifics>
## Specific Ideas

- Consider backward compat: existing trades/portfolio data should be preserved
- The "ai" portfolio starts fresh (or empty), "user" inherits existing data

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>

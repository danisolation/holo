---
phase: 44-trade-journal-p-l
plan: "01"
subsystem: backend
tags: [trade-journal, fifo, pnl, api, database]
dependency_graph:
  requires: [daily-picks-engine, user-risk-profile]
  provides: [trade-api, fifo-matching, lot-management]
  affects: [frontend-journal-page, phase-45-analytics]
tech_stack:
  added: []
  patterns: [service-class-with-pure-functions, fifo-lot-matching, lot-match-junction]
key_files:
  created:
    - backend/alembic/versions/020_trade_journal_tables.py
    - backend/app/models/trade.py
    - backend/app/models/lot.py
    - backend/app/models/lot_match.py
    - backend/app/schemas/trades.py
    - backend/app/services/trade_service.py
    - backend/app/api/trades.py
    - backend/tests/test_trade_service.py
  modified:
    - backend/app/models/__init__.py
    - backend/app/api/router.py
decisions:
  - Used lot_matches junction table for SELL→lot tracking, enabling clean delete reversal
  - Proportional buy-side broker fee allocation on SELL (matched_qty/buy_qty × buy_broker_fee)
  - Sort/order column whitelist to mitigate injection (T-44-05)
metrics:
  duration: 5m
  completed: 2026-04-23T09:52:27Z
  tasks_completed: 2
  tasks_total: 2
  test_count: 16
  test_status: all_passing
---

# Phase 44 Plan 01: Trade Journal Backend — Migration, Models, Service, API Summary

**One-liner:** FIFO lot matching with VN market fees (0.15% broker + 0.1% sell tax), 3 DB tables, 5 REST endpoints, 16 passing unit tests

## What Was Built

### Migration 020 — Trade Journal Tables
- `trades` table (14 columns): ticker_id, daily_pick_id (nullable FK to daily_picks), side BUY/SELL, quantity, price, broker_fee, sell_tax, total_fee, gross_pnl, net_pnl, trade_date, user_notes, created_at
- `lots` table (8 columns): trade_id, ticker_id, buy_price, quantity, remaining_quantity, buy_date, created_at
- `lot_matches` junction table (4 columns): sell_trade_id (CASCADE), lot_id, matched_quantity
- Indexes: ix_trades_ticker_date, ix_trades_trade_date, ix_lots_fifo_lookup (partial WHERE remaining_quantity > 0), ix_lot_matches_sell_trade

### ORM Models
- `Trade(Base)` — full trade record with P&L fields (nullable for BUY)
- `Lot(Base)` — buy-side lot with remaining_quantity for FIFO tracking
- `LotMatch(Base)` — junction table for SELL→lot consumption tracking

### Pydantic Schemas
- `TradeCreate` — with broker_fee_override, sell_tax_override, daily_pick_id
- `TradeResponse` — includes ticker_symbol, ticker_name, all P&L fields
- `TradeStatsResponse` — total_trades, realized_gross_pnl, realized_net_pnl, open_positions
- `TradesListResponse` — paginated trades list

### TradeService (Pure Functions + Async Class)
- `calculate_broker_fee(price, qty, pct)` — broker fee with Decimal precision
- `calculate_sell_tax(price, qty)` — VN 0.1% mandatory sell tax
- `fifo_match_lots(lots, sell_qty)` — FIFO algorithm, raises ValueError on insufficient lots
- `calculate_realized_pnl(sell_price, matches, fees)` — returns (gross_pnl, net_pnl)
- `TradeService.create_trade()` — BUY creates lot, SELL triggers FIFO + P&L
- `TradeService.list_trades()` — paginated/filtered/sorted with ticker join
- `TradeService.get_stats()` — aggregated totals
- `TradeService.get_trade()` — single trade by ID
- `TradeService.delete_trade()` — SELL reverses lots, BUY deletes unconsumed lot only

### API Endpoints
- `POST /api/trades` (201) — create trade with auto fees + FIFO
- `GET /api/trades` — paginated list with ticker/side filters, sort by trade_date/side/net_pnl
- `GET /api/trades/stats` — aggregated statistics
- `GET /api/trades/{id}` — single trade
- `DELETE /api/trades/{id}` (204) — delete with lot reversal

### Unit Tests (16 passing)
- 6 fee calculation tests (broker fee + sell tax)
- 6 FIFO matching tests (exact, partial, insufficient, order preservation)
- 4 P&L calculation tests (profit, loss, multi-lot, breakeven)

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat | Mitigation | Status |
|--------|-----------|--------|
| T-44-01 Tampering POST data | Pydantic validates side, quantity, price, fee overrides | ✅ Applied |
| T-44-02 Ticker filter injection | SQLAlchemy ILIKE with bound parameter | ✅ Applied |
| T-44-03 SELL exceeds lots | fifo_match_lots raises ValueError before DB write | ✅ Applied |
| T-44-04 Negative fee override | Pydantic Field(ge=0) on broker_fee_override, sell_tax_override | ✅ Applied |
| T-44-05 Sort/order injection | Whitelist: sort in {trade_date, side, net_pnl}, order in {asc, desc} | ✅ Applied |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 7c45f43 | Migration 020, ORM models, Pydantic schemas |
| TDD-RED | c73b8f5 | Failing tests for FIFO/fee/P&L |
| 2 | bc7f49a | TradeService, API endpoints, 16 passing tests |

## Self-Check: PASSED

All 8 created files verified on disk. All 3 commit hashes found in git log.

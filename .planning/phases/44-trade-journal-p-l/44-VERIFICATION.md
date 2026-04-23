---
phase: 44-trade-journal-p-l
verified: 2026-04-23T17:14:51Z
status: human_needed
score: 3/3 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open /journal page and verify trade entry form renders correctly"
    expected: "Dialog opens with ticker autocomplete, side buttons (MUA/BÁN), price, quantity (multiples of 100), date, notes fields. Fee section shows auto-calculated broker fee and sell tax."
    why_human: "Visual layout, form field rendering, and autocomplete UX cannot be verified programmatically"
  - test: "Create BUY then SELL trades and verify P&L color coding in table"
    expected: "BUY rows show '—' for P&L columns. SELL rows show green (▲ +value) for profit, red (▼ -value) for loss. Stats card shows realized P&L with matching color."
    why_human: "Color rendering and visual formatting require visual verification"
  - test: "Select a ticker that matches a recent daily pick and verify auto-suggest"
    expected: "Checkbox 'Theo gợi ý AI — {symbol} #{rank} ({date})' auto-appears and is pre-checked. Sparkles icon appears in table for linked trades."
    why_human: "Requires recent daily pick data in DB and visual verification of auto-suggest behavior"
  - test: "Test responsive layout on mobile viewport"
    expected: "Stats cards stack vertically, table scrolls horizontally, 'Nhật ký' link accessible in mobile hamburger menu"
    why_human: "Responsive behavior requires visual testing at different viewport sizes"
---

# Phase 44: Trade Journal & P&L Verification Report

**Phase Goal:** User can log real buy/sell trades and see accurate profit/loss calculations with VN market fees and taxes, optionally linking trades to daily AI picks
**Verified:** 2026-04-23T17:14:51Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can enter a buy or sell trade (ticker, price, quantity, date, fees) through a validated form on the journal page | ✓ VERIFIED | `trade-entry-dialog.tsx` (517 lines): zod schema validates ticker, side, price >0, quantity mod 100, date not future. Popover+Command ticker autocomplete. MUA/BÁN toggle buttons. `journal/page.tsx` (143 lines) wires dialog via `entryDialogOpen` state. POST /api/trades endpoint creates trade with Pydantic validation. |
| 2 | The app automatically calculates realized P&L using FIFO matching, including broker fees (0.15% each side) and mandatory sell tax (0.1%) per VN regulations — showing both gross and net P&L | ✓ VERIFIED | `trade_service.py`: `calculate_broker_fee()` = price×qty×pct/100, `calculate_sell_tax()` = price×qty×0.001, `fifo_match_lots()` consumes oldest lots first, `calculate_realized_pnl()` returns (gross_pnl, net_pnl). 16/16 unit tests passing covering fee calc (6), FIFO (6), P&L (4). `trades-table.tsx` renders gross_pnl and net_pnl with ▲/▼ + green/red colors. `trade-stats-cards.tsx` displays realized_net_pnl with color coding. |
| 3 | When logging a trade, user can optionally link it to a specific daily pick to track whether they followed the AI recommendation | ✓ VERIFIED | `trade.py`: `daily_pick_id` nullable FK to `daily_picks`. `trade-entry-dialog.tsx` lines 121-141: `matchingPick` memo searches picks+almost_selected by ticker_symbol, auto-checks "Theo gợi ý AI" checkbox when found. `trades-table.tsx` line 203-208: Sparkles icon for AI-linked trades. Backend `DailyPickResponse` has `id` field (added in plan 03). |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/alembic/versions/020_trade_journal_tables.py` | Migration creating trades, lots, lot_matches tables | ✓ VERIFIED | Creates 3 tables with 4 indexes, FKs to tickers and daily_picks |
| `backend/app/models/trade.py` | Trade ORM model | ✓ VERIFIED | 37 lines, 14 columns including gross_pnl/net_pnl nullable for BUY |
| `backend/app/models/lot.py` | Lot ORM model | ✓ VERIFIED | 31 lines, 8 columns with remaining_quantity for FIFO tracking |
| `backend/app/models/lot_match.py` | LotMatch junction model | ✓ VERIFIED | 22 lines, sell_trade_id FK with CASCADE delete |
| `backend/app/models/__init__.py` | Exports Trade, Lot, LotMatch | ✓ VERIFIED | All three models imported and in __all__ |
| `backend/app/schemas/trades.py` | Pydantic schemas | ✓ VERIFIED | TradeCreate, TradeResponse, TradeStatsResponse, TradesListResponse |
| `backend/app/services/trade_service.py` | FIFO service + pure functions | ✓ VERIFIED | 495 lines. 4 pure functions + TradeService class with 5 async methods |
| `backend/app/api/trades.py` | REST endpoints | ✓ VERIFIED | 5 endpoints: POST, GET list, GET stats, GET by id, DELETE |
| `backend/app/api/router.py` | Router registration | ✓ VERIFIED | `trades_router` included in `api_router` (line 19) |
| `backend/tests/test_trade_service.py` | Unit tests | ✓ VERIFIED | 16 tests, all passing (verified by running pytest) |
| `frontend/src/lib/api.ts` | Types + fetch functions | ✓ VERIFIED | TradeResponse, TradeCreate, TradesListResponse, TradeStatsResponse types. fetchTrades, fetchTradeStats, createTrade, deleteTrade functions. 204 handling fixed (line 176). |
| `frontend/src/lib/hooks.ts` | React Query hooks | ✓ VERIFIED | useTrades, useTradeStats, useCreateTrade, useDeleteTrade. Invalidates ["trades"] on mutations. |
| `frontend/src/components/trade-entry-dialog.tsx` | Trade entry form dialog | ✓ VERIFIED | 517 lines. Zod validation, Popover+Command autocomplete, fee auto-calc, pick link auto-suggest |
| `frontend/src/components/trades-table.tsx` | Sortable data table | ✓ VERIFIED | 253 lines. 10 columns, sortable headers with aria-sort, P&L color coding, pagination, empty/loading states |
| `frontend/src/components/trade-stats-cards.tsx` | Stats summary cards | ✓ VERIFIED | 59 lines. 3-card grid with loading skeletons, P&L color coding |
| `frontend/src/components/trade-filters.tsx` | Filter bar | ✓ VERIFIED | 53 lines. Ticker input + Tất cả/MUA/BÁN toggle with aria-pressed |
| `frontend/src/components/delete-trade-dialog.tsx` | Delete confirmation | ✓ VERIFIED | 60 lines. Destructive confirm, trade details in description, Loader2 spinner |
| `frontend/src/app/journal/page.tsx` | /journal page route | ✓ VERIFIED | 143 lines. Wires all 5 components with filter/sort/pagination state |
| `frontend/src/components/navbar.tsx` | "Nhật ký" nav link | ✓ VERIFIED | NAV_LINKS includes `{ href: "/journal", label: "Nhật ký" }` between "Huấn luyện" and "Sự kiện" |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `trade-entry-dialog.tsx` | `hooks.ts` | `useCreateTrade` mutation | ✓ WIRED | Line 82: `const mutation = useCreateTrade()`, line 174: `await mutation.mutateAsync(payload)` |
| `trade-entry-dialog.tsx` | `hooks.ts` | `useTickers` + `useDailyPicks` | ✓ WIRED | Lines 83-84: both hooks called, tickers used for autocomplete (line 236), dailyPicksData used for pick matching (line 123) |
| `journal/page.tsx` | `trades-table.tsx` | `TradesTable` component | ✓ WIRED | Line 9 import, line 106-121: renders with all props (trades, sort, pagination, callbacks) |
| `journal/page.tsx` | `trade-stats-cards.tsx` | `TradeStatsCards` component | ✓ WIRED | Line 7 import, line 83: self-fetching render |
| `journal/page.tsx` | `trade-entry-dialog.tsx` | `TradeEntryDialog` component | ✓ WIRED | Line 10 import, line 125-128: controlled via `entryDialogOpen` state |
| `hooks.ts` | `api.ts` | Fetch functions | ✓ WIRED | Lines 275-306: useTrades→fetchTrades, useTradeStats→fetchTradeStats, useCreateTrade→createTrade, useDeleteTrade→deleteTrade |
| `api.ts` | `trades.py` API | HTTP endpoints | ✓ WIRED | fetchTrades→GET /trades, fetchTradeStats→GET /trades/stats, createTrade→POST /trades, deleteTrade→DELETE /trades/{id} |
| `trades.py` API | `trade_service.py` | Service methods | ✓ WIRED | Each endpoint instantiates TradeService(session) and calls corresponding method |
| `trade_service.py` | ORM models | SQLAlchemy queries | ✓ WIRED | Uses Trade, Lot, LotMatch, Ticker models for all CRUD and FIFO operations |
| `router.py` | `trades.py` | Router include | ✓ WIRED | Line 10: imports trades_router, line 19: api_router.include_router(trades_router) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `trade-stats-cards.tsx` | `stats` via `useTradeStats()` | GET /api/trades/stats → `get_stats()` → `func.count(Trade)`, `func.sum(Trade.gross_pnl/net_pnl)`, `func.count(distinct(Lot.ticker_id))` | Real DB aggregation queries | ✓ FLOWING |
| `trades-table.tsx` | `trades` prop from `useTrades()` | GET /api/trades → `list_trades()` → `select(Trade).join(Ticker)` with filters/sort/pagination | Real DB query with join | ✓ FLOWING |
| `trade-entry-dialog.tsx` | `tickers` via `useTickers()` + `dailyPicksData` via `useDailyPicks()` | GET /api/tickers + GET /api/picks/today → DB queries | Real DB data for autocomplete and pick matching | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Unit tests pass | `cd backend && python -m pytest tests/test_trade_service.py -v` | 16 passed in 0.61s | ✓ PASS |
| FIFO broker fee 0.15% correct | Test: `calculate_broker_fee(60000, 200, 0.150) == 18000.00` | Assertion passes | ✓ PASS |
| Sell tax 0.1% correct | Test: `calculate_sell_tax(60000, 200) == 12000.00` | Assertion passes | ✓ PASS |
| FIFO insufficient lots rejected | Test: `fifo_match_lots([], 100)` raises ValueError | Assertion passes | ✓ PASS |
| apiFetch handles 204 No Content | api.ts line 176: `if (res.status === 204) return undefined as T` | Fix present in code | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-----------|-------------|--------|----------|
| JRNL-01 | 44-01, 44-02, 44-03 | User nhập lệnh mua/bán thực tế (mã, giá, số lượng, ngày, phí) vào app | ✓ SATISFIED | Trade entry dialog with validated form (zod), ticker autocomplete, BUY/SELL toggle, auto-calculated fees, POST endpoint creates trade |
| JRNL-02 | 44-01, 44-02 | App tự tính P&L theo FIFO, bao gồm phí môi giới (0.15%) và thuế bán (0.1%) theo quy định VN | ✓ SATISFIED | FIFO lot matching, proportional buy-side fee allocation, 16 passing tests for fee/FIFO/P&L calculations. Both gross and net P&L displayed. |
| JRNL-03 | 44-01, 44-03 | Khi log trade, user có thể link đến daily pick tương ứng để theo dõi "có follow AI không?" | ✓ SATISFIED | Optional daily_pick_id FK on trades, auto-suggest checkbox in form, Sparkles icon in table for linked trades |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `journal/page.tsx` | 62-67 | `handleDeleteConfirm` — unguarded `mutateAsync` call (no try/catch) | ⚠️ Warning | Dialog stays open on error without feedback. User can cancel. Not blocking. (WR-03 from code review) |
| `backend/app/api/trades.py` | 40-41 | No bounds validation on `page` (ge=1) and `page_size` (le=100) query params | ⚠️ Warning | page=0 or page=-1 produces negative offset; page_size=1000000 dumps all rows. Low risk (personal app). (WR-02 from code review) |
| `backend/app/services/trade_service.py` | 319 | LIKE wildcard chars (`%`, `_`) not escaped in ticker filter | ℹ️ Info | User entering `%` matches all tickers. SQLAlchemy prevents injection. Very low risk. (IN-01 from code review) |

**Code Review Critical Bug (CR-01): FIXED** — `apiFetch` now handles 204 No Content (api.ts line 176).
**Code Review WR-01: FIXED** — Delete endpoint now returns 404 for not-found trades (trades.py line 94).

### Human Verification Required

### 1. Trade Entry Form Rendering

**Test:** Open /journal page, click "Ghi lệnh" button, verify the trade entry dialog renders correctly
**Expected:** Dialog shows: ticker autocomplete (Popover+Command), side toggle (MUA green / BÁN red), date picker (default today), price and quantity inputs, fee auto-calculation section, optional notes textarea. Quantity rejects non-multiples of 100.
**Why human:** Visual layout verification, autocomplete UX, and form interaction flow require manual testing

### 2. P&L Color Coding in Table

**Test:** Create a BUY trade, then a SELL trade at higher and lower prices. Verify table display.
**Expected:** BUY rows show "—" for P&L columns. Profitable SELL shows green ▲ +value. Losing SELL shows red ▼ -value. Stats card "Lãi/lỗ thực hiện" matches with green/red color.
**Why human:** Color rendering, VND formatting, and visual contrast need visual verification

### 3. AI Pick Link Auto-Suggestion

**Test:** Ensure a daily pick exists, open trade entry, select the matching ticker
**Expected:** Checkbox "Theo gợi ý AI — {symbol} #{rank} ({date})" auto-appears and is pre-checked. After saving, Sparkles icon (✨) appears in the AI column of the trades table.
**Why human:** Requires recent daily pick data in DB, visual verification of auto-suggest behavior and icon display

### 4. Responsive Layout

**Test:** View /journal page at mobile viewport (375px width)
**Expected:** Stats cards stack to single column. Table scrolls horizontally. "Nhật ký" link accessible in hamburger menu. Trade entry dialog fits mobile screen.
**Why human:** Responsive behavior at different viewport breakpoints requires visual testing

### Gaps Summary

No functional gaps found. All 3 success criteria are verified with supporting artifacts, wiring, data flow, and 16 passing unit tests. The code review critical bug (CR-01: apiFetch 204 handling) has been fixed.

Two remaining code review warnings (WR-02: pagination bounds, WR-03: delete error handling) are not blocking — they are quality improvements that don't prevent the core trade journal functionality from working.

4 items require human visual verification: form rendering, P&L color coding, pick auto-suggest, and responsive layout.

---

_Verified: 2026-04-23T17:14:51Z_
_Verifier: the agent (gsd-verifier)_

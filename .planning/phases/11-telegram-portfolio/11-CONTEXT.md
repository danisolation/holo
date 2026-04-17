# Phase 11: Telegram Portfolio — Context

**Gathered:** 2026-04-18
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous smart discuss)

<domain>
## Phase Boundary

**Goal**: User can manage portfolio and receive P&L updates directly through Telegram commands.

**In scope:**
- `/buy <ticker> <qty> <price>` command — record buy trade
- `/sell <ticker> <qty> <price>` command — record sell trade, show realized P&L
- `/portfolio` command — display all holdings with P&L
- `/pnl <ticker>` command — detailed P&L with FIFO lot breakdown
- Daily portfolio P&L notification at 16:00 alongside market summary
- Daily summary highlights owned tickers first with position P&L context

**Out of scope:**
- Portfolio allocation chart via Telegram (too complex for chat)
- Trade edit/delete via Telegram
- Lot-level management commands

</domain>

<decisions>
## Implementation Decisions

### D-11-01: Command Pattern
**Decision:** Use python-telegram-bot command handlers. Each command creates a Trade via PortfolioService (from Phase 8).
**Rationale:** Reuses Phase 8 service layer. Commands are thin wrappers that format results for Telegram.

### D-11-02: Buy/Sell Commands
**Decision:** `/buy VNM 100 85000` records buy trade. `/sell VNM 50 90000` records sell and shows realized P&L. Optional: `/buy VNM 100 85000 150000` (with fee as 4th param).
**Rationale:** Simple positional arguments. Ticker validation against tickers table.

### D-11-03: Daily P&L Notification
**Decision:** Add portfolio P&L to daily_summary_send job. If user has positions, show portfolio value change alongside market summary.
**Rationale:** Per TBOT-04 — sent at 16:00 with existing summary. Natural extension of daily_summary_send job.

### D-11-04: Summary Highlights
**Decision:** In daily summary, sort owned tickers to top of recommendations with position-specific P&L annotation.
**Rationale:** Per TBOT-06 — user cares more about tickers they own.

</decisions>

<code_context>
## Existing Code Insights

- `backend/app/telegram/bot.py` — existing Telegram bot with command handlers
- `backend/app/telegram/formatter.py` — message formatting utilities
- `backend/app/telegram/services.py` — AlertService for daily summary
- Phase 8 will provide PortfolioService — this phase just wires it to Telegram

</code_context>

<deferred>
## Deferred Ideas

- None — all TBOT-01 through TBOT-06 are in scope

</deferred>

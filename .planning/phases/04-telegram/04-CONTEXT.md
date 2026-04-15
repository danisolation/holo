# Phase 4: Telegram Bot — Context & Decisions

**Date:** 2026-04-15
**Phase Goal:** User receives timely trading intelligence and market summaries on their phone via Telegram without opening a browser
**Requirements:** BOT-01, BOT-02, BOT-03

## Grey Area 1: Bot Architecture & Commands

| # | Question | Decision | Status |
|---|----------|----------|--------|
| 1 | Which library and architecture? | `python-telegram-bot` v22.7 (async). Long-polling integrated into FastAPI lifespan. No webhook (personal use, simpler). | 🔒 Locked |
| 2 | Bot commands? | `/start`, `/watch <ticker>`, `/unwatch <ticker>`, `/list`, `/check <ticker>` (on-demand summary), `/alert <ticker> <price>` (set price threshold), `/summary` (force daily summary). | 🔒 Locked |
| 3 | Data storage? | New `user_watchlist` table (chat_id, ticker_id). New `price_alerts` table (chat_id, ticker_id, target_price, direction up/down, is_triggered). Store Telegram chat_id for delivery. | 🔒 Locked |
| 4 | Config? | `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in .env. Single-user, no multi-user auth. | 🔒 Locked |

## Grey Area 2: Alert Logic & Triggers

| # | Question | Decision | Status |
|---|----------|----------|--------|
| 1 | Signal alerts (BOT-01)? | After combined analysis, check watched tickers for signal changes vs previous day. Alert on changes (e.g., neutral→mua). | 🔒 Locked |
| 2 | Price alerts (BOT-02)? | After daily price crawl, check active price alerts vs latest close. If crossed, send alert + mark triggered. | 🔒 Locked |
| 3 | Daily summary (BOT-03)? | Scheduled 16:00 UTC+7 (after full pipeline). Top 5 movers, watchlist signal changes, new recommendations. Vietnamese with emojis. | 🔒 Locked |
| 4 | Message formatting? | Telegram HTML parse mode. Concise, mobile-friendly. Ticker, price, signal, confidence. Vietnamese language. | 🔒 Locked |

## Grey Area 3: Integration with Pipeline

| # | Question | Decision | Status |
|---|----------|----------|--------|
| 1 | Bot startup? | Start in FastAPI lifespan alongside scheduler. `python-telegram-bot` Application with polling in background task. | 🔒 Locked |
| 2 | Alert scheduler jobs? | `daily_signal_alert_check` (after combined), `daily_price_alert_check` (after price crawl), `daily_summary_send` (16:00 cron). | 🔒 Locked |
| 3 | Migration? | Alembic 004: `user_watchlist` + `price_alerts` tables. | 🔒 Locked |
| 4 | Error handling? | Telegram API failures logged, never block data pipeline. Retry 2x for sends. | 🔒 Locked |

## Upstream Context

- Phase 1-3 complete: full pipeline crawl → indicators → tech/fund AI → news → sentiment → combined
- `ai_analyses` table has all analysis types (technical, fundamental, sentiment, combined)
- `AIAnalysisService` with batched Gemini calls
- APScheduler with EVENT_JOB_EXECUTED chaining
- 71 tests passing, async-first architecture
- `python-telegram-bot==22.7` specified in STACK.md (not yet in requirements.txt)

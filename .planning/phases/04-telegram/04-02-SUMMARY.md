---
phase: 04-telegram
plan: "02"
subsystem: telegram-bot
tags: [telegram, bot, commands, formatter, vietnamese]
dependency_graph:
  requires: [04-01]
  provides: [telegram-bot-module, command-handlers, message-formatter]
  affects: [04-03]
tech_stack:
  added: []
  patterns: [singleton-bot, lazy-import, on-conflict-do-nothing, html-parse-mode]
key_files:
  created:
    - backend/app/telegram/__init__.py
    - backend/app/telegram/bot.py
    - backend/app/telegram/handlers.py
    - backend/app/telegram/formatter.py
  modified: []
decisions:
  - "Fresh Bot() instance for send_message — allows sending from scheduler jobs outside Application event loop"
  - "HTML parse_mode everywhere — avoids MarkdownV2 aggressive escaping complexity"
  - "/summary imports AlertService lazily — Plan 04-03 will create it; graceful error until then"
  - "Auto-detect alert direction from current close price — user just provides ticker + price"
metrics:
  duration: 4m
  completed: "2026-04-15"
---

# Phase 4 Plan 02: Telegram Bot Module — Command Handlers & Formatter Summary

**One-liner:** Complete Telegram bot package with TelegramBot lifecycle, 7 Vietnamese command handlers (/start /watch /unwatch /list /check /alert /summary), and HTML MessageFormatter with emoji-rich mobile-friendly formatting.

## What Was Built

### TelegramBot Class (bot.py)
- `TelegramBot` class managing python-telegram-bot v22.7 `Application` lifecycle
- `start()` initializes Application, registers handlers, starts long-polling in background task
- `stop()` gracefully shuts down updater, application stop, and shutdown
- `send_message()` sends HTML-formatted messages with 2x retry and exponential backoff — never raises
- `is_configured` property returns False when token/chat_id empty — bot features skip silently
- `telegram_bot` singleton at module level for shared access across app
- `drop_pending_updates=True` on polling start — ignores queued messages from downtime

### MessageFormatter (formatter.py)
- `welcome()` — Vietnamese welcome with all 7 commands listed
- `watch_added/exists/removed/not_found` — watchlist operation confirmations
- `ticker_not_found` — unknown ticker error
- `watchlist()` — formatted list with signal emoji, price, score per ticker
- `ticker_summary()` — full /check response with 4 analysis dimensions + combined recommendation
- `alert_created/triggered` — price alert confirmations and notifications
- `signal_change` — signal change alert with old→new transition
- `daily_summary` — market summary with top movers, watchlist changes, new recommendations
- `usage_error` — syntax help for invalid command usage
- `_signal_emoji/_recommendation_emoji` — consistent emoji mapping for all signal types

### Command Handlers (handlers.py)
- `register_handlers()` — wires all 7 `CommandHandler`s to Application
- `/start` — welcome message via MessageFormatter
- `/watch <ticker>` — lookup ticker, upsert to user_watchlist with ON CONFLICT DO NOTHING
- `/unwatch <ticker>` — lookup ticker, delete from user_watchlist
- `/list` — query all watched tickers with latest combined analysis + close price
- `/check <ticker>` — full analysis summary: price + change%, 4 analysis types, combined reasoning
- `/alert <ticker> <price>` — auto-detect direction, create PriceAlert record
- `/summary` — lazy import AlertService (Plan 04-03), build + send daily summary

## Verification Results

| Check | Result |
|-------|--------|
| TelegramBot importable, is_configured=False with empty config | ✅ |
| MessageFormatter.welcome() produces HTML with Vietnamese | ✅ |
| All format methods produce correct output | ✅ |
| register_handlers importable | ✅ |
| 71 existing tests pass (no regressions) | ✅ |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Installed python-telegram-bot==22.7**
- **Found during:** Task 1 verification
- **Issue:** Package was in requirements.txt but not installed in venv
- **Fix:** `pip install python-telegram-bot==22.7`
- **Files modified:** none (runtime only)

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | f963336 | feat(04-02): TelegramBot class with lifecycle and send_message utility |
| 2 | 01a9273 | feat(04-02): command handlers (7 commands) and MessageFormatter |

## Self-Check: PASSED

All 4 files exist, both commits verified in git log.

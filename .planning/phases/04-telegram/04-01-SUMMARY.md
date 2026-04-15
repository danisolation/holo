---
phase: 04-telegram
plan: "01"
subsystem: telegram-data-foundation
tags: [models, migration, config, telegram, dependency]
dependency_graph:
  requires: []
  provides: [UserWatchlist-model, PriceAlert-model, telegram-config, migration-004]
  affects: [04-02-PLAN, 04-03-PLAN]
tech_stack:
  added: [python-telegram-bot==22.7]
  patterns: [ORM-models, raw-DDL-migration, partial-index, CHECK-constraint]
key_files:
  created:
    - backend/app/models/user_watchlist.py
    - backend/app/models/price_alert.py
    - backend/alembic/versions/004_telegram_tables.py
  modified:
    - backend/requirements.txt
    - backend/app/config.py
    - backend/.env.example
    - backend/app/models/__init__.py
decisions:
  - "chat_id stored as String(50) not Integer — safe for large Telegram IDs"
  - "direction stored as String(10) with DB CHECK constraint — no PostgreSQL ENUM for 2 values"
  - "Partial index on price_alerts for active (non-triggered) alerts"
  - "telegram_bot_token defaults to empty string — app starts without bot configured"
metrics:
  duration: 2m
  completed: "2026-04-15T08:09:30Z"
  tasks: 2
  files: 7
---

# Phase 4 Plan 1: Data Foundation Summary

**One-liner:** UserWatchlist + PriceAlert ORM models with migration 004, python-telegram-bot==22.7 dependency, and Telegram config settings for bot initialization.

## Tasks Completed

### Task 1: python-telegram-bot dependency, Telegram config settings, .env.example
- **Commit:** `4fe7201`
- **Files:** backend/requirements.txt, backend/app/config.py, backend/.env.example
- Added `python-telegram-bot==22.7` to requirements.txt (pinned per CONTEXT.md D-1.1)
- Added `telegram_bot_token` and `telegram_chat_id` to Settings with empty string defaults
- Documented `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in .env.example with placeholder values

### Task 2: UserWatchlist + PriceAlert models, __init__ exports, Alembic migration 004
- **Commit:** `e130873`
- **Files:** backend/app/models/user_watchlist.py, backend/app/models/price_alert.py, backend/app/models/__init__.py, backend/alembic/versions/004_telegram_tables.py
- Created UserWatchlist model: chat_id (String 50), ticker_id (FK→tickers), UniqueConstraint(chat_id, ticker_id)
- Created PriceAlert model: chat_id, ticker_id, target_price (Numeric 12,2), direction (String 10), is_triggered (Boolean default false), triggered_at
- Both models exported from `app.models.__init__` and added to `__all__`
- Migration 004: raw DDL creating both tables with `idx_user_watchlist_chat_id` index, `idx_price_alerts_active` partial index, and `CHECK (direction IN ('up', 'down'))` constraint

## Verification Results

| Check | Result |
|-------|--------|
| Models importable from app.models | ✅ |
| python-telegram-bot==22.7 in requirements.txt | ✅ |
| telegram_bot_token in config.py | ✅ |
| TELEGRAM_BOT_TOKEN in .env.example | ✅ |
| Migration 004 creates both tables | ✅ |
| 71 existing tests pass (no regressions) | ✅ |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all models are fully wired with complete column definitions, constraints, and indexes.

## Self-Check: PASSED

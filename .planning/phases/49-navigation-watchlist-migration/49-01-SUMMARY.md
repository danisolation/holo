---
phase: 49-navigation-watchlist-migration
plan: 01
subsystem: backend-watchlist
tags: [watchlist, api, migration, ai-enrichment]
dependency_graph:
  requires: []
  provides: [watchlist-api, watchlist-db-schema]
  affects: [frontend-watchlist, navigation]
tech_stack:
  added: []
  patterns: [LEFT JOIN AI enrichment, idempotent POST, bulk migrate endpoint]
key_files:
  created:
    - backend/alembic/versions/025_watchlist_web_migration.py
    - backend/app/schemas/watchlist.py
    - backend/app/api/watchlist.py
  modified:
    - backend/app/models/user_watchlist.py
    - backend/app/api/router.py
decisions:
  - "Symbol stored directly in user_watchlist (no FK to tickers) — simpler schema, watchlist can include symbols not yet in tickers table"
  - "AI enrichment via LEFT JOIN on GET — no denormalization, always fresh signal data"
  - "POST is idempotent — returns existing entry if symbol already in watchlist"
  - "Migrate endpoint for one-time localStorage→DB transition, capped at 50 symbols"
metrics:
  duration: 3m
  completed: 2026-04-24T14:16:33Z
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 2
---

# Phase 49 Plan 01: Backend Watchlist API Summary

Server-backed watchlist with Alembic migration from Telegram-era schema (chat_id + ticker_id) to web single-user schema (symbol), four FastAPI CRUD+migrate endpoints, and AI signal enrichment via latest combined analysis JOIN.

## Tasks Completed

### Task 1: Alembic migration + model update for web watchlist
- **Commit:** `15e7c54`
- Created migration 025: drops old `user_watchlist` table (chat_id + ticker_id + FK), recreates with `symbol` (String(10), unique) column
- Updated `UserWatchlist` model: removed chat_id, ticker_id, ForeignKey; added symbol column with unique constraint
- Downgrade path restores original Telegram-era schema
- **Files:** `025_watchlist_web_migration.py` (created), `user_watchlist.py` (modified)

### Task 2: FastAPI watchlist endpoints with AI signal enrichment
- **Commit:** `eeda139`
- Created Pydantic schemas: `WatchlistItemResponse` (with ai_signal, ai_score, signal_date), `WatchlistAddRequest` (symbol 1-10 chars), `WatchlistMigrateRequest` (symbols list, max 50)
- Created watchlist router with 4 endpoints:
  - **GET /api/watchlist/** — Returns all items enriched with latest combined AI analysis (LEFT JOIN: UserWatchlist.symbol → Ticker → AIAnalysis)
  - **POST /api/watchlist/** — Add symbol (uppercased, idempotent), returns 201
  - **DELETE /api/watchlist/{symbol}** — Remove symbol, returns 204 (or 404)
  - **POST /api/watchlist/migrate** — Bulk add from localStorage, returns enriched list
- Registered `watchlist_router` in main API router (now 59 routes total)
- **Files:** `watchlist.py` schema (created), `watchlist.py` api (created), `router.py` (modified)

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Mitigation |
|-----------|------------|
| T-49-01 | Pydantic `Field(min_length=1, max_length=10)` on symbol + `upper().strip()` in handler |
| T-49-02 | Pydantic `Field(max_length=50)` on symbols list in migrate endpoint |
| T-49-03 | Accepted — single-user app, no auth needed |
| T-49-04 | Accepted — single-user, no multi-tenancy concern |

## Known Stubs

None — all endpoints are fully wired to database and AI analysis models.

## Self-Check: PASSED

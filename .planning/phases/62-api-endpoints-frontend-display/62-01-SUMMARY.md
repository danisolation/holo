---
phase: 62-api-endpoints-frontend-display
plan: 01
subsystem: backend-api
tags: [api, fastapi, rumor-intelligence, pydantic]
dependency_graph:
  requires: [rumor-model, rumor-score-model, fireant-crawler, rumor-scoring-service]
  provides: [rumor-api-endpoints]
  affects: [frontend-rumor-display, watchlist-badges]
tech_stack:
  added: []
  patterns: [async-session, ticker-resolution-404, optional-response-fields]
key_files:
  created:
    - backend/app/api/rumors.py
  modified:
    - backend/app/schemas/rumor.py
    - backend/app/api/router.py
decisions:
  - Inline _get_ticker_by_symbol helper (avoid cross-import from analysis.py)
  - All score fields Optional in RumorScoreResponse for graceful empty-data handling
  - watchlist/summary route defined before /{symbol} to prevent FastAPI path conflict
  - N+1 accepted for watchlist summary (max ~30 tickers) — single-user app
metrics:
  duration: ~5min
  completed: 2026-05-05
---

# Phase 62 Plan 01: Rumor API Endpoints Summary

**One-liner:** FastAPI router with GET /rumors/{symbol} (score+posts) and GET /rumors/watchlist/summary (badge aggregates) using async SQLAlchemy queries

## What Was Built

### Task 1: Pydantic Response Schemas
- **RumorPostResponse**: content, author_name, is_authentic, total_likes, total_replies, posted_at
- **RumorScoreResponse**: symbol + optional score fields + posts list (graceful None when no data)
- **WatchlistRumorSummary**: symbol, rumor_count, avg_credibility, avg_impact, dominant_direction
- Commit: `898eba2`

### Task 2: Rumors Router + Registration
- Created `backend/app/api/rumors.py` with 2 endpoints:
  - `GET /rumors/watchlist/summary` — 7-day aggregated badge data for all watchlist tickers
  - `GET /rumors/{symbol}` — latest RumorScore + 20 recent Rumor posts
- Registered `rumors_router` in `backend/app/api/router.py`
- Route ordering ensures `/watchlist/summary` matches before `/{symbol}`
- Commit: `71023a7`

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 898eba2 | Add Pydantic response schemas (RumorPostResponse, RumorScoreResponse, WatchlistRumorSummary) |
| 2 | 71023a7 | Create rumors API router with 2 GET endpoints, register in main router |

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

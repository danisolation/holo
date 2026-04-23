---
phase: quick
plan: 260423-epd
subsystem: backend, frontend
tags: [cleanup, news, ui, config]
dependency_graph:
  requires: []
  provides: [news-endpoint, trading-signal-label, ticker-news-section]
  affects: [ticker-detail-page, analysis-card]
tech_stack:
  added: []
  patterns: [pydantic-response-schema, react-query-hook, card-component]
key_files:
  created:
    - frontend/src/components/news-list.tsx
  modified:
    - backend/app/config.py
    - backend/app/scheduler/jobs.py
    - backend/app/schemas/analysis.py
    - backend/app/api/analysis.py
    - frontend/src/components/analysis-card.tsx
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/ticker/[symbol]/page.tsx
key_decisions:
  - Used toLocaleDateString vi-VN for news dates (simple, no extra dependency) instead of date-fns formatDistanceToNow
metrics:
  duration: ~3min
  completed: 2026-04-23
---

# Quick Task 260423-epd: Tier 1 Upgrades Summary

**One-liner:** Remove stale Telegram config, clean scheduler docstring, add trading_signal label, and add CafeF news section to ticker detail page with new backend endpoint.

## Changes Made

### Task 1: Backend cleanup + news endpoint
- **Config cleanup:** Removed `telegram_bot_token` and `telegram_chat_id` from `Settings` class; updated `holo_test_mode` comment to remove "telegram" reference
- **Scheduler docstring:** Changed `D-10: Complete failure raises → EVENT_JOB_ERROR → Telegram alert` to `→ logged as CRITICAL`
- **News schema:** Added `NewsArticleResponse` Pydantic model (title, url, published_at)
- **News endpoint:** Added `GET /analysis/{symbol}/news` — returns latest news articles from `news_articles` table, joined via `_get_ticker_by_symbol` helper, ordered by `published_at DESC`, max 50
- **Commit:** 6886ed8

### Task 2: Frontend — trading signal label + news component + ticker page
- **Analysis card:** Added `Target` icon import, added `trading_signal: { label: "Kế hoạch giao dịch", icon: <Target /> }` to `TYPE_LABELS`
- **API types:** Added `NewsArticleResponse` interface and `fetchTickerNews` function
- **Hook:** Added `useTickerNews` with 10-minute staleTime
- **NewsList component:** Card with newspaper icon heading "Tin tức gần đây", each article is a clickable external link with Vietnamese-formatted date
- **Ticker page:** Added `useTickerNews` hook call, "Tin tức CafeF" section after analysis cards grid with Skeleton loading state
- **Commit:** 3c6a4c5

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

- ✅ Backend: `telegram_bot_token` and `telegram_chat_id` not in Settings model_fields
- ✅ Backend: `NewsArticleResponse` schema importable
- ✅ Backend: `/analysis/{symbol}/news` route registered
- ✅ Backend: 270 tests pass (pytest --tb=short -q)
- ✅ Frontend: TypeScript compiles with no errors (tsc --noEmit)

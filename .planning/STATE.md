---
gsd_state_version: 1.0
milestone: v12.0
milestone_name: Rumor Intelligence
status: defining
stopped_at: Milestone v11.0 shipped
last_updated: "2026-05-05T14:18:00.000Z"
last_activity: 2026-05-05
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-05-05)

**Core value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua web dashboard.
**Current focus:** Defining requirements for v12.0 Rumor Intelligence

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-05-05 — Milestone v12.0 started

## Shipped Milestones

| Version | Name | Phases | Plans | Date |
|---------|------|--------|-------|------|
| v1.0 | Holo Stock Intelligence Platform | 5 | 15 | 2026-04-15 |
| v1.1 | Reliability & Portfolio | 6 | 20 | 2026-04-17 |
| v2.0 | Full Coverage & Real-Time | 5 | 18 | 2026-04-17 |
| v3.0 | Smart Trading Signals | 5 | 10 | 2026-04-20 |
| v4.0 | Paper Trading & Signal Verification | 5 | 10 | 2025-07-20 |
| v5.0 | E2E Testing & Quality Assurance | 5 | 9 | 2025-07-21 |
| v6.0 | AI Backtesting Engine | 3 | 7 | 2026-04-22 |
| v7.0 | Consolidation & Quality Upgrade | 8 | 9 | 2025-07-22 |
| v8.0 | AI Trading Coach | 5 | 14 | 2026-04-23 |
| v9.0 | UX Rework & Simplification | 4 | 8 | 2026-05-04 |
| v10.0 | Watchlist-Centric & Stock Discovery | 4 | 7 | 2026-05-05 |

## Accumulated Context

### Decisions

All v1.0–v9.0 decisions archived in PROJECT.md Key Decisions table.

- [Phase 52]: Pure scoring functions at module level for testability; 3 batch queries for N+1 avoidance; PostgreSQL ON CONFLICT upsert for idempotency
- [Phase 52]: Discovery scoring inserted between indicators and AI in scheduler chain — replaces old direct link

### Research Context (v10.0)

- Discovery engine uses PURE indicator scoring (no Gemini) — RSI, MACD, ADX, volume, P/E, ROE
- Existing `ticker_filter` param in AIAnalysisService enables watchlist gating — no new API needed
- Schema changes needed first: `discovery_results` table + `sector_group` column on UserWatchlist
- Scheduler chain modification is highest risk — job ID string matching means typo kills pipeline silently
- DB pool (5+3) can't handle parallel heavy jobs — discovery MUST run sequentially after indicators
- Empty watchlist must skip gracefully (log + return normally) — not crash the chain
- Heatmap rework is frontend composition (existing APIs) — no new backend endpoint needed
- Discovery retention: 14 days (5,600 rows max)

### Research Context (v11.0)

- Market overview ~3 min load = TWO causes: Render cold start + ROW_NUMBER full table scan (200K+ rows)
- External pinger (UptimeRobot/cron-job.org) is zero-code — NOT in-process APScheduler (dies when Render sleeps)
- Ping root `/` only (zero DB access) — budget 750 hrs/month, consider market-hours-only pinging
- Search bug: `ticker-search.tsx:54` `.slice(0,50)` + API `limit=100` — 2-line fix
- Morning AI chain: shortened pipeline (price → indicators → AI → signals), skip discovery/news/sentiment
- Gemini budget: 15 RPM, morning run for ~15-20 watchlist tickers = ~2-4 batches = safe
- Keep-alive MUST be confirmed working before morning AI cron deploys (dependency)
- UX: simple empty states + VN30 preset + nav tooltips — NOT wizard/tour (single-user app)
- cachetools TTLCache for in-memory API caching — no Redis needed
- Query fix: `WHERE date >= CURRENT_DATE - 7` reduces 200K→2,800 rows

### Pending Todos

None yet.

### Blockers/Concerns

None.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260423-d83 | Remove entire backtest feature (backend + frontend + DB tables + tests) | 2026-04-23 | 194cad0 | [260423-d83-remove-entire-backtest-feature-backend-f](./quick/260423-d83-remove-entire-backtest-feature-backend-f/) |
| 260423-dqa | Remove portfolio, paper trading, and telegram bot (backend + frontend + DB tables + tests) | 2026-04-23 | c6a0c7a | [260423-dqa-remove-portfolio-paper-trading-and-teleg](./quick/260423-dqa-remove-portfolio-paper-trading-and-teleg/) |
| 260423-epd | Tier 1 upgrades: clean stale config, add news on ticker page, add trading signal label | 2026-04-23 | 3c6a4c5 | [260423-epd-tier-1-upgrades-clean-stale-config-add-d](./quick/260423-epd-tier-1-upgrades-clean-stale-config-add-d/) |
| 260423-f6p | Tier 2 Batch A: staleTime tuning, GZip, N+1 fix, error states, pagination | 2026-04-23 | 16cd356 | [260423-f6p-tier-2-batch-a-staletime-tuning-gzip-ana](./quick/260423-f6p-tier-2-batch-a-staletime-tuning-gzip-ana/) |
| 260423-feq | Tier 2 Batch B: market-overview sort/top, CafeF retry, realtime diff, home errors | 2026-04-23 | fee5e52 | [260423-feq-tier-2-batch-b-market-overview-optimizat](./quick/260423-feq-tier-2-batch-b-market-overview-optimizat/) |
| 260423-fuy | Tier 2 Batch C: news skeleton, tickers pagination, crawler types, exchange-aware realtime | 2026-04-23 | 09c92a8 | [260423-fuy-tier-2-batch-c-news-skeleton-home-page-e](./quick/260423-fuy-tier-2-batch-c-news-skeleton-home-page-e/) |
| 260424-ren | Add Render.com deployment config (render.yaml, CORS_ORIGINS, PORT binding) | 2026-04-24 | 7550c17 | — |
| 260424-vcl | Add Vercel deployment config for frontend (vercel.json) | 2026-04-24 | 398ed0c | — |

## Session Continuity

Last session: 2026-05-05
Stopped at: Milestone v10.0 shipped
Resume file: None

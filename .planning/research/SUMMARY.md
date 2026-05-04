# Project Research Summary

**Project:** Holo v10.0 — Watchlist-Centric & Stock Discovery
**Domain:** Single-user Vietnamese stock analysis platform restructuring
**Researched:** 2025-07-23
**Confidence:** HIGH

## Executive Summary

Holo v10.0 is an **architectural restructuring**, not a greenfield build. The core challenge is splitting the existing 400-ticker analysis firehose into two distinct pipelines: a lightweight discovery scan (pure computation across all ~400 tickers) and a deep AI analysis pipeline gated to only the user's ~15-30 watchlist tickers. This reduces Gemini API usage by ~70%, cuts pipeline time from ~25 minutes to ~8 minutes, and introduces a new Discovery feature that recommends tickers worth adding to the watchlist. No new dependencies are required — every technology in the stack is already in use.

The recommended approach is a **sequential chain modification** of the existing APScheduler pipeline. After daily indicators compute for all tickers, a new discovery scan scores tickers using pure technical computation (RSI zones, MACD crossovers, volume spikes, breakout detection, ADX trend strength). Then the existing AI analysis chain runs but is gated to watchlist tickers only via the already-supported `ticker_filter` parameter in `AIAnalysisService.analyze_all_tickers()`. The frontend gains a new `/discovery` page and a heatmap rework that groups by user-assigned sector groups instead of ticker metadata.

The key risks are: (1) breaking the scheduler chain during rewiring — exact job ID string matching means a typo silently kills the entire pipeline, (2) empty watchlists crashing or bypassing the AI pipeline, and (3) DB pool exhaustion if discovery and AI analysis ever run concurrently (pool_size=5, max_overflow=3). All three are mitigated by sequential execution, guard clauses with graceful skipping, and end-to-end chain testing after modification.

## Key Findings

### Recommended Stack

**Zero new dependencies.** The existing FastAPI + PostgreSQL + SQLAlchemy + APScheduler + Gemini backend and Next.js 16 + TypeScript + Tailwind + shadcn/ui + TanStack frontend handle all v10.0 requirements. The only infrastructure action is running one Alembic migration for a new `discovery_results` table and a `sector_group` column on `user_watchlist`.

**Core technologies (all existing):**
- **FastAPI + SQLAlchemy 2.x**: Adding 1 new router, 1 new model, modified queries — all within existing patterns
- **APScheduler 3.11**: Adding 1 new job to the existing sequential chain — the riskiest modification
- **Google Gemini (gemini-2.5-flash-lite)**: Usage *decreases* — from ~250 calls/day to ~80 calls/day thanks to watchlist gating
- **Next.js 16 + TanStack Query/Table**: Adding 1 new route, 2 new components, frontend data composition for heatmap
- **Pure computation (ta library)**: Discovery scoring reads existing indicator data — no AI API calls needed

### Expected Features

**Must have (table stakes):**
- AI analysis runs only on watchlist tickers — core promise of v10.0
- Daily picks come from watchlist only — downstream of AI gating
- Heatmap shows only watchlist tickers grouped by user sector — visual centerpiece
- Sector grouping on watchlist with inline editing — enables heatmap groups
- Discovery page with scored recommendations — the new feature
- One-click add from discovery to watchlist — completes the discovery-to-watchlist loop

**Should have (differentiators):**
- Technical score breakdown (RSI, MACD, volume, breakout, trend) — builds trust in recommendations
- Auto-suggest sector group from `Ticker.sector` vnstock metadata — reduces manual work
- Discovery filters by signal type and sector — makes discovery manageable
- "New since last check" badge — drives engagement with discovery page

**Defer (v2+):**
- Discovery score trend (needs 2+ days of data accumulation)
- Historical discovery comparison UI
- Custom scoring weights (change in code if needed)
- Watchlist alerts/notifications (no notification channel exists since v7.0)

### Architecture Approach

The architecture splits into two pipelines sharing the same scheduler chain: discovery scan (all tickers, pure computation, <5 seconds) → AI pipeline (watchlist tickers only, Gemini-powered, ~8 minutes). A new `WatchlistService` provides a single source of truth for "which tickers to analyze" used by all gated jobs. Discovery scoring follows the existing `pick_service.py` pattern of pure functions. The heatmap rework uses frontend composition of existing APIs (watchlist + market-overview) rather than a new backend endpoint.

**Major components:**
1. **DiscoveryScoringEngine** — Pure functions scoring tickers on 5 technical dimensions (RSI, MACD, volume, breakout, ADX)
2. **DiscoveryService** — Orchestrates scoring for all tickers, persists to `discovery_results` table with UPSERT
3. **WatchlistService** — Provides `get_watchlist_ticker_map()` used by all gated AI pipeline jobs
4. **Modified scheduler chain** — Fork after indicators: discovery → AI analysis (sequential, not parallel)
5. **Discovery API + page** — New router + frontend route showing recommendations with add-to-watchlist flow
6. **Heatmap rework** — Frontend composition filtering market data to watchlist, grouping by `sector_group`

### Critical Pitfalls

1. **Empty watchlist crashes AI pipeline** — Every gated job must check `if not ticker_filter: log warning + return normally`. Return normally so the chain continues; downstream jobs like pick_outcome_check must still run on existing data.
2. **Chain fork breaks job execution tracking** — The `_on_job_executed` listener uses exact string matching on job IDs. Inserting `daily_discovery_scan` requires updating both outgoing (indicator→discovery) and incoming (discovery→AI) chain links with exact ID strings. A single typo silently kills the pipeline.
3. **DB pool exhaustion from parallel execution** — Pool is only 5+3=8 connections. Discovery and AI analysis must NEVER run concurrently. Sequential chain is mandatory, not optional.
4. **Stale heatmap after watchlist mutation** — React Query caches must be invalidated for both `watchlist` and `market-overview` queries when watchlist changes. Extend existing `onSuccess` mutation handlers.
5. **Discovery ranks illiquid penny stocks as "strong buy"** — Filter out tickers with avg daily volume < 100,000 shares. Include volume and ADX as scoring factors. Show score breakdown so user understands rankings.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Database Foundation & Discovery Engine

**Rationale:** Everything depends on the Alembic migration (new table + new column). Discovery scoring is pure computation with zero external dependencies — the safest code to write and test first. Building the backend pipeline before any frontend ensures data exists when the UI is built.
**Delivers:** `discovery_results` table populated daily with scored tickers; `sector_group` column available on watchlist
**Addresses:** Discovery scoring engine, discovery service, discovery scheduler job, database migration
**Avoids:** Pitfall 2 (chain fork) — insert discovery job into chain here and validate the full chain runs end-to-end
**Key files:** `models/discovery_result.py`, `services/discovery/scoring.py`, `services/discovery/discovery_service.py`, `scheduler/jobs.py`, `scheduler/manager.py`, Alembic migration

### Phase 2: Watchlist-Gated AI Pipeline

**Rationale:** This is the highest-risk and highest-value change. It modifies the core scheduler chain that runs every market day. Must be done after Phase 1 because the chain already has the discovery fork point. Reduces Gemini API usage by ~70% and pipeline time by ~3x.
**Delivers:** AI analysis, news crawl, sentiment, combined analysis, trading signals, and picks all run on watchlist tickers only
**Addresses:** Watchlist-gated AI analysis (table stake), picks from watchlist only (table stake), WatchlistService helper
**Avoids:** Pitfall 1 (empty watchlist) — implement guard clauses in every gated job; Pitfall 3 (DB pool) — verify sequential execution
**Key files:** `services/watchlist_service.py`, `scheduler/jobs.py` (all gated jobs), `scheduler/manager.py` (chain rewire)

### Phase 3: Sector Grouping & Heatmap Rework

**Rationale:** Depends on `sector_group` column from Phase 1. The heatmap rework is the most visible user-facing change on the home page — it transforms the daily experience from "400-ticker noise" to "my curated portfolio view." Lower risk than Phase 2 since it's mostly frontend composition.
**Delivers:** Inline sector group editing on watchlist table, heatmap filtered to watchlist and grouped by user sectors, auto-suggest sector from vnstock metadata
**Addresses:** Sector grouping (table stake), heatmap watchlist-only mode (table stake)
**Avoids:** Pitfall 4 (stale heatmap) — implement cache invalidation; Pitfall 5 (sector naming) — combobox with existing values + free text; Pitfall 10 (inconsistent naming) — case-normalize on save
**Key files:** `api/watchlist.py`, `schemas/watchlist.py`, `components/watchlist-table.tsx`, `components/heatmap.tsx`, `app/page.tsx`

### Phase 4: Discovery Frontend & Integration

**Rationale:** Requires Phase 1 (discovery data exists) and Phase 2 (watchlist gating works, so add-to-watchlist triggers AI analysis on next pipeline run). This phase makes discovery results visible and actionable. Lower priority than Phases 1-3 because discovery data accumulates automatically regardless of whether the UI exists.
**Delivers:** Discovery page with scored ticker cards, add-to-watchlist flow with sector group assignment, navigation link
**Addresses:** Discovery page (table stake), one-click add-to-watchlist (table stake), discovery score breakdown (differentiator), auto-suggest sector group (differentiator)
**Avoids:** Pitfall 6 (unintuitive rankings) — display score breakdown prominently; Pitfall 7 (missing AI for new tickers) — show "AI sẽ phân tích mã này vào phiên tối" message + link to analyze-now button
**Key files:** `api/discovery.py`, `schemas/discovery.py`, `app/discovery/page.tsx`, `components/discovery-card.tsx`, `components/navbar.tsx`, `lib/api.ts`, `lib/hooks.ts`

### Phase Ordering Rationale

- **Dependency-driven:** Migration must come first → discovery engine depends on migration → AI gating depends on chain having discovery fork → heatmap depends on sector_group column → discovery page depends on discovery data existing
- **Risk-ordered:** Phase 2 (scheduler chain rewire) is the highest-risk change and should be tackled early when there's maximum room for debugging. Phases 3-4 are lower-risk frontend work.
- **Value-ordered:** Phase 2 delivers the biggest operational improvement (70% fewer API calls, 3x faster pipeline). Phase 3 delivers the biggest UX improvement (personalized home page). Phase 4 is the new feature.
- **Independent frontends:** Phases 3 and 4 are frontend-heavy and could theoretically be built in parallel by different developers, but for a single-developer workflow, sequential is cleaner.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Discovery Engine):** Scoring weights and thresholds for RSI/MACD/volume/breakout/ADX need tuning. The initial pure-function implementation should use conservative defaults, but expect iteration after seeing real results on Vietnamese market data. The `compute_discovery_score` breakdown needs testing against known good/bad tickers.
- **Phase 2 (Pipeline Gating):** Exact job ID strings and chain listener behavior need verification against current `manager.py` state at implementation time. The existing `ticker_filter` parameter behavior with edge cases (empty dict vs None vs partial match) should be tested before building on it.

Phases with standard patterns (skip research-phase):
- **Phase 3 (Sector Grouping & Heatmap):** Standard CRUD + inline editing + frontend composition. All UI components (combobox, table column, heatmap grouping) are well-documented patterns in shadcn/ui and TanStack Table. Existing `heatmap.tsx` grouping logic (lines 41-51) provides a direct template.
- **Phase 4 (Discovery Frontend):** Standard new page + API + card components. Mirrors existing patterns in the codebase (watchlist page, picks page). React Query hooks follow established patterns in `hooks.ts`.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | Zero new dependencies; all tech verified from existing `requirements.txt` and `package.json` |
| Features | **HIGH** | Feature scope derived from direct codebase analysis of what's possible with existing infrastructure |
| Architecture | **HIGH** | All integration points verified through direct code analysis; `ticker_filter` parameter confirmed at line 87 of `ai_analysis_service.py` |
| Pitfalls | **HIGH** | Pitfalls derived from concrete code analysis (exact pool sizes, exact job ID matching logic, exact chain behavior) |

**Overall confidence:** HIGH — This is an internal restructuring of a well-understood codebase, not an exploration of unknown technologies. Every recommendation is grounded in specific files and line numbers.

### Gaps to Address

- **Discovery scoring weights:** Initial weights (equal weighting across 5 dimensions) are a guess. Need to validate against real market data after Phase 1 deployment. Consider logging score distributions for the first week to tune thresholds.
- **vnstock sector name mapping:** The exact mapping from vnstock ICB sector names to short Vietnamese labels needs to be built during Phase 3. A quick audit of `Ticker.sector` distinct values will inform the mapping dict size.
- **Volume threshold for discovery filtering:** The 100,000 shares/day minimum for discovery results is a rough heuristic. May need adjustment for HOSE market liquidity norms.
- **Discovery retention policy:** 7 vs 14 days of `discovery_results` retention — 7 is suggested but depends on whether score trend feature (deferred) is wanted soon. Start with 14 days, it's only 5,600 rows max.
- **Heatmap empty state:** What to show when watchlist is empty? Probably a CTA to visit the Discovery page. Design decision for Phase 3.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis of `scheduler/manager.py` — chain logic, job ID matching (lines 58-162)
- Direct codebase analysis of `ai_analysis_service.py` — `ticker_filter` parameter support (line 87-98)
- Direct codebase analysis of `config.py` — Gemini settings (batch_size=8, delay=4s), DB pool (pool_size=5, max_overflow=3)
- Direct codebase analysis of `models/user_watchlist.py`, `models/ticker.py` — current schemas
- Direct codebase analysis of `components/heatmap.tsx` — grouping logic (lines 41-51)
- Direct codebase analysis of `services/pick_service.py` — pure function scoring pattern
- Direct codebase analysis of `api/watchlist.py` — enrichment query pattern
- Direct codebase analysis of `hooks.ts` — React Query mutation/invalidation patterns

### Secondary (MEDIUM confidence)
- v10.0 milestone description in PROJECT.md — feature scope definition
- Gemini API rate limits (15 RPM) — operational constraint informing discovery architecture

---
*Research completed: 2025-07-23*
*Ready for roadmap: yes*

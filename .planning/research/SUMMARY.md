# Project Research Summary

**Project:** Holo v9.0 — UX Rework & Simplification
**Domain:** Personal stock trading intelligence platform (single-user, Vietnam HOSE market)
**Researched:** 2025-07-21
**Confidence:** HIGH

## Executive Summary

Holo is a single-user stock intelligence tool with strong backend capabilities (Gemini AI analysis, daily picks, trade journaling, behavior tracking) but a fragmented frontend that makes the daily workflow painful. The app has 7 navigation items, 3 overlapping market-overview pages, a Coach page that dumps 12+ unrelated sections on one screen, and zero connection between seeing an AI recommendation and recording a trade. The v9.0 rework is fundamentally a **reorganization and simplification** — not a feature-building exercise. The existing stack (FastAPI + Next.js + PostgreSQL + Gemini) is validated and requires zero new required dependencies.

The recommended approach is a strict **cleanup-first, restructure-second** strategy. Phase 1 removes dead features (corporate events, HNX/UPCOM exchanges) to reduce surface area by ~1,050 LOC and simplify the scheduler pipeline from 3 parallel exchange crawls to 1 linear HOSE chain. Phase 2 migrates the watchlist from fragile localStorage to PostgreSQL and restructures navigation from 7 items to 5. Phase 3 rewires the Coach page into a tab-based interactive layout where pick cards have "Record Trade" buttons, and expands AI analysis output from terse 2-3 sentence paragraphs to structured multi-section analysis. This order respects the critical dependency: the scheduler chain trigger currently fires from the UPCOM crawl job, so removing HNX/UPCOM without first rewiring the chain causes the **entire daily pipeline to silently stop** — the single most dangerous pitfall identified.

The primary risks are: (1) silent scheduler pipeline failure from incorrect chain rewiring, (2) watchlist data loss during localStorage-to-DB migration if the migration bridge isn't deployed as a two-step process, and (3) AI structured output truncation if prompt length increases aren't paired with batch size reductions. All three have clear, well-documented prevention strategies derived from direct codebase analysis.

## Key Findings

### Recommended Stack

The existing stack is mature and complete. No required additions. The research identified 5 items to **remove** (dead `python-telegram-bot` dependency, corporate events full stack, exchange filter/store, old `user_watchlist` table, VNDirect config) and 3 **optional** additions only if UX demands them.

**Core technologies (no changes):**
- **FastAPI + SQLAlchemy 2.0 + asyncpg**: Backend API and ORM — battle-tested, handles all new endpoints needed
- **Next.js 16 + shadcn/ui + Tailwind 4**: Frontend — existing animation/transition utilities cover all UX needs
- **@tanstack/react-query**: Already in use for data fetching — will replace zustand for watchlist state
- **google-genai (Gemini)**: AI analysis — longer output achieved via prompt/config changes, no SDK changes
- **APScheduler**: Scheduler — chain simplification from 3 exchanges to 1, no version change needed

**Optional additions (MEDIUM confidence — add only if needed):**
- `sonner` (~3KB): Toast notifications for trade recording feedback
- `react-markdown` + `remark-gfm`: Only if AI prompts are redesigned to output markdown

**Removals (HIGH confidence — confirmed via code audit):**
- `python-telegram-bot` (dead since v7.0, still in requirements.txt)
- Corporate events: 3 backend files, 3 frontend files, 1 DB table, 1 scheduler job
- Exchange filter/badge/store: ~150 LOC across 6 files
- Old `user_watchlist` table (Telegram-era, replaced by new `watchlist` table)

### Expected Features

**Must have (table stakes — v9.0 launch blockers):**
- **T8+T9: Remove corporate events + HNX/UPCOM** — cleanup before any rework begins
- **T5: Simplified navigation (7→5 items)** — merge overlapping pages, clear daily workflow
- **T1: Action-first home page** — daily picks, open positions, market pulse; not a heatmap landing
- **T2: "Record trade" button on pick cards** — 4-step manual flow → 1 click with pre-fill
- **T6: Watchlist to server-side DB** — replace fragile localStorage with PostgreSQL
- **T4: Structured AI analysis output** — sections (situation, levels, risks, action plan) instead of 1 paragraph

**Should have (high value, immediately after core rework):**
- **T3: Post-trade next steps** — SL/TP confirmation, monitoring link after recording a trade
- **T7: Open position monitoring** — live P&L on home page
- **D4: Watchlist with AI signals** — show latest score/signal per watchlist entry
- **D5: Smart trade pre-fill** — pre-fill from any context (ticker page, watchlist, pick card)

**Defer (v2+):**
- **D1: Daily briefing card** — AI morning summary (burns Gemini quota, 15 RPM limit)
- **D2: Trade-to-review loop** — post-SELL reflection prompt feeding weekly review
- **D3: Contextual coaching on ticker page** — show position/habit info in context

**Anti-features (do NOT build):**
- Separate Coach page (distribute components to home/journal instead)
- Customizable dashboard widgets (single user, design the right default)
- Chat-with-AI interface (15 RPM quota, structured analysis is more reliable)
- Gamification (single user, intrinsic motivation > streaks/badges)

### Architecture Approach

The architecture is a straightforward FastAPI monolith + Next.js App Router with APScheduler orchestrating a daily pipeline: price crawl → indicators → AI analysis (5 types) → picks → outcomes. The v9.0 changes are surgical: remove 2 isolated vertical slices (corporate events, HNX/UPCOM), add 1 new simple CRUD endpoint (watchlist), restructure the frontend page hierarchy, and tune AI prompts. No new services, no new infrastructure, no new architectural patterns needed.

**Major components affected:**
1. **Scheduler pipeline** — simplify from 3-exchange parallel chain to 1-exchange linear chain; remove corporate events parallel branch; rewire trigger from UPCOM→HOSE
2. **Frontend page structure** — merge Coach page sections into Home (picks, positions, goals) and Journal (history, behavior); eliminate overlapping Dashboard; reduce nav to 5 items
3. **Watchlist subsystem** — new `watchlist` DB table + REST API + React Query hooks replacing zustand/localStorage; one-time client-side migration bridge
4. **AI analysis prompts** — expand reasoning limits (2-3→4-6 sentences), increase token budgets, reduce batch sizes proportionally; no schema changes (TEXT column is unlimited)

### Critical Pitfalls

1. **Silent scheduler pipeline failure (#1)** — The entire daily pipeline chains from `daily_price_crawl_upcom` completion. Removing UPCOM crawl without changing the trigger to `daily_price_crawl_hose` means no indicators, no AI analysis, no picks, no trading signals. **Silent failure** — app looks fine but shows stale data forever. **Prevention:** Rewire `_on_job_executed` trigger in the SAME code change that removes UPCOM crawl jobs.

2. **Watchlist data loss during migration (#3)** — localStorage watchlist can't be read server-side. The migration MUST happen in the browser on first visit. If the new frontend deploys before the backend API exists, or if zustand persist middleware is removed before the migration bridge runs, data is permanently lost. **Prevention:** Two-step deploy — backend API first, then frontend migration bridge. Keep localStorage as read-only fallback for 1 release cycle.

3. **AI structured output truncation (#5)** — Doubling reasoning length with batch size 25 causes Gemini to hit output token limits, silently truncating the last 3-5 tickers per batch. Coverage drops ~14%. **Prevention:** Reduce `gemini_batch_size` from 25→15 when increasing prompt lengths. Test ONE batch before running full pipeline.

4. **Stale exchange filter in localStorage (#7)** — Removing `ExchangeFilter` component while `holo-exchange-filter` localStorage key still holds `"HNX"` causes empty heatmap/watchlist on first load. **Prevention:** Clear localStorage key on app mount before removing the component.

5. **E2E test and bookmark breakage (#6)** — 119 Playwright tests reference current routes. Navigation restructure must include Next.js redirects for removed routes and test updates. **Prevention:** Add redirects in `next.config.ts` for all removed/renamed routes; update E2E tests atomically with nav changes.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Backend Cleanup & Scheduler Simplification
**Rationale:** Remove dead features FIRST to reduce surface area before any rework. The scheduler chain rewiring is the highest-risk change in the entire milestone — isolate it so failures are immediately attributable.
**Delivers:** Cleaned backend — corporate events removed, HNX/UPCOM deactivated, scheduler chain simplified to HOSE-only linear pipeline, dead `python-telegram-bot` removed.
**Addresses:** T8 (remove corporate events), T9 (remove HNX/UPCOM) — backend only
**Avoids:** Pitfall #1 (chain breakage), #2 (orphaned FK), #4 (ticker data orphaning), #13 (migration ordering), #14 (WebSocket config), #15 (test coverage gap)
**Key deliverable:** Single Alembic migration that drops `corporate_events`, deactivates HNX/UPCOM tickers. Scheduler rechain from UPCOM→HOSE trigger. Verification test that HOSE crawl → indicators → AI → picks completes.

### Phase 2: Frontend Cleanup & Watchlist Migration
**Rationale:** With backend clean, remove all frontend references to deleted features. Migrate watchlist to DB while old data is still in localStorage (before user clears browser).
**Delivers:** Corporate events UI removed, exchange filter/badge/store removed, watchlist backed by PostgreSQL with one-time migration bridge, navigation reduced to 5 items.
**Addresses:** T8 frontend, T9 frontend, T5 (simplified navigation), T6 (watchlist to DB)
**Avoids:** Pitfall #3 (watchlist data loss), #6 (E2E breakage), #7 (stale exchange filter), #12 (frontend references removed endpoints)
**Key deliverable:** New `watchlist` table + REST API deployed BEFORE frontend migration bridge. localStorage cleared safely. Redirects for removed routes. E2E tests updated.

### Phase 3: Coach Page Restructure & Trade Flow
**Rationale:** Now that cleanup is done and navigation is settled, restructure the Coach page from kitchen-sink into tab-based interactive layout. Add the critical "Record Trade from Pick Card" flow that connects AI recommendations to action.
**Delivers:** Coach page with 3 tabs (Today's Picks, Positions & History, Behavior Analysis). Pick cards with "Ghi lệnh" button that opens pre-filled TradeEntryDialog. Redistributed coach components (picks→home flow, behavior→journal).
**Addresses:** T1 (action-first home page — partially), T2 (record trade from pick cards), D5 (smart trade pre-fill)
**Avoids:** Pitfall #9 (losing existing coach data relationships), #10 (trade journal data disruption)
**Important:** Audit existing backend coach capabilities BEFORE redesigning. Backend already supports `respondRiskSuggestion` and `respondWeeklyPrompt` — don't duplicate.

### Phase 4: AI Analysis Improvement
**Rationale:** AI prompt changes affect the entire daily pipeline (~400 tickers × 5 analysis types). Isolate this from structural changes so truncation or batch issues are immediately diagnosable.
**Delivers:** Longer, structured AI analysis output (4-6 sentences per type, 300-500 words combined). Frontend rendering with expandable sections. Optional: evaluate `gemini-2.5-flash` (non-lite) for combined/trading signal analysis.
**Addresses:** T4 (structured AI analysis)
**Avoids:** Pitfall #5 (output truncation from batch size), #11 (cost/rate increase)
**Key deliverable:** Reduced batch sizes (25→15), increased token budgets, tested ONE batch before full pipeline run. Token usage monitoring for 1 week post-deploy.

### Phase 5: Enhancement Layer
**Rationale:** Core rework complete. Now add the features that make the reworked layout shine — position monitoring on home, post-trade guidance, AI signals on watchlist.
**Delivers:** Open position monitoring with live P&L (T7), post-trade SL/TP confirmation (T3), watchlist entries with AI score/signal (D4).
**Addresses:** T3, T7, D4
**Avoids:** No critical pitfalls — built on stable foundation from phases 1-4.

### Phase Ordering Rationale

- **Backend before frontend** for all removals — prevents 404 windows and import errors. Outside-in removal pattern (consumers → producers → DB).
- **Cleanup before restructure** — removing corporate events + HNX/UPCOM first eliminates ~1,050 LOC and simplifies the Coach page from 12 sections to ~9 before any reorganization.
- **Watchlist migration early** — localStorage data degrades over time (browser clears, device changes). Migrate while data is fresh. Also gates Phase 5's D4 (watchlist with AI signals).
- **AI changes isolated** — prompt tuning affects every ticker in the daily pipeline. If it breaks, it should be the only thing that changed that day.
- **Enhancements last** — T3/T7/D4 all build on the restructured UI from phases 2-3. They're additive, not structural.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Scheduler Rechain):** The `_on_job_executed` chain logic in `scheduler/manager.py` is the most complex and dangerous code to modify. Research-phase should map every chain step before making changes.
- **Phase 4 (AI Prompt Tuning):** Batch size ↔ token limit ↔ rate limit interaction needs empirical testing. Run test batches before committing to production config.

Phases with standard patterns (skip research-phase):
- **Phase 2 (Frontend Cleanup + Watchlist):** Well-documented patterns — React Query optimistic mutations, Alembic CRUD, localStorage migration bridge. All code examples exist in ARCHITECTURE.md.
- **Phase 3 (Coach Restructure):** Pure UI reorganization — moving existing components between pages. No new backend capabilities needed (existing response endpoints already exist).
- **Phase 5 (Enhancements):** Additive features combining existing data — trades + realtime prices + pick SL/TP. Standard React Query composition.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | Direct `requirements.txt` + `package.json` audit. Zero required additions confirmed. All versions validated against existing codebase. |
| Features | **HIGH** | Feature gaps identified via direct component inspection (pick cards lack CTAs, coach page is kitchen sink, overlapping pages confirmed). Anti-features grounded in single-user constraints. |
| Architecture | **HIGH** | All dependency chains, removal sequences, and migration patterns derived from line-by-line codebase analysis. Scheduler chain trigger identified at exact line number (`manager.py:73`). |
| Pitfalls | **HIGH** | All 15 pitfalls sourced from direct code inspection, not inference. Critical chain-trigger pitfall verified against actual `_on_job_executed` implementation. |

**Overall confidence:** HIGH — This is a rework of an existing codebase the research had full access to, not a greenfield build with uncertain requirements. All findings are grounded in actual code, not community patterns or documentation.

### Gaps to Address

- **Gemini `gemini-2.5-flash` vs `gemini-2.5-flash-lite` quality**: MEDIUM confidence that the non-lite model produces meaningfully better long-form analysis. Needs A/B testing during Phase 4 — compare output quality for 10 tickers before committing.
- **Exact batch size for expanded prompts**: The recommendation is 25→15 for regular analysis, but the optimal number depends on actual Gemini token usage. Monitor `usage_metadata.candidates_token_count` during Phase 4 testing.
- **Coach page component redistribution**: The proposed 3-tab layout is an opinionated design decision (MEDIUM confidence). During Phase 3 planning, validate that the "Today's Picks" tab doesn't become its own kitchen sink.
- **`sonner` toast necessity**: Whether trade recording feedback needs toasts or can use existing inline status patterns. Defer decision to Phase 3 implementation.
- **Navigation naming**: "Gợi ý" vs "Huấn luyện" vs other Vietnamese labels for the coach/picks page — UX decision, not a technical gap.

## Sources

### Primary (HIGH confidence)
- Direct codebase audit of all affected files — `scheduler/manager.py`, `scheduler/jobs.py`, `models/corporate_event.py`, `api/corporate_events.py`, `crawlers/corporate_event_crawler.py`, `store.ts`, `navbar.tsx`, `exchange-filter.tsx`, `config.py`, `prompts.py`, `gemini_client.py`
- `PROJECT.md` v9.0 goals and constraints
- `requirements.txt` and `package.json` dependency audit
- Alembic migration history (23 existing migrations)
- APScheduler 3.11 job chain implementation

### Secondary (MEDIUM confidence)
- Trading UX patterns from TradingView, Robinhood, moomoo, Tradervue, Edgewonk — used for feature prioritization and anti-feature decisions
- React Query optimistic mutation pattern — TanStack official docs
- Navigation UX research (Miller's law, mobile nav conventions) — for 5-item nav recommendation

---
*Research completed: 2025-07-21*
*Ready for roadmap: yes*

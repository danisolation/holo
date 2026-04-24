# Domain Pitfalls — v9.0 UX Rework & Simplification

**Domain:** Feature removal + UX rework on existing production stock intelligence platform
**Project:** Holo v9.0 — UX Rework & Simplification
**Researched:** 2025-07-21
**Platform context:** Holo — 800+ tickers (HOSE/HNX/UPCOM), Gemini structured output, PostgreSQL/Aiven, FastAPI + Next.js, single-user personal use

---

## Critical Pitfalls

Mistakes that cause data loss, broken pipelines, or require emergency rollbacks.

---

### Pitfall 1: Broken Job Chain When Removing HNX/UPCOM Crawls

**What goes wrong:** The scheduler's job chain is deeply coupled to HNX/UPCOM. The chain trigger fires from `daily_price_crawl_upcom` → `daily_indicator_compute` → `daily_ai_analysis` → ... → `daily_hnx_upcom_analysis` → `daily_pick_generation`. If you remove the UPCOM crawl job without rewiring the chain trigger, the entire downstream pipeline (indicators, AI analysis, news, sentiment, combined, trading signals, picks) **never fires**.

**Why it happens:** The chain listener in `scheduler/manager.py:73` specifically checks `event.job_id == "daily_price_crawl_upcom"` as the trigger for indicator compute. It's the *last* exchange crawl (HOSE 15:30 → HNX 16:00 → UPCOM 16:30), so it was chosen as the chain initiator. Removing it without moving the chain trigger to `daily_price_crawl_hose` silently breaks the entire daily pipeline.

**Consequences:**
- No daily indicators computed
- No AI analysis generated
- No trading signals, picks, or sentiment analysis
- The app appears functional but shows stale data — worst kind of bug (silent failure)

**Prevention:**
1. In the SAME migration/code change that removes HNX/UPCOM crawl jobs, rewire `_on_job_executed` to trigger from `daily_price_crawl_hose` (or whatever the new last/only exchange crawl is)
2. Also remove the `daily_hnx_upcom_analysis` job and its chain step — it chains from `daily_trading_signal_triggered` to `daily_hnx_upcom_analysis_triggered` to `daily_pick_generation_triggered`
3. Write a verification test: trigger HOSE crawl → assert indicator compute fires → assert AI analysis fires → assert pick generation completes
4. Remove all three cron entries (HOSE/HNX/UPCOM staggered) and replace with single HOSE cron

**Detection:** Daily picks stop generating. Health dashboard shows `daily_indicator_compute` hasn't run. Job execution table shows no new entries after the day of deployment.

**Phase:** Must be addressed in the FIRST phase that touches HNX/UPCOM removal. Backend changes only — no frontend dependency.

---

### Pitfall 2: Orphaned Foreign Key Data After Corporate Events Table Drop

**What goes wrong:** Dropping the `corporate_events` table via Alembic migration while the `ticker_id` foreign key still references `tickers.id`. If done in wrong order, or if other tables were added that reference `corporate_events`, the migration fails. Worse: if you just remove the model without a migration, SQLAlchemy's metadata diverges from the actual DB schema.

**Why it happens:** The `corporate_events` table has `ForeignKey("tickers.id")` on `ticker_id`. The table *itself* doesn't have anything referencing it (no other table has FK → corporate_events), so DROP is safe. But developers often forget to:
- Remove the model from `models/__init__.py` `__all__` list and imports
- Remove the CorporateEvent import from Alembic's `env.py` target metadata
- Actually create and run the Alembic migration (not just delete the .py model file)

**Consequences:**
- If model removed without migration: `alembic upgrade head` still sees the old table, autogenerate creates confusing diff
- If migration drops table before removing code references: imports break at startup → 500 on all requests
- If only code removed (no migration): dead table sitting in production DB consuming space, confusing future developers

**Prevention:**
1. Order of operations: Create Alembic migration FIRST → `DROP TABLE corporate_events` (the table has no inbound FKs, so this is clean)
2. In the SAME commit: remove `models/corporate_event.py`, remove import from `models/__init__.py`, remove from `__all__`
3. Remove `api/corporate_events.py` and its router registration in `api/router.py`
4. Remove `crawlers/corporate_event_crawler.py`
5. Remove `daily_corporate_action_check` job from `scheduler/jobs.py` AND its chain entry in `scheduler/manager.py` (line 83-90, triggered from `daily_price_crawl_upcom`)
6. Remove the `_JOB_NAMES` entries for corporate action check in `scheduler/manager.py`
7. Run `alembic check` to verify no drift

**Detection:** `alembic check` shows pending operations. Backend fails to start with ImportError. Tests referencing corporate events fail.

**Phase:** Backend feature removal phase. Do corporate events and HNX/UPCOM in the same phase since the chain trigger from UPCOM also triggers corporate action check.

---

### Pitfall 3: Watchlist Migration Data Loss — localStorage to DB

**What goes wrong:** User has a curated watchlist in `localStorage` (key: `holo-watchlist`). During migration to DB-backed watchlist, the localStorage data is lost because:
- The migration code runs before the user visits the page
- The user clears browser data between versions
- The new frontend code removes the zustand persist middleware before reading the old data
- The DB migration creates a new empty `watchlist` table, and old localStorage data is never transferred

**Why it happens:** localStorage → DB migration is fundamentally a client-to-server data migration. There's no server-side way to read `localStorage`. The migration MUST happen in the browser on first visit after deployment. Most developers write the new DB-backed code and forget the one-time migration bridge.

**Consequences:**
- User loses their carefully curated watchlist (the whole point of the feature)
- Since this is a single-user personal app, there's exactly ONE user to anger — the developer/user themselves
- If localStorage is cleared before first visit with new code, data is permanently gone

**Prevention:**
1. **Phase 1 — Add DB watchlist API** (backend): Create `POST/GET/DELETE /api/watchlist` endpoints. Use existing `user_watchlist` table (already exists! — it was for Telegram bot but has `chat_id` + `ticker_id`). Repurpose or create new table.
2. **Phase 2 — Frontend migration bridge**: On app mount, check if `localStorage` has `holo-watchlist` data AND DB watchlist is empty → bulk POST to DB → clear localStorage flag (but keep data as backup for 30 days)
3. **Never** remove `zustand/persist` middleware UNTIL after the migration bridge has been deployed and confirmed working
4. Add a `migrated_from_local` flag in DB or localStorage to prevent double-migration
5. Keep localStorage as read-only fallback for 1 release cycle

**Detection:** Watchlist page shows empty after deployment. User notices missing symbols.

**Phase:** Watchlist rework phase. Must be a two-step deployment: backend API first, then frontend migration bridge.

---

### Pitfall 4: HNX/UPCOM Ticker Data Orphaning — 400+ Tickers Left in DB

**What goes wrong:** Removing HNX/UPCOM support from the code but leaving ~400 HNX/UPCOM tickers in the `tickers` table (200 HNX + 200 UPCOM, currently active). These tickers have associated rows in `daily_prices`, `technical_indicators`, `ai_analysis`, `news_articles`, and `financials`. The data becomes stale and pollutes queries.

**Why it happens:** Developers remove the crawl jobs and exchange filter UI but forget that existing data in 6+ tables still references these tickers. Simply marking tickers as `is_active=false` stops new data from being generated but doesn't clean up the presence of these tickers in API responses, search results, and market overview.

**Consequences:**
- `GET /api/tickers` returns HNX/UPCOM tickers unless filtered — confusing
- Heatmap shows stale HNX/UPCOM data from the last crawl day (prices frozen in time)
- Ticker search autocomplete returns HNX/UPCOM symbols that lead to pages with no current data
- `daily_prices` table retains millions of rows for 400 dead tickers (storage waste on Aiven free tier)
- AI analysis summaries for HNX/UPCOM tickers show outdated scores

**Prevention:**
1. Alembic migration: `UPDATE tickers SET is_active = false WHERE exchange IN ('HNX', 'UPCOM')`
2. Ensure ALL API endpoints that list tickers filter by `is_active=true` (verify `tickers.py` does this)
3. Optionally: `DELETE FROM daily_prices WHERE ticker_id IN (SELECT id FROM tickers WHERE exchange IN ('HNX', 'UPCOM'))` — but be careful with partition table if yearly partitioning is used
4. Remove the `exchange` filter UI (`ExchangeFilter` component, `ExchangeBadge`, `useExchangeStore`) — or simplify to show "HOSE" only / remove entirely
5. Clean up the `EXCHANGE_MAX_TICKERS` dict in `ticker_service.py` to only have HOSE
6. Remove `VALID_EXCHANGES` tuple in `jobs.py`
7. Update `realtime_priority_exchanges` in config to only `["HOSE"]`

**Detection:** Search for a known HNX ticker (e.g., "SHB") — if it appears in results, cleanup is incomplete.

**Phase:** Same phase as HNX/UPCOM job removal. Data cleanup migration should be the LAST step after code changes.

---

## Moderate Pitfalls

---

### Pitfall 5: AI Prompt Length Change Breaks Structured Output Parsing

**What goes wrong:** Making AI analysis "longer and more detailed" by increasing reasoning token limits or changing prompt instructions (e.g., from "2-3 câu" to "5-7 câu") causes Gemini to exceed the response schema's expected structure, return partial JSON, or hit token limits. The `google-genai` structured output (Pydantic schema) may truncate or fail validation.

**Why it happens:** The current prompts are tightly calibrated:
- `TECHNICAL_SYSTEM_INSTRUCTION`: "reasoning (2-3 câu tiếng Việt)"
- `COMBINED_SYSTEM_INSTRUCTION`: "explanation (tiếng Việt, tối đa 200 từ)"
- `TRADING_SIGNAL_SYSTEM_INSTRUCTION`: "reasoning: tối đa 300 ký tự"
- `gemini_batch_size: 25` — 25 tickers per prompt
- `trading_signal_batch_size: 15` — already reduced for larger output

Doubling the reasoning length means each ticker's response is ~2x larger. With batch size 25, the total response can hit Gemini's output token limit. The model silently truncates, producing invalid JSON for the last few tickers in the batch.

**Consequences:**
- Last 3-5 tickers in each batch get no analysis (truncated response)
- Pydantic validation rejects malformed JSON → those tickers recorded as "failed"
- Overall analysis coverage drops from ~400 tickers to ~350 (14% loss)
- Cost increases proportionally (more output tokens billed)
- Response time per batch increases from ~4s to ~6-8s, extending the full pipeline from ~45min to ~75min

**Prevention:**
1. When increasing reasoning length, SIMULTANEOUSLY reduce `gemini_batch_size` (e.g., 25→15 for regular analysis, 15→10 for trading signals)
2. Increase `gemini_max_tokens` in config proportionally
3. Test with ONE batch first — verify full JSON response before running full pipeline
4. Add a token usage check: if response `usage_metadata.candidates_token_count` is within 90% of max, log a warning
5. Consider increasing `gemini_delay_seconds` from 4.0→5.0 to stay within rate limits with larger responses
6. Update the reasoning field's `max_length` in Pydantic schemas if they have one

**Detection:** Spike in "failed_symbols" in daily AI analysis job execution records. `gemini_usage` table shows increased token counts per call.

**Phase:** AI improvement phase. Must be tested in isolation before deploying to production pipeline.

---

### Pitfall 6: Navigation Restructure Breaks E2E Tests and Bookmarks

**What goes wrong:** Changing the navbar links (currently 7 items: Tổng quan, Danh mục, Bảng điều khiển, Huấn luyện, Nhật ký, Sự kiện, Hệ thống) breaks:
- 119 Playwright E2E tests that navigate by URL or click nav links
- Any bookmarked URLs the user has
- The `data-testid="navbar"` and `data-testid="nav-desktop"` selectors used in tests
- Mobile sheet navigation (duplicated link list)

**Why it happens:** The `NAV_LINKS` array in `navbar.tsx` is the single source of truth for navigation. But E2E tests reference specific routes (`/dashboard`, `/watchlist`, `/coach`, `/journal`, `/dashboard/corporate-events`, `/dashboard/health`). Removing "Sự kiện" (corporate events) link without adding a redirect means tests AND bookmarks hit a 404 or empty page.

**Consequences:**
- E2E test suite fails (was passing 119/119 → now unknown failures)
- User's browser history links break
- If routes are renamed (e.g., `/dashboard` → something else), deep links from any saved notes break

**Prevention:**
1. When removing `/dashboard/corporate-events` route, delete the page directory AND remove from `NAV_LINKS`
2. Add a Next.js redirect in `next.config.ts` for removed routes → home page (graceful degradation)
3. Update ALL E2E tests that reference removed routes BEFORE merging the change
4. Keep route structure stable where possible — rename only when necessary
5. For navigation restructure: update `NAV_LINKS` as a single atomic change, then update tests

**Detection:** E2E test run fails immediately. Manual: visit `/dashboard/corporate-events` → should redirect, not 404.

**Phase:** Navigation/onboarding phase. Run E2E suite as validation gate after changes.

---

### Pitfall 7: Removing Exchange Filter Breaks Market Overview Page Logic

**What goes wrong:** The market overview page (`/dashboard/page.tsx`) and heatmap heavily depend on `useExchangeStore` to filter which tickers to display. The `ExchangeFilter` component controls a zustand store that persists to localStorage. If you remove the filter component but the store still has `exchange: "HNX"` persisted from a previous session, the heatmap renders an empty view (no HNX tickers after cleanup).

**Why it happens:** `zustand/persist` stores the selected exchange in `localStorage` under key `holo-exchange-filter`. Even after removing the `ExchangeFilter` UI component, the persisted value remains. If the API endpoint still accepts `exchange` parameter, it'll filter to an exchange that no longer has active tickers.

**Consequences:**
- User sees empty heatmap on first visit after update (had "HNX" selected)
- Watchlist table shows zero rows (was filtered to HNX/UPCOM)
- No obvious way to "fix" it from the UI since the filter toggle is gone

**Prevention:**
1. When removing `ExchangeFilter`, also clear the persisted store. Add a one-time migration in the app root: `localStorage.removeItem("holo-exchange-filter")`
2. OR: Set default exchange to `"HOSE"` (not `"all"`) and remove the ability to change it
3. Remove the `exchange` parameter from API calls in the frontend OR hardcode to "HOSE"
4. Remove `useExchangeStore` entirely from `store.ts` after migration
5. Remove `ExchangeBadge` component (no longer needed with single exchange)

**Detection:** Heatmap is empty on first load after deployment. Console shows API returning empty array for `exchange=HNX`.

**Phase:** Same phase as HNX/UPCOM frontend cleanup. Must handle localStorage stale state.

---

### Pitfall 8: Onboarding Flow Blocks Experienced User

**What goes wrong:** Adding a "where to start" onboarding experience (one of v9.0 goals) that shows on every visit, uses a modal/overlay pattern, or requires clicking through steps before accessing the dashboard. The single user is already experienced with the app and will be annoyed by onboarding they can't dismiss permanently.

**Why it happens:** Developer thinks "new users need guidance" but forgets this is a single-user app where the user already knows the workflow. Common anti-pattern: using a framework's onboarding library (like react-joyride or shepherd.js) that defaults to showing on every new session.

**Consequences:**
- Daily friction for the one user who matters
- User starts ignoring/resenting the onboarding, defeating its purpose
- Time wasted implementing something that gets disabled immediately

**Prevention:**
1. Onboarding should be a one-time experience stored in localStorage (`holo-onboarding-completed: true`)
2. Better approach for single-user app: improve the DEFAULT layout so it's self-explanatory, not a tutorial overlay
3. Add a "What's New" section on the home page after v9.0 ships — one dismissible card, not a modal flow
4. Focus on making navigation labels clear (Vietnamese, action-oriented) rather than adding tooltip tours
5. If implementing guided flow, add a "Bỏ qua" (Skip) button that permanently dismisses

**Detection:** User complains about onboarding appearing repeatedly. Onboarding state not persisting across browser restarts.

**Phase:** Navigation/onboarding phase. Design decision should favor layout clarity over tutorial overlays.

---

### Pitfall 9: Coach Page Rework Loses Existing Data Relationships

**What goes wrong:** The Coach page currently shows read-only data (behavior tracking, habit detection, risk suggestions, sector preferences, weekly reviews). Making it "actionable" (allowing user actions) requires new API endpoints, potentially new DB tables, and careful handling of existing data flows. If the rework replaces components rather than extending them, the existing data visualizations break.

**Why it happens:** "Making the coach page actionable" is vague. The backend already has:
- `behavior_service.py` — behavior event tracking
- `habit_detection.py` model — detected habits
- `risk_suggestion.py` model — risk suggestions with response capability
- `weekly_review.py` model — AI-generated reviews
- `weekly_prompt.py` model — weekly prompts with response capability

Some of these already support user responses (`respondRiskSuggestion`, `respondWeeklyPrompt`). The rework might duplicate this by adding new action endpoints without realizing the backend capability already exists.

**Consequences:**
- Duplicate endpoints for the same functionality
- Existing response data (weekly prompt answers, risk suggestion responses) orphaned if tables are restructured
- Frontend components rebuilt from scratch when they only needed UI polish

**Prevention:**
1. Audit existing Coach page functionality BEFORE redesigning: list every component, what data it shows, what actions are already supported
2. The backend already supports `POST /api/behavior/risk-suggestions/{id}/respond` and `POST /api/goals/weekly-prompts/{id}/respond` — the frontend just needs to expose these better
3. Start by adding action buttons to EXISTING components, not rebuilding
4. If restructuring: keep the same API contracts, just change how data is displayed/interacted with

**Detection:** Previously working coach features (habit detection cards, risk suggestion banners) stop rendering after rework.

**Phase:** Coach page rework phase. Start with UI-only changes before adding new backend capabilities.

---

### Pitfall 10: Trade Journal "Next Step" Redesign Disrupts Existing Trade Data

**What goes wrong:** Redesigning the Trade Journal flow to add "clear next steps after recording a trade" may change the `Trade` model or `Lot`/`LotMatch` structure. If new fields are added (e.g., `next_action`, `follow_up_date`) without Alembic migration, or if existing trades are assumed to have these fields, the journal page crashes for historical data.

**Why it happens:** Desire to show "what to do after recording a trade" (e.g., set alerts, review in 3 days, check stop-loss levels). Developers add non-nullable fields to the Trade model without defaults, breaking existing records.

**Consequences:**
- Existing trade history renders as errors (null values where not expected)
- Alembic migration fails if adding NOT NULL columns without defaults
- Historical P&L calculations break if trade structure changes

**Prevention:**
1. New fields MUST be nullable or have defaults — existing trades don't have this data
2. "Next step" guidance should be a UI-ONLY feature (show suggested actions based on trade type/status) rather than new DB columns
3. If new columns are needed, use `server_default` in Alembic migration
4. Test with existing trade data BEFORE deploying — query `SELECT count(*) FROM trades` to know the scale
5. Prefer adding a new related table (e.g., `trade_actions`) over modifying the existing `Trade` model

**Detection:** Trade journal page crashes after migration. Alembic migration fails with "column cannot be null" error.

**Phase:** Trade Journal rework phase. Favor UI-only changes; DB changes only if strictly necessary.

---

## Minor Pitfalls

---

### Pitfall 11: Gemini API Cost Increase from Longer Analysis

**What goes wrong:** Switching from "2-3 câu" to "5-7 câu" reasoning doubles output tokens. With 400 tickers × 5 analysis types × 2x tokens, the daily Gemini API cost roughly doubles. On free tier (gemini-2.5-flash-lite), this might not cost money but WILL hit rate limits more aggressively.

**Prevention:**
1. Calculate expected token increase BEFORE changing prompts: `current_daily_tokens × 2 = new_daily_tokens`
2. Check Gemini free tier limits: 15 RPM is the bottleneck, not token count — but longer responses = longer per-request time = fewer effective RPM
3. Consider increasing `gemini_delay_seconds` from 4.0→5.0 to compensate for longer processing
4. Monitor `gemini_usage` table daily for a week after changes

**Phase:** AI improvement phase.

---

### Pitfall 12: Frontend Components Reference Removed Backend Endpoints

**What goes wrong:** Frontend still imports `fetchCorporateEvents` from `lib/api.ts` and uses `useCorporateEvents` from `lib/hooks.ts` after backend endpoint is removed. The corporate events calendar component throws uncaught fetch errors.

**Prevention:**
1. Full-text search for `corporate` in ALL frontend files before marking backend removal as complete
2. Remove: `corporate-events-calendar.tsx`, `/dashboard/corporate-events/page.tsx`, `fetchCorporateEvents` in `api.ts`, `useCorporateEvents` in `hooks.ts`
3. Remove the `{ href: "/dashboard/corporate-events", label: "Sự kiện" }` from `NAV_LINKS` in `navbar.tsx`
4. Run `npx tsc --noEmit` after removal to catch any remaining type references

**Phase:** Frontend cleanup phase, immediately after or alongside backend corporate events removal.

---

### Pitfall 13: Alembic Migration Ordering for Multiple Table Drops

**What goes wrong:** Creating separate Alembic migrations for "drop corporate_events" and "deactivate HNX/UPCOM tickers" in the wrong dependency order. If the ticker deactivation migration runs first and assumes corporate events are already gone (or vice versa), the migrations become order-dependent.

**Prevention:**
1. Create ONE migration for all v9.0 cleanup: drop `corporate_events` table, deactivate HNX/UPCOM tickers, clean up any orphaned data
2. Name it clearly: `024_v9_remove_corporate_events_and_hnx_upcom.py`
3. Test both `upgrade` and `downgrade` paths — downgrade should recreate the table and reactivate tickers
4. Run on a test database BEFORE production

**Phase:** First backend phase. Migration should be the very first deliverable.

---

### Pitfall 14: WebSocket Real-Time Polling Still Includes HNX/UPCOM Symbols

**What goes wrong:** `realtime_priority_exchanges` in `config.py` is set to `["HOSE", "HNX", "UPCOM"]`. The `realtime_price_poll` job uses this to determine which symbols to poll from VCI. After removing HNX/UPCOM support, this config still tries to poll prices for exchanges with no active tickers, wasting API calls.

**Prevention:**
1. Update `realtime_priority_exchanges` default to `["HOSE"]` in `config.py`
2. Check `realtime_price_service.py` for any hardcoded exchange references
3. The service should already filter by `is_active=true` tickers, but verify this

**Phase:** Backend cleanup phase, same as HNX/UPCOM removal.

---

### Pitfall 15: Test Coverage Gap After Feature Removal

**What goes wrong:** Removing 560+ lines of corporate events code and HNX/UPCOM logic also removes their associated tests. The overall test count drops significantly, but more importantly, tests that INCIDENTALLY covered shared code paths (like job chaining, ticker service, price service) are gone — reducing coverage of the remaining code.

**Prevention:**
1. Before removing: check which tests cover shared utilities (e.g., `_determine_status`, `_build_summary`, `_dlq_failures` in `jobs.py`)
2. After removing: run full test suite AND check coverage report for regressions
3. Add new tests for the modified job chain (HOSE-only pipeline)
4. Ensure E2E tests cover the modified navigation (one less nav item, no exchange filter)

**Phase:** Every phase should include test updates as a checklist item.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| **Remove corporate events (backend)** | Chain trigger breakage (#1), orphan imports (#2), frontend still referencing endpoint (#12) | Do backend + frontend removal atomically; rewire chain trigger; run `tsc --noEmit` |
| **Remove HNX/UPCOM (backend)** | Chain trigger breakage (#1), stale ticker data (#4), WebSocket config (#14) | Rewire chain to HOSE-only; deactivate tickers in migration; update config defaults |
| **Remove HNX/UPCOM (frontend)** | Persisted exchange filter (#7), exchange badge dead references | Clear localStorage stale state; remove all exchange-related components |
| **Watchlist migration** | Data loss from localStorage (#3) | Two-step deploy: backend API first, then frontend migration bridge with fallback |
| **AI prompt improvement** | Structured output truncation (#5), cost/rate increase (#11) | Reduce batch size proportionally; test single batch first; monitor token usage |
| **Trade Journal rework** | Existing trade data breakage (#10) | UI-only changes preferred; nullable new fields with defaults if DB changes needed |
| **Coach page rework** | Losing existing functionality (#9) | Audit existing backend capabilities first; extend, don't replace |
| **Navigation & onboarding** | E2E test breakage (#6), annoying onboarding (#8) | Add redirects for removed routes; one-time dismissible onboarding only |
| **Combined: corporate + HNX/UPCOM** | Migration ordering (#13) | Single Alembic migration for all DB schema changes |

---

## Recommended Removal Order (Dependency-Safe)

Based on the pitfall analysis, the safest order for feature removal is:

```
1. Alembic migration (deactivate HNX/UPCOM tickers, drop corporate_events table)
2. Backend code removal (models, crawlers, API endpoints, scheduler jobs)
3. Scheduler chain rewiring (UPCOM trigger → HOSE trigger, remove corporate action chain)
4. Frontend code removal (components, routes, store cleanup, localStorage migration)
5. Test updates (remove dead tests, add new chain verification tests)
6. Config cleanup (exchange lists, batch sizes, timeouts)
```

Doing it in any other order risks the silent pipeline failure described in Pitfall #1 — the most critical and hardest-to-detect failure mode in this codebase.

---

## Sources

- Direct codebase analysis:
  - `backend/app/scheduler/manager.py` — job chain listener with UPCOM-specific trigger (line 73)
  - `backend/app/scheduler/jobs.py` — HNX/UPCOM job functions, VALID_EXCHANGES constant
  - `backend/app/models/corporate_event.py` — FK to tickers, unique constraints
  - `backend/app/api/corporate_events.py` — API endpoint to remove
  - `backend/app/crawlers/corporate_event_crawler.py` — crawler to remove
  - `frontend/src/lib/store.ts` — zustand persist for watchlist (localStorage) and exchange filter
  - `frontend/src/components/navbar.tsx` — NAV_LINKS array with corporate events route
  - `frontend/src/components/exchange-filter.tsx` — HNX/UPCOM filter component
  - `backend/app/config.py` — realtime_priority_exchanges, batch sizes, token limits
  - `backend/app/services/analysis/prompts.py` — current prompt reasoning length constraints
  - `backend/app/models/__init__.py` — model registry with CorporateEvent
- Confidence: **HIGH** — all findings derived from direct code inspection, not inference

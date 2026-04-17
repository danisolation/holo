---
phase: 12-multi-market-foundation
verified: 2025-07-19T13:00:00Z
status: human_needed
score: 4/4 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Switch exchange filter tabs on market overview and verify heatmap shows only tickers from selected exchange with correct border colors"
    expected: "HOSE tiles have blue borders, HNX tiles have green borders, UPCOM tiles have orange borders; switching tabs refetches and re-renders"
    why_human: "Visual rendering of CSS custom properties and color accuracy cannot be verified programmatically"
  - test: "Navigate to an HNX ticker detail page that is NOT in watchlist and verify the 'Phân tích ngay' button appears"
    expected: "Button labeled 'Phân tích ngay' with Sparkles icon visible in the AI analysis section; button hidden for HOSE tickers and watchlisted tickers"
    why_human: "Conditional visibility depends on live ticker data, watchlist state, and recent analysis — requires visual confirmation"
  - test: "Verify exchange badges appear correctly in ticker search, watchlist table, and ticker detail header"
    expected: "Color-coded badges (HOSE=blue, HNX=green, UPCOM=orange) with correct text render inline at each location"
    why_human: "Badge color rendering via CSS custom properties needs visual spot-check"
---

# Phase 12: Multi-Market Foundation Verification Report

**Phase Goal:** Dashboard and analysis cover all Vietnamese stock exchanges (HOSE, HNX, UPCOM), not just HOSE
**Verified:** 2025-07-19T13:00:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can view OHLCV data and charts for HNX and UPCOM tickers alongside existing HOSE tickers | ✓ VERIFIED | `TickerService.fetch_and_sync_tickers(exchange=)` parameterized for all 3 exchanges (HOSE=400, HNX=200, UPCOM=200). `PriceService.crawl_daily(exchange=)` passes filter through. Frontend `Ticker` and `MarketTicker` types include `exchange` field. API endpoints return exchange field in responses. |
| 2 | User can filter stock lists, market overview, and heatmap by exchange (HOSE/HNX/UPCOM/All) | ✓ VERIFIED | `ExchangeFilter` component renders 4 tabs (Tất cả/HOSE/HNX/UPCOM). `useExchangeStore` with zustand persist. Exchange filter present on market overview (`page.tsx`), watchlist (`watchlist/page.tsx`), and dashboard (`dashboard/page.tsx`). API `?exchange=` param validated against `ALLOWED_EXCHANGES`. Heatmap uses `EXCHANGE_BORDER_COLORS` for colored borders. |
| 3 | HNX and UPCOM tickers are crawled daily on staggered schedules without exceeding pipeline window or starving DB pool | ✓ VERIFIED | `EXCHANGE_CRAWL_SCHEDULE` in `manager.py`: HOSE 15:30, HNX 16:00, UPCOM 16:30. Chain triggers only from `daily_price_crawl_upcom` (last exchange). `weekly_ticker_refresh` syncs all 3 exchanges. `daily_price_crawl_for_exchange` validates exchange against `VALID_EXCHANGES`. |
| 4 | AI analysis runs daily for all HOSE tickers and watchlisted HNX/UPCOM tickers; remaining HNX/UPCOM tickers analyzed on-demand only | ✓ VERIFIED | `analyze_watchlisted_tickers(exchanges=["HNX","UPCOM"], max_extra=50)` queries `UserWatchlist × Ticker` for target exchanges, capped at 50. `daily_hnx_upcom_analysis` job chained after `daily_combined`. `POST /api/analysis/{symbol}/analyze-now` endpoint with 5-min server-side cooldown. `analyze_single_ticker` runs all 4 types under single lock. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/services/ticker_service.py` | Exchange-parameterized ticker sync with per-exchange deactivation | ✓ VERIFIED | `EXCHANGE_MAX_TICKERS` dict (HOSE=400, HNX=200, UPCOM=200). `Ticker.exchange == exchange` in deactivation WHERE clause. Exchange validation on entry (ValueError for invalid). |
| `backend/app/services/price_service.py` | Exchange-parameterized daily crawl | ✓ VERIFIED | `crawl_daily(exchange=None)` passes filter to `get_ticker_id_map(exchange=exchange)`. Backward compatible when None. |
| `backend/app/scheduler/manager.py` | Staggered cron triggers + updated chaining | ✓ VERIFIED | `EXCHANGE_CRAWL_SCHEDULE` with 3 entries. `functools.partial` for per-exchange job functions. Chain from `daily_price_crawl_upcom` only. HNX/UPCOM analysis chained after `daily_combined`. |
| `backend/app/scheduler/jobs.py` | Exchange-parameterized job functions | ✓ VERIFIED | `daily_price_crawl_for_exchange(exchange)` with `VALID_EXCHANGES` validation. `weekly_ticker_refresh` syncs all 3 exchanges. `daily_hnx_upcom_analysis` calls `analyze_watchlisted_tickers`. |
| `backend/app/api/tickers.py` | Exchange-filtered API endpoints | ✓ VERIFIED | `ALLOWED_EXCHANGES = {"HOSE", "HNX", "UPCOM"}`. Exchange query param on `list_tickers` and `market_overview`. 400 on invalid exchange. `TickerResponse` and `MarketTickerResponse` include `exchange` field. |
| `backend/app/api/analysis.py` | On-demand analysis endpoint | ✓ VERIFIED | `POST /{symbol}/analyze-now` with ticker validation (404), server-side 5-min cooldown (429), background task execution via `analyze_single_ticker`. |
| `backend/app/services/ai_analysis_service.py` | Tiered AI analysis + on-demand | ✓ VERIFIED | `analyze_watchlisted_tickers` caps at `max_extra=50`. `analyze_single_ticker` runs all 4 types under single `_gemini_lock`. `analyze_all_tickers` accepts `ticker_filter: dict[str, int] | None`. |
| `backend/tests/test_ticker_service_multi.py` | Multi-exchange ticker service tests | ✓ VERIFIED | 8 tests: HNX/HOSE/UPCOM max limits, deactivation scoping, exchange-filtered queries, upsert exchange field. |
| `backend/tests/test_ai_analysis_tiered.py` | Tiered AI analysis + on-demand tests | ✓ VERIFIED | 6 tests: caps at max_extra, exchange filter in query, return shape, single ticker all 4 types, on-demand 200, on-demand 404. |
| `frontend/src/components/exchange-filter.tsx` | Reusable exchange tabs component | ✓ VERIFIED | 4 tabs (Tất cả/HOSE/HNX/UPCOM). Reads/writes `useExchangeStore`. Shadcn Tabs component. |
| `frontend/src/components/exchange-badge.tsx` | Color-coded exchange badge | ✓ VERIFIED | `EXCHANGE_CLASSES` map with CSS custom properties for HOSE (blue), HNX (green), UPCOM (orange). Badge variant="outline". |
| `frontend/src/lib/store.ts` | Exchange filter zustand store | ✓ VERIFIED | `Exchange` type: `"all" | "HOSE" | "HNX" | "UPCOM"`. `useExchangeStore` with persist (key: `holo-exchange-filter`), default `"all"`. |
| `frontend/src/app/globals.css` | Exchange CSS custom properties | ✓ VERIFIED | `:root` defines `--exchange-hose`, `--exchange-hnx`, `--exchange-upcom` + `-fg` variants. `.dark` overrides with brighter variants for contrast. |
| `frontend/src/lib/api.ts` | Exchange-aware API client | ✓ VERIFIED | `Ticker` and `MarketTicker` interfaces include `exchange: string`. `fetchTickers(sector?, exchange?)`, `fetchMarketOverview(exchange?)`, `triggerOnDemandAnalysis(symbol)` all present. |
| `frontend/src/lib/hooks.ts` | Exchange-aware query hooks | ✓ VERIFIED | `useTickers(sector?, exchange?)` with exchange in queryKey. `useMarketOverview(exchange?)` with exchange in queryKey. `useTriggerAnalysis()` mutation with cache invalidation. |
| `frontend/src/app/page.tsx` | Market overview with exchange filter | ✓ VERIFIED | `ExchangeFilter` between title and stats grid. Dynamic subtitle per exchange. `useMarketOverview(exchange)` refetches on tab switch. Exchange passed to Heatmap. |
| `frontend/src/components/heatmap.tsx` | Exchange-colored heatmap | ✓ VERIFIED | `EXCHANGE_BORDER_COLORS` map (HOSE→blue, HNX→green, UPCOM→orange via CSS vars). Desktop: `border-2` with exchange color. Mobile: `ExchangeBadge` inline. Exchange-specific empty state. |
| `frontend/src/components/watchlist-table.tsx` | Watchlist with exchange column | ✓ VERIFIED | Exchange "Sàn" column with `ExchangeBadge`. `useExchangeStore` integration for row filtering. `filteredRows` useMemo. |
| `frontend/src/app/watchlist/page.tsx` | Watchlist page with exchange filter | ✓ VERIFIED | `ExchangeFilter` tabs between title and `WatchlistTable`. |
| `frontend/src/app/dashboard/page.tsx` | Dashboard with exchange filter | ✓ VERIFIED | `ExchangeFilter` after title. `useExchangeStore` exchange passed to `useMarketOverview(exchange)`. |
| `frontend/src/app/ticker/[symbol]/page.tsx` | Ticker detail with badge + AnalyzeNow | ✓ VERIFIED | `ExchangeBadge` next to symbol in header (line 157-159). `AnalyzeNowButton` component (lines 36-102) with full state machine (idle/loading/success/error/cooldown). Visibility: only for non-HOSE, non-watchlisted, no recent analysis. Rendered at line 265. |
| `frontend/src/components/ticker-search.tsx` | Search with exchange badges | ✓ VERIFIED | `ExchangeBadge` inline in each `CommandItem` (line 63). |
| `frontend/src/app/layout.tsx` | Metadata with all exchanges | ✓ VERIFIED | Description: "AI-powered stock analysis dashboard for Vietnamese stock market (HOSE, HNX, UPCOM)". |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `ticker_service.py` | `EXCHANGE_MAX_TICKERS` dict | Module-level constant + class attribute | ✓ WIRED | Defined at module level (line 17) and referenced as class attribute (line 27). Used in `fetch_and_sync_tickers` (line 50). |
| `scheduler/manager.py` | `scheduler/jobs.py` | `functools.partial(daily_price_crawl_for_exchange, exchange)` | ✓ WIRED | `functools.partial` wraps exchange arg for each cron job (line 182). |
| `scheduler/manager.py` | Chain trigger | `_on_job_executed` listener on `daily_price_crawl_upcom` | ✓ WIRED | Line 80: `if event.job_id == "daily_price_crawl_upcom"` triggers indicators, price alerts, corporate actions. |
| `manager.py` | `daily_hnx_upcom_analysis` | Chain from `daily_combined` | ✓ WIRED | Lines 152-160: After combined analysis completes, chains HNX/UPCOM analysis parallel with signal alerts. |
| `api/tickers.py` | Exchange validation | `ALLOWED_EXCHANGES` set | ✓ WIRED | Lines 59-63 (`list_tickers`) and 136-140 (`market_overview`) validate against set, 400 on invalid. |
| `api/analysis.py` | `AIAnalysisService.analyze_single_ticker` | Background task `_run()` | ✓ WIRED | Line 66: `await service.analyze_single_ticker(ticker_id, ticker_symbol)` in background task. |
| `frontend/exchange-filter.tsx` | `store.ts` | `useExchangeStore` | ✓ WIRED | Line 14: reads `exchange` and `setExchange` from store. |
| `frontend/page.tsx` | `hooks.ts` | `useMarketOverview(exchange)` | ✓ WIRED | Line 13: passes exchange from store to hook. Hook includes exchange in queryKey (line 81 of hooks.ts). |
| `frontend/api.ts` | Backend API | `fetchMarketOverview(exchange?)` → `?exchange=` query param | ✓ WIRED | Line 138: constructs `?exchange=` param when not "all". |
| `frontend/api.ts` | Backend API | `triggerOnDemandAnalysis(symbol)` → `POST /api/analysis/{symbol}/analyze-now` | ✓ WIRED | Lines 142-146: POST to correct endpoint. |
| `frontend/hooks.ts` | `api.ts` | `useTriggerAnalysis()` → `triggerOnDemandAnalysis` | ✓ WIRED | Line 90: `mutationFn: (symbol) => triggerOnDemandAnalysis(symbol)`. Cache invalidation on success. |
| `frontend/ticker/[symbol]/page.tsx` | `AnalyzeNowButton` | Rendered with props from page state | ✓ WIRED | Line 265-270: passes `symbol`, `exchange`, `isWatchlisted`, `hasRecentAnalysis`. Button calls `useTriggerAnalysis` mutate. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend tests pass | `python -m pytest tests/ -x -q` | 222 passed, 0 failed, 6 warnings | ✓ PASS |
| Frontend TypeScript compiles | `npx tsc --noEmit` | Exit code 0, no errors | ✓ PASS |
| No TODO/FIXME in key files | grep scan on 13 key files | 0 blocking patterns found | ✓ PASS |
| Review HIGH issues fixed | Code inspection of analysis.py:46-59 and ai_analysis_service.py:441-452 | Server-side 5-min cooldown + single lock acquisition | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MKT-01 | 12-01, 12-03 | HNX/UPCOM data coverage (top 200 each) | ✓ SATISFIED | `EXCHANGE_MAX_TICKERS`: HNX=200, UPCOM=200. Frontend types include exchange field. API endpoints return exchange. |
| MKT-02 | 12-02, 12-03, 12-04 | Exchange identification UI (filter tabs, badges, colors) | ✓ SATISFIED | ExchangeFilter on 3 pages. ExchangeBadge on watchlist, ticker detail, search, heatmap mobile. CSS custom properties for 3 exchange colors with dark mode. |
| MKT-03 | 12-01, 12-02 | Smart crawl scheduling (staggered: HOSE 15:30, HNX 16:00, UPCOM 16:30) | ✓ SATISFIED | `EXCHANGE_CRAWL_SCHEDULE` in manager.py. Chain from UPCOM only. Weekly refresh syncs all 3. Daily summary moved to 18:30. |
| MKT-04 | 12-02, 12-04 | On-demand AI analysis for non-watchlisted HNX/UPCOM tickers | ✓ SATISFIED | `analyze_watchlisted_tickers` (capped 50). `daily_hnx_upcom_analysis` job. `POST /api/analysis/{symbol}/analyze-now` with cooldown. AnalyzeNowButton on ticker detail with full state machine. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `watchlist-table.tsx` | 82 | `return []` | ℹ️ Info | Guard clause for null data — not a stub. Appropriate empty return when `marketData` is undefined. |
| `watchlist-table.tsx` | 274 | `isPlaceholder` | ℹ️ Info | Standard tanstack/react-table property — not a placeholder pattern. |

No blocking or warning anti-patterns found.

### Human Verification Required

### 1. Exchange Filter Visual Behavior

**Test:** Navigate to market overview page, click each exchange tab (Tất cả → HOSE → HNX → UPCOM) and observe heatmap changes.
**Expected:** Tiles show only tickers from selected exchange. HOSE tiles have blue borders, HNX green, UPCOM orange. Stats cards update counts. Subtitle changes dynamically ("Bản đồ nhiệt sàn HOSE...").
**Why human:** Visual rendering of CSS custom properties, color accuracy, and dynamic data refetch behavior cannot be verified programmatically.

### 2. AnalyzeNow Button Visibility & Behavior

**Test:** Navigate to an HNX or UPCOM ticker detail page that is NOT in watchlist and has no recent analysis.
**Expected:** "Phân tích ngay" button visible with Sparkles icon in AI analysis section. Button hidden for HOSE tickers and watchlisted tickers. Clicking triggers loading state with spinner.
**Why human:** Conditional visibility depends on live ticker data, watchlist state, and analysis recency — requires visual confirmation with real data.

### 3. Exchange Badges Across Pages

**Test:** Check ExchangeBadge rendering in: (a) ticker search results, (b) watchlist table "Sàn" column, (c) ticker detail header next to symbol.
**Expected:** Color-coded outline badges (HOSE=blue, HNX=green, UPCOM=orange) render correctly at each location with proper sizing.
**Why human:** Badge visual rendering via CSS custom properties needs spot-check across multiple pages.

### Gaps Summary

No code-level gaps found. All 4 roadmap success criteria are verified at the artifact, wiring, and behavioral levels:

1. **Multi-exchange data support** — TickerService and PriceService fully parameterized with per-exchange limits and deactivation scoping.
2. **Exchange filter UI** — ExchangeFilter tabs + ExchangeBadge components wired across all relevant pages with zustand persist.
3. **Staggered crawl scheduling** — Three cron jobs with 30-minute offsets, chain triggers from last exchange only.
4. **Tiered AI analysis** — HOSE daily all, HNX/UPCOM watchlisted (capped 50), remainder on-demand via endpoint with cooldown.

Code review issues (HIGH-01 server-side rate limit, HIGH-02 lock starvation) were both addressed in the final implementation. All 222 backend tests pass. TypeScript compiles with zero errors.

3 items require human visual verification: exchange filter behavior, AnalyzeNow button visibility, and exchange badge rendering across pages.

---

_Verified: 2025-07-19T13:00:00Z_
_Verifier: the agent (gsd-verifier)_

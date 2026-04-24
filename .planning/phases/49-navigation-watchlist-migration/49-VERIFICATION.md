---
phase: 49-navigation-watchlist-migration
verified: 2026-04-24T14:30:38Z
status: human_needed
score: 4/4 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Navigate between all 5 nav items and verify correct page loads"
    expected: "Each nav link (Tổng quan, Danh mục, Huấn luyện, Nhật ký, Hệ thống) navigates to the correct page with active state highlighting"
    why_human: "Visual navigation behavior, active state styling, mobile hamburger menu"
  - test: "Visit /dashboard URL directly"
    expected: "Browser redirects to / (home page) with no flash of dashboard content"
    why_human: "Redirect timing and visual smoothness can't be verified statically"
  - test: "Add and remove a ticker from watchlist on the ticker detail page"
    expected: "Star button toggles, watchlist updates immediately, persists after page refresh and in another browser/incognito"
    why_human: "Cross-device persistence requires real browser testing with server running"
  - test: "Clear watchlist, add tickers to localStorage under key 'holo-watchlist' with zustand format, then visit /watchlist"
    expected: "Symbols migrate to server automatically, localStorage key removed, tickers appear in watchlist table"
    why_human: "localStorage migration is a one-time side effect that requires manual setup"
  - test: "View watchlist with tickers that have AI analysis data"
    expected: "Each row shows colored signal badge (buy/sell/hold) with icon and numeric score (X/10)"
    why_human: "Visual rendering of AI signal badges, colors, icons needs human eye"
---

# Phase 49: Navigation & Watchlist Migration Verification Report

**Phase Goal:** User has a clean, simplified navigation and a server-backed watchlist that persists across devices and shows AI signal data alongside each ticker
**Verified:** 2026-04-24T14:30:38Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Navigation shows 4-5 items (reduced from 7), with overlapping pages merged or removed and redirects in place for old routes | ✓ VERIFIED | `navbar.tsx` NAV_LINKS has exactly 5 items: Tổng quan, Danh mục, Huấn luyện, Nhật ký, Hệ thống. `/dashboard` redirects to `/` via both `next.config.ts` permanent redirect and `dashboard/page.tsx` client-side `router.replace("/")`. Home page includes top movers section merged from dashboard. |
| 2 | User's watchlist is stored in PostgreSQL — adding/removing tickers persists across browsers and devices without data loss | ✓ VERIFIED | Alembic migration 025 creates `user_watchlist` table with `symbol` column (String(10), unique). Backend API has full CRUD: `GET /api/watchlist`, `POST /api/watchlist` (add), `DELETE /api/watchlist/{symbol}` (remove). Frontend uses React Query hooks (`useWatchlist`, `useAddToWatchlist`, `useRemoveFromWatchlist`) calling server API — no localStorage for persistence. Ticker detail page wires add/remove mutations. |
| 3 | Existing localStorage watchlist data is automatically migrated to the database on first visit, with localStorage cleared after successful migration | ✓ VERIFIED | `store.ts` exports `migrateLocalWatchlist()` that reads `holo-watchlist` localStorage key, parses zustand persist format (`parsed.state.watchlist`), calls `POST /api/watchlist/migrate`, then removes localStorage key. `watchlist/page.tsx` calls `migrateLocalWatchlist()` in `useEffect` on mount. Backend `/migrate` endpoint bulk-adds symbols, skips duplicates, and returns enriched list. |
| 4 | Each ticker in the watchlist displays the latest AI signal score and buy/sell/hold recommendation alongside the ticker name | ✓ VERIFIED | Backend `_get_enriched_watchlist()` LEFT JOINs `UserWatchlist → Ticker → AIAnalysis` for latest combined analysis, returning `ai_signal`, `ai_score`, `signal_date` per item. `watchlist-table.tsx` renders a `signal` column that displays colored Badge with signal label (buy/sell/hold with TrendingUp/TrendingDown/Minus icons) and `{score}/10` numeric score from server data. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/alembic/versions/025_watchlist_web_migration.py` | Alembic migration for web watchlist | ✓ VERIFIED | 44 lines, `upgrade()` drops old table, creates new with symbol column, unique constraint. `downgrade()` restores old schema. Revision 025, down_revision 024. |
| `backend/app/models/user_watchlist.py` | Updated SQLAlchemy model with symbol column | ✓ VERIFIED | 27 lines, `UserWatchlist` with columns `id`, `symbol`, `created_at`. No `chat_id` or `ticker_id`. Programmatic check confirmed: `['id', 'symbol', 'created_at']`. |
| `backend/app/schemas/watchlist.py` | Pydantic schemas for watchlist API | ✓ VERIFIED | Exports `WatchlistItemResponse` (with ai_signal, ai_score, signal_date), `WatchlistAddRequest` (symbol 1-10 chars), `WatchlistMigrateRequest` (symbols list, max 50). |
| `backend/app/api/watchlist.py` | FastAPI router with CRUD + migrate + AI signal enrichment | ✓ VERIFIED | 156 lines, 5 functions: `_get_enriched_watchlist`, `get_watchlist`, `add_to_watchlist`, `remove_from_watchlist`, `migrate_watchlist`. Imports `UserWatchlist`, `Ticker`, `AIAnalysis`, `AnalysisType`. |
| `backend/app/api/router.py` | Watchlist router registered in main API router | ✓ VERIFIED | `watchlist_router` imported and included via `api_router.include_router(watchlist_router)`. |
| `frontend/src/components/navbar.tsx` | Reduced navigation with 5 items | ✓ VERIFIED | `NAV_LINKS` array has exactly 5 entries. Used in both desktop nav and mobile Sheet. |
| `frontend/next.config.ts` | Redirect from /dashboard to / | ✓ VERIFIED | Permanent redirect `/dashboard → /` configured in `redirects()`. |
| `frontend/src/lib/api.ts` | Watchlist API functions | ✓ VERIFIED | `WatchlistItem` interface + 4 functions: `fetchWatchlist`, `addWatchlistItem`, `removeWatchlistItem`, `migrateWatchlist`. All call correct API endpoints with proper HTTP methods. |
| `frontend/src/lib/hooks.ts` | React Query hooks for watchlist | ✓ VERIFIED | `useWatchlist` (query, 2min staleTime), `useAddToWatchlist` (mutation + invalidation), `useRemoveFromWatchlist` (mutation + invalidation). All import from `@/lib/api`. |
| `frontend/src/lib/store.ts` | localStorage migration logic, zustand store removed | ✓ VERIFIED | Zustand store completely removed. Only exports `migrateLocalWatchlist()` function. Reads `holo-watchlist`, parses, calls migrate API, clears localStorage. Try/catch around parse/migrate. |
| `frontend/src/components/watchlist-table.tsx` | Server-backed watchlist table with AI score display | ✓ VERIFIED | 300 lines, uses `useWatchlist()` hook, renders signal column with colored Badge + score. Remove button calls `removeMutation.mutate()`. No localStorage access. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `backend/app/api/watchlist.py` | `backend/app/models/user_watchlist.py` | SQLAlchemy query | ✓ WIRED | `from app.models.user_watchlist import UserWatchlist` — used in all 5 functions for SELECT/INSERT/DELETE. |
| `backend/app/api/watchlist.py` | `backend/app/models/ai_analysis.py` | JOIN for signal enrichment | ✓ WIRED | `from app.models.ai_analysis import AIAnalysis, AnalysisType` — LEFT JOIN in `_get_enriched_watchlist()` with subquery for max analysis_date. |
| `frontend/src/lib/hooks.ts` | `/api/watchlist` | fetchWatchlist in useWatchlist hook | ✓ WIRED | `useWatchlist` calls `fetchWatchlist` → `apiFetch("/watchlist")`. Mutations call `addWatchlistItem`/`removeWatchlistItem` → POST/DELETE to `/watchlist`. |
| `frontend/src/components/watchlist-table.tsx` | `frontend/src/lib/hooks.ts` | useWatchlist hook | ✓ WIRED | `import { useMarketOverview, useWatchlist, useRemoveFromWatchlist } from "@/lib/hooks"` — data consumed for rows, signal column, and remove button. |
| `frontend/src/lib/store.ts` | `/api/watchlist/migrate` | one-time migration on app mount | ✓ WIRED | `import { migrateWatchlist } from "@/lib/api"` called in `migrateLocalWatchlist()`. Triggered from `watchlist/page.tsx` via `useEffect`. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `watchlist-table.tsx` | `watchlistData` (via `useWatchlist`) | `GET /api/watchlist` → `_get_enriched_watchlist()` → SQLAlchemy LEFT JOIN query on `user_watchlist`, `tickers`, `ai_analyses` | Yes — real DB query with JOIN | ✓ FLOWING |
| `watchlist-table.tsx` | `watchItem.ai_signal` / `watchItem.ai_score` | `_get_enriched_watchlist()` → `AIAnalysis.signal` / `AIAnalysis.score` from LEFT JOIN | Yes — from `ai_analyses` table via JOIN, nullable for tickers without analysis | ✓ FLOWING |
| `navbar.tsx` | `NAV_LINKS` | Hardcoded constant array | N/A — static config, not dynamic data | ✓ N/A (config) |
| `home/page.tsx` | `topMovers` | `useMarketOverview()` → sorted/sliced market data | Yes — derived from real market API data | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| UserWatchlist model has correct columns | `python -c "from app.models.user_watchlist import UserWatchlist; print([c.name for c in UserWatchlist.__table__.columns])"` | `['id', 'symbol', 'created_at']` | ✓ PASS |
| Watchlist API module parses cleanly with expected functions | `python -c "import ast; ..."` on `backend/app/api/watchlist.py` | 5 functions: `_get_enriched_watchlist`, `get_watchlist`, `add_to_watchlist`, `remove_from_watchlist`, `migrate_watchlist` | ✓ PASS |
| No chat_id in new model | `grep "chat_id" backend/app/models/user_watchlist.py` | Only in docstring ("No chat_id...needed") — column removed | ✓ PASS |
| No zustand store remaining | `grep "zustand\|create(\|useWatchlistStore" frontend/src/lib/store.ts` | No matches — zustand fully removed | ✓ PASS |
| No localStorage references in E2E tests | `grep "localStorage" frontend/e2e/` | Only 1 comment line noting "no localStorage" in `interact-watchlist.spec.ts` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| NAV-01 | 49-02 | Giảm navigation từ 7 items xuống 4-5 items, gộp các trang có nội dung trùng lặp | ✓ SATISFIED | Navigation reduced to 5 items. Dashboard merged into home (top movers section). `/dashboard` redirects to `/`. |
| NAV-02 | 49-01, 49-02 | Migrate watchlist từ localStorage sang PostgreSQL (Alembic migration + REST API + React Query hooks) | ✓ SATISFIED | Alembic migration 025 creates new schema. Full REST API (4 endpoints). React Query hooks replace zustand store. localStorage migration bridge. |
| NAV-03 | 49-01, 49-02 | Watchlist hiển thị AI signal score/recommendation bên cạnh mỗi mã trong danh sách | ✓ SATISFIED | Backend enriches via LEFT JOIN to `ai_analyses`. Frontend renders signal Badge + `{score}/10` in dedicated column. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `frontend/src/app/dashboard/page.tsx` | 11 | `return null` | ℹ️ Info | By design — redirect page renders nothing while `router.replace("/")` executes. Not a stub. |
| `frontend/src/components/watchlist-table.tsx` | 47 | `return []` | ℹ️ Info | Guard clause in `useMemo` when data hasn't loaded yet. Correct pattern — data flows in via `useWatchlist()`. Not a stub. |

No 🛑 Blockers or ⚠️ Warnings found.

### Human Verification Required

### 1. Navigation Visual Flow

**Test:** Navigate between all 5 nav items in desktop and mobile (hamburger menu)
**Expected:** Each link navigates correctly, active state highlights current page, mobile sheet closes on selection
**Why human:** Visual styling, active state behavior, and mobile sheet interaction need browser testing

### 2. Dashboard Redirect Smoothness

**Test:** Navigate directly to `/dashboard` URL
**Expected:** Immediate redirect to `/` with no flash of old dashboard content, top movers visible on home page
**Why human:** Redirect timing, visual transition quality

### 3. Cross-Device Watchlist Persistence

**Test:** Add tickers to watchlist in one browser, open another browser/incognito and check watchlist
**Expected:** Same tickers appear, add/remove in one reflects in the other after refresh
**Why human:** Requires running server with real database, multi-browser testing

### 4. localStorage Migration

**Test:** Set `localStorage.setItem("holo-watchlist", JSON.stringify({state:{watchlist:["VNM","FPT"]}}))` then navigate to /watchlist
**Expected:** VNM and FPT appear in server-backed watchlist, `holo-watchlist` key removed from localStorage
**Why human:** Requires manual localStorage manipulation and observing one-time migration behavior

### 5. AI Signal Display Quality

**Test:** View watchlist with tickers that have combined AI analysis
**Expected:** Colored badge (green for buy, red for sell, neutral for hold) with directional icon and `X/10` score renders alongside each ticker
**Why human:** Visual quality of badge colors, icons, score formatting needs human verification

### Gaps Summary

No automated gaps found. All 4 success criteria are structurally verified — code exists, is substantive, is wired, and data flows through real database queries. 5 human verification items remain to confirm visual and behavioral quality in a running application.

---

_Verified: 2026-04-24T14:30:38Z_
_Verifier: the agent (gsd-verifier)_

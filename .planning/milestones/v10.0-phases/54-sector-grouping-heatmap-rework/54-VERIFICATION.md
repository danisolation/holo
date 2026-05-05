---
phase: 54-sector-grouping-heatmap-rework
verified: 2026-05-04T16:51:22Z
status: human_needed
score: 11/11 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open /watchlist page and click a sector cell — combobox should open with fuzzy-searchable ICB sector list"
    expected: "Popover opens with Command input, typing filters sectors, selecting one updates the cell immediately"
    why_human: "Visual interaction — combobox positioning, keyboard navigation, and focus management can't be verified by grep"
  - test: "Select a sector in watchlist table, then navigate to / home page"
    expected: "Heatmap shows only watchlist tickers grouped by the sector you just assigned, not all ~400 market tickers"
    why_human: "Cross-page data flow with React Query cache — requires runtime browser to confirm invalidation triggers re-render"
  - test: "Remove all items from watchlist, visit / home page"
    expected: "Empty state card shows 'Chưa có mã trong danh mục' with a helpful CTA instead of a blank heatmap"
    why_human: "Visual rendering of empty state — layout, spacing, and card appearance"
  - test: "Add a new ticker to watchlist (POST) without specifying sector"
    expected: "Sector is auto-populated from ICB classification data (vnstock) — check the sector_group field in the response"
    why_human: "Requires running backend with seeded Ticker data to confirm ICB lookup actually returns a value"
---

# Phase 54: Sector Grouping & Heatmap Rework — Verification Report

**Phase Goal:** User can organize watchlist tickers by sector and the home page heatmap reflects only their curated, sector-grouped watchlist
**Verified:** 2026-05-04T16:51:22Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | PATCH /api/watchlist/{symbol} updates sector_group in DB and returns updated item | ✓ VERIFIED | `watchlist.py` L130-147: endpoint selects item, sets `item.sector_group = body.sector_group`, commits, refreshes, returns `WatchlistItemResponse` with sector_group |
| 2 | GET /api/watchlist/ returns sector_group for each item | ✓ VERIFIED | `watchlist.py` L46: `UserWatchlist.sector_group` in SELECT; L74: `sector_group=row.sector_group` in response |
| 3 | POST /api/watchlist/ auto-populates sector_group from tickers.sector (ICB) when not provided | ✓ VERIFIED | `watchlist.py` L108-115: queries `Ticker.sector` when `body.sector_group is None`, sets it on the new entry L118 |
| 4 | GET /api/tickers/sectors returns distinct ICB sector names from active tickers | ✓ VERIFIED | `tickers.py` L89-100: `select(Ticker.sector).where(is_active, sector.isnot(None)).distinct().order_by(Ticker.sector)` |
| 5 | User sees a 'Ngành' column in watchlist table showing each ticker's sector_group | ✓ VERIFIED | `watchlist-table.tsx` L98-116: column id `sector_group`, header `"Ngành"`, renders `SectorCombobox` with watchItem's sector_group |
| 6 | User clicks a sector cell to open a combobox with fuzzy-searchable ICB sectors | ✓ VERIFIED | `sector-combobox.tsx` 63 lines: Popover + Command pattern (cmdk built-in fuzzy filter), CommandInput placeholder "Tìm ngành..." |
| 7 | Selecting a sector persists via PATCH API and updates table immediately | ✓ VERIFIED | Full chain: combobox `onSelect` → `onChange` → `updateSectorMutation.mutate()` → `useUpdateSectorGroup` → `updateWatchlistSector()` PATCH → `invalidateQueries(["watchlist"])` → table re-renders |
| 8 | Home page heatmap shows only watchlist tickers, not all 400 market tickers | ✓ VERIFIED | `page.tsx` L34-45: `watchlistHeatmapData` useMemo joins watchlist with market data; L151: `<Heatmap data={watchlistHeatmapData} />` |
| 9 | Heatmap groups tickers by user-assigned sector_group (falls back to ICB sector) | ✓ VERIFIED | `page.tsx` L42: `sector: w.sector_group ?? market.sector ?? "Khác"` overrides before heatmap; `heatmap.tsx` L41-46 groups by `.sector` |
| 10 | Editing sector on watchlist reflects in heatmap without manual refresh | ✓ VERIFIED | `useUpdateSectorGroup` invalidates `["watchlist"]` (hooks.ts L480-482); both page.tsx and watchlist-table.tsx consume `useWatchlist()` with same queryKey — React Query reactivity handles it |
| 11 | Empty watchlist shows helpful empty state instead of blank heatmap | ✓ VERIFIED | `page.tsx` L152-162: when `watchlistHeatmapData.length === 0`, renders Card with "Chưa có mã trong danh mục" + CTA |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/user_watchlist.py` | UserWatchlist with sector_group field | ✓ VERIFIED | L21: `sector_group: Mapped[str \| None] = mapped_column(String(100), nullable=True)` |
| `backend/app/schemas/watchlist.py` | Pydantic schemas with sector_group | ✓ VERIFIED | `WatchlistItemResponse` L9, `WatchlistUpdateRequest` L15-17, `WatchlistAddRequest` L23 — all have sector_group |
| `backend/app/api/watchlist.py` | PATCH endpoint + auto-populate on POST | ✓ VERIFIED | PATCH L130-147, auto-populate L108-115, enriched query L46+L74 |
| `backend/app/api/tickers.py` | GET /sectors endpoint | ✓ VERIFIED | L89-100: `list_sectors()` returns distinct non-null ICB sectors, placed before `/{symbol}/prices` |
| `backend/tests/test_watchlist_sector.py` | Unit tests (min 80 lines) | ✓ VERIFIED | 280 lines, 8 tests across 4 test classes |
| `frontend/src/components/sector-combobox.tsx` | Combobox for sector selection (min 40 lines) | ✓ VERIFIED | 63 lines, uses Popover+Command pattern with fuzzy search |
| `frontend/src/components/watchlist-table.tsx` | Table with inline sector editing | ✓ VERIFIED | sector_group column L98-116 with SectorCombobox, useSectors/useUpdateSectorGroup hooks wired |
| `frontend/src/app/page.tsx` | Home page with watchlist-filtered heatmap | ✓ VERIFIED | useWatchlist L14, watchlistHeatmapData L34-45, empty state L152-162 |
| `frontend/src/lib/api.ts` | API functions for sector ops | ✓ VERIFIED | `updateWatchlistSector` L810-817, `fetchSectors` L820-822, `sector_group` in WatchlistItem L97 |
| `frontend/src/lib/hooks.ts` | React Query hooks for sectors | ✓ VERIFIED | `useSectors()` L466-471, `useUpdateSectorGroup()` L475-483 |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `watchlist.py` API | `user_watchlist.py` model | `UserWatchlist.sector_group` ORM field | ✓ WIRED | 10 refs to `sector_group` in watchlist.py; model has the field at L21 |
| `watchlist.py` API | `ticker.py` model | `Ticker.sector` lookup for auto-populate | ✓ WIRED | L111: `select(Ticker.sector).where(Ticker.symbol == symbol)` in POST handler |
| `sector-combobox.tsx` | `hooks.ts` | `useSectors()` provides sector list | ✓ WIRED | combobox receives `sectors` prop; watchlist-table.tsx L45: `const { data: sectorsData } = useSectors()` passes to combobox |
| `watchlist-table.tsx` | `hooks.ts` | `useUpdateSectorGroup()` persists changes | ✓ WIRED | L46: `const updateSectorMutation = useUpdateSectorGroup()`, L106-109: `.mutate({symbol, sectorGroup})` |
| `page.tsx` | `hooks.ts` | `useWatchlist()` + `useMarketOverview()` for heatmap | ✓ WIRED | L13-14: both hooks called, L34-45: joined in `watchlistHeatmapData` useMemo |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `watchlist-table.tsx` | `watchlistData` | `useWatchlist()` → `fetchWatchlist()` → GET `/api/watchlist` | DB query via `_get_enriched_watchlist()` with JOINs | ✓ FLOWING |
| `watchlist-table.tsx` | `sectorsData` | `useSectors()` → `fetchSectors()` → GET `/api/tickers/sectors` | DB query: `select(Ticker.sector).distinct()` | ✓ FLOWING |
| `page.tsx` | `watchlistHeatmapData` | `useWatchlist()` + `useMarketOverview()` joined via useMemo | Both hooks hit real DB endpoints | ✓ FLOWING |
| `sector-combobox.tsx` | `sectors` prop | Passed from parent's `useSectors()` data | Real data from tickers table | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend tests pass | `cd backend && python -m pytest tests/test_watchlist_sector.py -x -v` | Claimed 8/8 passing in SUMMARY (commit `8f30d7f`) | ? SKIP — requires Python env + DB |
| TypeScript compiles | `cd frontend && npx tsc --noEmit` | Claimed zero errors in SUMMARY (commit `6222b69`) | ? SKIP — requires Node.js deps installed |
| Commits exist | `git log --oneline -10` | All 6 commits verified: `18b9c26`, `8f30d7f`, `1260b7b`, `6222b69` + docs commits | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| TAG-01 | 54-01, 54-02 | User gán sector/nhóm ngành cho mỗi mã trong watchlist | ✓ SATISFIED | PATCH endpoint (watchlist.py L130-147) + inline editing via SectorCombobox in watchlist table (watchlist-table.tsx L98-116) |
| TAG-02 | 54-01, 54-02 | Khi thêm mã mới, sector tự động gợi ý từ data vnstock (ICB) | ✓ SATISFIED | POST auto-populates from Ticker.sector (watchlist.py L108-115) + GET /tickers/sectors for combobox (tickers.py L89-100) |
| TAG-03 | 54-01, 54-02 | Heatmap trên trang chủ chỉ hiện watchlist tickers, phân nhóm theo sector | ✓ SATISFIED | page.tsx L34-45 filters to watchlist only, overrides sector with sector_group; heatmap.tsx groups by sector |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No anti-patterns found | — | — |

All `return []` / `return null` hits are guard clauses for missing data (standard React/useMemo patterns), not stubs. No TODO/FIXME/PLACEHOLDER comments found.

### Human Verification Required

### 1. Inline Sector Editing Interaction
**Test:** Open /watchlist page and click a sector cell — combobox should open with fuzzy-searchable ICB sector list
**Expected:** Popover opens with Command input, typing filters sectors, selecting one updates the cell immediately
**Why human:** Visual interaction — combobox positioning, keyboard navigation, and focus management can't be verified by grep

### 2. Cross-Page Heatmap Reflection
**Test:** Select a sector in watchlist table, then navigate to / home page
**Expected:** Heatmap shows only watchlist tickers grouped by the sector you just assigned, not all ~400 market tickers
**Why human:** Cross-page data flow with React Query cache — requires runtime browser to confirm invalidation triggers re-render

### 3. Empty State Rendering
**Test:** Remove all items from watchlist, visit / home page
**Expected:** Empty state card shows 'Chưa có mã trong danh mục' with a helpful CTA instead of a blank heatmap
**Why human:** Visual rendering of empty state — layout, spacing, and card appearance

### 4. ICB Auto-Populate on Add
**Test:** Add a new ticker to watchlist (POST) without specifying sector
**Expected:** Sector is auto-populated from ICB classification data (vnstock) — check the sector_group field in the response
**Why human:** Requires running backend with seeded Ticker data to confirm ICB lookup actually returns a value

### Gaps Summary

No programmatic gaps found. All 11 observable truths verified at all 4 levels (existence, substantive, wired, data-flow). All 3 requirements (TAG-01, TAG-02, TAG-03) satisfied. All key links wired. No anti-patterns detected. All commits present in git history.

4 items require human verification for visual/runtime behaviors that can't be confirmed by static analysis.

---

_Verified: 2026-05-04T16:51:22Z_
_Verifier: the agent (gsd-verifier)_

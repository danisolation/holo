---
phase: 45-coach-dashboard-pick-performance
verified: 2026-04-23T11:30:00Z
status: human_needed
score: 3/3 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open /coach in browser and verify the 4-section vertical layout renders correctly: performance cards → today's picks → open trades → pick history"
    expected: "All 4 sections visible in vertical scroll, performance cards in a 4-column grid (2 on mobile), pick history table with filter buttons and pagination"
    why_human: "Visual layout verification — code analysis confirms wiring but can't confirm CSS renders correctly in browser"
  - test: "Verify outcome badges display with correct colors: Thắng (green), Thua (red), Hết hạn (outline/neutral), Đang theo dõi (blue)"
    expected: "Each badge type renders with the correct color scheme and is readable in both light and dark mode"
    why_human: "Color rendering and dark mode compatibility need visual confirmation"
  - test: "Verify pick history table is responsive — shrink browser width to mobile size"
    expected: "Table scrolls horizontally with overflow-x-auto, filter buttons wrap, pagination controls remain accessible"
    why_human: "Mobile responsive behavior requires real browser viewport testing"
---

# Phase 45: Coach Dashboard & Pick Performance — Verification Report

**Phase Goal:** The /coach page becomes the daily landing page — displaying today's picks, open trades, performance metrics, and full pick history with actual outcome tracking for every pick
**Verified:** 2026-04-23T11:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | The /coach page displays today's picks, currently open trades, and a performance summary all on a single page | ✓ VERIFIED | `coach/page.tsx` renders 4 sections: PickPerformanceCards (L69), today's picks grid (L71-112), open trades via TradesTable (L119-142), PickHistoryTable (L144-145) — all in `space-y-8` vertical layout |
| 2 | Pick history shows actual outcomes for every pick — whether entry was hit, SL was hit, TP was hit, and return after N days — including picks the user didn't trade | ✓ VERIFIED | `compute_pick_outcome()` pure function determines LOSER/WINNER/EXPIRED/PENDING from DailyPrice data (pick_service.py:32-99). `get_pick_history()` returns paginated picks with outcome badges, return %, days_held, has_trades flag via LEFT JOIN (pick_service.py:640-710). History tracks ALL "picked" status picks, has_trades distinguishes traded from non-traded. |
| 3 | Performance cards display win rate, total P&L, average risk-to-reward ratio, and current winning/losing streak | ✓ VERIFIED | `PickPerformanceCards` renders 4 cards: win rate (color-coded >50%/<50%), total P&L (formatted VND with sign), avg R:R as "1:N", streak with 🔥/❄️ icons (pick-performance-cards.tsx:89-133). Backend `get_performance_stats()` computes all 4 from DB queries (pick_service.py:712-811). |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/alembic/versions/021_pick_outcome_columns.py` | Migration adding 6 outcome columns + partial index | ✓ VERIFIED | Adds pick_outcome, days_held, hit_stop_loss, hit_take_profit_1, hit_take_profit_2, actual_return_pct + partial index `ix_daily_picks_outcome_pending` |
| `backend/app/models/daily_pick.py` | PickOutcome enum + 6 new mapped columns | ✓ VERIFIED | PickOutcome(PENDING/WINNER/LOSER/EXPIRED) at L23-28; 6 new columns at L49-54 |
| `backend/app/services/pick_service.py` | compute_pick_outcome, compute_pick_outcomes, get_performance_stats, get_pick_history | ✓ VERIFIED | Pure function L32-99, batch processor L813-882, performance stats L712-811, paginated history L640-710 |
| `backend/app/schemas/picks.py` | PickHistoryItem, PickHistoryListResponse, PickPerformanceResponse | ✓ VERIFIED | 3 schemas at L50-82 with all required fields |
| `backend/app/api/picks.py` | GET /picks/history, GET /picks/performance | ✓ VERIFIED | History endpoint L33-48 with status whitelist + pagination cap; performance endpoint L51-57 |
| `backend/app/scheduler/jobs.py` | daily_pick_outcome_check job function | ✓ VERIFIED | Job at L595-607, calls PickService.compute_pick_outcomes() |
| `backend/app/scheduler/manager.py` | Chain outcome check after pick generation | ✓ VERIFIED | Chain at L151-160, added to _JOB_NAMES dict at L43-44 |
| `backend/tests/test_pick_outcome.py` | Unit tests for outcome computation + schema validation | ✓ VERIFIED | 13 tests: 10 outcome scenarios + 3 schema validations. All 13 pass. |
| `frontend/src/components/pick-performance-cards.tsx` | 4-card performance grid | ✓ VERIFIED | 135 lines. Win rate, P&L, R:R, streak cards with loading/error/data states and aria-labels |
| `frontend/src/components/pick-history-table.tsx` | Paginated history table with outcome badges and filters | ✓ VERIFIED | 253 lines. 10 columns, 5 filter options (incl. expired), pagination, loading/error/empty states |
| `frontend/src/app/coach/page.tsx` | Unified 4-section coach page | ✓ VERIFIED | 161 lines. Sections 0-4: header, performance cards, today's picks, open trades (conditional), pick history |
| `frontend/src/lib/api.ts` | PickPerformanceResponse, PickHistoryItem, PickHistoryResponse types + fetch functions | ✓ VERIFIED | 3 interfaces at L482-511; fetchPickHistory L519-529; fetchPickPerformance L532-533 |
| `frontend/src/lib/hooks.ts` | usePickHistory, usePickPerformance hooks | ✓ VERIFIED | usePickHistory L313-318 with page+status queryKey; usePickPerformance L321-326 with 5min staleTime |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| PickPerformanceCards | /api/picks/performance | usePickPerformance → fetchPickPerformance → apiFetch | ✓ WIRED | Hook calls fetch function which calls `/picks/performance`; API route calls `PickService.get_performance_stats()` |
| PickHistoryTable | /api/picks/history | usePickHistory → fetchPickHistory → apiFetch | ✓ WIRED | Hook passes page+status; fetch builds query params; API route validates + delegates to `PickService.get_pick_history()` |
| coach/page.tsx | PickPerformanceCards | import + JSX render | ✓ WIRED | Import at L15, rendered at L69 |
| coach/page.tsx | PickHistoryTable | import + JSX render | ✓ WIRED | Import at L16, rendered at L145 |
| Scheduler chain | compute_pick_outcomes | manager.py event handler → jobs.py → PickService | ✓ WIRED | Chain triggers at L151-160 after pick generation; job calls service.compute_pick_outcomes() |
| compute_pick_outcomes | compute_pick_outcome | Service method → pure function | ✓ WIRED | Service at L854 calls pure function with DailyPrice data; updates pick model fields at L862-877 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| PickPerformanceCards | stats (usePickPerformance) | GET /picks/performance → `get_performance_stats()` | Yes — DB queries: `func.count(DailyPick.id)`, `func.sum(Trade.net_pnl)`, `select(DailyPick.actual_return_pct)` | ✓ FLOWING |
| PickHistoryTable | data (usePickHistory) | GET /picks/history → `get_pick_history()` | Yes — DB JOIN query: `select(DailyPick, Ticker.symbol, traded_picks_sq)` with pagination | ✓ FLOWING |
| Coach page today's picks | picksData (useDailyPicks) | Existing Phase 43 hook | Yes — reuses existing working data flow | ✓ FLOWING |
| Coach page open trades | tradesData (useTrades) | Existing Phase 44 hook with side="BUY" | Yes — reuses existing working data flow with filter | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Backend tests pass | `pytest tests/test_pick_outcome.py -v` | 13/13 passed in 2.18s | ✓ PASS |
| TypeScript compiles clean | `npx tsc --noEmit` | Exit code 0, no errors | ✓ PASS |
| Migration file exists with correct structure | File check: `021_pick_outcome_columns.py` | 6 columns + partial index in upgrade(), clean downgrade() | ✓ PASS |
| API endpoint status validation | Code check: `_VALID_STATUSES = {"all", "winner", "loser", "expired", "pending"}` with 422 on invalid | Whitelist present at picks.py:20, validated at L40-44 | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-----------|-------------|--------|----------|
| CDSH-01 | 45-02 | /coach hiển thị picks hôm nay, trades đang mở, và performance summary trên 1 trang | ✓ SATISFIED | Coach page has all 4 sections in single-page vertical scroll layout |
| CDSH-02 | 45-01, 45-02 | Lịch sử picks với kết quả thực tế (entry hit?, SL hit?, TP hit?, return sau N ngày) — track TẤT CẢ picks kể cả không trade | ✓ SATISFIED | Backend outcome computation + PickHistoryTable with outcome badges, return %, days held, has_trades indicator. All picks tracked (picked status filter, not just traded) |
| CDSH-03 | 45-01, 45-02 | Performance cards: win rate, total P&L, average R:R, streak hiện tại | ✓ SATISFIED | PickPerformanceCards with all 4 metrics, color-coded, with loading/error states |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| backend/app/scheduler/jobs.py | 595-607 | `daily_pick_outcome_check` missing JobExecutionService tracking + try/except (unlike every other job in codebase) | ⚠️ Warning | Health dashboard won't show this job's status; failures silent. Functional but inconsistent with codebase conventions. |
| backend/app/services/pick_service.py | 68, 79, 91 | `compute_pick_outcome` divides by `entry_price` without zero guard | ⚠️ Warning | Edge case: corrupt entry_price=0 causes ZeroDivisionError. Pick generation already filters entry_price<=0, so low real-world risk. |

No blockers found. No TODOs, FIXMEs, placeholders, or console.logs in any Phase 45 file.

### Human Verification Required

### 1. Four-Section Dashboard Layout

**Test:** Open /coach in browser and verify the vertical layout renders: performance cards (4-card grid) → today's picks → open trades (if any BUY trades exist) → pick history table with filters and pagination
**Expected:** All sections visible in vertical scroll with `space-y-8` spacing, performance cards in responsive 2-col (mobile) / 4-col (desktop) grid
**Why human:** CSS layout and responsive grid behavior can't be verified by code inspection alone

### 2. Outcome Badge Colors

**Test:** View pick history with a mix of outcomes (winner/loser/expired/pending) in both light and dark mode
**Expected:** Thắng = green badge, Thua = red badge, Hết hạn = outline/neutral badge, Đang theo dõi = blue badge — all readable in both modes
**Why human:** Tailwind color rendering and dark mode variant behavior needs visual confirmation

### 3. Pick History Table Responsiveness

**Test:** Shrink browser to mobile width (~375px) while viewing pick history table
**Expected:** Table scrolls horizontally via `overflow-x-auto`, filter buttons wrap in flex, pagination shows "Hiển thị X-Y / Z gợi ý" text with Trước/Sau buttons accessible
**Why human:** Responsive overflow behavior requires real viewport testing

### Gaps Summary

No gaps found. All 3 success criteria are fully verified at the code level:

1. **Single-page coach dashboard** — 4 sections wired with working data flows
2. **Pick history with outcomes** — Full backend outcome computation pipeline (pure function → batch processor → scheduler job → API endpoint) connected to frontend table with badges, return %, days held, and traded indicator
3. **Performance cards** — 4 metrics (win rate, P&L, R:R, streak) computed from real DB queries and rendered with proper formatting

The code review warnings (WR-01: missing job tracking, WR-02: entry_price=0 edge case) are quality improvements that don't block goal achievement. WR-03 (missing expired filter) was found resolved in the actual code.

---

_Verified: 2026-04-23T11:30:00Z_
_Verifier: the agent (gsd-verifier)_

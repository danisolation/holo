---
phase: 43-daily-picks-engine
verified: 2025-07-24T22:45:00Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Open /coach page in browser with live data"
    expected: "3-5 pick cards display with Vietnamese explanations, entry/SL/TP prices, position sizing text, and live WebSocket price badges"
    why_human: "Visual layout, responsive grid, card styling, and Vietnamese text rendering cannot be verified programmatically"
  - test: "Click Settings gear icon → change capital and risk level → save"
    expected: "Dialog opens, formatted capital input works, risk toggle buttons highlight, save updates profile and picks refresh with new sizing"
    why_human: "Form interaction UX, vi-VN number formatting display, mutation/invalidation cascade are runtime behaviors"
  - test: "Verify WebSocket live price updates on pick cards"
    expected: "Price badge updates in real-time with green ▲ or red ▼ P&L percentage"
    why_human: "Requires live WebSocket connection and market-hours data"
  - test: "Verify Gemini Vietnamese explanation quality"
    expected: "200-300 word explanation per pick covering technical + fundamental + sentiment, in friendly Vietnamese"
    why_human: "AI output quality and language correctness require human judgment"
---

# Phase 43: Daily Picks Engine Verification Report

**Phase Goal:** Each trading day, the app selects and displays 3-5 specific stock picks with entry/SL/TP, position sizing, and Vietnamese explanations — filtered for the user's capital and scored for safety
**Verified:** 2025-07-24T22:45:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User sees 3-5 daily stock picks on the /coach page, each with a Vietnamese explanation (200-300 words) combining technical, fundamental, and sentiment reasoning | ✓ VERIFIED | `/coach` page.tsx renders PickCard grid, PickService selects top 3-5 (lines 392-399), Gemini prompt enforces 200-300 word Vietnamese explanation with system instruction covering kỹ thuật + cơ bản + tâm lý |
| 2 | Every pick displays entry price, stop-loss, and take-profit level inherited from trading signal pipeline | ✓ VERIFIED | `extract_trading_plan()` reads from `raw_response.long_analysis.trading_plan` JSONB; PickCard renders "Giá vào", "Cắt lỗ", "Chốt lời 1/2", "R:R" in 2-column grid |
| 3 | Every pick shows position sizing: "Mua X cổ × Y đồng = Z VND (N% vốn)" based on capital and 100-share lot sizes | ✓ VERIFIED | `compute_position_sizing()` with 100-share lots, 30% cap; PickCard line 115-118 renders exact format `Mua {shares} cổ × {price}đ = {vnd} VND ({pct}% vốn)` |
| 4 | Picks filtered by affordability (1 lot minimum) and scored with safety bias — high-ATR, low-ADX, low-volume penalized | ✓ VERIFIED | `is_affordable()` checks `price*100 <= capital`; `compute_safety_score()` penalizes high ATR%, low ADX, low volume; 6 unit tests validate both |
| 5 | Below main picks, 5-10 "almost selected" tickers shown with one-line explanation of why not chosen | ✓ VERIFIED | `almost = candidates[:10]` after picked removed; `generate_rejection_reason()` generates Vietnamese 1-liner; AlmostSelectedList accordion renders "Mã suýt được chọn (N mã)" |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/daily_pick.py` | DailyPick SQLAlchemy model | ✓ VERIFIED | 50 lines, 16 columns including entry/SL/TP/sizing, PickStatus enum, unique constraint |
| `backend/app/models/user_risk_profile.py` | UserRiskProfile single-row table | ✓ VERIFIED | 29 lines, capital default 50M, risk_level default 3, broker_fee_pct 0.15 |
| `backend/app/schemas/picks.py` | Pydantic API schemas | ✓ VERIFIED | 44 lines, 4 schemas: DailyPickResponse, DailyPicksResponse, ProfileResponse, ProfileUpdate with validation |
| `backend/alembic/versions/019_daily_picks_tables.py` | Migration creating both tables | ✓ VERIFIED | 63 lines, creates daily_picks + user_risk_profile, inserts default profile row, has upgrade/downgrade |
| `backend/app/services/pick_service.py` | PickService with scoring/filtering/Gemini/persistence | ✓ VERIFIED | 593 lines (≥150 min), 7 pure functions + PickService class with 5 async methods, full DB queries |
| `backend/app/api/picks.py` | FastAPI router for picks + profile endpoints | ✓ VERIFIED | 60 lines, 4 endpoints: GET /picks/today, GET /picks/history, GET /profile, PUT /profile |
| `backend/app/scheduler/jobs.py` | daily_pick_generation job function | ✓ VERIFIED | Lines 561-589, creates PickService, calls generate_daily_picks, records job execution |
| `backend/app/scheduler/manager.py` | Job chain after hnx_upcom analysis | ✓ VERIFIED | Lines 139-148, chains daily_pick_generation after daily_hnx_upcom_analysis_triggered |
| `backend/tests/test_pick_service.py` | Test scaffold for all PICK requirements | ✓ VERIFIED | 17 tests across 7 classes, all GREEN (2.30s) |
| `frontend/src/app/coach/page.tsx` | /coach page assembling all components | ✓ VERIFIED | 80 lines, 4 states (loading/error/empty/success), responsive 3-col grid, profile settings |
| `frontend/src/components/pick-card.tsx` | PickCard + PickCardSkeleton components | ✓ VERIFIED | 165 lines, rank badge, score bar, explanation, price grid, position sizing block, live WebSocket price with P&L badge |
| `frontend/src/components/almost-selected-list.tsx` | Collapsible accordion for almost-selected | ✓ VERIFIED | 45 lines, Accordion with trigger "Mã suýt được chọn (N mã)", symbol + rejection reason rows |
| `frontend/src/components/profile-settings-card.tsx` | Profile settings dialog | ✓ VERIFIED | 183 lines, react-hook-form + zod, vi-VN formatted capital input, 5-button risk toggle with Vietnamese labels, Loader2 spinner |
| `frontend/src/components/navbar.tsx` | Updated navbar with coach link | ✓ VERIFIED | Line 26: `{ href: "/coach", label: "Huấn luyện" }` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `models/__init__.py` | `daily_pick.py` | `from app.models.daily_pick import DailyPick, PickStatus` | ✓ WIRED | Line 20 of __init__.py |
| `models/__init__.py` | `user_risk_profile.py` | `from app.models.user_risk_profile import UserRiskProfile` | ✓ WIRED | Line 21 of __init__.py |
| `api/picks.py` | `pick_service.py` | `PickService(session)` in endpoint handlers | ✓ WIRED | Lines 18, 28, 37, 50 of picks.py |
| `scheduler/jobs.py` | `pick_service.py` | `from app.services.pick_service import PickService` | ✓ WIRED | Line 572 of jobs.py |
| `api/router.py` | `api/picks.py` | `include_router(picks_router)` | ✓ WIRED | Lines 9, 17 of router.py |
| `scheduler/manager.py` | `scheduler/jobs.py` | job chain after hnx_upcom | ✓ WIRED | Lines 141-148 of manager.py |
| `coach/page.tsx` | `hooks.ts` | `useDailyPicks()` and `useProfile()` | ✓ WIRED | Lines 6, 13-14 of page.tsx |
| `hooks.ts` | `api.ts` | `fetchDailyPicks` and `fetchProfile` | ✓ WIRED | Lines 22-23, 229, 241 of hooks.ts |
| `pick-card.tsx` | `use-realtime-prices.ts` | `useRealtimePrices` hook for live price | ✓ WIRED | Lines 8, 16 of pick-card.tsx |
| `navbar.tsx` | `/coach` page | NAV_LINKS href "/coach" | ✓ WIRED | Line 26 of navbar.tsx |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `coach/page.tsx` | `picksData` | `useDailyPicks()` → `fetchDailyPicks()` → `GET /api/picks/today` → `PickService.get_today_picks()` → DB SELECT daily_picks JOIN tickers | Yes — real DB query with JOIN, WHERE, ORDER BY | ✓ FLOWING |
| `coach/page.tsx` | `profile` | `useProfile()` → `fetchProfile()` → `GET /api/profile` → `PickService.get_or_create_profile()` → DB SELECT user_risk_profile | Yes — real DB query | ✓ FLOWING |
| `pick-card.tsx` | `currentPrice` | `useRealtimePrices([symbol])` → WebSocket price feed | Yes — live WebSocket hook (pre-existing infrastructure) | ✓ FLOWING |
| `profile-settings-card.tsx` | `mutation.mutate(data)` | `useUpdateProfile()` → `updateProfile(data)` → `PUT /api/profile` → `PickService.update_profile()` → DB UPDATE | Yes — real DB mutation + query invalidation | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 17 pick service tests pass | `pytest tests/test_pick_service.py -v` | 17 passed in 2.30s | ✓ PASS |
| Composite scoring formula correct | Tested via `test_composite_scoring_formula` | confidence×0.4 + combined×0.3 + safety×0.3 verified | ✓ PASS |
| Affordability filter works | Tested via `TestCapitalFilter` (3 tests) | 100-share lot minimum correctly enforced | ✓ PASS |
| Safety scoring penalizes correctly | Tested via `TestSafetyScoring` (3 tests) | High ATR/low ADX/low volume produce low scores | ✓ PASS |
| Position sizing lot-aligned | Tested via `TestPositionSizing` (3 tests) | 100-share lots, 30% cap, minimum 1 lot | ✓ PASS |
| Rejection reasons Vietnamese | Tested via `TestAlmostSelected` (3 tests) | Generates RSI/volume/ADX/fallback Vietnamese reasons | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-----------|-------------|--------|----------|
| PICK-01 | 43-02 | App chọn 3-5 mã dựa trên composite scoring | ✓ SATISFIED | `generate_daily_picks()` computes composite scores, selects top 3-5, persists to DB |
| PICK-02 | 43-02 | Lọc theo vốn — chỉ mã mua được ≥1 lot (100 cổ) | ✓ SATISFIED | `is_affordable()` + capital filter at line 385; 3 unit tests confirm |
| PICK-03 | 43-02 | Ưu tiên an toàn — penalize ATR cao, ADX thấp, volume thấp | ✓ SATISFIED | `compute_safety_score()` with ATR/ADX/volume normalization; 3 unit tests confirm |
| PICK-04 | 43-02, 43-03 | Giải thích tiếng Việt 200-300 từ (kỹ thuật + cơ bản + sentiment) | ✓ SATISFIED | Gemini system instruction enforces 200-300 words, 4 content sections, Vietnamese language; PickCard renders explanation |
| PICK-05 | 43-01, 43-02 | Giá vào, SL, TP kế thừa từ trading signal pipeline | ✓ SATISFIED | `extract_trading_plan()` reads from `raw_response.long_analysis.trading_plan`; DailyPick model stores; PickCard renders |
| PICK-06 | 43-02, 43-03 | Position sizing "Mua X cổ × Y đồng = Z VND (N% vốn)" | ✓ SATISFIED | `compute_position_sizing()` with 100-share lots; PickCard renders exact format; 3 unit tests confirm |
| PICK-07 | 43-02, 43-03 | Top 5-10 mã suýt được chọn + 1 câu giải thích | ✓ SATISFIED | `almost = candidates[:10]`; `generate_rejection_reason()` generates Vietnamese 1-liner; AlmostSelectedList accordion renders |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `backend/app/api/picks.py` | 26 | Comment "Placeholder for Phase 45" | ℹ️ Info | Comment only — actual `get_pick_history` is fully implemented with real DB queries (lines 566-593 of pick_service.py) |

### Human Verification Required

### 1. Visual Coach Page Layout

**Test:** Open `/coach` in browser after picks have been generated
**Expected:** Responsive 3-column grid of pick cards with Vietnamese text, score bars, price grids, and position sizing blocks. Loading skeletons → data transition smooth. Empty/error states display correctly.
**Why human:** Visual layout, responsive behavior, card styling, and Vietnamese text rendering cannot be verified programmatically.

### 2. Profile Settings Dialog UX

**Test:** Click Settings gear icon → change capital (e.g., 30,000,000) and risk level → save → verify picks refresh
**Expected:** Dialog opens, capital input shows vi-VN formatted number (30.000.000), risk toggle buttons highlight selected level with Vietnamese label, save triggers spinner then closes dialog, pick cards update position sizing.
**Why human:** Form interaction UX, vi-VN number formatting display, and mutation/invalidation cascade are runtime behaviors.

### 3. WebSocket Live Price on Pick Cards

**Test:** View pick cards during market hours with WebSocket connected
**Expected:** Live price updates with color-coded P&L badge (green ▲ for gain, red ▼ for loss), aria-live announces changes.
**Why human:** Requires live WebSocket connection and real-time price data.

### 4. Gemini Vietnamese Explanation Quality

**Test:** Review generated explanations for 3-5 picks
**Expected:** 200-300 word Vietnamese explanation per pick covering technical indicators (RSI, MACD), fundamentals (P/E, ROE), and market sentiment. Friendly tone, specific numbers from data.
**Why human:** AI output quality, language correctness, and pedagogical clarity require human judgment.

### Gaps Summary

No automated gaps found. All 5 roadmap success criteria verified through artifact existence, substantive implementation, wiring verification, data-flow tracing, and 17 passing unit tests. All 7 PICK requirements (PICK-01 through PICK-07) are satisfied with full backend scoring engine, API endpoints, scheduler job chain, and frontend /coach page.

4 items require human verification: visual layout, profile dialog UX, WebSocket live prices, and Gemini explanation quality.

---

_Verified: 2025-07-24T22:45:00Z_
_Verifier: the agent (gsd-verifier)_

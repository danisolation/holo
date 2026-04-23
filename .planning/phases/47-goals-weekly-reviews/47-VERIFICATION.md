---
phase: 47-goals-weekly-reviews
verified: 2026-04-23T20:15:00Z
status: human_needed
score: 3/3
overrides_applied: 0
human_verification:
  - test: "Set a monthly profit target via the coach dashboard dialog, verify progress bar renders with correct color and actual/target values"
    expected: "Dialog opens, validates input (min 100k, max 1B), saves goal, progress bar shows actual P&L vs target with green/amber/red coloring"
    why_human: "Visual layout, progress bar rendering, color accuracy, and dialog UX flow cannot be verified programmatically"
  - test: "When a weekly risk prompt is pending, verify the prompt card appears with 3 buttons and responds correctly"
    expected: "Card shows 'Tuần này bạn muốn giao dịch thế nào?' with cautious/unchanged/aggressive buttons, boundary guards disable at risk 1 or 5, response updates risk level"
    why_human: "Button states, loading spinners, conditional card visibility, and risk level update feedback are visual behaviors"
  - test: "View the AI-generated weekly review card on the coach dashboard"
    expected: "Collapsible card shows Vietnamese summary text, green good highlights, red bad highlights, suggestions list, and stats footer (trades/wins/PnL)"
    why_human: "Vietnamese text rendering, collapsible interaction, color-coded highlights, and overall layout quality need visual confirmation"
  - test: "Verify Section 5 placement between pick history and behavior insights on /coach"
    expected: "Goals & Reviews section ('Mục tiêu & Nhận xét') appears after pick history table and before behavior insights section"
    why_human: "Page layout ordering and section spacing are visual properties"
---

# Phase 47: Goals & Weekly Reviews Verification Report

**Phase Goal:** User sets monthly profit targets, tracks progress visually, and receives AI-generated weekly coaching reviews with risk tolerance adjustments
**Verified:** 2026-04-23T20:15:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can set a monthly profit target, and a progress bar on the coach dashboard shows real-time tracking of actual P&L toward that goal | ✓ VERIFIED | `POST /api/goals` creates/replaces goal (GoalCreate validates target_pnl>0, ≤1B). `GET /api/goals/current` returns GoalResponse with computed actual_pnl (SUM of SELL trades net_pnl) and progress_pct/progress_color. MonthlyGoalCard renders 3-color progress bar (`role="progressbar"`) with actual/target display. SetGoalDialog provides create/edit flow. Full data path: useCurrentGoal → fetchCurrentGoal → /goals/current → GoalService.get_current_goal → _compute_actual_pnl |
| 2 | Each week the app prompts: "Bạn muốn thận trọng hơn hay mạo hiểm hơn?" — the user's response adjusts the risk level for the following week | ✓ VERIFIED | Monday 8:00 AM cron job `create_weekly_risk_prompt` creates pending prompt. WeeklyPromptCard shows 3 buttons (cautious/unchanged/aggressive) with boundary guards (disabled at risk 1 or 5). `POST /api/goals/weekly-prompt/{id}/respond` validates Literal response, calls `respond_to_prompt()` which computes delta via `clamp_risk_level()` and updates `UserRiskProfile.risk_level`. Cache invalidation includes `["profile"]` key. Full data path: useWeeklyPrompt → fetchWeeklyPrompt → /goals/weekly-prompt → GoalService.get_pending_prompt |
| 3 | Every Sunday, an AI-generated weekly performance review summarizes the week in Vietnamese, highlights good and bad trading habits, and suggests specific improvements | ✓ VERIFIED | Sunday 21:00 cron job + chaining from `weekly_behavior_analysis` (Sun 20:00). `generate_review()` gathers trades (with ticker symbol resolution via JOIN), habits (with ticker lookup), picks, risk level, and goal progress. `build_review_prompt()` produces Vietnamese text. Gemini called with `WeeklyReviewOutput` schema and Vietnamese system instruction. 3-stage fallback (parsed → low-temp → manual JSON). Idempotency guard prevents duplicates. WeeklyReviewCard renders summary_text, green good/red bad highlights, suggestions list, and stats footer |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/alembic/versions/023_goals_weekly_reviews.py` | Migration for 3 tables | ✓ VERIFIED | Creates trading_goals, weekly_prompts, weekly_reviews with indexes (70 lines) |
| `backend/app/models/trading_goal.py` | TradingGoal ORM model | ✓ VERIFIED | 29 lines, BigInteger PK, Numeric(18,2) target_pnl, Date month, String status |
| `backend/app/models/weekly_prompt.py` | WeeklyPrompt ORM model | ✓ VERIFIED | 29 lines, risk_level_before/after, nullable response, Date week_start |
| `backend/app/models/weekly_review.py` | WeeklyReview ORM model | ✓ VERIFIED | 34 lines, Text summary_text, JSONB highlights/suggestions, trade stats |
| `backend/app/schemas/goals.py` | Pydantic schemas | ✓ VERIFIED | 7 schemas: GoalCreate(gt=0, le=1B), GoalResponse, GoalHistoryResponse, WeeklyPromptResponse, WeeklyPromptRespondRequest(Literal), WeeklyReviewResponse, WeeklyReviewHistoryResponse |
| `backend/app/services/goal_service.py` | GoalService with pure functions + Gemini | ✓ VERIFIED | 630+ lines, 4 pure functions, GoalService with 10 async methods, 3-stage Gemini fallback, idempotency guard, ticker symbol resolution |
| `backend/app/api/goals.py` | 7 API endpoints | ✓ VERIFIED | 190 lines, POST /goals, GET /current, GET /history, GET /weekly-prompt, POST /weekly-prompt/{id}/respond, GET /weekly-review, GET /weekly-reviews |
| `backend/app/scheduler/jobs.py` | 2 new job functions | ✓ VERIFIED | create_weekly_risk_prompt (line 723) and generate_weekly_review (line 756) with JobExecutionService tracking |
| `backend/app/scheduler/manager.py` | Job registration + chaining | ✓ VERIFIED | 3 _JOB_NAMES entries (lines 48-50), chaining at line 177, 2 cron registrations at lines 281/297 |
| `backend/tests/test_goal_service.py` | 25+ unit tests | ✓ VERIFIED | 148 lines, 4 test classes, covers compute_goal_progress (10 tests), clamp_risk_level (7 tests), build_review_prompt (3 tests), parse_review_response (5 tests) |
| `frontend/src/lib/api.ts` | API types + fetch functions | ✓ VERIFIED | 3 interfaces (GoalResponse, WeeklyPromptResponse, WeeklyReviewResponse) + 5 fetch functions using apiFetch pattern |
| `frontend/src/lib/hooks.ts` | React Query hooks | ✓ VERIFIED | 5 hooks: useCurrentGoal, useSetGoal, useWeeklyPrompt, useRespondWeeklyPrompt, useLatestReview with cache invalidation |
| `frontend/src/components/monthly-goal-card.tsx` | Progress bar card | ✓ VERIFIED | 146 lines, 4 states (loading/error/no-goal/goal-set), 3-color progress bar with role="progressbar", SetGoalDialog integration |
| `frontend/src/components/set-goal-dialog.tsx` | Goal setting dialog | ✓ VERIFIED | 145 lines, validation (100k min, 1B max), loading/error states, form reset on open, Enter key submit |
| `frontend/src/components/weekly-prompt-card.tsx` | Risk prompt card | ✓ VERIFIED | 123 lines, conditional render (null when no pending), 3 buttons with boundary guards, Loader2 on submit |
| `frontend/src/components/weekly-review-card.tsx` | Weekly review card | ✓ VERIFIED | 147 lines, collapsible with aria-expanded, Vietnamese prose, green good / red bad highlights, suggestions, stats footer |
| `frontend/src/app/coach/page.tsx` | Coach page Section 5 | ✓ VERIFIED | Lines 23-25: imports, Lines 157-163: Section 5 "Mục tiêu & Nhận xét" with all 3 components |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `goals.py` API | `goal_service.py` | `GoalService(session)` per endpoint | ✓ WIRED | Every endpoint creates GoalService(session) within async_session context |
| `router.py` | `goals.py` | `api_router.include_router(goals_router)` | ✓ WIRED | Line 12: import, Line 23: include_router |
| `manager.py` | `jobs.py` | `scheduler.add_job` for Mon + Sun jobs | ✓ WIRED | Lines 281-308: CronTrigger Mon 8:00 + Sun 21:00 |
| `manager.py` | `_on_job_executed` | `weekly_behavior_analysis → generate_weekly_review` | ✓ WIRED | Line 177: elif event.job_id == "weekly_behavior_analysis" chains to generate_weekly_review_triggered |
| `models/__init__.py` | 3 new model files | import + __all__ | ✓ WIRED | Lines 29-31: imports, Line 33: __all__ includes all 3 |
| `goal_service.py` | `trade.py` | SUM(Trade.net_pnl) | ✓ WIRED | _compute_actual_pnl (line 313): select sum(Trade.net_pnl) WHERE side=='SELL' |
| `monthly-goal-card.tsx` | `/api/goals/current` | useCurrentGoal() | ✓ WIRED | Line 37: useCurrentGoal() → fetchCurrentGoal → apiFetch("/goals/current") |
| `set-goal-dialog.tsx` | `/api/goals` | useSetGoal() | ✓ WIRED | Line 38: useSetGoal() → setGoal → apiFetch("/goals", POST) |
| `weekly-prompt-card.tsx` | `/api/goals/weekly-prompt` | useWeeklyPrompt() + useRespondWeeklyPrompt() | ✓ WIRED | Lines 18-19: Both hooks used, respond.mutate calls respondWeeklyPrompt |
| `weekly-review-card.tsx` | `/api/goals/weekly-review` | useLatestReview() | ✓ WIRED | Line 18: useLatestReview() → fetchLatestReview → apiFetch("/goals/weekly-review") |
| `coach/page.tsx` | 3 new components | import + JSX render | ✓ WIRED | Lines 23-25: imports, Lines 160-162: rendered in Section 5 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|-------------------|--------|
| `monthly-goal-card.tsx` | `goal` (GoalResponse) | useCurrentGoal → GET /goals/current → GoalService.get_current_goal → _compute_actual_pnl (SUM Trade.net_pnl WHERE SELL) | DB query sums real trades | ✓ FLOWING |
| `weekly-prompt-card.tsx` | `prompt` (WeeklyPromptResponse) | useWeeklyPrompt → GET /goals/weekly-prompt → GoalService.get_pending_prompt → select(WeeklyPrompt).where(response.is_(None)) | DB query for pending prompts | ✓ FLOWING |
| `weekly-review-card.tsx` | `review` (WeeklyReviewResponse) | useLatestReview → GET /goals/weekly-review → GoalService.get_latest_review → select(WeeklyReview).order_by(week_end.desc()) | DB query for latest review | ✓ FLOWING |
| `set-goal-dialog.tsx` | mutation (GoalResponse) | useSetGoal → POST /goals → GoalService.set_goal → INSERT/UPDATE TradingGoal | DB write + invalidates ["goals","current"] | ✓ FLOWING |

### Behavioral Spot-Checks

Step 7b: SKIPPED — Backend requires database connection (PostgreSQL) and frontend requires running dev server. Both are server-dependent. Code inspection confirms all wiring is complete.

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-----------|-------------|--------|----------|
| GOAL-01 | 47-01, 47-02, 47-03 | User đặt mục tiêu lãi/tháng, track tiến độ bằng progress bar | ✓ SATISFIED | TradingGoal model + GoalService.set_goal/get_current_goal + POST/GET /api/goals endpoints + MonthlyGoalCard with progress bar + SetGoalDialog |
| GOAL-02 | 47-01, 47-02, 47-03 | Weekly risk tolerance prompt adjusting risk level | ✓ SATISFIED | WeeklyPrompt model + GoalService.create_weekly_prompt/respond_to_prompt (updates UserRiskProfile) + Monday 8:00 AM cron job + GET/POST /api/goals/weekly-prompt endpoints + WeeklyPromptCard with 3 buttons |
| GOAL-03 | 47-01, 47-02, 47-03 | AI weekly performance review in Vietnamese | ✓ SATISFIED | WeeklyReview model + GoalService.generate_review (Gemini with Vietnamese instruction + 3-stage fallback) + Sunday 21:00 cron + chaining + GET /api/goals/weekly-review endpoint + WeeklyReviewCard with highlights/suggestions |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `set-goal-dialog.tsx` | 92 | `placeholder="5,000,000"` | ℹ️ Info | HTML input placeholder — not a code stub |
| `weekly-prompt-card.tsx` | 23 | `return null` when no pending prompt | ℹ️ Info | Intentional conditional rendering — renders nothing when no prompt pending |

No blockers or warnings found. All patterns are intentional design decisions.

### Human Verification Required

### 1. Monthly Goal Progress Bar Visual

**Test:** Navigate to /coach, set a monthly profit target via the "Đặt mục tiêu" button, then verify the progress bar renders correctly
**Expected:** Dialog opens with validation (min 100,000 VND, max 1B VND). After saving, progress bar shows actual P&L / target with color coding: red (<50%), amber (50-99%), green (≥100%). Percentage and emoji (🎉 at 100%+) display correctly.
**Why human:** Visual progress bar rendering, color accuracy, and dialog UX flow require visual inspection

### 2. Weekly Risk Prompt Interaction

**Test:** When a weekly risk prompt is pending (created Monday 8:00 AM), verify the prompt card appears on /coach with 3 response buttons
**Expected:** Card shows "Tuần này bạn muốn giao dịch thế nào?" with current risk level displayed. Three buttons: "Thận trọng hơn" (disabled if risk=1), "Giữ nguyên", "Mạo hiểm hơn" (disabled if risk=5). Clicking a button shows Loader2 spinner, then card disappears. Risk level updates in profile.
**Why human:** Button states, loading spinners, conditional card visibility, and risk level update feedback require interactive testing

### 3. Weekly Review Card Display

**Test:** After a weekly review has been generated (Sunday 21:00), verify the review card renders Vietnamese content correctly
**Expected:** Collapsible card shows week range (DD/MM format), Vietnamese summary text (300-500 words), green "Điểm tốt" highlights, red "Cần cải thiện" highlights, "Gợi ý tuần tới" suggestions, and stats footer with trades/wins/PnL
**Why human:** Vietnamese text rendering quality, collapsible interaction, color-coded highlights, and overall layout aesthetics need visual confirmation

### 4. Section 5 Page Placement

**Test:** Scroll through /coach page and verify "Mục tiêu & Nhận xét" section placement
**Expected:** Section appears after pick history table (Section 4) and before behavior insights "Phân tích hành vi" (Section 6)
**Why human:** Page layout ordering and section spacing are visual properties

### Gaps Summary

No automated gaps found. All 3 roadmap success criteria are verified through code inspection:

1. **Monthly profit target with progress bar** — Complete end-to-end: DB model → service (actual P&L from trades) → API endpoints → frontend progress bar with 3-color scheme
2. **Weekly risk tolerance prompt** — Complete end-to-end: Monday cron job → pending prompt → API → 3-button UI → risk level update on UserRiskProfile
3. **AI weekly review in Vietnamese** — Complete end-to-end: Sunday cron + chaining → trade/habit/pick data gathering with ticker resolution → Vietnamese Gemini prompt → 3-stage fallback → persistent review → collapsible card UI

4 items require human visual verification before the phase can be marked as fully passed.

---

_Verified: 2026-04-23T20:15:00Z_
_Verifier: the agent (gsd-verifier)_

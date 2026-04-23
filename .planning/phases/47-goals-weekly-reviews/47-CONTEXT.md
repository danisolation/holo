# Phase 47: Goals & Weekly Reviews - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

User sets monthly profit targets tracked via progress bar on the coach dashboard, receives weekly risk tolerance prompts that adjust risk_level, and gets AI-generated weekly performance reviews in Vietnamese. This is the final v8.0 milestone phase — focuses on goal-setting, weekly cadence, and Gemini-powered coaching summaries.

</domain>

<decisions>
## Implementation Decisions

### Monthly Profit Target (GOAL-01)
- New `trading_goals` table: id, target_pnl (Decimal), month (DATE — first of month), actual_pnl (Decimal, computed), status (active/completed/missed), created_at, updated_at
- Only 1 active goal per month — setting new goal for same month replaces previous
- API: POST /api/goals (set target), GET /api/goals/current (current month goal with progress), GET /api/goals/history (past months)
- actual_pnl computed from trades table: SUM(net_pnl) WHERE trade_date in current month AND side='SELL'
- Progress bar on coach dashboard: percentage = (actual_pnl / target_pnl) × 100, capped at 200%
- Display: "Mục tiêu tháng N: X/Y VND (Z%)" with colored progress bar (green >= 100%, amber 50-99%, red < 50%)
- Goal setting via simple dialog on coach page — input target amount in VND

### Weekly Risk Tolerance Prompt (GOAL-02)
- New `weekly_prompts` table: id, week_start (DATE), prompt_type (risk_tolerance), response (text: cautious/aggressive/unchanged), risk_level_before, risk_level_after, created_at
- Every Monday 8:00 AM (before market open), system creates a pending prompt
- On coach page, when pending prompt exists, show a card: "Tuần này bạn muốn thận trọng hơn hay mạo hiểm hơn?"
- 3 buttons: "Thận trọng hơn" (risk_level -= 1, min 1), "Giữ nguyên" (no change), "Mạo hiểm hơn" (risk_level += 1, max 5)
- Response updates UserRiskProfile.risk_level immediately
- Only 1 pending prompt at a time — auto-expire previous if unanswered after 7 days
- API: GET /api/goals/weekly-prompt (current pending), POST /api/goals/weekly-prompt/{id}/respond

### AI Weekly Performance Review (GOAL-03)
- New `weekly_reviews` table: id, week_start (DATE), week_end (DATE), summary_text (TEXT — Vietnamese), highlights (JSONB — good/bad habits list), suggestions (JSONB — improvement list), trades_count, win_count, total_pnl, created_at
- Generated every Sunday 21:00 via Gemini (after behavior analysis at 20:00)
- Gemini prompt includes: week's trades (ticker, side, pnl), habit detections from Phase 46, pick outcomes, current risk level, goal progress
- Output: Vietnamese narrative (300-500 words) + structured highlights + suggestions
- Use existing GeminiClient pattern (google.genai, structured output, rate limiting)
- Display on coach page as "Nhận xét tuần" card — collapsible with latest review shown by default
- API: GET /api/goals/weekly-review (latest), GET /api/goals/weekly-reviews (history with pagination)
- If no trades in the week, still generate a review noting inactivity and suggesting next steps

### Frontend & API
- New API routes in backend/app/api/goals.py:
  - POST /api/goals (set monthly target)
  - GET /api/goals/current (current month goal + progress)
  - GET /api/goals/history (past goals, paginated)
  - GET /api/goals/weekly-prompt (current pending prompt)
  - POST /api/goals/weekly-prompt/{id}/respond (answer prompt)
  - GET /api/goals/weekly-review (latest review)
  - GET /api/goals/weekly-reviews (review history, paginated)
- Coach page additions: 2 new sections above behavior insights
  1. Monthly goal progress bar (always visible when goal set)
  2. Weekly prompt card (conditional, when pending) + weekly review card (latest)

### Scheduler Jobs
- `create_weekly_risk_prompt` job: Monday 8:00 AM, creates pending prompt
- `generate_weekly_review` job: Sunday 21:00, calls Gemini to generate review
- Chain: weekly_behavior_analysis (Sun 20:00) → generate_weekly_review (Sun 21:00)

### Agent's Discretion
- Gemini prompt template for weekly review — balance between detail and token efficiency
- Whether to include sector preference data in the weekly review
- Progress bar visual style (simple bar vs animated)
- Weekly review card expand/collapse default state

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `UserRiskProfile` model with risk_level — updated by weekly prompt response
- `GeminiClient` in backend/app/services/analysis/gemini_client.py — reuse for weekly review generation
- `Trade` model with net_pnl — for monthly goal computation and weekly review data
- `HabitDetection` model — feed into weekly review prompt
- `DailyPick` with outcome columns — feed pick results into weekly review
- `BehaviorService` — provides habit + sector data for review context
- Scheduler chaining pattern — well-established for new jobs
- `google.genai` with structured output — proven pattern for Vietnamese text generation

### Integration Points
- `backend/app/api/router.py` — register goals_router
- `backend/app/models/__init__.py` — export new models
- `frontend/src/app/coach/page.tsx` — add goal + review sections
- `frontend/src/lib/api.ts` + `hooks.ts` — add goal fetch/hooks
- `backend/app/scheduler/jobs.py` — add 2 new jobs
- `backend/app/scheduler/manager.py` — register + chain new jobs

</code_context>

<deferred>
## Deferred Ideas

- **Goal streaks/achievements**: Track consecutive months of goal achievement — gamification out of scope
- **AI-powered goal suggestions**: Gemini suggests target based on past performance — keep manual for v8.0
- **Daily micro-reviews**: More frequent AI feedback — weekly cadence sufficient for now
- **Risk level auto-adjustment**: Remove confirm step — user control is a core principle
</deferred>

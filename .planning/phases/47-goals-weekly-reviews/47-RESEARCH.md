# Phase 47: Goals & Weekly Reviews - Research

**Researched:** 2026-04-23
**Domain:** Monthly goal tracking, weekly risk prompts, AI-generated weekly reviews (Gemini)
**Confidence:** HIGH

## Summary

Phase 47 is the final v8.0 milestone phase, adding three interconnected features to the coach dashboard: (1) monthly profit target tracking with a progress bar, (2) weekly risk tolerance prompts that adjust `UserRiskProfile.risk_level`, and (3) AI-generated weekly performance reviews in Vietnamese via Gemini. All three features follow well-established patterns already proven in Phases 44-46: new SQLAlchemy models → Alembic migration → service layer with pure functions → API routes → frontend hooks/components on the coach page.

The codebase already contains every building block needed: `GeminiClient` for AI generation with structured output and retry/circuit-breaker protection, `UserRiskProfile` for risk_level mutation, `Trade.net_pnl` for P&L aggregation, `HabitDetection` + `DailyPick` outcomes for review context, APScheduler with cron triggers and job chaining, and the coach page layout with sections for banners, cards, and conditional content. Zero new Python or npm packages are required.

**Primary recommendation:** Build in 3 waves matching the 3 sub-features — (1) DB models + migration + goal service + API, (2) weekly prompt scheduler + risk adjustment, (3) Gemini weekly review generation + scheduler chaining — then add all frontend components in a final wave.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **trading_goals table**: id, target_pnl (Decimal), month (DATE — first of month), actual_pnl (Decimal, computed), status (active/completed/missed), created_at, updated_at
- **Only 1 active goal per month** — setting new goal for same month replaces previous
- **API routes**: POST /api/goals, GET /api/goals/current, GET /api/goals/history, GET /api/goals/weekly-prompt, POST /api/goals/weekly-prompt/{id}/respond, GET /api/goals/weekly-review, GET /api/goals/weekly-reviews
- **actual_pnl computed from trades table**: SUM(net_pnl) WHERE trade_date in current month AND side='SELL'
- **Progress bar**: percentage = (actual_pnl / target_pnl) × 100, capped at 200%
- **Display**: "Mục tiêu tháng N: X/Y VND (Z%)" with colored progress bar (green >= 100%, amber 50-99%, red < 50%)
- **weekly_prompts table**: id, week_start (DATE), prompt_type (risk_tolerance), response (text), risk_level_before, risk_level_after, created_at
- **Every Monday 8:00 AM** system creates pending prompt
- **3 buttons**: "Thận trọng hơn" (risk_level -= 1, min 1), "Giữ nguyên" (no change), "Mạo hiểm hơn" (risk_level += 1, max 5)
- **Response updates UserRiskProfile.risk_level immediately**
- **Only 1 pending prompt at a time** — auto-expire previous if unanswered after 7 days
- **weekly_reviews table**: id, week_start (DATE), week_end (DATE), summary_text (TEXT), highlights (JSONB), suggestions (JSONB), trades_count, win_count, total_pnl, created_at
- **Generated every Sunday 21:00 via Gemini** (after behavior analysis at 20:00)
- **Use existing GeminiClient pattern** (google.genai, structured output, rate limiting)
- **Vietnamese narrative 300-500 words** + structured highlights + suggestions
- **If no trades in the week**, still generate review noting inactivity
- **Coach page additions**: 2 new sections above behavior insights — (1) monthly goal progress bar, (2) weekly prompt card + weekly review card
- **create_weekly_risk_prompt job**: Monday 8:00 AM
- **generate_weekly_review job**: Sunday 21:00
- **Chain**: weekly_behavior_analysis (Sun 20:00) → generate_weekly_review (Sun 21:00)

### Agent's Discretion
- Gemini prompt template for weekly review — balance between detail and token efficiency
- Whether to include sector preference data in the weekly review
- Progress bar visual style (simple bar vs animated)
- Weekly review card expand/collapse default state

### Deferred Ideas (OUT OF SCOPE)
- Goal streaks/achievements (gamification)
- AI-powered goal suggestions based on past performance
- Daily micro-reviews
- Risk level auto-adjustment without user confirm
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GOAL-01 | User sets monthly profit target, progress bar on coach dashboard tracks actual P&L | trading_goals table + SUM(net_pnl) WHERE side='SELL' + progress bar component with 3-color scheme |
| GOAL-02 | Weekly prompt "Bạn muốn thận trọng hơn hay mạo hiểm hơn?" adjusts risk_level | weekly_prompts table + Monday 8:00 AM scheduler job + UserRiskProfile.risk_level mutation |
| GOAL-03 | AI weekly review summarizes week in Vietnamese, highlights habits, suggests improvements | weekly_reviews table + Sunday 21:00 Gemini call + chain from weekly_behavior_analysis |
</phase_requirements>

## Standard Stack

### Core (already installed — zero new packages)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | ~2.0 | ORM for 3 new tables | Existing pattern — mapped_column style [VERIFIED: codebase] |
| Alembic | ~1.18 | Migration 023 for new tables | Sequential numbering from 022 [VERIFIED: codebase] |
| google-genai | ~1.73 | Gemini API for weekly review generation | Existing GeminiClient pattern [VERIFIED: codebase] |
| APScheduler | 3.11.2 | Cron jobs for Monday prompt + Sunday review | CronTrigger + chaining pattern [VERIFIED: codebase] |
| Pydantic | ~2.13 | Request/response schemas for goals API | Existing schemas pattern [VERIFIED: codebase] |
| @tanstack/react-query | ^5.99.0 | Frontend data fetching hooks | useQuery/useMutation pattern [VERIFIED: package.json] |
| shadcn/ui | 4.x | Card, Dialog, Button, Badge components | All needed UI components exist [VERIFIED: components/ui/] |
| recharts | ^3.8.1 | Progress bar could use this but simple div is better | Already available but not recommended for this use case |
| lucide-react | ^1.8.0 | Icons for goal/prompt/review cards | Target, TrendingUp, FileText, etc. [VERIFIED: package.json] |

### No New Packages Needed
[VERIFIED: codebase audit] — All required libraries are already installed. This phase only creates new files using existing dependencies.

## Architecture Patterns

### Recommended Project Structure (new files only)
```
backend/
├── alembic/versions/
│   └── 023_goals_weekly_reviews.py     # Migration for 3 new tables
├── app/
│   ├── models/
│   │   ├── trading_goal.py             # TradingGoal model
│   │   ├── weekly_prompt.py            # WeeklyPrompt model
│   │   └── weekly_review.py            # WeeklyReview model
│   ├── schemas/
│   │   └── goals.py                    # Request/response schemas
│   ├── services/
│   │   └── goal_service.py             # GoalService (pure fns + async class)
│   └── api/
│       └── goals.py                    # /api/goals routes
frontend/
├── src/
│   ├── components/
│   │   ├── monthly-goal-card.tsx       # Progress bar + goal setting
│   │   ├── weekly-prompt-card.tsx       # Risk tolerance prompt
│   │   └── weekly-review-card.tsx       # AI review display
│   └── lib/
│       ├── api.ts                      # + goal types & fetch functions
│       └── hooks.ts                    # + goal hooks
```

### Pattern 1: Service Layer (Pure Functions + Async DB Class)
**What:** Module-level pure functions for computation, class for DB operations
**When to use:** Always — established in Phases 44-46
**Example:**
```python
# Source: [VERIFIED: backend/app/services/behavior_service.py pattern]

# ── Pure computation functions (testable without DB) ───────────
def compute_goal_progress(actual_pnl: float, target_pnl: float) -> dict:
    """Return progress percentage capped at 200%."""
    if target_pnl <= 0:
        return {"percentage": 0.0, "color": "red"}
    pct = (actual_pnl / target_pnl) * 100
    pct = min(pct, 200.0)
    color = "green" if pct >= 100 else "amber" if pct >= 50 else "red"
    return {"percentage": round(pct, 1), "color": color}


class GoalService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_current_goal(self) -> dict | None:
        """Get current month's active goal with computed actual_pnl."""
        ...
```

### Pattern 2: Scheduler Job with Chaining
**What:** Job function using `async_session()` + `JobExecutionService` tracking
**When to use:** For new Monday prompt + Sunday review jobs
**Example:**
```python
# Source: [VERIFIED: backend/app/scheduler/jobs.py — weekly_behavior_analysis pattern]

async def generate_weekly_review():
    """Generate AI weekly review via Gemini. Chains after weekly_behavior_analysis."""
    logger.info("=== GENERATE WEEKLY REVIEW START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("generate_weekly_review")
        try:
            service = GoalService(session)
            result = await service.generate_review()
            await job_svc.complete(execution, status="success", result_summary=result)
            await session.commit()
            logger.info(f"=== GENERATE WEEKLY REVIEW DONE: {result} ===")
        except Exception as e:
            if execution.status == "running":
                await job_svc.fail(execution, error=str(e))
                await session.commit()
            logger.error(f"Weekly review generation failed: {e}")
            raise
```

### Pattern 3: GeminiClient for Weekly Review (NEW — single prompt, not batch)
**What:** Use existing `_call_gemini` pattern but with a single weekly prompt, not ticker batches
**When to use:** Sunday 21:00 review generation
**Key difference from existing batch usage:** The weekly review is ONE Gemini call per week (not per-ticker batches), but reuses the same retry + circuit-breaker + usage tracking infrastructure.
**Example approach:**
```python
# Source: [VERIFIED: backend/app/services/analysis/gemini_client.py + prompts.py patterns]

# Option A: Reuse GeminiClient directly (requires session + client + model)
# Option B: Create lightweight wrapper in GoalService

# Recommended: Option B — GoalService creates its own genai client instance
# (like PickService does for explanation generation)

import google.genai as genai
from google.genai.errors import ServerError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Structured output schema for review
class WeeklyReviewOutput(BaseModel):
    summary_text: str  # Vietnamese narrative 300-500 words
    highlights: list[str]  # Good/bad habits
    suggestions: list[str]  # Improvement suggestions
```

### Pattern 4: Frontend Component Self-Contained with Own Hook
**What:** Each component fetches its own data internally
**When to use:** For MonthlyGoalCard, WeeklyPromptCard, WeeklyReviewCard
**Example:**
```tsx
// Source: [VERIFIED: frontend/src/components/habit-detection-card.tsx pattern]

export function MonthlyGoalCard() {
  const { data, isLoading, isError } = useCurrentGoal();
  if (isLoading) return <Skeleton className="h-24 rounded-xl" />;
  if (isError) return <ErrorCard />;
  if (!data) return <SetGoalPrompt />;
  return <ProgressBar goal={data} />;
}
```

### Pattern 5: API Route with async_session Context Manager
**What:** All routes create their own session, no FastAPI `Depends`
**When to use:** All 7 new goal routes
**Example:**
```python
# Source: [VERIFIED: backend/app/api/behavior.py pattern]
router = APIRouter(prefix="/goals", tags=["goals"])

@router.get("/current")
async def get_current_goal():
    async with async_session() as session:
        service = GoalService(session)
        result = await service.get_current_goal()
        if result is None:
            return None
        return result
```

### Anti-Patterns to Avoid
- **Don't use FastAPI Depends for DB sessions** — established pattern uses `async_session()` context manager directly [VERIFIED: all API routes]
- **Don't create a separate GeminiClient instance for reviews** — use same `google.genai` with `genai.Client` pattern from pick_service.py [VERIFIED: codebase]
- **Don't make actual_pnl a stored column** — compute it on read from trades table to stay consistent [LOCKED: CONTEXT.md]
- **Don't chain weekly_review from daily pipeline** — it's an independent Sunday job chained from weekly_behavior_analysis [LOCKED: CONTEXT.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Vietnamese text generation | Custom templates | Gemini structured output | Consistent with existing prompts.py pattern, handles Vietnamese grammar nuances |
| Progress bar UI | Custom SVG/canvas | Tailwind div with bg-* colors | shadcn has no Progress component in project, but a `div` with `w-[X%]` + transitions is the standard approach |
| Date computation (month boundaries) | Manual datetime math | Python `date.replace(day=1)` + `calendar.monthrange` or `date-fns` on frontend | Edge cases with month boundaries, timezone awareness |
| Risk level clamping | Manual if/else | `max(1, min(5, new_level))` | One-liner, no library needed |
| Week boundaries (ISO) | Manual computation | Python `date.isocalendar()` or `timedelta(days=date.weekday())` | ISO week numbering is tricky, use stdlib |

**Key insight:** This phase composes existing patterns (Gemini calls, scheduler jobs, CRUD services, coach page sections) rather than introducing new infrastructure. The primary risk is integration correctness, not technology choice.

## Common Pitfalls

### Pitfall 1: Month Boundary Edge Cases for Goal Progress
**What goes wrong:** Computing SUM(net_pnl) with incorrect date range — missing first/last day of month
**Why it happens:** Using `>= month_start AND < next_month_start` vs `BETWEEN` semantics; timezone vs date type confusion
**How to avoid:** Use `Trade.trade_date` (DATE type, not TIMESTAMP) with `>= first_of_month AND < first_of_next_month`. The Trade model's `trade_date` is already a `date` column, not timezone-aware timestamp.
**Warning signs:** Goal progress shows unexpected value at month boundaries, especially on the 1st

### Pitfall 2: Race Condition on Weekly Prompt Expiration
**What goes wrong:** Monday job creates new prompt while user is answering the previous one
**Why it happens:** The "auto-expire previous if unanswered after 7 days" logic runs at the same time as new prompt creation
**How to avoid:** In `create_weekly_risk_prompt` job, first expire any pending prompts (set status='expired'), THEN create new one — all in same transaction. Use `SELECT FOR UPDATE` or flush-then-create pattern.
**Warning signs:** Two pending prompts in the database simultaneously

### Pitfall 3: Gemini Call Failure on Sunday Night
**What goes wrong:** Weekly review generation fails (rate limit, API outage) and there's no retry until next Sunday
**Why it happens:** Unlike daily jobs that run again tomorrow, weekly jobs have 7-day gaps
**How to avoid:** (1) Use existing tenacity retry (2 attempts), (2) Record failure in job_executions, (3) Consider allowing manual trigger via health dashboard. The existing `JobExecutionService` failure tracking handles visibility.
**Warning signs:** Missing weekly reviews with errors in job_executions table

### Pitfall 4: Division by Zero in Goal Progress
**What goes wrong:** User sets target_pnl = 0 or negative, progress calculation crashes
**Why it happens:** No validation on target_pnl input
**How to avoid:** Pydantic schema for `POST /api/goals` must validate `target_pnl > 0`. Pure function `compute_goal_progress` should also guard.
**Warning signs:** 500 error on GET /api/goals/current

### Pitfall 5: Gemini Structured Output for Vietnamese Long Text
**What goes wrong:** `response.parsed` returns None when Gemini generates Vietnamese text that doesn't cleanly parse into the schema
**Why it happens:** Existing batch analyzers have this issue (see the 3-stage fallback in gemini_client.py: parsed → low-temp retry → manual JSON parse)
**How to avoid:** Implement same 3-stage fallback for weekly review. Use `response_mime_type="application/json"` + Pydantic `response_schema`. Keep summary_text as a single string field (don't over-structure the narrative).
**Warning signs:** `response.parsed is None` in logs, empty weekly reviews

### Pitfall 6: Stale Query Cache After Risk Level Change
**What goes wrong:** User answers weekly prompt (risk_level changes), but picks and profile data still show old values
**Why it happens:** React Query cache not invalidated after prompt response mutation
**How to avoid:** In `useRespondWeeklyPrompt` mutation's `onSuccess`, invalidate `["profile"]` and `["picks", "today"]` queryKeys — same pattern as existing `useRespondRiskSuggestion`.
**Warning signs:** Profile settings card shows old risk level after weekly prompt response

## Code Examples

### Model: TradingGoal
```python
# Source: [VERIFIED: Follows backend/app/models/user_risk_profile.py and trade.py patterns]
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Integer, String, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.models import Base


class TradingGoal(Base):
    __tablename__ = "trading_goals"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    target_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    month: Mapped[date] = mapped_column(Date, nullable=False)  # First of month
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="active")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
```

### Model: WeeklyPrompt
```python
# Source: [VERIFIED: Follows backend/app/models/risk_suggestion.py pattern]
class WeeklyPrompt(Base):
    __tablename__ = "weekly_prompts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    prompt_type: Mapped[str] = mapped_column(String(20), nullable=False, server_default="risk_tolerance")
    response: Mapped[str | None] = mapped_column(String(20), nullable=True)  # cautious/aggressive/unchanged/expired
    risk_level_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level_after: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
```

### Model: WeeklyReview
```python
# Source: [VERIFIED: Follows habit_detection.py + daily_pick.py JSONB pattern]
from sqlalchemy.dialects.postgresql import JSONB

class WeeklyReview(Base):
    __tablename__ = "weekly_reviews"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    week_end: Mapped[date] = mapped_column(Date, nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    highlights: Mapped[dict] = mapped_column(JSONB, nullable=False)
    suggestions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    trades_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    win_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
```

### Actual P&L Computation (Pure Function)
```python
# Source: [VERIFIED: Trade model with side='SELL' and net_pnl — backend/app/models/trade.py]

async def _compute_actual_pnl(self, month_start: date, month_end_exclusive: date) -> Decimal:
    """SUM(net_pnl) for SELL trades in the given month."""
    result = await self.session.execute(
        select(func.coalesce(func.sum(Trade.net_pnl), 0))
        .where(Trade.side == "SELL")
        .where(Trade.trade_date >= month_start)
        .where(Trade.trade_date < month_end_exclusive)
    )
    return result.scalar_one()
```

### Gemini Prompt for Weekly Review
```python
# Source: [VERIFIED: prompts.py system instruction pattern]

WEEKLY_REVIEW_SYSTEM_INSTRUCTION = (
    "Bạn là huấn luyện viên giao dịch chứng khoán cá nhân. "
    "Viết bản đánh giá tuần bằng tiếng Việt (300-500 từ). "
    "Bao gồm: tóm tắt hiệu suất, thói quen tốt/xấu, gợi ý cải thiện cụ thể. "
    "Giọng văn thân thiện, động viên nhưng thẳng thắn. "
    "Nếu không có giao dịch, khuyến khích kiên nhẫn và kỷ luật."
)
```

### Scheduler Registration (Monday + Sunday)
```python
# Source: [VERIFIED: backend/app/scheduler/manager.py — configure_jobs pattern]

# In configure_jobs():
from app.scheduler.jobs import create_weekly_risk_prompt, generate_weekly_review

# Monday 8:00 AM — weekly risk tolerance prompt
scheduler.add_job(
    create_weekly_risk_prompt,
    trigger=CronTrigger(
        day_of_week="mon",
        hour=8, minute=0,
        timezone=settings.timezone,
    ),
    id="create_weekly_risk_prompt",
    name="Weekly Risk Tolerance Prompt",
    replace_existing=True,
    misfire_grace_time=7200,
)

# Sunday 21:00 — AI weekly review (chain handled in _on_job_executed)
scheduler.add_job(
    generate_weekly_review,
    trigger=CronTrigger(
        day_of_week="sun",
        hour=21, minute=0,
        timezone=settings.timezone,
    ),
    id="generate_weekly_review",
    name="AI Weekly Performance Review",
    replace_existing=True,
    misfire_grace_time=7200,
)
```

### Job Chaining Addition
```python
# Source: [VERIFIED: backend/app/scheduler/manager.py — _on_job_executed]

# Add to _on_job_executed:
elif event.job_id == "weekly_behavior_analysis":
    from app.scheduler.jobs import generate_weekly_review
    logger.info("Chaining: weekly_behavior_analysis → generate_weekly_review")
    scheduler.add_job(
        generate_weekly_review,
        id="generate_weekly_review_triggered",
        replace_existing=True,
        misfire_grace_time=3600,
    )
```

### Frontend Progress Bar Component
```tsx
// Source: [VERIFIED: Tailwind pattern from existing cards]

function GoalProgressBar({ percentage, color }: { percentage: number; color: string }) {
  const bgClass = color === "green" ? "bg-[#26a69a]"
    : color === "amber" ? "bg-amber-500"
    : "bg-red-500";

  return (
    <div className="w-full bg-muted rounded-full h-3 overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-500 ${bgClass}`}
        style={{ width: `${Math.min(percentage, 100)}%` }}
      />
    </div>
  );
}
```

### Frontend Risk Prompt Card
```tsx
// Source: [VERIFIED: Follows risk-suggestion-banner.tsx pattern]

export function WeeklyPromptCard() {
  const { data: prompt } = useWeeklyPrompt();
  const respond = useRespondWeeklyPrompt();

  if (!prompt) return null; // No pending prompt

  return (
    <Card>
      <CardContent className="py-4">
        <p className="font-bold">Tuần này bạn muốn thận trọng hơn hay mạo hiểm hơn?</p>
        <div className="flex gap-2 mt-3">
          <Button variant="outline" onClick={() => respond.mutate({ id: prompt.id, response: "cautious" })}>
            Thận trọng hơn
          </Button>
          <Button variant="outline" onClick={() => respond.mutate({ id: prompt.id, response: "unchanged" })}>
            Giữ nguyên
          </Button>
          <Button variant="outline" onClick={() => respond.mutate({ id: prompt.id, response: "aggressive" })}>
            Mạo hiểm hơn
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| google-generativeai | google-genai | 2025 | Already using new SDK [VERIFIED: codebase] |
| APScheduler 4.0 | APScheduler 3.11 | N/A (v4 never released) | Stay on 3.11 [VERIFIED: STATE.md] |
| response.text + JSON.parse | response.parsed (structured output) | google-genai 1.x | Already using, but need fallback [VERIFIED: gemini_client.py] |

**Deprecated/outdated:**
- None relevant — all tech in use is current

## Assumptions Log

> List all claims tagged `[ASSUMED]` in this research.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Gemini 2.5-flash-lite can generate 300-500 word Vietnamese narrative in structured output mode | Code Examples | Review may be truncated or unparseable — mitigated by 3-stage fallback pattern |
| A2 | Simple div-based progress bar is sufficient (no need for shadcn Progress component) | Don't Hand-Roll | Minor visual issue — easy to swap to Recharts bar if needed |
| A3 | Including sector preference data in weekly review is beneficial but not critical | Agent's Discretion | Slightly less detailed review without it — user impact is low |

## Open Questions

1. **Goal Setting Dialog UX**
   - What we know: CONTEXT.md says "simple dialog on coach page — input target amount in VND"
   - What's unclear: Should it use the existing shadcn Dialog component or an inline form?
   - Recommendation: Use shadcn Dialog with a single number input + "Đặt mục tiêu" button — matches existing ProfileSettingsCard dialog pattern [VERIFIED: profile-settings-card.tsx exists]

2. **Weekly Review Card Default State**
   - What we know: CONTEXT.md says "collapsible with latest review shown by default"
   - What's unclear: How much of the review to show — full summary or truncated?
   - Recommendation: Show full summary_text collapsed by default, expand to show highlights + suggestions. Use Accordion from shadcn/ui (available as accordion.tsx) [VERIFIED: components/ui/accordion.tsx exists]

3. **Sector Preference in Weekly Review**
   - What we know: Agent's discretion per CONTEXT.md
   - Recommendation: Include sector data in review prompt — it adds value for sector-biased trading habits. Keep it as supplementary context (not primary focus) to avoid inflating token usage.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with AsyncMock |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/test_goal_service.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GOAL-01 | compute_goal_progress pure function (percentage, color) | unit | `pytest tests/test_goal_service.py::test_compute_goal_progress -x` | ❌ Wave 0 |
| GOAL-01 | actual_pnl SUM query correctness | unit | `pytest tests/test_goal_service.py::test_actual_pnl_computation -x` | ❌ Wave 0 |
| GOAL-01 | target_pnl validation (>0 required) | unit | `pytest tests/test_goal_service.py::test_goal_validation -x` | ❌ Wave 0 |
| GOAL-02 | risk_level clamping (min 1, max 5) | unit | `pytest tests/test_goal_service.py::test_risk_level_clamping -x` | ❌ Wave 0 |
| GOAL-02 | prompt expiration after 7 days | unit | `pytest tests/test_goal_service.py::test_prompt_expiration -x` | ❌ Wave 0 |
| GOAL-03 | review generation with no trades produces inactivity review | unit | `pytest tests/test_goal_service.py::test_review_no_trades -x` | ❌ Wave 0 |
| GOAL-03 | structured output parsing + fallback | unit | `pytest tests/test_goal_service.py::test_review_parsing_fallback -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_goal_service.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_goal_service.py` — covers GOAL-01, GOAL-02, GOAL-03 pure functions
- [ ] No new framework install needed — pytest already configured

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user app, no auth |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | Single-user |
| V5 Input Validation | yes | Pydantic schemas — target_pnl > 0, response enum validation, sort/order whitelist |
| V6 Cryptography | no | No secrets handled |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL injection via sort params | Tampering | Whitelist allowed sort columns (same as trades API) [VERIFIED: backend/app/api/trades.py] |
| Negative/zero target_pnl → division by zero | Tampering | Pydantic Field(gt=0) validation |
| Prompt response tampering | Tampering | Pydantic regex validation for response values (cautious/aggressive/unchanged) |
| Gemini API key exposure | Information Disclosure | Key in .env, not in code [VERIFIED: backend/app/config.py] |

## Sources

### Primary (HIGH confidence)
- Codebase audit: backend/app/models/*.py — all model patterns verified
- Codebase audit: backend/app/services/behavior_service.py — service pattern verified
- Codebase audit: backend/app/scheduler/manager.py — scheduler chaining pattern verified
- Codebase audit: backend/app/services/analysis/gemini_client.py — Gemini usage pattern verified
- Codebase audit: frontend/src/lib/api.ts + hooks.ts — frontend data layer verified
- Codebase audit: frontend/src/app/coach/page.tsx — coach page layout verified
- Codebase audit: frontend/src/components/risk-suggestion-banner.tsx — interactive card pattern verified

### Secondary (MEDIUM confidence)
- Google genai structured output for long Vietnamese text — behavior observed in existing batch analyzers, extended to single-prompt use case

### Tertiary (LOW confidence)
- None — all findings verified against codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new packages, all patterns verified in codebase
- Architecture: HIGH — follows exact same patterns from Phases 44-46
- Pitfalls: HIGH — identified from actual codebase issues (Gemini parsing fallback, cache invalidation)
- Security: HIGH — minimal surface, same patterns as existing API routes

**Research date:** 2026-04-23
**Valid until:** 2026-05-23 (stable — all dependencies already pinned)

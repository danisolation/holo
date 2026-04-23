# Technology Stack — AI Trading Coach

**Project:** Holo v8.0 — AI Trading Coach
**Researched:** 2025-07-23
**Confidence:** HIGH (versions verified via npm/pip registries, existing codebase audited)

## Executive Principle

**The existing stack covers 90% of what v8.0 needs.** The only new dependencies are 5 frontend libraries for form handling, date picking, and toast notifications — all from the shadcn/ui ecosystem. Zero new Python packages needed.

---

## Stack Additions (NEW for v8.0)

### Frontend — New Dependencies

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| `react-hook-form` | ^7.73.1 | Form state management for trade journal + goal setting | Trade journal requires multi-field forms (ticker, price, qty, date, direction, notes). Controlled components alone get messy with 8+ fields + validation. react-hook-form is the shadcn/ui standard — all shadcn `<Form>` examples use it. Supports React 19 (peerDep: `^16.8 \|\| ^17 \|\| ^18 \|\| ^19`). | HIGH |
| `@hookform/resolvers` | ^5.2.2 | Connects react-hook-form with zod validation | Bridge library. v5.x uses `@standard-schema/utils` internally — works with both zod 3.x and zod 4.x via Standard Schema protocol. | HIGH |
| `zod` | ^3.25.76 | Schema validation for trade forms + API request bodies | Type-safe validation. Generates TypeScript types from schemas (`z.infer<typeof schema>`). **Use zod 3.x, not 4.x** — zod 4 is brand new (June 2025), shadcn/ui docs + community examples all target zod 3. @hookform/resolvers 5.x supports both via Standard Schema but zod 3 is battle-tested. | HIGH |
| `react-day-picker` | ^9.14.0 | Calendar date picker for trade entry dates | Required by shadcn/ui `<Calendar>` and `<DatePicker>` components. v9 depends on `date-fns ^4.1.0` which the project already has — zero extra transitive deps for date logic. Supports React ≥16.8. | HIGH |
| `sonner` | ^2.0.7 | Toast notifications for trade actions + form feedback | shadcn/ui's recommended toast library (replaced radix-ui/toast). Shows success/error feedback: "Trade saved", "Goal updated", "Pick generated". Supports React 18+19. Lightweight (~3KB). | HIGH |

### Frontend — shadcn/ui Components to Add

These are copy-paste components (not npm dependencies), installed via `npx shadcn add`:

| Component | Purpose | Depends On |
|-----------|---------|------------|
| `form` | Wraps react-hook-form + zod for trade journal / goal forms | react-hook-form, zod, @hookform/resolvers |
| `calendar` | Date picker for trade entry dates | react-day-picker |
| `select` | Dropdown: direction (buy/sell), timeframe, ticker selection | @radix-ui/react-select (auto-installed) |
| `switch` | Toggle: active/closed trades, goal tracking on/off | @radix-ui/react-switch (auto-installed) |
| `sonner` | Toast notifications provider | sonner |
| `progress` | Goal progress bars (profit target %, weekly progress) | (none — pure CSS/Tailwind) |
| `slider` | Risk tolerance adjustment (1-10 scale) | @radix-ui/react-slider (auto-installed) |
| `label` | Form field labels (dependency of `form` component) | @radix-ui/react-label (auto-installed) |

### Backend — No New Packages

**Zero new Python dependencies.** The existing stack handles everything:

| Existing Technology | How It Serves v8.0 |
|--------------------|--------------------|
| SQLAlchemy 2.0 + asyncpg | New models: `daily_picks`, `trades`, `trading_goals`, `weekly_reviews`, `user_profile` |
| Alembic | Migrations for all new tables |
| APScheduler 3.11 | New jobs: `daily_pick_generation` (chain after pipeline), `weekly_review_generation` (Sunday cron) |
| google-genai (Gemini) | New prompts: pick selection, weekly coaching review, adaptive strategy context |
| Pydantic 2.x | New structured output schemas for daily picks + weekly reviews |
| FastAPI | New API routers: `/api/coach/picks`, `/api/coach/trades`, `/api/coach/goals`, `/api/coach/reviews` |
| loguru | Logging for new services |
| tenacity | Retry on Gemini calls for pick generation |

---

## Existing Stack (Validated — DO NOT change)

### Backend (Python 3.12)

| Technology | Version | v8.0 Role |
|------------|---------|-----------|
| FastAPI | ~0.135 | New `/api/coach/*` router group |
| SQLAlchemy | ~2.0 | 5 new models with JSONB columns for flexible AI output storage |
| asyncpg | ~0.31 | Same connection pool (5+3 is sufficient for single-user) |
| Alembic | ~1.18 | ~3 migration files for new tables |
| APScheduler | 3.11 | 2 new jobs chained into existing pipeline |
| google-genai | ≥1.73 | 3 new Gemini prompt types (picks, review, adaptive) |
| Pydantic | ~2.13 | New schemas: DailyPickResponse, TradeSchema, GoalSchema, WeeklyReviewResponse |
| httpx | ~0.28 | No change |
| ta | 0.11.0 | No change — indicators feed into pick selection |

### Frontend (Next.js 16 + React 19)

| Technology | Version | v8.0 Role |
|------------|---------|-----------|
| Next.js | 16.2.3 | New routes: `/coach`, `/coach/journal`, `/coach/goals`, `/coach/reviews` |
| React | 19.2.4 | Standard component development |
| TypeScript | ~5.x | Type definitions for new API types |
| Tailwind CSS | ~4.x | Styling new coaching pages |
| @tanstack/react-query | ~5.99 | New query hooks: `useDailyPicks`, `useTrades`, `useGoals`, `useWeeklyReviews` |
| @tanstack/react-table | ~8.21 | Trade journal table with sorting/filtering |
| Recharts | ~3.8 | P&L charts, goal progress, behavior pattern visualization |
| zustand | ~5.0 | Coach page state: active tab, filter preferences, form drafts |
| lightweight-charts | ~5.1 | Display pick entry/SL levels on ticker charts (reuse existing pattern) |
| react-activity-calendar | ~3.2 | **Already installed** — reuse for trading activity heatmap |
| date-fns | ~4.1 | Date formatting, week boundaries for reviews |
| lucide-react | ~1.x | Icons for coaching UI |

---

## Database Schema Strategy

### New Tables (5 tables, all via Alembic)

```
daily_picks           — AI-generated daily stock picks (3-5 per day)
trades                — User's actual trade journal entries
trading_goals         — Profit targets, risk tolerance settings
weekly_reviews        — AI-generated weekly coaching summaries
user_profile          — Trading behavior profile (updated by system)
```

### Schema Patterns

**Use JSONB for flexible AI output** — same pattern as existing `ai_analyses.raw_response`:

```python
# daily_picks: Store full pick detail in JSONB (entry, SL, reasoning can evolve)
class DailyPick(Base):
    __tablename__ = "daily_picks"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pick_date: Mapped[date] = mapped_column(Date, nullable=False)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"))
    rank: Mapped[int] = mapped_column(Integer)  # 1-5 ranking
    entry_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float] = mapped_column(Float)
    reasoning: Mapped[str] = mapped_column(Text)  # Vietnamese
    pick_detail: Mapped[dict | None] = mapped_column(JSONB)  # Full Gemini output
    outcome: Mapped[str | None] = mapped_column(String(20))  # win/loss/pending
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
```

**Trade journal — denormalized for query simplicity** (single-user, no multi-table joins needed):

```python
class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"))
    direction: Mapped[str] = mapped_column(String(10))  # buy/sell
    entry_price: Mapped[float] = mapped_column(Float)
    entry_date: Mapped[date] = mapped_column(Date)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer)
    fees: Mapped[float] = mapped_column(Float, default=0)
    pnl: Mapped[float | None] = mapped_column(Float, nullable=True)  # Computed on exit
    pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open/closed
    from_daily_pick_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # FK if from pick
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
```

**Goals — simple key-value style with period tracking:**

```python
class TradingGoal(Base):
    __tablename__ = "trading_goals"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    period_type: Mapped[str] = mapped_column(String(20))  # weekly/monthly
    period_start: Mapped[date] = mapped_column(Date)
    period_end: Mapped[date] = mapped_column(Date)
    profit_target_pct: Mapped[float] = mapped_column(Float)
    max_loss_pct: Mapped[float] = mapped_column(Float)
    risk_tolerance: Mapped[int] = mapped_column(Integer)  # 1-10
    status: Mapped[str] = mapped_column(String(20), default="active")
    actual_pnl_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))
```

### Index Strategy

```sql
-- Daily picks: fast lookup by date
CREATE INDEX ix_daily_picks_date ON daily_picks(pick_date DESC);

-- Trades: filter by status, date range
CREATE INDEX ix_trades_status_date ON trades(status, entry_date DESC);
CREATE INDEX ix_trades_ticker ON trades(ticker_id, entry_date DESC);

-- Goals: active period lookup
CREATE INDEX ix_goals_period ON trading_goals(period_type, period_start DESC);
```

---

## Scheduling Integration

### Daily Pick Generation — Chain Into Existing Pipeline

Current chain ends at: `daily_trading_signal → daily_hnx_upcom_analysis`

**Extend to:** `daily_hnx_upcom_analysis → daily_pick_generation`

```python
# In scheduler/manager.py — add to _on_job_executed
elif event.job_id in ("daily_hnx_upcom_analysis_triggered",):
    from app.scheduler.jobs import daily_pick_generation
    logger.info("Chaining: daily_hnx_upcom_analysis → daily_pick_generation")
    scheduler.add_job(
        daily_pick_generation,
        id="daily_pick_generation_triggered",
        replace_existing=True,
        misfire_grace_time=3600,
    )
```

### Weekly Review — New Cron Job

```python
# In scheduler/manager.py — add to configure_jobs()
from app.scheduler.jobs import weekly_coaching_review

scheduler.add_job(
    weekly_coaching_review,
    trigger=CronTrigger(
        day_of_week="sun",
        hour=20,
        minute=0,
        timezone=settings.timezone,
    ),
    id="weekly_coaching_review",
    name="Weekly AI Coaching Review",
    replace_existing=True,
    misfire_grace_time=7200,
)
```

---

## Gemini Prompt Patterns for Coaching

### Pattern 1: Daily Pick Selection

**Input:** Top candidates (combined score ≥ 7) with their full analysis data + user profile (risk tolerance, recent performance).

**Key design:** This is a RANKING + SELECTION prompt, not an analysis prompt. Gemini receives pre-analyzed data and selects the best 3-5.

```python
DAILY_PICK_SYSTEM_INSTRUCTION = (
    "Bạn là huấn luyện viên trading cá nhân cho thị trường chứng khoán Việt Nam. "
    "Từ danh sách các mã đã phân tích, chọn 3-5 mã TỐT NHẤT cho hôm nay.\n\n"
    "Tiêu chí chọn:\n"
    "- Ưu tiên mã có signal đồng thuận (tech + fundamental + sentiment)\n"
    "- Risk/Reward ratio ≥ 1.5\n"
    "- Tránh mã có SL quá rộng (>3% entry)\n"
    "- Đa dạng ngành — không chọn 3 mã cùng ngành\n"
    "- Xem xét profile rủi ro của trader\n\n"
    "Output: danh sách 3-5 mã với giá vào, SL, lý do ngắn gọn."
)

class DailyPickItem(BaseModel):
    ticker: str
    entry_price: float
    stop_loss: float
    expected_gain_pct: float = Field(ge=0)
    risk_reward_ratio: float = Field(ge=0.5)
    reasoning: str = Field(description="Vietnamese, max 200 chars")
    confidence: int = Field(ge=1, le=10)

class DailyPicksResponse(BaseModel):
    picks: list[DailyPickItem] = Field(min_length=3, max_length=5)
    market_context: str = Field(description="Brief market overview, Vietnamese")
```

### Pattern 2: Weekly Coaching Review

**Input:** Week's trades (P&L, patterns), goals progress, behavior data.

**Key design:** Gemini as personal coach — encouraging but honest. Adjusts tone based on performance.

```python
WEEKLY_REVIEW_SYSTEM_INSTRUCTION = (
    "Bạn là huấn luyện viên trading cá nhân. Đánh giá tuần giao dịch vừa qua.\n"
    "Phong cách: thẳng thắn nhưng khích lệ, như một mentor đáng tin.\n\n"
    "Nội dung review:\n"
    "1. Tóm tắt hiệu suất (P&L, win rate, trades thực hiện)\n"
    "2. Điểm mạnh tuần này (giao dịch tốt nhất, kỷ luật)\n"
    "3. Điểm cần cải thiện (sai lầm, cảm xúc giao dịch)\n"
    "4. Gợi ý tuần tới (điều chỉnh chiến lược cụ thể)\n"
    "5. Đánh giá mức rủi ro: nên giữ/tăng/giảm?\n"
)
```

### Pattern 3: Adaptive Strategy Context

**NOT a new prompt** — inject user performance into existing trading signal prompt:

```python
# Add to trading signal context builder
def _build_user_context(user_profile: dict) -> str:
    """Build user performance context for adaptive recommendations."""
    return (
        f"\n--- TRADER PROFILE ---\n"
        f"Win rate 30 ngày: {user_profile['win_rate_30d']}%\n"
        f"Avg P&L per trade: {user_profile['avg_pnl_pct']}%\n"
        f"Risk tolerance: {user_profile['risk_tolerance']}/10\n"
        f"Losing streak hiện tại: {user_profile['current_losing_streak']}\n"
        f"Ngành hay giao dịch: {', '.join(user_profile['preferred_sectors'])}\n"
        f"Quy tắc: "
        + ("Gợi ý AN TOÀN HƠN — trader đang thua nhiều." if user_profile['current_losing_streak'] >= 3
           else "Gợi ý bình thường theo phân tích.")
    )
```

### Gemini Token Budget for v8.0

| Prompt Type | Est. Input Tokens | Est. Output Tokens | Calls/Day | Daily Total |
|------------|-------------------|-------------------|-----------|-------------|
| Daily Picks (1 call) | ~3,000 | ~1,500 | 1 | ~4,500 |
| Weekly Review (1/week) | ~2,000 | ~2,000 | 0.14 | ~600 |
| Existing pipeline | — | — | — | ~50,000 |
| **v8.0 addition** | — | — | — | **~5,100** |

**Impact: ~10% increase in daily Gemini usage.** Well within free tier limits.

---

## What NOT to Add

| Technology | Why NOT |
|-----------|---------|
| Redis / Celery | Behavior tracking can be done with simple DB inserts. No pub/sub or background queues needed for single-user. APScheduler handles all scheduling. |
| Pandas for P&L calculation | P&L is simple arithmetic: `(exit - entry) × qty - fees`. Python built-in math suffices. Don't import pandas for 4 lines of math. |
| chart.js / victory / nivo | Recharts already handles all non-financial charts. Don't add a second charting library. |
| D3.js | Overkill. Recharts is built on D3 and provides high-level API. |
| framer-motion | Animations are nice-to-have, not needed. Tailwind CSS 4 `tw-animate-css` (already installed) covers basic transitions. |
| Redux Toolkit / MobX | zustand already handles client state. Trade journal form state is managed by react-hook-form, not global state. |
| Prisma / Drizzle | SQLAlchemy 2.0 is the established ORM. Adding a second ORM for new tables would be insane. |
| tRPC | Already have a REST API pattern with FastAPI + React Query. tRPC solves a problem Holo doesn't have (type-safe API layer — Holo manually types API responses). |
| NextAuth / Auth.js | Single-user app. No auth needed per PROJECT.md constraints. |
| Supabase / Firebase | Already have PostgreSQL + FastAPI. These are full platforms, not libraries. |
| scikit-learn / ML libraries | Behavior analysis is pattern recognition via Gemini, not ML training. Per PROJECT.md: "ML price prediction — tạo false confidence." |
| LangChain / LlamaIndex | Single model (Gemini), direct SDK calls. LangChain adds abstraction with zero benefit. Already rejected in v1.0 research. |
| zod 4.x | Too new (June 2025). shadcn/ui docs, community examples, and @hookform/resolvers all target zod 3.x. Stick with 3.25.x. |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Form Library | react-hook-form 7.73 | Formik 2.x | Formik: larger bundle, less performant (re-renders entire form on change), fewer updates. RHF is the shadcn/ui standard. |
| Form Library | react-hook-form 7.73 | Controlled components (no lib) | Works for 2-3 fields. Trade journal has 8+ fields with validation, date pickers, conditional logic. RHF saves significant boilerplate. |
| Validation | zod 3.25 | yup | zod has better TypeScript inference, better error messages, and is the shadcn/ui default. |
| Validation | zod 3.25 | valibot | Smaller bundle but much smaller ecosystem. zod has 100x more examples/docs. |
| Toast | sonner 2.0 | react-hot-toast | sonner is shadcn/ui's official recommendation. Better styling, stacking, promise support. |
| Toast | sonner 2.0 | @radix-ui/react-toast | Lower-level — requires manual styling. sonner is built on Radix but provides styled defaults. |
| Calendar | react-day-picker 9.14 | @internationalized/date | Adobe library, used by react-aria. Overkill — rdp is shadcn/ui standard, already depends on date-fns (which project has). |
| Calendar | react-day-picker 9.14 | date-fns-picker (doesn't exist) | No standalone date picker from date-fns. rdp + date-fns is the canonical combo. |
| P&L Tracking | Python arithmetic | pandas P&L calculation | Trade P&L is `(exit - entry) * qty - fees`. This isn't a DataFrame operation. |
| Behavior Store | PostgreSQL table | localStorage + zustand | Behavior data must persist across browser sessions and feed into Gemini prompts (server-side). DB is the right place. |
| Behavior Store | PostgreSQL table | ClickHouse / TimescaleDB | Single-user. Behavioral events are ~10-50/day. PostgreSQL handles this without breaking a sweat. |

---

## Installation

### Frontend (from `frontend/` directory)

```bash
# Form handling (trade journal, goal setting)
npm install react-hook-form @hookform/resolvers zod

# Date picker (trade entry dates)
npm install react-day-picker

# Toast notifications (trade actions feedback)
npm install sonner

# shadcn/ui components (copy-paste, not npm deps)
npx shadcn add form calendar select switch sonner progress slider label
```

### Backend (from `backend/` directory)

```bash
# No new packages needed!
# Existing requirements.txt covers all v8.0 needs.
```

### Settings Additions (`backend/app/config.py`)

```python
# AI Trading Coach (v8.0)
daily_pick_count: int = 5                    # Max picks per day
daily_pick_min_combined_score: int = 7       # Minimum combined score to be candidate
daily_pick_thinking_budget: int = 2048       # Gemini thinking budget for pick selection
weekly_review_thinking_budget: int = 4096    # Larger budget for coaching review
coach_risk_tolerance_default: int = 5        # Default risk tolerance 1-10
```

---

## Integration Points Summary

| Feature | Backend Integration | Frontend Integration |
|---------|-------------------|---------------------|
| Daily Picks | New `DailyPickService` + chain into scheduler after HNX/UPCOM analysis | New `/coach` page, reuse `<TradingPlanPanel>` pattern for pick cards |
| Trade Journal | New `TradeService` + CRUD endpoints + P&L auto-calc on trade close | `react-hook-form` + `zod` forms, `@tanstack/react-table` for trade list, `Recharts` for P&L chart |
| Behavior Tracking | API middleware logs ticker views → `user_profile` table updated | Existing `useAnalysisSummary` / `useTradingSignal` hooks log pageviews server-side |
| Adaptive Strategy | Inject `user_profile` context into existing Gemini prompts | No frontend change — recommendations automatically adapt |
| Goal & Review | New `GoalService` + `WeeklyReviewService` + Sunday cron job | `react-hook-form` for goal form, `<Progress>` for tracking, review display card |

---

## Version Compatibility Matrix

| Package | Version | React 19 | Node 22 | Notes |
|---------|---------|----------|---------|-------|
| react-hook-form | 7.73.1 | ✅ peer: ^19 | ✅ | Current stable |
| @hookform/resolvers | 5.2.2 | ✅ (via RHF) | ✅ | Uses Standard Schema |
| zod | 3.25.76 | N/A (runtime) | ✅ | Latest 3.x stable |
| react-day-picker | 9.14.0 | ✅ peer: ≥16.8 | ✅ | Depends on date-fns ^4.1 (already installed) |
| sonner | 2.0.7 | ✅ peer: ^19 | ✅ | Lightweight toast |

---

## Sources

- npm registry: `npm view react-hook-form version` → 7.73.1, peerDeps: react ^19 (verified 2025-07-23)
- npm registry: `npm view @hookform/resolvers version` → 5.2.2, peerDeps: react-hook-form ^7.55 (verified 2025-07-23)
- npm registry: `npm view zod@3 version` → 3.25.76 (verified 2025-07-23)
- npm registry: `npm view react-day-picker version` → 9.14.0, deps: date-fns ^4.1.0 (verified 2025-07-23)
- npm registry: `npm view sonner version` → 2.0.7, peerDeps: react ^19 (verified 2025-07-23)
- pip registry: `pip index versions google-genai` → 1.73.1 (verified 2025-07-23)
- Existing codebase: `frontend/package.json`, `backend/requirements.txt`, `backend/app/` models/services/scheduler
- shadcn/ui docs: form, calendar, sonner component patterns (shadcn v4)

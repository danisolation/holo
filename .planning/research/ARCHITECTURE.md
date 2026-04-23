# Architecture Patterns — AI Trading Coach Integration

**Domain:** AI Trading Coach features for existing stock intelligence platform
**Researched:** 2026-04-23
**Overall confidence:** HIGH — based on direct codebase inspection of existing architecture

## Recommended Architecture

### Design Principle: Extension Over Modification

The existing Holo architecture is well-structured as a monolith with clear separation (ContextBuilder → GeminiClient → AnalysisStorage → AIAnalysisService). The AI Trading Coach features integrate as **new modules alongside existing ones**, not as modifications to the existing AI pipeline.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXISTING (unchanged)                         │
│  VnstockCrawler → PriceService → IndicatorService → AIAnalysis     │
│  (OHLCV)         (daily_prices)  (technical_indicator) (ai_analyses)│
│                                                                     │
│  CafeF → NewsArticle → SentimentAnalysis → CombinedAnalysis        │
│                                           → TradingSignal           │
└────────────────────────────┬────────────────────────────────────────┘
                             │ reads from
┌────────────────────────────▼────────────────────────────────────────┐
│                      NEW: AI Trading Coach                          │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │ DailyPick    │───▶│ TradeJournal │───▶│ BehaviorTracker      │  │
│  │ Generator    │    │ Service      │    │                      │  │
│  │              │    │              │    │ (event aggregation)  │  │
│  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │
│         │                   │                       │              │
│         │                   ▼                       ▼              │
│         │            ┌──────────────┐    ┌──────────────────────┐  │
│         │            │ P&L Engine   │    │ Adaptive Strategy    │  │
│         │            │ (auto-calc)  │    │ Engine               │  │
│         │            └──────────────┘    │ (risk adjustment)    │  │
│         │                               └──────────┬───────────┘  │
│         │                                          │              │
│         ▼                                          ▼              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                   Goal & Review System                        │  │
│  │  (monthly targets, weekly check-ins, progress tracking)      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### Component Boundaries

| Component | Responsibility | New/Extended | Communicates With |
|-----------|---------------|--------------|-------------------|
| **DailyPickGenerator** | Rank 800+ tickers → select top 3-5 daily picks with entry/SL rationale | **NEW service** | Reads: `ai_analyses`, `daily_prices`, `technical_indicator`. Reads: `user_risk_profile`. Writes: `daily_picks` |
| **DailyPickContextBuilder** | Gather ranking signals (combined score, trading signal, volume, momentum) for pick selection | **NEW** (extends pattern) | Reads: `ai_analyses`, `technical_indicator`, `daily_prices` |
| **TradeJournalService** | CRUD for manual trade entries, auto-link to daily picks | **NEW service** | Reads/writes: `trade_journal`. Reads: `daily_picks`, `daily_prices` |
| **PnLEngine** | Calculate realized/unrealized P&L, costs, fees | **NEW** (pure logic) | Reads: `trade_journal`, `daily_prices` |
| **BehaviorTracker** | Record and aggregate user behavior events (views, trades, timing patterns) | **NEW service** | Writes: `behavior_events`. Reads: `trade_journal`, `daily_picks` |
| **AdaptiveStrategyEngine** | Adjust risk profile based on trading history and P&L patterns | **NEW service** | Reads: `trade_journal`, `behavior_events`, `user_risk_profile`. Writes: `user_risk_profile` |
| **GoalReviewService** | Monthly targets, weekly progress snapshots, review generation | **NEW service** | Reads: `trade_journal`, `goals`. Writes: `goals`, `weekly_reviews` |
| **CoachPromptBuilder** | Build Gemini prompts for personalized coaching insights (weekly review, pick rationale) | **NEW** (extends GeminiClient pattern) | Reads: aggregated data from other services |
| **Scheduler (manager.py)** | Add daily_pick_generation job to chain | **EXTENDED** | Chains after `daily_trading_signal` |
| **API Router** | New `/api/coach/*` routes | **NEW router** | All new services |
| **Frontend** | New pages: `/coach`, `/journal`, `/goals` | **NEW pages** | New API endpoints |

## Data Model — New Tables

### Core Tables

```sql
-- 1. daily_picks: AI-selected daily trading recommendations
CREATE TABLE daily_picks (
    id BIGSERIAL PRIMARY KEY,
    pick_date DATE NOT NULL,
    ticker_id INTEGER NOT NULL REFERENCES tickers(id),
    rank INTEGER NOT NULL,              -- 1-5 (pick position)
    entry_price NUMERIC(12,2) NOT NULL,
    stop_loss NUMERIC(12,2) NOT NULL,
    take_profit_1 NUMERIC(12,2),
    take_profit_2 NUMERIC(12,2),
    risk_reward_ratio NUMERIC(4,2),
    reasoning TEXT NOT NULL,            -- Vietnamese explanation
    source_analysis_id BIGINT REFERENCES ai_analyses(id),  -- link to trading_signal
    composite_score NUMERIC(6,2) NOT NULL,  -- ranking score used for selection
    score_breakdown JSONB,              -- {technical: 8, fundamental: 7, ...}
    status VARCHAR(20) DEFAULT 'active', -- active/expired/followed
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(pick_date, ticker_id)
);

-- 2. trade_journal: Manual trade entries
CREATE TABLE trade_journal (
    id BIGSERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(id),
    trade_type VARCHAR(10) NOT NULL,    -- 'buy' or 'sell'
    entry_date DATE NOT NULL,
    entry_price NUMERIC(12,2) NOT NULL,
    quantity INTEGER NOT NULL,
    exit_date DATE,
    exit_price NUMERIC(12,2),
    fees NUMERIC(12,2) DEFAULT 0,       -- VN: 0.15% buy + 0.15% sell + 0.1% tax
    realized_pnl NUMERIC(14,2),         -- auto-calculated on close
    realized_pnl_pct NUMERIC(8,4),
    notes TEXT,
    linked_pick_id BIGINT REFERENCES daily_picks(id),  -- optional link
    tags JSONB DEFAULT '[]',            -- user-defined tags
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. user_risk_profile: Single-row, evolving risk preferences
CREATE TABLE user_risk_profile (
    id INTEGER PRIMARY KEY DEFAULT 1,   -- single user
    risk_level VARCHAR(20) NOT NULL DEFAULT 'moderate',  -- conservative/moderate/aggressive
    max_position_pct INTEGER DEFAULT 20,    -- max % of portfolio per position
    max_daily_picks INTEGER DEFAULT 5,
    preferred_sectors JSONB DEFAULT '[]',
    avoided_sectors JSONB DEFAULT '[]',
    min_rr_ratio NUMERIC(4,2) DEFAULT 1.5,
    preferred_timeframe VARCHAR(20) DEFAULT 'swing',
    last_adjusted_at TIMESTAMPTZ DEFAULT NOW(),
    adjustment_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. behavior_events: Raw event tracking
CREATE TABLE behavior_events (
    id BIGSERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,    -- 'ticker_view', 'pick_followed', 'trade_opened', etc.
    event_data JSONB NOT NULL,          -- {ticker: 'VNM', source: 'heatmap', ...}
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. goals: Monthly trading goals
CREATE TABLE goals (
    id BIGSERIAL PRIMARY KEY,
    month DATE NOT NULL UNIQUE,         -- first day of month
    target_pnl_pct NUMERIC(8,4),        -- target return %
    target_win_rate NUMERIC(5,2),
    max_drawdown_pct NUMERIC(8,4),
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. weekly_reviews: AI-generated weekly coaching reviews
CREATE TABLE weekly_reviews (
    id BIGSERIAL PRIMARY KEY,
    week_start DATE NOT NULL UNIQUE,
    trades_count INTEGER DEFAULT 0,
    realized_pnl NUMERIC(14,2) DEFAULT 0,
    win_rate NUMERIC(5,2),
    picks_followed INTEGER DEFAULT 0,
    picks_total INTEGER DEFAULT 0,
    behavior_summary JSONB,             -- aggregated behavior metrics
    ai_review TEXT,                      -- Gemini-generated coaching text
    risk_adjustment TEXT,               -- suggested risk level change
    model_version VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Indexes

```sql
CREATE INDEX idx_daily_picks_date ON daily_picks(pick_date DESC);
CREATE INDEX idx_daily_picks_ticker_date ON daily_picks(ticker_id, pick_date DESC);
CREATE INDEX idx_trade_journal_ticker ON trade_journal(ticker_id);
CREATE INDEX idx_trade_journal_entry_date ON trade_journal(entry_date DESC);
CREATE INDEX idx_trade_journal_exit_date ON trade_journal(exit_date DESC) WHERE exit_date IS NOT NULL;
CREATE INDEX idx_behavior_events_type_date ON behavior_events(event_type, occurred_at DESC);
CREATE INDEX idx_behavior_events_occurred ON behavior_events(occurred_at DESC);
CREATE INDEX idx_weekly_reviews_week ON weekly_reviews(week_start DESC);
```

## Data Flow

### Flow 1: Daily Pick Generation (automated, chains after trading_signal)

```
Existing Pipeline (unchanged):
  HOSE crawl → HNX crawl → UPCOM crawl
  → indicator_compute → ai_analysis (tech/fund)
  → news_crawl → sentiment → combined → trading_signal
  → hnx_upcom_analysis
                    │
                    ▼ NEW chain link
  daily_pick_generation (NEW job)
    │
    ├─ 1. Query today's ai_analyses: combined scores + trading signals
    │     for ALL tickers with score ≥ 6 and valid trading_signal
    │
    ├─ 2. Compute composite_score per ticker:
    │     = 0.35 × combined_score + 0.30 × trading_signal_confidence
    │       + 0.20 × volume_surge_score + 0.15 × sector_momentum
    │
    ├─ 3. Apply risk profile filters:
    │     - Skip avoided_sectors
    │     - Prefer preferred_sectors (boost +1)
    │     - Filter by min_rr_ratio from trading_signal
    │     - If risk_level='conservative': require combined ≥ 7
    │
    ├─ 4. Rank and select top N (from user_risk_profile.max_daily_picks)
    │
    ├─ 5. For each pick: extract entry/SL/TP from trading_signal.raw_response
    │     Build reasoning via Gemini (WHY this pick today, in Vietnamese)
    │     Store to daily_picks table
    │
    └─ 6. Mark yesterday's picks as 'expired' if not followed
```

**Scheduler integration** — Add to `manager.py._on_job_executed`:
```python
elif event.job_id in ("daily_hnx_upcom_analysis_triggered",):
    # Chain: hnx_upcom_analysis → daily_pick_generation
    from app.scheduler.jobs import daily_pick_generation
    scheduler.add_job(daily_pick_generation, id="daily_pick_generation_triggered", ...)
```

**Gemini budget impact**: 1 additional API call/day (batch of 5 picks for reasoning). Negligible vs. existing 800+ ticker analysis.

### Flow 2: Trade Journal → P&L Calculation

```
User Action (frontend form):
  POST /api/coach/journal/trades
    │
    ├─ Validate: ticker exists, price reasonable (±5% of last close)
    ├─ Auto-link: if ticker has today's daily_pick → set linked_pick_id
    ├─ Store to trade_journal
    └─ Track behavior_event: {type: 'trade_opened', ticker, entry_price}

Trade Close (frontend form):
  PATCH /api/coach/journal/trades/{id}/close
    │
    ├─ Set exit_date, exit_price
    ├─ Calculate realized_pnl:
    │     pnl = (exit_price - entry_price) × quantity - fees
    │     fees = entry_value × 0.0015 + exit_value × 0.0025  (VN market)
    │     pnl_pct = pnl / (entry_price × quantity) × 100
    ├─ Store realized_pnl, realized_pnl_pct
    └─ Track behavior_event: {type: 'trade_closed', pnl, hold_days}

Auto P&L (daily job, optional):
  For open trades: compute unrealized_pnl using latest daily_prices.close
  → Serves display only, NOT stored (avoids stale data)
```

### Flow 3: Behavior Tracking → Adaptive Strategy

```
Behavior Events Collected:
  ┌─────────────────────────────────────────┐
  │ ticker_view      — from frontend visits  │
  │ pick_viewed      — daily pick card click │
  │ pick_followed    — trade linked to pick  │
  │ pick_ignored     — pick expired unfollowed│
  │ trade_opened     — journal entry created │
  │ trade_closed     — journal entry closed  │
  │ analysis_viewed  — AI analysis page visit│
  │ heatmap_click    — market overview click │
  └─────────────────────────┬───────────────┘
                            │
         Weekly Aggregation (scheduled job, Sunday evening)
                            │
                            ▼
  BehaviorTracker.aggregate_weekly():
    ├─ Most viewed tickers (top 10)
    ├─ Average trade duration (days)
    ├─ Trading frequency (trades/week)
    ├─ Pick follow rate (followed/total)
    ├─ Preferred trading hours (from timestamps)
    ├─ Sector concentration (% per sector)
    └─ Win/loss streak detection

         Weekly Review Generation (chains after aggregation)
                            │
                            ▼
  AdaptiveStrategyEngine.evaluate():
    │
    ├─ IF win_rate < 40% over last 4 weeks:
    │     → Suggest risk_level downgrade (aggressive→moderate, moderate→conservative)
    │     → Increase min_rr_ratio by 0.5
    │
    ├─ IF win_rate > 65% over last 4 weeks AND avg_pnl_pct > 3%:
    │     → Suggest risk_level upgrade
    │     → Allow higher position sizes
    │
    ├─ IF sector_concentration > 60% in one sector:
    │     → Add diversification warning to review
    │
    ├─ IF pick_follow_rate < 20%:
    │     → Suggest reviewing pick criteria (maybe too conservative)
    │
    └─ Generate risk_adjustment recommendation
        → Store to weekly_reviews.risk_adjustment
        → User CONFIRMS or REJECTS via frontend
           (risk_profile only changes on explicit confirmation)
```

### Flow 4: Goal & Review System

```
Goal Setting (frontend form):
  POST /api/coach/goals
    │
    ├─ Store monthly target: target_pnl_pct, target_win_rate, max_drawdown
    └─ Calculate baseline from last 3 months of trading history

Weekly Check-in (automated, Sunday 20:00):
  daily_weekly_review job:
    │
    ├─ 1. Aggregate week's trades from trade_journal
    ├─ 2. Calculate: realized_pnl, win_rate, picks_followed
    ├─ 3. Aggregate behavior metrics from behavior_events
    ├─ 4. Run AdaptiveStrategyEngine.evaluate()
    ├─ 5. Build Gemini prompt with:
    │     - Week summary (trades, P&L)
    │     - Behavior patterns
    │     - Current vs target progress
    │     - Risk adjustment suggestion
    │
    ├─ 6. Call Gemini for coaching review (Vietnamese text)
    │     System instruction: "Act as a trading coach..."
    │     Structured output: {review_text, risk_suggestion, action_items}
    │
    └─ 7. Store to weekly_reviews table

Monthly Review:
  → Same flow but comparing month-end vs goals
  → Auto-suggest next month's goals based on trend
```

## Component Details

### New Backend Services

#### `services/coach/pick_generator.py` — DailyPickGenerator

```python
class DailyPickGenerator:
    """Selects top daily picks from today's analysis results.
    
    Follows the ContextBuilder → GeminiClient → Storage pattern.
    """
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def generate_daily_picks(self) -> list[DailyPick]:
        """Main entry point. Called by scheduler job."""
        # 1. Load risk profile
        profile = await self._get_risk_profile()
        # 2. Get candidates (combined score ≥ 6 + valid trading signal)
        candidates = await self._get_candidates(profile)
        # 3. Compute composite scores
        ranked = self._rank_candidates(candidates, profile)
        # 4. Select top N
        picks = ranked[:profile.max_daily_picks]
        # 5. Generate reasoning via Gemini
        picks_with_reasoning = await self._generate_reasoning(picks)
        # 6. Store
        await self._store_picks(picks_with_reasoning)
        # 7. Expire yesterday's unfollowed
        await self._expire_old_picks()
        return picks_with_reasoning
```

#### `services/coach/trade_journal_service.py` — TradeJournalService

```python
class TradeJournalService:
    """CRUD + P&L for trade journal entries."""
    
    async def open_trade(self, ticker_symbol: str, entry_price: float, 
                         quantity: int, notes: str = None) -> TradeJournal:
        """Create a new trade. Auto-links to daily pick if applicable."""
    
    async def close_trade(self, trade_id: int, exit_price: float, 
                          exit_date: date = None) -> TradeJournal:
        """Close trade, calculate realized P&L with VN fees."""
    
    async def get_open_trades(self) -> list[TradeJournal]:
        """All trades without exit_date."""
    
    async def get_trade_history(self, days: int = 30) -> list[TradeJournal]:
        """Closed trades within period."""
    
    async def get_unrealized_pnl(self) -> list[dict]:
        """Open trades with current market value from daily_prices."""
```

#### `services/coach/behavior_tracker.py` — BehaviorTracker

```python
class BehaviorTracker:
    """Records and aggregates user behavior events."""
    
    async def track_event(self, event_type: str, event_data: dict) -> None:
        """Record a single behavior event. Called from API endpoints."""
    
    async def aggregate_weekly(self, week_start: date) -> dict:
        """Aggregate behavior metrics for a given week."""
        # Returns: {top_tickers, avg_trade_duration, trade_frequency, 
        #           pick_follow_rate, sector_concentration, ...}
    
    async def cleanup_old_events(self, days: int = 90) -> int:
        """Purge events older than N days. behavior_events is high-volume."""
```

#### `services/coach/adaptive_strategy.py` — AdaptiveStrategyEngine

```python
class AdaptiveStrategyEngine:
    """Evaluates trading performance and suggests risk adjustments."""
    
    async def evaluate(self, lookback_weeks: int = 4) -> StrategyAdjustment:
        """Analyze recent performance and suggest risk profile changes.
        
        Returns StrategyAdjustment with:
        - suggested_risk_level
        - suggested_min_rr_ratio  
        - reasoning (why this change)
        - requires_confirmation: True (user must accept)
        """
    
    async def apply_adjustment(self, adjustment_id: int) -> UserRiskProfile:
        """User confirmed — apply the suggested changes to risk profile."""
    
    async def reject_adjustment(self, adjustment_id: int) -> None:
        """User rejected — log and keep current profile."""
```

### New API Routes

```python
# app/api/coach.py — NEW router
router = APIRouter(prefix="/coach", tags=["coach"])

# Daily Picks
GET  /coach/picks/today           → list[DailyPickResponse]
GET  /coach/picks/history?days=30 → list[DailyPickResponse]
POST /coach/picks/{id}/follow     → mark pick as followed

# Trade Journal
GET    /coach/journal/trades                → list[TradeJournalResponse]
GET    /coach/journal/trades/open           → list[TradeJournalResponse]  
POST   /coach/journal/trades                → TradeJournalResponse
PATCH  /coach/journal/trades/{id}/close     → TradeJournalResponse
DELETE /coach/journal/trades/{id}           → confirmation
GET    /coach/journal/summary?period=month  → TradeSummaryResponse

# Behavior (frontend calls this transparently)
POST /coach/behavior/track        → {ok: true}

# Risk Profile
GET   /coach/profile              → UserRiskProfileResponse
PATCH /coach/profile              → UserRiskProfileResponse

# Goals & Reviews
GET  /coach/goals/current         → GoalResponse
POST /coach/goals                 → GoalResponse
GET  /coach/reviews/weekly        → list[WeeklyReviewResponse]
GET  /coach/reviews/latest        → WeeklyReviewResponse

# Strategy Adjustments
GET  /coach/adjustments/pending   → StrategyAdjustmentResponse | null
POST /coach/adjustments/{id}/accept → UserRiskProfileResponse
POST /coach/adjustments/{id}/reject → confirmation
```

### New Scheduler Jobs

```python
# Added to scheduler/jobs.py

async def daily_pick_generation():
    """Generate daily picks. Chains after hnx_upcom_analysis.
    Runs Mon-Fri ~18:00+ (after full pipeline completes)."""
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_pick_generation")
        try:
            generator = DailyPickGenerator(session)
            picks = await generator.generate_daily_picks()
            await job_svc.complete(execution, status="success", 
                                   result_summary={"picks": len(picks)})
            await session.commit()
        except Exception as e:
            await job_svc.fail(execution, error=str(e))
            await session.commit()
            raise

async def weekly_review_generation():
    """Generate weekly coaching review. Runs Sunday 20:00."""
    async with async_session() as session:
        # 1. Aggregate behavior
        tracker = BehaviorTracker(session)
        behavior = await tracker.aggregate_weekly(get_last_monday())
        # 2. Evaluate strategy  
        engine = AdaptiveStrategyEngine(session)
        adjustment = await engine.evaluate()
        # 3. Generate review via Gemini
        review_service = GoalReviewService(session)
        await review_service.generate_weekly_review(behavior, adjustment)
        await session.commit()

async def behavior_cleanup():
    """Purge old behavior events. Runs monthly."""
    async with async_session() as session:
        tracker = BehaviorTracker(session)
        deleted = await tracker.cleanup_old_events(days=90)
```

### Frontend New Pages & Components

```
src/app/
  coach/                    # NEW: Daily picks dashboard
    page.tsx                # Today's picks + pick history
  journal/                  # NEW: Trade journal
    page.tsx                # Trade list + open positions + P&L summary
  goals/                    # NEW: Goals & reviews
    page.tsx                # Monthly goals + weekly reviews + strategy

src/components/
  daily-pick-card.tsx       # Single pick with entry/SL/TP, follow button
  trade-form.tsx            # Open/close trade form (modal or inline)
  pnl-summary-card.tsx      # Realized + unrealized P&L
  weekly-review-card.tsx    # AI coaching review display
  risk-profile-badge.tsx    # Current risk level indicator
  goal-progress-chart.tsx   # Progress toward monthly goal (Recharts)
  pick-follow-rate.tsx      # Pick follow rate visualization
  strategy-adjustment-banner.tsx  # Pending risk adjustment CTA
```

### Zustand Store Extensions

```typescript
// New store: src/lib/coach-store.ts
interface CoachState {
  riskProfile: RiskProfile | null;
  setRiskProfile: (profile: RiskProfile) => void;
  
  // Behavior tracking (fire-and-forget)
  trackEvent: (type: string, data: Record<string, unknown>) => void;
}
```

Behavior tracking uses fire-and-forget POST — failures are silently ignored (behavior data is supplementary, not critical).

## Patterns to Follow

### Pattern 1: Compose Services Like AIAnalysisService

**What:** The existing AIAnalysisService composes ContextBuilder + GeminiClient + AnalysisStorage. New coach services follow the same composition pattern.

**When:** Any service that touches multiple data sources or calls Gemini.

**Example:** DailyPickGenerator composes:
- `DailyPickContextBuilder` (reads ai_analyses, prices, indicators)
- `GeminiClient` (reuse existing, add `analyze_pick_reasoning_batch`)
- `DailyPickStorage` (writes daily_picks)

### Pattern 2: Job Chaining via EVENT_JOB_EXECUTED

**What:** The scheduler chains jobs via `_on_job_executed` listener. New jobs chain into the existing pipeline.

**When:** Daily pick generation must run AFTER the full analysis pipeline completes.

**Integration point:** Chain `daily_pick_generation` after `daily_hnx_upcom_analysis_triggered` in `manager.py`. This is the last job in the current chain.

### Pattern 3: Background Tasks for Non-Blocking Operations

**What:** Behavior tracking and event recording use FastAPI's `BackgroundTasks` to avoid blocking the user's request.

**When:** Any write operation that the user doesn't need to wait for.

**Example:**
```python
@router.post("/coach/behavior/track")
async def track_behavior(event: BehaviorEventRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(_record_event, event)
    return {"ok": True}
```

### Pattern 4: Gemini Lock for New AI Calls

**What:** The existing `_gemini_lock` serializes all Gemini access. New Gemini calls (pick reasoning, weekly review) must also acquire this lock.

**When:** Any new Gemini API call.

**Implementation:** Import `_gemini_lock` from `ai_analysis_service` or move it to a shared module. All new Gemini calls acquire the lock.

### Pattern 5: Single-User Simplification

**What:** No auth, no multi-user concerns. `user_risk_profile` is a single-row table. Trade journal has no user_id column.

**When:** All new features. Don't add user scoping — this is a personal tool (per PROJECT.md constraints).

## Anti-Patterns to Avoid

### Anti-Pattern 1: Modifying Existing AI Pipeline

**What:** Don't change how existing analysis types (technical, fundamental, sentiment, combined, trading_signal) work.

**Why bad:** The existing pipeline processes 800+ tickers daily with delicate rate limiting, batch sizing, and chaining. Any modification risks breaking the core analysis flow.

**Instead:** Daily picks READ from existing ai_analyses table. They don't modify the analysis pipeline — they consume its output.

### Anti-Pattern 2: Real-Time Behavior Tracking via WebSocket

**What:** Don't try to stream behavior events over WebSocket.

**Why bad:** The existing WebSocket (`/ws/prices`) is purpose-built for price streaming with 30s polling. Mixing behavior tracking into it adds complexity for negligible benefit.

**Instead:** Use simple POST requests for behavior events. They're low-volume (maybe 20-50 events/day for a single user). Fire-and-forget with `BackgroundTasks`.

### Anti-Pattern 3: Auto-Adjusting Risk Profile Without Confirmation

**What:** Don't let the AdaptiveStrategyEngine silently change the user's risk profile.

**Why bad:** Trading involves real money. Silently changing risk parameters could lead to unexpected position sizes or pick criteria. The user must stay in control.

**Instead:** AdaptiveStrategyEngine SUGGESTS changes → stored as pending → user CONFIRMS or REJECTS via frontend button. Risk profile only changes on explicit action.

### Anti-Pattern 4: Storing Unrealized P&L in the Database

**What:** Don't store unrealized P&L as a column in trade_journal.

**Why bad:** Unrealized P&L changes every day with price movements. Storing it creates stale data that must be recomputed anyway.

**Instead:** Calculate unrealized P&L on-the-fly by joining `trade_journal` (open trades) with latest `daily_prices.close`. Return in API response, never persist.

### Anti-Pattern 5: Over-Calling Gemini for Coaching

**What:** Don't call Gemini for every minor coaching insight (per-trade feedback, daily tips, etc.).

**Why bad:** Free tier is 15 RPM / 1500 RPD. The existing pipeline already uses most of this budget for 800+ ticker analysis.

**Instead:** Limit NEW Gemini calls to:
1. Daily pick reasoning: 1 call/day (batch of 5 picks)
2. Weekly review: 1 call/week
3. Total new budget: ~8 calls/week. Minimal impact.

### Anti-Pattern 6: Complex Trade Matching Logic

**What:** Don't implement FIFO/LIFO/average-cost matching for multiple lots of the same ticker.

**Why bad:** VN market trades are typically simple (buy → sell one lot). Over-engineering trade matching adds complexity for a single user who knows their own trades.

**Instead:** Each trade_journal entry is one buy→sell cycle. If user buys VNM twice, they create two journal entries. Keep it simple.

## Integration Points Summary

### Existing Components That Get Extended

| File | Change | Scope |
|------|--------|-------|
| `scheduler/manager.py` | Add chain link: `hnx_upcom → daily_pick_generation` | ~10 lines |
| `scheduler/manager.py` | Add `weekly_review_generation` cron job (Sunday 20:00) | ~15 lines |
| `scheduler/manager.py` | Add `behavior_cleanup` monthly job | ~10 lines |
| `scheduler/jobs.py` | Add 3 new job functions | ~100 lines |
| `api/router.py` | Include new `coach_router` | 2 lines |
| `models/__init__.py` | Import new models | 6 lines |
| `frontend/src/components/navbar.tsx` | Add Coach/Journal/Goals nav links | ~5 lines |
| `frontend/src/lib/api.ts` | Add new fetch functions for coach endpoints | ~80 lines |
| `frontend/src/lib/hooks.ts` | Add new React Query hooks | ~60 lines |

### Existing Components That Stay Untouched

- `services/analysis/*` — All existing AI analysis code
- `services/ai_analysis_service.py` — Orchestration stays the same
- `crawlers/*` — Data crawling unchanged
- `ws/prices.py` — WebSocket unchanged
- All existing models — No column changes
- All existing API endpoints — No modifications
- All existing frontend components — No changes

## Scalability Considerations

| Concern | Current (800 tickers) | At 2000 tickers | Notes |
|---------|----------------------|------------------|-------|
| Pick generation time | <10s (queries + 1 Gemini call) | <15s | Bottleneck is Gemini call, not DB queries |
| behavior_events volume | ~50 rows/day | ~200 rows/day | Cleanup job keeps <90 days. Add partition by month if needed later |
| trade_journal volume | ~5-10 rows/week | Same (single user) | Tiny table, no concern |
| Weekly review Gemini call | 1 call/week | 1 call/week | Fixed, not per-ticker |
| Aiven connection pool (5+3) | Adequate | Adequate | New services use same `async_session()` pattern |

## Build Order (Dependency-Based)

```
Phase 1: Data Foundation
  ├─ DB migrations (6 new tables)
  ├─ SQLAlchemy models  
  ├─ Pydantic schemas
  └─ user_risk_profile with defaults (must exist before picks)

Phase 2: Daily Picks
  ├─ DailyPickContextBuilder (reads existing ai_analyses)
  ├─ DailyPickGenerator service
  ├─ Scheduler chain integration
  ├─ API endpoints (GET picks)
  └─ Frontend: /coach page with pick cards

Phase 3: Trade Journal  
  ├─ TradeJournalService (CRUD)
  ├─ PnLEngine (fee calculation, P&L)
  ├─ Auto-link to daily picks
  ├─ API endpoints (CRUD trades)
  └─ Frontend: /journal page

Phase 4: Behavior Tracking + Adaptive Strategy
  ├─ BehaviorTracker service
  ├─ Frontend event tracking integration
  ├─ AdaptiveStrategyEngine
  ├─ Risk profile adjustment flow
  └─ Frontend: strategy adjustment banner

Phase 5: Goal & Review System
  ├─ GoalReviewService
  ├─ Weekly review Gemini prompt
  ├─ Scheduler: weekly_review_generation job
  ├─ API endpoints (goals, reviews)
  └─ Frontend: /goals page
```

**Rationale:** Phase 1 creates the schema everything depends on. Phase 2 (picks) is the core value — users see picks immediately. Phase 3 (journal) lets users act on picks. Phase 4 (behavior + strategy) requires journal data to be meaningful. Phase 5 (goals) requires all previous phases for comprehensive reviews.

## Sources

- Direct codebase inspection of all referenced files (HIGH confidence)
- Existing patterns from `services/analysis/` module (established in v1.0-v3.0)
- Scheduler chaining pattern from `scheduler/manager.py` (established in v1.0)
- VN market fee structure: 0.15% brokerage + 0.1% selling tax (MEDIUM confidence — varies by broker)
- Gemini free tier limits from PROJECT.md constraints (HIGH confidence)

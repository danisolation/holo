# Phase 43: Daily Picks Engine - Research

**Researched:** 2025-07-24
**Domain:** Backend scoring engine + Gemini explanation generation + FastAPI endpoints + Next.js coach page
**Confidence:** HIGH

## Summary

This phase builds a daily stock pick selection engine on top of the existing AI analysis pipeline. The codebase already produces trading signals (entry/SL/TP) for ~400 HOSE tickers daily via `daily_trading_signal_analysis`. Phase 43 adds a ranking/filtering layer that selects 3-5 LONG picks based on composite scoring (signal confidence × 0.4 + combined score × 0.3 + safety score × 0.3), filters by user capital affordability, and generates Vietnamese explanations via a single Gemini API call. Results are persisted in 2 new DB tables (`daily_picks` + `user_risk_profile`) and served via 4 new API endpoints, consumed by a new `/coach` frontend page.

The core technical challenge is correctly reading existing `ai_analyses.raw_response` JSONB (which stores full `TickerTradingSignal` objects for trading_signal analysis type), joining with `technical_indicators` for safety metrics (ATR, ADX, volume), and `daily_prices` for affordability filtering — all within a single job that chains after the existing `daily_trading_signal_analysis` job. The Gemini explanation call is the only new AI cost (~1 call/day for 3-5 picks).

**Primary recommendation:** Build `PickService` as a new service class following the existing service pattern (e.g., `AIAnalysisService`), chain the pick generation job after `daily_trading_signal_triggered` in the existing job chain, and reuse all existing frontend patterns (React Query hooks, shadcn/ui components, WebSocket `RealtimePriceProvider`).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Generate daily picks after `daily_trading_signal_analysis` job chain (~17:00) — uses same-day analysis results
- Composite score: trading_signal_confidence×0.4 + combined_score×0.3 + safety_score×0.3 (safety = low ATR + high ADX + adequate volume)
- Filter from top 50 LONG tickers with score>0, then apply capital + safety filters → select top 3-5
- Default capital 50,000,000 VND, configurable in user_risk_profile table
- 200-300 word Vietnamese explanation per pick — 1 Gemini call batching all 3-5 picks with coaching-style prompt
- "Almost selected" displayed as collapsible list, 1 line per ticker
- Position sizing format: "Mua 200 cổ × 60,000đ = 12,000,000 VND (24% vốn)" — calculated by 100-share lots, round down
- Entry/SL/TP inherited directly from TradingPlanDetail.long_analysis — no recalculation
- 2 new tables: `daily_picks` + `user_risk_profile`
- New route `/coach` with navbar entry "Huấn luyện"
- API endpoints: GET /api/picks/today, GET /api/picks/history, GET /api/profile, PUT /api/profile
- Pick card layout: symbol + name + explanation on top, entry/SL/TP + position sizing as badges below
- Live price on pick cards via existing WebSocket — shows unrealized P&L from entry
- Picks are BUY-only (no short selling in VN retail market)
- Only LONG direction from trading signals
- Lot size is 100 shares for HOSE
- Gemini budget impact: 1 extra call/day for pick explanations (within free tier)

### the agent's Discretion
No items deferred to the agent's discretion — all decisions captured above.

### Deferred Ideas (OUT OF SCOPE)
- Trade journal linking to picks (Phase 44)
- Pick outcome tracking with SL/TP hit detection (Phase 45)
- Adaptive pick scoring based on user trade history (Phase 46)
- Risk level adjustment affecting pick aggressiveness (Phase 46-47)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PICK-01 | Mỗi ngày app chọn 3-5 mã cụ thể nên mua, dựa trên composite scoring từ AI analysis có sẵn | Composite scoring from `ai_analyses` table: trading_signal confidence (raw_response JSONB) × 0.4 + combined score × 0.3 + safety score × 0.3. Job chains after `daily_trading_signal_triggered`. |
| PICK-02 | Picks được lọc theo vốn (<50M VND) — chỉ gợi ý mã mà user mua được ít nhất 1 lot (100 cổ) | Filter: `price × 100 <= user_capital`. Price from `daily_prices.close`. Capital from `user_risk_profile.capital` (default 50M). |
| PICK-03 | Picks ưu tiên an toàn — penalize mã có ATR cao, ADX thấp, volume thấp | Safety score from `technical_indicators` (ATR, ADX) + `daily_prices` (volume). Penalize: high ATR = volatile, low ADX = no trend, low volume = illiquid. |
| PICK-04 | Mỗi pick kèm giải thích tiếng Việt 200-300 từ | Single Gemini call batching 3-5 picks. Reuse existing `GeminiClient._call_gemini_with_retry()` with coaching-style system instruction. |
| PICK-05 | Mỗi pick có giá vào, SL, TP kế thừa từ trading signal pipeline | Inherited from `ai_analyses.raw_response` where `analysis_type='trading_signal'`. The `long_analysis.trading_plan` contains entry_price, stop_loss, take_profit_1, take_profit_2. |
| PICK-06 | Mỗi pick hiển thị position sizing: "Mua X cổ × Y đồng = Z VND (N% vốn)" | Compute: `shares = floor(capital × position_pct / 100 / price / 100) × 100`. Display: `formatVND()` utilities. |
| PICK-07 | Top 5-10 mã "suýt được chọn" kèm 1 câu giải thích | Tickers ranked #6-15 after scoring. Rejection reason generated from scoring data: RSI overbought, volume too low, ATR too high, etc. |
</phase_requirements>

## Standard Stack

### Core (No New Dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | ~2.0 | ORM for `daily_picks` + `user_risk_profile` tables | Already used for all 11 existing models [VERIFIED: codebase models/__init__.py] |
| Alembic | ~1.18 | DB migration (migration 019) | Already used, latest migration is 018 [VERIFIED: codebase alembic/versions/] |
| FastAPI | ~0.135 | New `/api/picks` + `/api/profile` routers | Already used for all 5 existing routers [VERIFIED: codebase api/router.py] |
| google-genai | 1.73.1 | Gemini API for pick explanations | Already installed and used by GeminiClient [VERIFIED: pip show google-genai] |
| APScheduler | 3.11 | Job chaining for pick generation | Already used for all scheduled jobs [VERIFIED: codebase scheduler/manager.py] |
| @tanstack/react-query | ^5.99.0 | Frontend data fetching for picks/profile | Already used for all API hooks [VERIFIED: package.json] |
| shadcn/ui | 4.x | Card, Badge, Skeleton, Accordion, Button, Input, Dialog components | Already installed, all needed components available [VERIFIED: components/ui/] |

### New Frontend Dependencies (Phase 43)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-hook-form | latest | Profile settings form (capital + risk level) | Capital input + risk level form on profile settings dialog |
| zod | ^3.x (direct dep) | Schema validation for profile form | Validate capital > 0, risk level 1-5 |
| @hookform/resolvers | latest | Connect zod schemas to react-hook-form | Profile settings form validation |

**Note:** `zod` is currently only a transitive dependency (via shadcn/eslint). It needs to be added as a **direct** dependency. `react-hook-form` and `@hookform/resolvers` are not installed at all. [VERIFIED: npm ls react-hook-form returns empty, npm ls zod shows only transitive deps]

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| react-hook-form + zod | Uncontrolled form with manual validation | Profile settings is simple (2 fields), but RHF+zod is the v8.0 standard per STATE.md for future forms |
| Separate Gemini call per pick | Batch all 3-5 picks in 1 call | Batching saves API quota; 1 call for 3-5 picks stays well within free tier |
| Compute composite score in Python | Compute in SQL query | Python is clearer for business logic; SQL for aggregation gets complex with JSONB extraction |

**Installation:**
```bash
cd frontend
npm install react-hook-form zod @hookform/resolvers
```

## Architecture Patterns

### Recommended Project Structure
```
backend/
├── app/
│   ├── models/
│   │   ├── daily_pick.py          # NEW: DailyPick model
│   │   └── user_risk_profile.py   # NEW: UserRiskProfile model
│   ├── services/
│   │   └── pick_service.py        # NEW: PickService (scoring, filtering, explanation)
│   ├── api/
│   │   └── picks.py               # NEW: /api/picks + /api/profile router
│   ├── scheduler/
│   │   ├── jobs.py                # MODIFY: add daily_pick_generation() job
│   │   └── manager.py            # MODIFY: add chain after trading_signal, add job name
│   └── schemas/
│       └── picks.py               # NEW: Pydantic schemas for pick API responses
├── alembic/versions/
│   └── 019_daily_picks_tables.py  # NEW: migration for 2 tables

frontend/
├── src/
│   ├── app/
│   │   └── coach/
│   │       └── page.tsx           # NEW: /coach page
│   ├── components/
│   │   ├── pick-card.tsx          # NEW: PickCard + PickCardSkeleton
│   │   ├── almost-selected-list.tsx # NEW: AlmostSelectedList
│   │   ├── profile-settings-card.tsx # NEW: ProfileSettingsCard dialog
│   │   └── navbar.tsx             # MODIFY: add "Huấn luyện" nav link
│   └── lib/
│       ├── api.ts                 # MODIFY: add pick/profile types + fetch functions
│       └── hooks.ts               # MODIFY: add useDailyPicks, useProfile, useUpdateProfile hooks
```

### Pattern 1: Service Class Pattern (PickService)
**What:** New `PickService` class follows the same async session + composed services pattern
**When to use:** For all business logic — scoring, filtering, Gemini explanation generation
**Example:**
```python
# Source: existing AIAnalysisService pattern in codebase
class PickService:
    def __init__(self, session: AsyncSession, api_key: str | None = None):
        self.session = session
        key = api_key or settings.gemini_api_key
        self.client = genai.Client(api_key=key)
        self.model = settings.gemini_model

    async def generate_daily_picks(self) -> dict:
        """Main entry: score → filter → rank → explain → store."""
        # 1. Fetch all LONG trading signals from today
        # 2. Join with combined scores + technical indicators
        # 3. Compute composite score per ticker
        # 4. Filter by capital affordability
        # 5. Apply safety scoring
        # 6. Select top 3-5 → generate explanations
        # 7. Select next 5-10 → generate rejection reasons
        # 8. Store in daily_picks table
```

### Pattern 2: Job Chaining (Scheduler)
**What:** New job chains after `daily_trading_signal_triggered` via `EVENT_JOB_EXECUTED` listener
**When to use:** Automatic daily pick generation
**Example:**
```python
# Source: existing pattern in manager.py _on_job_executed()
elif event.job_id in ("daily_trading_signal_triggered", "daily_trading_signal_manual"):
    from app.scheduler.jobs import daily_pick_generation
    logger.info("Chaining: daily_trading_signal → daily_pick_generation")
    scheduler.add_job(
        daily_pick_generation,
        id="daily_pick_generation_triggered",
        replace_existing=True,
        misfire_grace_time=3600,
    )
```

### Pattern 3: DB Session in Jobs
**What:** Jobs create their own `async_session()` context (not FastAPI Depends)
**When to use:** For `daily_pick_generation` job
**Example:**
```python
# Source: existing pattern in scheduler/jobs.py
async def daily_pick_generation():
    logger.info("=== DAILY PICK GENERATION START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("daily_pick_generation")
        try:
            service = PickService(session)
            result = await service.generate_daily_picks()
            # ... standard job tracking pattern
```

### Pattern 4: React Query Hooks + API Fetch
**What:** New hooks follow `useTickers()`/`useAnalysisSummary()` pattern
**When to use:** For `useDailyPicks()`, `useProfile()`, `useUpdateProfile()`
**Example:**
```typescript
// Source: existing pattern in lib/hooks.ts
export function useDailyPicks() {
  return useQuery({
    queryKey: ["picks", "today"],
    queryFn: () => fetchDailyPicks(),
    staleTime: 5 * 60 * 1000,  // 5 min — picks update once/day
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ProfileUpdate) => updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      queryClient.invalidateQueries({ queryKey: ["picks", "today"] });
    },
  });
}
```

### Pattern 5: JSONB Extraction from ai_analyses.raw_response
**What:** Trading signal data stored as JSONB in `ai_analyses.raw_response` with full `TickerTradingSignal` structure
**When to use:** Reading entry/SL/TP + confidence for composite scoring
**Example:**
```python
# Source: verified in ai_analysis_service.py line 551
# raw_response = analysis.model_dump() → stores full TickerTradingSignal as JSONB
# Structure: {ticker, recommended_direction, long_analysis: {direction, confidence, trading_plan: {entry_price, stop_loss, take_profit_1, ...}}}

# SQLAlchemy JSONB query:
stmt = (
    select(
        AIAnalysis.ticker_id,
        AIAnalysis.raw_response["long_analysis"]["confidence"].as_integer(),
        AIAnalysis.raw_response["long_analysis"]["trading_plan"]["entry_price"].as_float(),
        AIAnalysis.score,  # This is the recommended direction's confidence
    )
    .where(
        AIAnalysis.analysis_type == AnalysisType.TRADING_SIGNAL,
        AIAnalysis.analysis_date == today,
        AIAnalysis.signal == "long",  # Only LONG recommended tickers
    )
)
```

### Anti-Patterns to Avoid
- **Re-analyzing tickers for picks:** Don't call Gemini for scoring — composite score is a pure calculation from existing data. Only 1 Gemini call for explanations.
- **Storing position sizing in the database:** Position sizing depends on user capital which can change. Compute it on-the-fly in the API response. Store the raw pick data (entry, shares formula inputs), compute display values at read time.
- **Recalculating entry/SL/TP:** Per CONTEXT.md — inherit directly from `TradingPlanDetail.long_analysis`. No recalculation.
- **Filtering only by `recommended_direction == 'long'`:** Also need `signal != 'invalid'` to exclude tickers that failed post-validation.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Position sizing with lot rounding | Custom rounding logic | `math.floor(shares / 100) * 100` | VN HOSE lot = 100 shares; simple but must round DOWN, not nearest |
| Vietnamese number formatting | Custom format function | Existing `formatVND()` in `lib/format.ts` | Already handles `Intl.NumberFormat("vi-VN")` [VERIFIED: codebase] |
| Date formatting (DD/MM/YYYY) | Custom date format | Existing `formatDateVN()` in `lib/format.ts` | Already handles Vietnamese convention [VERIFIED: codebase] |
| Score bar visualization | Custom progress bar | Existing `ScoreBar` component from `analysis-card.tsx` | Already handles 1-10 scale with color coding [VERIFIED: codebase] |
| Live price WebSocket | Custom WebSocket | Existing `useRealtimePrices()` hook | Already handles subscribe/unsubscribe, market hours, reconnect [VERIFIED: codebase] |
| Form validation | Manual validation logic | `react-hook-form` + `zod` | Standard for v8.0 per STATE.md research context |
| Gemini API retry/circuit breaker | Custom retry | Existing `GeminiClient._call_gemini_with_retry()` + `gemini_breaker` | Already has tenacity retry + circuit breaker [VERIFIED: codebase] |

**Key insight:** Almost everything needed already exists — this phase is a composition layer, not a foundation-building exercise. The only genuinely new code is: composite scoring algorithm, safety scoring formula, Gemini explanation prompt, and frontend pick cards.

## Common Pitfalls

### Pitfall 1: JSONB Extraction Type Casting
**What goes wrong:** SQLAlchemy JSONB path extraction returns `JSON` type, not Python float/int. Comparisons and math fail silently or raise type errors.
**Why it happens:** PostgreSQL JSONB operators return `jsonb` type; you need explicit casts.
**How to avoid:** Use `.as_float()`, `.as_integer()`, or `cast()` when extracting from JSONB columns for arithmetic operations. Alternatively, extract raw_response in Python and deserialize with Pydantic: `TickerTradingSignal.model_validate(row.raw_response)`.
**Warning signs:** Scores always 0, or TypeError in composite calculation.

### Pitfall 2: Missing Trading Signal Data
**What goes wrong:** Some tickers don't have trading_signal analysis for today (failed batch, validation failure, or skipped due to missing ATR).
**Why it happens:** The trading signal pipeline skips tickers without ATR data [VERIFIED: context_builder.py line 296], and failed validations store `signal='invalid', score=0`.
**How to avoid:** Filter for `signal IN ('long')` AND `score > 0`. Don't assume all 400 tickers have valid trading signals. Expect 200-350 usable LONG signals on any given day.
**Warning signs:** `daily_picks` table always empty, or picks include invalid signals.

### Pitfall 3: Stale Combined Scores
**What goes wrong:** Using combined analysis score from a different date than the trading signal.
**Why it happens:** Combined analysis runs before trading signals in the chain. If either fails, dates may mismatch.
**How to avoid:** Join on `analysis_date = today` for BOTH types. If combined analysis is missing for a ticker, use a neutral score (5) as fallback. Log a warning.
**Warning signs:** Composite scores don't change day-to-day, or sudden score jumps.

### Pitfall 4: Division by Zero in Safety Scoring
**What goes wrong:** ATR = 0, ADX = 0, or volume = 0 causes division errors in normalization.
**Why it happens:** Some tickers have NULL or 0 indicator values (newly listed, insufficient data).
**How to avoid:** Guard against None/0 values. Skip tickers with None ATR/ADX. For volume, use a minimum threshold (e.g., > 10,000 shares avg).
**Warning signs:** NaN in composite scores, or crashes in the pick generation job.

### Pitfall 5: Position Sizing Off-by-One with Lot Sizes
**What goes wrong:** Position sizing doesn't respect 100-share lot sizes, or suggests more capital than available.
**Why it happens:** Dividing capital by price without rounding down to lot boundaries.
**How to avoid:** Formula: `lots = floor(max_spend / (price * 100)); shares = lots * 100; total = shares * price`. Where `max_spend = capital * position_size_pct / 100`. Verify `total <= capital`.
**Warning signs:** "Mua 150 cổ" (not a multiple of 100), or total VND exceeds user capital.

### Pitfall 6: Job Chain Break When HNX/UPCOM Analysis is Removed
**What goes wrong:** Currently, the chain after `daily_trading_signal_triggered` goes to `daily_hnx_upcom_analysis`. Adding pick generation here could break the HNX/UPCOM chain.
**Why it happens:** The `_on_job_executed` listener uses `elif` — only one chain per job ID. Need to handle both chains.
**How to avoid:** Chain pick generation after `daily_trading_signal_triggered` (alongside HNX/UPCOM), OR chain it after `daily_hnx_upcom_analysis_triggered` as the very last step. The latter is safer since it ensures ALL analysis is complete. **Recommendation:** Chain after `daily_hnx_upcom_analysis_triggered` (the last job in the current chain).
**Warning signs:** HNX/UPCOM analysis stops running after pick generation is added.

### Pitfall 7: Gemini Explanation Token Budget
**What goes wrong:** 200-300 words × 5 picks = 1000-1500 words output. With coaching context, this can exceed token limits.
**Why it happens:** Default `max_output_tokens=16384` is plenty, but system instruction + pick context + response all count.
**How to avoid:** Use the standard `_call_gemini_with_retry()` with default token settings (16384 output tokens is sufficient for ~1500 words). Include clear word count constraints in the prompt.
**Warning signs:** Truncated explanations, or Gemini returning fewer picks than requested.

## Code Examples

### Composite Scoring Algorithm
```python
# Source: CONTEXT.md locked decision
def compute_composite_score(
    trading_signal_confidence: int,  # 1-10 from long_analysis.confidence
    combined_score: int,             # 1-10 from combined analysis
    safety_score: float,             # 0-10 computed from ATR/ADX/volume
) -> float:
    """Composite = confidence×0.4 + combined×0.3 + safety×0.3"""
    return (
        trading_signal_confidence * 0.4
        + combined_score * 0.3
        + safety_score * 0.3
    )
```

### Safety Score Computation
```python
# Source: CONTEXT.md — safety = low ATR + high ADX + adequate volume
def compute_safety_score(
    atr_14: float,
    adx_14: float,
    avg_volume: int,
    current_price: float,
) -> float:
    """Safety score 0-10. High = safer pick.
    
    Components (each 0-10, then averaged):
    - ATR score: lower relative ATR = higher score (less volatile)
    - ADX score: higher ADX = higher score (stronger trend)
    - Volume score: higher volume = higher score (more liquid)
    """
    # ATR as % of price (relative volatility)
    atr_pct = (atr_14 / current_price * 100) if current_price > 0 else 10
    # Invert: low ATR% = high score. ATR% < 1% → 10, > 5% → 0
    atr_score = max(0, min(10, (5 - atr_pct) * 2.5))
    
    # ADX: > 25 = trending. Scale: 0 → 0, 25 → 5, 50+ → 10
    adx_score = max(0, min(10, adx_14 / 5))
    
    # Volume: > 500k = liquid. Scale: 0 → 0, 250k → 5, 500k+ → 10
    vol_score = max(0, min(10, avg_volume / 50000))
    
    return (atr_score + adx_score + vol_score) / 3
```

### Position Sizing Calculation
```python
# Source: CONTEXT.md locked decision
def compute_position_sizing(
    capital: int,           # e.g., 50_000_000 VND
    entry_price: float,     # e.g., 60_000 VND
    position_pct: int,      # e.g., 8 (percent from trading plan)
) -> dict:
    """Compute VN lot-aligned position sizing.
    
    Returns: {shares, total_vnd, capital_pct}
    """
    max_spend = capital * position_pct / 100
    lot_size = 100  # HOSE standard
    lots = int(max_spend / (entry_price * lot_size))
    if lots < 1:
        lots = 1  # Minimum 1 lot if affordable
    shares = lots * lot_size
    total_vnd = shares * entry_price
    capital_pct = total_vnd / capital * 100
    return {
        "shares": shares,
        "total_vnd": total_vnd,
        "capital_pct": round(capital_pct, 1),
    }
```

### Rejection Reason Generation (Almost-Selected)
```python
# Source: CONTEXT.md + safety scoring logic
def generate_rejection_reason(
    rsi: float | None,
    atr_pct: float,
    adx: float | None,
    avg_volume: int,
    composite_score: float,
) -> str:
    """Generate a 1-line Vietnamese explanation for why ticker wasn't selected."""
    reasons = []
    if rsi is not None and rsi > 70:
        reasons.append(f"RSI overbought ({rsi:.0f}), chờ pullback")
    if atr_pct > 4:
        reasons.append(f"Biến động cao (ATR {atr_pct:.1f}%)")
    if adx is not None and adx < 20:
        reasons.append(f"Xu hướng yếu (ADX {adx:.0f})")
    if avg_volume < 100_000:
        reasons.append(f"Volume quá thấp (avg {avg_volume:,.0f}/ngày)")
    if not reasons:
        reasons.append(f"Điểm tổng hợp thấp hơn ({composite_score:.1f})")
    return ", ".join(reasons[:2])  # Max 2 reasons per line
```

### Gemini Pick Explanation Prompt
```python
# Source: Pattern from existing prompts.py + CONTEXT.md coaching style
PICK_EXPLANATION_SYSTEM_INSTRUCTION = (
    "Bạn là huấn luyện viên đầu tư cá nhân cho nhà đầu tư mới tại Việt Nam. "
    "Viết giải thích 200-300 từ cho MỖI mã cổ phiếu được chọn. "
    "Phong cách: thân thiện, rõ ràng, như đang dạy bạn bè. "
    "Nội dung mỗi giải thích PHẢI bao gồm:\n"
    "1. Tại sao chọn mã này (kỹ thuật: RSI, MACD, support/resistance)\n"
    "2. Điểm mạnh cơ bản (P/E, ROE, tăng trưởng)\n"
    "3. Tâm lý thị trường hiện tại cho mã\n"
    "4. Rủi ro cần lưu ý và mức cắt lỗ\n"
    "KHÔNG dùng thuật ngữ tiếng Anh trừ tên chỉ báo (RSI, MACD, P/E). "
    "Dùng ví dụ số cụ thể từ dữ liệu.\n"
)
```

### Database Models
```python
# Source: CONTEXT.md data model decisions
# daily_pick.py
class PickStatus(str, enum.Enum):
    PICKED = "picked"
    ALMOST = "almost"

class DailyPick(Base):
    __tablename__ = "daily_picks"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    pick_date: Mapped[date] = mapped_column(Date, nullable=False)
    ticker_id: Mapped[int] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1-5 for picked, NULL for almost
    composite_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    entry_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    stop_loss: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    take_profit_1: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    take_profit_2: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    risk_reward: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    position_size_shares: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position_size_vnd: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    position_size_pct: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)  # Vietnamese, 200-300 words
    status: Mapped[str] = mapped_column(String(10), nullable=False)  # "picked" or "almost"
    rejection_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    
    __table_args__ = (
        UniqueConstraint("pick_date", "ticker_id", name="uq_daily_picks_date_ticker"),
    )

# user_risk_profile.py — single-row table
class UserRiskProfile(Base):
    __tablename__ = "user_risk_profile"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    capital: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, server_default="50000000")
    risk_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default="3")  # 1-5
    broker_fee_pct: Mapped[Decimal] = mapped_column(Numeric(5, 3), nullable=False, server_default="0.150")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
```

### API Response Schema
```python
# Source: CONTEXT.md + UI-SPEC data flow
class DailyPickResponse(BaseModel):
    pick_date: str
    ticker_symbol: str
    ticker_name: str
    rank: int | None
    composite_score: float
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float | None
    risk_reward: float
    position_size_shares: int
    position_size_vnd: int
    position_size_pct: float
    explanation: str | None
    status: str  # "picked" or "almost"
    rejection_reason: str | None

class DailyPicksResponse(BaseModel):
    date: str
    capital: int
    picks: list[DailyPickResponse]
    almost_selected: list[DailyPickResponse]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual stock picking | AI composite scoring from existing pipeline | Phase 43 (new) | Fully automated daily pick generation |
| Trading signals as standalone | Signals → Picks ranking layer | Phase 43 (new) | Adds user-facing actionability to raw signals |

**Existing infrastructure leveraged:**
- Trading signal pipeline (Phase 19) — entry/SL/TP generation [VERIFIED: codebase]
- Combined analysis (Phase 3) — holistic scoring [VERIFIED: codebase]
- Technical indicators (Phase 2/17) — ATR, ADX, RSI, volume [VERIFIED: codebase]
- WebSocket real-time prices (Phase 16) — live P&L on pick cards [VERIFIED: codebase]
- Job chaining (Phase 2+) — automatic pipeline execution [VERIFIED: codebase]

## Assumptions Log

> List all claims tagged `[ASSUMED]` in this research.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Safety score formula (ATR%→score, ADX→score, vol→score scaling) produces reasonable 0-10 values | Code Examples | Picks may be poorly ranked; fix by tuning thresholds based on actual data distribution |
| A2 | ~200-350 tickers will have valid LONG signals on any given day | Pitfall 2 | If fewer, may not reach 3-5 picks; add fallback messaging |
| A3 | 1 Gemini call with 5 picks × 300 words fits comfortably in default token limits | Pitfall 7 | Could truncate; increase max_output_tokens if needed |
| A4 | Chaining after `daily_hnx_upcom_analysis_triggered` is the safest insertion point | Pitfall 6 | If HNX/UPCOM analysis fails, picks won't generate; alternative: chain after trading_signal with parallel branch |

## Open Questions

1. **Safety score thresholds**
   - What we know: ATR, ADX, volume data exists in `technical_indicators` table
   - What's unclear: Exact distribution of ATR% and volume across HOSE tickers — are the thresholds (ATR% < 5%, ADX > 25, vol > 500k) reasonable?
   - Recommendation: Start with the proposed thresholds, log distribution statistics in the first week, tune if picks are consistently low-quality. The scoring is stored alongside picks, so retroactive analysis is possible.

2. **Position sizing: use trading_plan.position_size_pct or fixed formula?**
   - What we know: `TradingPlanDetail` includes `position_size_pct` (1-100) from Gemini's recommendation
   - What's unclear: Whether Gemini's suggested % is appropriate for a 50M VND account (it may suggest 8% = 4M per position, which is reasonable, but could also suggest 20% for high-confidence picks)
   - Recommendation: Use Gemini's `position_size_pct` as-is, capped at 30% max per position. This preserves the AI's risk assessment while preventing over-concentration.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + Playwright (frontend E2E) |
| Config file | `backend/pytest.ini` + `frontend/playwright.config.ts` |
| Quick run command | `cd backend && python -m pytest tests/ -x --tb=short` |
| Full suite command | `cd backend && python -m pytest tests/ && cd ../frontend && npx playwright test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PICK-01 | Composite scoring selects 3-5 picks | unit | `pytest tests/test_pick_service.py::test_composite_scoring -x` | ❌ Wave 0 |
| PICK-02 | Capital filter excludes unaffordable tickers | unit | `pytest tests/test_pick_service.py::test_capital_filter -x` | ❌ Wave 0 |
| PICK-03 | Safety scoring penalizes high ATR/low ADX/low vol | unit | `pytest tests/test_pick_service.py::test_safety_scoring -x` | ❌ Wave 0 |
| PICK-04 | Gemini generates Vietnamese explanations | unit (mock) | `pytest tests/test_pick_service.py::test_explanation_generation -x` | ❌ Wave 0 |
| PICK-05 | Entry/SL/TP inherited from trading signal | unit | `pytest tests/test_pick_service.py::test_entry_sl_tp_inheritance -x` | ❌ Wave 0 |
| PICK-06 | Position sizing respects lot sizes | unit | `pytest tests/test_pick_service.py::test_position_sizing -x` | ❌ Wave 0 |
| PICK-07 | Almost-selected with rejection reasons | unit | `pytest tests/test_pick_service.py::test_almost_selected -x` | ❌ Wave 0 |
| ALL | /coach page loads, shows picks | E2E | `npx playwright test e2e/page-smoke.spec.ts` | ❌ Wave 0 (add /coach route) |
| ALL | API endpoints return valid responses | E2E | `npx playwright test e2e/api-smoke.spec.ts` | ❌ Wave 0 (add /api/picks endpoints) |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_pick_service.py -x --tb=short`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x --tb=short`
- **Phase gate:** Full backend tests + frontend build + Playwright smoke

### Wave 0 Gaps
- [ ] `tests/test_pick_service.py` — covers PICK-01 through PICK-07 (unit tests with mocked DB)
- [ ] `tests/test_picks_api.py` — covers API endpoint response schemas
- [ ] Update `e2e/fixtures/test-helpers.ts` — add `/coach` to `APP_ROUTES`
- [ ] Framework install: None needed (pytest already configured, asyncio_mode=auto)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user app, no auth |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | Single user |
| V5 Input Validation | yes | Pydantic for all API inputs (capital > 0, risk_level 1-5) |
| V6 Cryptography | no | No secrets handled in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Invalid capital value (negative, zero) | Tampering | Pydantic validation: `capital > 0`, `risk_level ge=1 le=5` |
| SQL injection via profile update | Tampering | SQLAlchemy parameterized queries (already standard) |
| Gemini prompt injection via ticker data | Tampering | Data comes from own DB (not user input); low risk |

## Sources

### Primary (HIGH confidence)
- **Codebase inspection** — All models, services, API routers, scheduler, frontend hooks, UI components verified directly
- `backend/app/services/ai_analysis_service.py` — Trading signal pipeline, batching, JSONB storage pattern
- `backend/app/scheduler/manager.py` — Job chaining pattern with `EVENT_JOB_EXECUTED`
- `backend/app/schemas/analysis.py` — `TickerTradingSignal`, `TradingPlanDetail` schemas
- `backend/app/services/analysis/context_builder.py` — ATR, ADX, price data extraction
- `frontend/src/lib/api.ts` — `apiFetch<T>()` pattern, existing type definitions
- `frontend/src/lib/hooks.ts` — React Query hook patterns with `staleTime`
- `frontend/src/components/analysis-card.tsx` — `ScoreBar` component (reusable)
- `frontend/src/lib/use-realtime-prices.ts` — WebSocket integration pattern
- `.planning/phases/43-daily-picks-engine/43-CONTEXT.md` — All locked decisions
- `.planning/phases/43-daily-picks-engine/43-UI-SPEC.md` — Complete UI contract

### Secondary (MEDIUM confidence)
- pip verified: google-genai 1.73.1 installed [VERIFIED: pip show]
- npm verified: react-hook-form NOT installed, zod only transitive [VERIFIED: npm ls]
- Alembic migration count: 018 is latest [VERIFIED: filesystem listing]

### Tertiary (LOW confidence)
- Safety score threshold values (A1 in assumptions) — need real data distribution to validate

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new backend deps, 3 small frontend deps (well-known libraries)
- Architecture: HIGH — 100% follows existing codebase patterns verified by direct inspection
- Pitfalls: HIGH — identified from actual codebase structure and data flow analysis
- Scoring algorithm: MEDIUM — thresholds are reasonable defaults but may need tuning

**Research date:** 2025-07-24
**Valid until:** 2025-08-24 (stable — no external dependency changes expected)

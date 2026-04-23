# Phase 46: Behavior Tracking & Adaptive Strategy - Research

**Researched:** 2026-04-23
**Domain:** Behavioral analytics, adaptive scoring, user habit detection (FastAPI + SQLAlchemy + React)
**Confidence:** HIGH

## Summary

Phase 46 adds four interconnected features to the Holo trading coach: (1) viewing behavior tracking — logging which tickers the user views most, (2) trading habit detection — identifying patterns like premature profit-taking, holding losers, and impulsive trading, (3) risk level management — suggesting risk reductions after consecutive losses, and (4) sector preference learning — biasing future picks toward sectors where the user trades profitably.

All four features are analytics layers built on top of existing data (Trade, Ticker, DailyPrice, NewsArticle tables) plus one new event collection mechanism (behavior_events). No new Python packages are needed — everything is built with the existing SQLAlchemy/FastAPI/APScheduler stack. The frontend additions follow the established coach page pattern with self-contained components using React Query hooks.

**Primary recommendation:** Build in layered order — DB migrations first, then backend service with pure computation functions, then API endpoints, then scheduler jobs, then frontend components, and finally the PickService sector bias integration (the riskiest change as it modifies existing scoring logic).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **behavior_events table**: id, event_type (ticker_view/search/pick_click), ticker_id (FK nullable), metadata (JSONB), created_at
- **Frontend sends POST /api/behavior/event** on: ticker detail page view, search result click, pick card click
- **Debounce**: max 1 event per ticker per 5 minutes to avoid flooding
- **Backend aggregates**: GET /api/behavior/viewing-stats returns top 10 most-viewed tickers with view count, last viewed, sector
- **Habit detection patterns**: 3 specific patterns — premature profit-taking (>5% continued rise after sell), holding losers (>10% unrealized loss held >5 trading days), impulsive trading (BUY within 2 hours of CafeF news about same ticker)
- **Detection runs weekly batch job on Sunday** — not real-time
- **habit_detections table**: id, habit_type, ticker_id, trade_id, evidence (JSONB), detected_at
- **risk_suggestions table**: id, current_level, suggested_level, reason, status (pending/accepted/rejected), created_at, responded_at
- **After 3 consecutive losing trades** → create risk suggestion (suggest reducing by 1 level)
- **Only 1 pending suggestion at a time** — don't spam if user already rejected
- **Two buttons on banner**: "Đồng ý giảm" (accept) and "Giữ nguyên" (reject)
- **sector_preferences table**: id, sector, total_trades, win_count, loss_count, net_pnl, preference_score, updated_at
- **Preference score formula**: (win_rate × 0.6) + (normalized_pnl × 0.4)
- **Sector bias in PickService**: multiply composite_score by (1 + preference_score × 0.1) for preferred, (1 - penalty × 0.1) for poor
- **Minimum 3 trades in a sector** before applying any bias
- **API routes in backend/app/api/behavior.py**: POST event, GET viewing-stats, GET habits, GET sector-preferences, GET risk-suggestion, POST risk-suggestion/{id}/respond
- **Coach page sections**: Risk banner (conditional, top), habit card, viewing stats + sector preferences side-by-side
- **Scheduler jobs**: weekly_behavior_analysis (Sunday 20:00), check_consecutive_losses (after trade creation or daily after market close)

### Agent's Discretion
- Exact thresholds for habit detection (5%/10%/2h are starting points — adjust based on testing)
- Sector preference normalization method — simple min-max or z-score
- Whether habit detection needs a dedicated table or can be computed on-the-fly from trades

### Deferred Ideas (OUT OF SCOPE)
- Real-time habit notifications (push when impulsive pattern detected)
- Gamification / badges for good trading habits
- ML-based pattern detection
- Multi-factor adaptive strategy (combine sector + timing + position size)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BEHV-01 | Record tickers user views most frequently, surfacing unconscious biases on coach dashboard | behavior_events table + POST /api/behavior/event + "Mã bạn hay xem" coach section + debounce logic |
| BEHV-02 | Detect trading habits: selling too early when in profit, holding too long when in loss, impulsive trading after news | habit_detections table + weekly batch analysis using Trade + DailyPrice + NewsArticle joins |
| ADPT-01 | Risk level (1-5) maintained — after 3 consecutive losses suggests reducing risk, user confirms before applying | risk_suggestions table + consecutive loss detection + banner UI with accept/reject + UserRiskProfile update |
| ADPT-02 | Learn sector preferences from trade results — bias future picks toward profitable sectors | sector_preferences table + preference scoring + PickService composite_score sector multiplier |
</phase_requirements>

## Standard Stack

### Core (Already Installed — Zero New Packages)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | ~2.0 | ORM for 4 new tables | Already in use, mapped_column pattern established | [VERIFIED: codebase inspection] |
| FastAPI | ~0.135 | New API router for behavior endpoints | Existing pattern in api/ directory | [VERIFIED: codebase inspection] |
| Pydantic | ~2.13 | Schemas for behavior API responses | Established pattern in schemas/ directory | [VERIFIED: codebase inspection] |
| APScheduler | 3.11.2 | Two new scheduled jobs | Existing scheduler infrastructure in scheduler/manager.py | [VERIFIED: codebase inspection] |
| @tanstack/react-query | ~5.x | Frontend data fetching for behavior APIs | Already used for all frontend data fetching | [VERIFIED: codebase hooks.ts] |
| shadcn/ui | 4.x | UI components for behavior sections | Already used throughout frontend | [VERIFIED: codebase components/] |

### No New Packages Required

This phase adds zero new backend or frontend dependencies. [VERIFIED: codebase analysis — all required functionality (JSONB columns, date math, SQL aggregations, cron scheduling) is covered by existing stack]

**Installation:** None needed.

## Architecture Patterns

### Recommended Project Structure (New Files)
```
backend/
├── app/
│   ├── api/
│   │   └── behavior.py          # NEW: 6 endpoints
│   ├── models/
│   │   ├── behavior_event.py    # NEW: BehaviorEvent model
│   │   ├── habit_detection.py   # NEW: HabitDetection model
│   │   ├── risk_suggestion.py   # NEW: RiskSuggestion model
│   │   └── sector_preference.py # NEW: SectorPreference model
│   ├── schemas/
│   │   └── behavior.py          # NEW: Pydantic schemas
│   └── services/
│       └── behavior_service.py  # NEW: BehaviorService class + pure functions
├── alembic/versions/
│   └── 022_behavior_tracking_tables.py  # NEW: migration
frontend/
├── src/
│   ├── components/
│   │   ├── risk-suggestion-banner.tsx   # NEW
│   │   ├── trading-habits-card.tsx      # NEW
│   │   ├── viewing-stats-card.tsx       # NEW
│   │   └── sector-preferences-card.tsx  # NEW
│   ├── lib/
│   │   ├── api.ts                       # MODIFY: add behavior types + fetch functions
│   │   └── hooks.ts                     # MODIFY: add behavior hooks
│   └── app/coach/
│       └── page.tsx                     # MODIFY: add 3 behavior sections
```

### Pattern 1: Pure Function + Async Service (Established Pattern)
**What:** Module-level pure functions for computation, class for DB operations
**When to use:** Always for services in this project
**Example:**
```python
# Source: [VERIFIED: codebase — trade_service.py, pick_service.py follow this exact pattern]

# ── Pure computation functions ────────────────────────────────────
def detect_premature_profit_taking(
    sell_price: float, prices_after_sell: list[tuple[date, float]], threshold_pct: float = 5.0
) -> dict | None:
    """Detect if price rose >threshold% after sell. Pure function — no DB."""
    ...

# ── BehaviorService (async DB operations) ─────────────────────────
class BehaviorService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_event(self, event_type: str, ticker_id: int | None, metadata: dict) -> int:
        ...
```

### Pattern 2: Self-Contained Coach Components (Established Pattern)
**What:** Each coach section is a self-contained component with its own hooks
**When to use:** All new coach page sections
**Example:**
```typescript
// Source: [VERIFIED: codebase — PickPerformanceCards, PickHistoryTable follow this pattern]
// Phase 45 decision: "PickPerformanceCards and PickHistoryTable are self-contained (own hooks internally)"

export function TradingHabitsCard() {
  const { data, isLoading, isError } = useHabitDetections();
  // Renders its own loading/error/data states
  if (isLoading) return <Skeleton />;
  ...
}
```

### Pattern 3: Scheduler Job with Job Execution Tracking (Established Pattern)
**What:** Each job creates its own DB session, uses JobExecutionService for tracking
**When to use:** All new scheduled jobs
**Example:**
```python
# Source: [VERIFIED: codebase — scheduler/jobs.py, daily_pick_generation follows this exact pattern]
async def weekly_behavior_analysis():
    logger.info("=== WEEKLY BEHAVIOR ANALYSIS START ===")
    async with async_session() as session:
        job_svc = JobExecutionService(session)
        execution = await job_svc.start("weekly_behavior_analysis")
        try:
            service = BehaviorService(session)
            result = await service.detect_all_habits()
            # ...
```

### Pattern 4: API Router Registration (Established Pattern)
**What:** New router file, registered in api/router.py
**Example:**
```python
# Source: [VERIFIED: codebase — api/router.py]
from app.api.behavior import router as behavior_router
api_router.include_router(behavior_router)
```

### Anti-Patterns to Avoid
- **Don't inline behavior logic in PickService:** Keep BehaviorService separate; PickService only queries sector_preferences table for bias. [VERIFIED: codebase — services are separate concerns]
- **Don't use real-time detection for habits:** CONTEXT.md explicitly states weekly batch job. Real-time is deferred.
- **Don't modify UserRiskProfile directly:** Risk changes go through risk_suggestions → user confirms → then update profile. Never auto-apply.
- **Don't debounce on backend only:** Frontend must debounce (5 min per ticker) to avoid unnecessary network traffic. Backend can also enforce as a safety net.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSONB column handling | Custom JSON serialization | SQLAlchemy `JSONB` type | PostgreSQL native JSONB, already used in ai_analysis.raw_response [VERIFIED: codebase] |
| Cron scheduling | Custom timer/sleep loops | APScheduler CronTrigger | Established pattern, timezone-aware, misfire handling [VERIFIED: codebase scheduler/manager.py] |
| Frontend debouncing | Custom setTimeout tracking | Simple ref-based timestamp check | Only need per-ticker 5min check, not complex debounce |
| SQL aggregations for sector stats | Python-side groupby | PostgreSQL GROUP BY with aggregate functions | PostgreSQL handles millions of rows; Python-side would be slow and memory-heavy |
| Date arithmetic for "held > N days" | Python date subtraction | PostgreSQL `current_date - interval` | Let the DB do the work in queries |

**Key insight:** This phase is pure analytics — every computation can be expressed as SQL aggregations on existing tables. The only new data collection is behavior_events; everything else (habits, sectors, risk) is derived from existing Trade/DailyPrice/NewsArticle data.

## Common Pitfalls

### Pitfall 1: Premature Profit-Taking Detection Requires Future Prices
**What goes wrong:** Detecting "price continued rising >5% after sell" requires prices AFTER the sell_date, which may not exist yet for recent trades.
**Why it happens:** The sell might have happened today/yesterday, and we don't have enough post-sell price data.
**How to avoid:** Only evaluate sells where sell_date is at least 5 trading days ago. Query DailyPrice for prices between sell_date and sell_date + 10 trading days. If max(high) after sell exceeds sell_price by >5%, flag it.
**Warning signs:** Flagging trades that are only 1-2 days old as "premature" — that's not enough data.

### Pitfall 2: Impulsive Trading Detection Time Window
**What goes wrong:** Matching BUY trade time to news article published_at within 2 hours is tricky because trade_date is DATE not TIMESTAMP.
**Why it happens:** Trade model stores `trade_date` as `Date` (not TIMESTAMP), while NewsArticle stores `published_at` as TIMESTAMP.
**How to avoid:** Use `created_at` on the Trade model (which IS a TIMESTAMP) as proxy for "when the user decided to buy." Compare Trade.created_at with NewsArticle.published_at for the same ticker within 2 hours. Alternatively, match by same calendar day if created_at isn't precise enough.
**Warning signs:** Zero impulsive detections because date resolution mismatch.

### Pitfall 3: Consecutive Loss Detection Race Condition
**What goes wrong:** If check runs daily but user creates multiple trades in one day, the "3 consecutive losses" might span trades created in the same batch.
**Why it happens:** Trades ordered by trade_date might not reflect actual chronological order.
**How to avoid:** Order by `trade_date DESC, id DESC` to get true chronological order. Only count SELL trades (BUY trades don't have P&L). Filter `Trade.side == "SELL"` and check last 3 have `net_pnl < 0`.
**Warning signs:** False positives from mixing BUY and SELL trades in the consecutive check.

### Pitfall 4: Sector Bias Amplifying Bad Picks
**What goes wrong:** Sector bias multiplier makes bad picks look good just because they're in a historically profitable sector.
**Why it happens:** Multiplying composite_score by (1 + preference_score × 0.1) can push a mediocre pick above good picks from other sectors.
**How to avoid:** Cap the sector multiplier effect. The CONTEXT.md formula (× 0.1) keeps it modest. Also enforce the minimum 3 trades threshold strictly. Consider capping the max bias at ±10% of composite score.
**Warning signs:** Top 3 picks all from the same sector repeatedly.

### Pitfall 5: Empty State / Not Enough Data
**What goes wrong:** All behavior features return empty data when user has < 20 trades.
**Why it happens:** STATE.md notes "adaptive strategy needs ~20 trades before activation."
**How to avoid:** Every endpoint and UI component must handle empty state gracefully. Show informative "not enough data" messages instead of empty sections. Sector preferences need 3 trades per sector; habit detection needs closed trades with post-sell price data.
**Warning signs:** Coach page has 3 new empty sections that add no value for new users.

### Pitfall 6: N+1 Query in Habit Detection
**What goes wrong:** For each SELL trade, querying DailyPrice individually to check post-sell movement creates N+1.
**Why it happens:** Naive loop: `for trade in sell_trades: query prices after trade.sell_date`.
**How to avoid:** Batch all SELL trades, find the date range needed, query DailyPrice in one batch for all ticker_ids. Process results in memory.
**Warning signs:** Weekly job taking >30 seconds with <100 trades.

## Code Examples

### New Model: BehaviorEvent
```python
# Source: [VERIFIED: codebase model patterns — trade.py, daily_pick.py]
from datetime import datetime
from sqlalchemy import BigInteger, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP
from app.models import Base

class BehaviorEvent(Base):
    __tablename__ = "behavior_events"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)  # ticker_view, search, pick_click
    ticker_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tickers.id"), nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
```

### New Model: RiskSuggestion
```python
# Source: [VERIFIED: codebase model patterns]
class RiskSuggestion(Base):
    __tablename__ = "risk_suggestions"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    current_level: Mapped[int] = mapped_column(Integer, nullable=False)
    suggested_level: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, server_default="pending")  # pending/accepted/rejected
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    responded_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
```

### Pure Function: Detect Premature Profit-Taking
```python
# Source: [ASSUMED — logic derived from CONTEXT.md habit detection rules]
def detect_premature_profit_taking(
    sell_price: float,
    prices_after_sell: list[float],  # close prices after sell_date
    threshold_pct: float = 5.0,
) -> bool:
    """Check if price rose >threshold% after selling at a profit."""
    if not prices_after_sell:
        return False
    max_after = max(prices_after_sell)
    rise_pct = ((max_after - sell_price) / sell_price) * 100
    return rise_pct > threshold_pct
```

### Consecutive Loss Check
```python
# Source: [VERIFIED: codebase Trade model has net_pnl, side fields]
async def check_consecutive_losses(self) -> dict | None:
    """Check if last 3 SELL trades are all losses. Returns suggestion dict or None."""
    result = await self.session.execute(
        select(Trade.net_pnl)
        .where(Trade.side == "SELL")
        .order_by(Trade.trade_date.desc(), Trade.id.desc())
        .limit(3)
    )
    recent_pnls = [row.net_pnl for row in result.all()]
    
    if len(recent_pnls) < 3:
        return None
    
    if all(pnl < 0 for pnl in recent_pnls):
        # Check no pending suggestion exists
        pending = await self.session.execute(
            select(RiskSuggestion).where(RiskSuggestion.status == "pending")
        )
        if pending.scalar_one_or_none() is not None:
            return None  # Already have a pending suggestion
        
        profile = await self._get_risk_profile()
        if profile.risk_level <= 1:
            return None  # Already at minimum risk
        
        return {
            "current_level": profile.risk_level,
            "suggested_level": profile.risk_level - 1,
            "reason": f"3 lần lỗ liên tiếp ({', '.join(f'{float(p):,.0f}' for p in recent_pnls)} VND)",
        }
    return None
```

### Sector Bias in PickService (Integration Point)
```python
# Source: [VERIFIED: codebase — pick_service.py line ~458, candidates.sort()]
# After computing composite_score, before sorting:

# Load sector preferences (min 3 trades per sector)
sector_prefs = {}  # {sector: preference_score}
pref_query = select(SectorPreference).where(SectorPreference.total_trades >= 3)
for pref in (await self.session.execute(pref_query)).scalars():
    sector_prefs[pref.sector] = float(pref.preference_score)

# Apply sector bias to each candidate's composite_score
for c in candidates:
    ticker_sector = c.get("sector")
    if ticker_sector and ticker_sector in sector_prefs:
        bias = sector_prefs[ticker_sector]
        c["composite_score"] *= (1 + bias * 0.1)
```

### Frontend: Risk Suggestion Banner
```typescript
// Source: [VERIFIED: codebase — coach page, shadcn/ui patterns]
"use client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";
import { useRiskSuggestion, useRespondRiskSuggestion } from "@/lib/hooks";

export function RiskSuggestionBanner() {
  const { data: suggestion } = useRiskSuggestion();
  const respond = useRespondRiskSuggestion();
  
  if (!suggestion) return null;
  
  return (
    <Alert variant="destructive">
      <AlertTriangle className="size-4" />
      <AlertTitle>Cảnh báo rủi ro</AlertTitle>
      <AlertDescription className="flex items-center justify-between">
        <span>{suggestion.reason}</span>
        <div className="flex gap-2">
          <Button size="sm" variant="destructive" onClick={() => respond.mutate({ id: suggestion.id, action: "accept" })}>
            Đồng ý giảm
          </Button>
          <Button size="sm" variant="outline" onClick={() => respond.mutate({ id: suggestion.id, action: "reject" })}>
            Giữ nguyên
          </Button>
        </div>
      </AlertDescription>
    </Alert>
  );
}
```

### Frontend: Debounced Behavior Event Tracking
```typescript
// Source: [ASSUMED — standard debounce pattern for event tracking]
const DEBOUNCE_MS = 5 * 60 * 1000; // 5 minutes
const viewTimestamps = new Map<string, number>(); // tickerSymbol -> lastSentAt

export async function trackTickerView(tickerSymbol: string, tickerId: number) {
  const now = Date.now();
  const last = viewTimestamps.get(tickerSymbol) || 0;
  if (now - last < DEBOUNCE_MS) return; // Skip if within 5 min
  
  viewTimestamps.set(tickerSymbol, now);
  await fetch(`${API_BASE}/behavior/event`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ event_type: "ticker_view", ticker_id: tickerId }),
  });
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No behavior tracking | Phase 46 adds passive tracking | Now | New capability |
| Static risk level (user sets manually) | Adaptive risk suggestions after losses | Now | Risk management becomes data-driven |
| Equal sector weighting in pick scoring | Sector-biased scoring from trade results | Now | Picks personalized to user's profitable sectors |

**No deprecated patterns to note** — this is all new functionality built on existing stable infrastructure.

## Assumptions Log

> List all claims tagged `[ASSUMED]` in this research.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Premature profit-taking detection logic (check max price 5 days after sell) | Code Examples | Low — pure function, easily adjustable thresholds |
| A2 | Using Trade.created_at as proxy for "when user decided to buy" for impulsive trade detection | Pitfall 2 | Medium — if created_at doesn't match actual decision time, impulsive detection misses |
| A3 | Simple min-max normalization sufficient for sector preference scoring | Agent's Discretion | Low — can switch to z-score later without schema change |
| A4 | Frontend debounce using in-memory Map is sufficient (no persistence needed) | Code Examples | Low — page refresh resets timestamps, which is acceptable |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), Playwright (frontend e2e) |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/test_behavior_service.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -x` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BEHV-01 | Viewing stats aggregation (top 10 tickers, debounce) | unit | `pytest tests/test_behavior_service.py::TestViewingStats -x` | ❌ Wave 0 |
| BEHV-02 | Habit detection: premature sell, holding losers, impulsive trade | unit | `pytest tests/test_behavior_service.py::TestHabitDetection -x` | ❌ Wave 0 |
| ADPT-01 | Consecutive loss detection + risk suggestion lifecycle (create/accept/reject) | unit | `pytest tests/test_behavior_service.py::TestRiskSuggestion -x` | ❌ Wave 0 |
| ADPT-02 | Sector preference scoring + pick bias multiplier | unit | `pytest tests/test_behavior_service.py::TestSectorPreference -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_behavior_service.py -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_behavior_service.py` — covers BEHV-01, BEHV-02, ADPT-01, ADPT-02 (pure function tests)
- [ ] No new conftest fixtures needed — existing `mock_db_session` covers async service mocking

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user app, no auth |
| V3 Session Management | no | N/A |
| V4 Access Control | no | Single-user app |
| V5 Input Validation | yes | Pydantic schema validation on all API inputs (event_type whitelist, ticker_id FK validation, risk suggestion ID validation) |
| V6 Cryptography | no | No secrets stored |

### Known Threat Patterns for This Phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Event flooding (behavior_events) | DoS | Frontend debounce (5 min) + backend rate limiting via event_type whitelist |
| Invalid event_type injection | Tampering | Pydantic enum validation — only allow "ticker_view", "search", "pick_click" |
| Risk suggestion manipulation | Tampering | Validate suggestion ID exists and status is "pending" before allowing response |
| SQL injection in sort/filter params | Tampering | Whitelist approach established in trade_service.py (T-44-05 pattern) |

## Open Questions

1. **check_consecutive_losses trigger timing**
   - What we know: CONTEXT.md says "runs after each trade creation (or daily after market close)"
   - What's unclear: Should it hook into TradeService.create_trade() or be a separate scheduled job?
   - Recommendation: Run as daily scheduled job (after market close, ~16:00) to keep trade creation fast. Also optionally check in the API response of POST /trades. The daily job is the safety net.

2. **Sector field coverage in Ticker table**
   - What we know: Ticker.sector is `String(100), nullable=True`
   - What's unclear: How many tickers actually have sector data populated?
   - Recommendation: The sector preference system gracefully handles NULL sectors by excluding them from analysis. No action needed but worth monitoring.

3. **Habit detection table vs. on-the-fly computation**
   - What we know: CONTEXT.md lists this as agent's discretion
   - Recommendation: **Use the table**. Batch computation on Sunday stores results; API reads from table. This avoids expensive on-the-fly queries on every page load. Table also provides historical tracking of detected habits over time.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: all model files, service files, API routes, scheduler, frontend components — direct file reads
- 46-CONTEXT.md — locked decisions for all tables, APIs, formulas
- REQUIREMENTS.md — BEHV-01, BEHV-02, ADPT-01, ADPT-02 definitions

### Secondary (MEDIUM confidence)
- STATE.md — accumulated context: "Adaptive strategy needs ~20 trades before activation"
- Prior phase patterns (Phase 44 trade service, Phase 45 pick performance) — established patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - zero new packages, all patterns verified in codebase
- Architecture: HIGH - follows established patterns from Phase 44 and 45 exactly
- Pitfalls: HIGH - identified from codebase inspection (data types, query patterns)
- Habit detection logic: MEDIUM - thresholds are adjustable, impulsive trade timing needs validation

**Research date:** 2026-04-23
**Valid until:** 2026-05-23 (30 days — stable stack, no version changes)

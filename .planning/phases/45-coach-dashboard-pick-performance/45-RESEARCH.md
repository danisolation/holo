# Phase 45: Coach Dashboard & Pick Performance - Research

**Researched:** 2026-04-23
**Domain:** Full-stack dashboard (SQLAlchemy migration, FastAPI endpoints, React/Next.js UI, APScheduler job)
**Confidence:** HIGH

## Summary

Phase 45 unifies the daily picks engine (Phase 43) and trade journal (Phase 44) into a single coaching dashboard at `/coach`. This requires three workstreams: (1) backend pick outcome tracking — adding columns to `daily_picks` table, computing outcomes from DailyPrice data, and a new scheduler job; (2) backend API endpoints for paginated pick history and aggregated performance stats; (3) frontend dashboard layout with performance cards, open trades section, and pick history table.

The codebase is well-structured for this phase. All integration points exist: DailyPick model, Trade model with `daily_pick_id` FK, DailyPrice model with OHLCV data, PickService with placeholder `get_pick_history()`, picks API with placeholder `/picks/history` endpoint, scheduler chain with `daily_pick_generation` as current terminal job. No new packages required — zero backend dependencies, zero frontend dependencies.

**Primary recommendation:** Implement in 3 waves — (1) DB migration + outcome computation service + scheduler job, (2) API endpoints for history and performance, (3) frontend coach page layout with all 4 sections.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Pick Outcome Tracking (CDSH-02):** Add outcome columns to `daily_picks` via migration 021: pick_outcome (pending/winner/loser/expired), days_held, hit_stop_loss, hit_take_profit_1, hit_take_profit_2, actual_return_pct. Outcome computed automatically from DailyPrice data by daily scheduler job. Logic: close <= stop_loss → loser; close >= take_profit_1 → winner; days_held > 10 trading days → expired. actual_return_pct = ((latest_close - entry_price) / entry_price) × 100. Track ALL picks including untraded ones. For traded picks (via daily_pick_id FK): also show realized P&L alongside theoretical outcome.
- **Performance Cards (CDSH-03):** 4 cards — Win Rate, Total P&L (realized from trades), Average R:R, Current Streak (🔥/❄️). Cards show skeleton loading.
- **Unified Coach Page Layout (CDSH-01):** Single /coach page with 4 sections: Performance Cards, Today's Picks, Open Trades, Pick History. Almost-selected remains inside Today's Picks as collapsible.
- **Pick History Table (CDSH-02):** Columns: Date, Mã, Rank, Entry, SL, TP1, Outcome badge, Return %, Days Held, Traded?. Badges: "Thắng" (green), "Thua" (red), "Hết hạn" (neutral), "Đang theo dõi" (blue). Default sort date DESC, filterable by outcome status, paginated 20/page, includes ALL picks.
- **Backend API:** GET /api/picks/history?page=1&per_page=20&status=all; GET /api/picks/performance. Outcome computation: new method in PickService. No manual pick close endpoint.
- **Scheduler Job:** `daily_pick_outcome_check` runs after market close (~15:30), chains after `daily_pick_generation`. Idempotent.
- **Frontend Integration:** Reuse useDailyPicks() for today's section. Reuse useTrades() with filter for open trades. New usePickHistory() and usePickPerformance() hooks.

### Agent's Discretion
- Pick detail page (click through from history) — build only if straightforward, otherwise defer
- Chart overlay showing price vs entry/SL/TP — defer to future
- Performance breakdown by rank — include in stats response if simple aggregation

### Deferred Ideas (OUT OF SCOPE)
- Pick detail page with chart overlay
- Outcome notifications (Telegram/push)
- AI analysis of performance patterns (Phase 46 territory)
- Manual outcome override
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CDSH-01 | Trang /coach hiển thị picks hôm nay, trades đang mở, và performance summary trên 1 trang duy nhất | Existing coach page.tsx (80 lines) extended with 4 vertical sections. Reuse existing PickCard, TradesTable components. New PerformanceCards component modeled on TradeStatsCards. |
| CDSH-02 | Lịch sử picks với kết quả thực tế (entry hit?, SL hit?, TP hit?, return sau N ngày) — track TẤT CẢ picks kể cả không trade | Migration 021 adds outcome columns to daily_picks. PickService gets compute_pick_outcomes() method querying DailyPrice. New PickHistoryTable component. Existing placeholder `/picks/history` endpoint upgraded to paginated + outcome data. |
| CDSH-03 | Performance cards: win rate, total P&L, average R:R, streak hiện tại | New GET /api/picks/performance endpoint. Win rate computed from pick outcomes. Total P&L from trades linked to picks via daily_pick_id FK. Average R:R from actual_return_pct / risk per pick. Streak from consecutive outcomes sorted by date. |
</phase_requirements>

## Standard Stack

### Core (already installed — zero new packages)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | ~2.0 | ORM — add columns to DailyPick model | Already used everywhere [VERIFIED: codebase] |
| Alembic | ~1.18 | Migration 021 for outcome columns | Migration convention: sequential numbering [VERIFIED: codebase] |
| FastAPI | ~0.135 | 2 new API endpoints (history + performance) | Existing API layer [VERIFIED: codebase] |
| Pydantic | ~2.13 | New response schemas for history/performance | Schema convention [VERIFIED: codebase] |
| APScheduler | 3.11.2 | New job chained after pick_generation | Existing scheduler chain pattern [VERIFIED: codebase] |
| Next.js | ~15.x | Coach page extension | Existing frontend [VERIFIED: codebase] |
| @tanstack/react-query | ~5.x | New hooks for history + performance | Existing hook pattern [VERIFIED: codebase] |
| shadcn/ui | 4.x | Cards, Table, Badge, Skeleton components | All UI components needed already exist [VERIFIED: codebase] |
| Recharts | ~3.x | Not needed this phase | Stats are cards, not charts |

### No New Dependencies Required

This phase requires zero new npm packages and zero new Python packages. Everything builds on existing infrastructure. [VERIFIED: codebase audit]

## Architecture Patterns

### Recommended Project Structure (changes only)

```
backend/
├── alembic/versions/
│   └── 021_pick_outcome_columns.py    # NEW — adds outcome columns to daily_picks
├── app/
│   ├── models/
│   │   └── daily_pick.py              # MODIFY — add PickOutcome enum + outcome columns
│   ├── services/
│   │   └── pick_service.py            # MODIFY — add compute_pick_outcomes(), get_performance_stats(), upgrade get_pick_history()
│   ├── schemas/
│   │   └── picks.py                   # MODIFY — add PickHistoryResponse, PickPerformanceResponse, PickHistoryListResponse
│   ├── api/
│   │   └── picks.py                   # MODIFY — upgrade /picks/history, add /picks/performance
│   └── scheduler/
│       ├── jobs.py                    # MODIFY — add daily_pick_outcome_check() function
│       └── manager.py                 # MODIFY — chain outcome check after pick_generation
frontend/
├── src/
│   ├── app/coach/
│   │   └── page.tsx                   # MODIFY — restructure into 4-section dashboard
│   ├── components/
│   │   ├── performance-cards.tsx      # NEW — 4 performance stat cards
│   │   └── pick-history-table.tsx     # NEW — paginated pick history with outcome badges
│   └── lib/
│       ├── api.ts                     # MODIFY — add fetchPickPerformance, upgrade fetchPickHistory types
│       └── hooks.ts                   # MODIFY — add usePickHistory(), usePickPerformance()
```

### Pattern 1: Outcome Computation Logic (Pure Function)

**What:** Pure function that takes a DailyPick + price data and computes outcome.
**When to use:** Called by scheduler job for batch processing. Also usable in tests.

```python
# Source: CONTEXT.md decisions + existing compute_composite_score pattern
import enum

class PickOutcome(str, enum.Enum):
    PENDING = "pending"
    WINNER = "winner"
    LOSER = "loser"
    EXPIRED = "expired"

def compute_pick_outcome(
    entry_price: float,
    stop_loss: float,
    take_profit_1: float,
    daily_closes: list[tuple[date, float]],  # [(date, close), ...]
    max_trading_days: int = 10,
) -> dict:
    """Compute pick outcome from daily close prices after pick date.
    
    Returns dict with: outcome, days_held, hit_stop_loss, hit_take_profit_1,
    actual_return_pct
    """
    # sorted by date ascending
    for i, (d, close) in enumerate(daily_closes):
        days = i + 1
        if close <= stop_loss:
            return {
                "outcome": PickOutcome.LOSER,
                "days_held": days,
                "hit_stop_loss": True,
                "hit_take_profit_1": False,
                "actual_return_pct": ((close - entry_price) / entry_price) * 100,
            }
        if close >= take_profit_1:
            return {
                "outcome": PickOutcome.WINNER,
                "days_held": days,
                "hit_stop_loss": False,
                "hit_take_profit_1": True,
                "actual_return_pct": ((close - entry_price) / entry_price) * 100,
            }
    # If we have enough days without hitting either level
    if len(daily_closes) >= max_trading_days:
        last_close = daily_closes[-1][1]
        return {
            "outcome": PickOutcome.EXPIRED,
            "days_held": len(daily_closes),
            "hit_stop_loss": False,
            "hit_take_profit_1": False,
            "actual_return_pct": ((last_close - entry_price) / entry_price) * 100,
        }
    # Not enough data yet
    return {"outcome": PickOutcome.PENDING, "days_held": len(daily_closes)}
```

### Pattern 2: Scheduler Job Chaining (Existing Pattern)

**What:** APScheduler EVENT_JOB_EXECUTED listener chains jobs sequentially.
**When to use:** New `daily_pick_outcome_check` chains after `daily_pick_generation_triggered`.

```python
# Source: existing manager.py _on_job_executed pattern [VERIFIED: codebase]
# In manager.py, add to _on_job_executed:
elif event.job_id in ("daily_pick_generation_triggered", "daily_pick_generation_manual"):
    from app.scheduler.jobs import daily_pick_outcome_check
    logger.info("Chaining: daily_pick_generation → daily_pick_outcome_check")
    scheduler.add_job(
        daily_pick_outcome_check,
        id="daily_pick_outcome_check_triggered",
        replace_existing=True,
        misfire_grace_time=3600,
    )
```

### Pattern 3: Paginated API Response (Existing Pattern)

**What:** Page-based pagination with total count, matching TradesListResponse pattern.
**When to use:** Pick history endpoint.

```python
# Source: existing TradesListResponse pattern [VERIFIED: backend/app/schemas/trades.py]
class PickHistoryListResponse(BaseModel):
    picks: list[PickHistoryResponse]
    total: int
    page: int
    page_size: int
```

### Pattern 4: Performance Stats Cards (Existing Pattern)

**What:** Card grid showing aggregated stats with skeleton loading.
**When to use:** New PerformanceCards component.

```tsx
// Source: existing TradeStatsCards pattern [VERIFIED: frontend/src/components/trade-stats-cards.tsx]
// 4-card grid with Skeleton loading, same pattern as TradeStatsCards (3-card grid)
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
  {/* Win Rate | Total P&L | Avg R:R | Streak */}
</div>
```

### Anti-Patterns to Avoid

- **Don't compute outcomes on every API request:** Outcomes should be pre-computed by the scheduler job and stored in the DB. The API just reads stored values. [VERIFIED: CONTEXT.md decision]
- **Don't filter open trades in frontend:** Use the existing `useTrades()` hook with a server-side filter (side/ticker param) to get only open positions. TradeService already supports filtering. [VERIFIED: codebase]
- **Don't create a separate outcomes table:** CONTEXT.md specifies adding columns directly to `daily_picks` table, not creating a join table. This keeps queries simple.
- **Don't recompute already-resolved picks:** The outcome check must be idempotent — only update picks with `pick_outcome = 'pending'`. Already-resolved picks (winner/loser/expired) stay as-is.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Pagination | Custom offset logic | Existing page/page_size pattern from TradesListResponse | Consistency with journal page [VERIFIED: codebase] |
| Outcome badges | Custom badge styling | shadcn Badge with variant + Tailwind color classes | Pattern from trades table BUY/SELL badges [VERIFIED: codebase] |
| Skeleton loading | Custom loading spinners | Skeleton component (existing pattern) | Consistent UX [VERIFIED: codebase] |
| Date formatting | Manual string ops | formatDateVN from lib/format.ts | Already handles DD/MM/YYYY for VN locale [VERIFIED: codebase] |
| Stats aggregation | JS client-side calculation | Backend SQL aggregation in PickService | DB is the source of truth, avoids N+1 and pagination conflicts |

**Key insight:** This phase is 80% integration of existing patterns (TradesTable → PickHistoryTable, TradeStatsCards → PerformanceCards, existing hooks → new hooks). Minimize novelty.

## Common Pitfalls

### Pitfall 1: Outcome Computation Without Price Data
**What goes wrong:** Pick has entry_price/SL/TP but no daily prices exist after pick_date (new ticker, market holiday, data gap).
**Why it happens:** DailyPrice data depends on daily crawl which can fail.
**How to avoid:** In `compute_pick_outcomes()`, if no price rows found after pick_date, keep as PENDING. Don't crash or mark as expired.
**Warning signs:** Picks staying "pending" forever despite being 30+ days old.

### Pitfall 2: Picks Without Entry/SL/TP Prices
**What goes wrong:** Some DailyPick rows have NULL entry_price, stop_loss, or take_profit_1 (from analysis failures).
**Why it happens:** Trading signal extraction can fail to provide prices. `almost` status picks may lack SL/TP.
**How to avoid:** Only compute outcomes for picks where status='picked' AND entry_price IS NOT NULL AND stop_loss IS NOT NULL AND take_profit_1 IS NOT NULL. Skip `almost` picks entirely for outcome tracking.
**Warning signs:** NULL division errors in actual_return_pct calculation.

### Pitfall 3: Streak Calculation Edge Cases
**What goes wrong:** Streak shows wrong value when no picks have been resolved yet, or all picks are pending.
**Why it happens:** Empty result set or all-pending results confuse consecutive counting.
**How to avoid:** Streak defaults to 0 when no resolved picks exist. Streak counts only from most recent resolved pick backward.
**Warning signs:** Streak showing "🔥 0 thắng liên tiếp" instead of neutral display.

### Pitfall 4: Open Trades Section — Data Mismatch
**What goes wrong:** "Open trades" section shows trades with no lots remaining (already fully sold).
**Why it happens:** Using trades list without filtering by lot status. A BUY trade with remaining_quantity=0 is NOT an open position.
**How to avoid:** The existing TradeStatsResponse already computes `open_positions` correctly from lots. For the open trades list, either: (a) add a `side=open` server filter, or (b) fetch trades and cross-reference with lots. Recommendation: add a new API endpoint or filter param that returns only tickers with remaining lots > 0.
**Warning signs:** "Open Trades" showing BUY trades where all shares were already sold.

### Pitfall 5: Performance P&L Mixing Theoretical vs Realized
**What goes wrong:** Total P&L card mixes "theoretical return from picks" with "realized P&L from trades."
**Why it happens:** CONTEXT.md clearly separates: Total P&L = sum of realized net_pnl from trades linked to picks. But developer might compute from pick outcomes.
**How to avoid:** Total P&L reads from trades table (SUM of net_pnl WHERE daily_pick_id IS NOT NULL). Win Rate reads from pick outcomes. These are intentionally different data sources.
**Warning signs:** P&L number doesn't match the journal page's realized P&L.

### Pitfall 6: Migration Column Defaults
**What goes wrong:** Adding NOT NULL columns without defaults to a table with existing rows fails.
**Why it happens:** daily_picks already has rows from Phase 43.
**How to avoid:** All new outcome columns must be NULLABLE or have server_default. pick_outcome defaults to 'pending'. All others (days_held, hit_stop_loss, etc.) are nullable.
**Warning signs:** Alembic migration fails with "column cannot contain null values."

## Code Examples

### Migration 021: Pick Outcome Columns

```python
# Source: existing migration conventions [VERIFIED: 019_daily_picks_tables.py, 020_trade_journal_tables.py]
def upgrade() -> None:
    op.add_column("daily_picks", sa.Column("pick_outcome", sa.String(10), nullable=False, server_default="pending"))
    op.add_column("daily_picks", sa.Column("days_held", sa.Integer, nullable=True))
    op.add_column("daily_picks", sa.Column("hit_stop_loss", sa.Boolean, nullable=True))
    op.add_column("daily_picks", sa.Column("hit_take_profit_1", sa.Boolean, nullable=True))
    op.add_column("daily_picks", sa.Column("hit_take_profit_2", sa.Boolean, nullable=True))
    op.add_column("daily_picks", sa.Column("actual_return_pct", sa.Numeric(8, 2), nullable=True))
    # Index for outcome check query: only pending picks need processing
    op.create_index("ix_daily_picks_outcome_pending", "daily_picks", ["pick_outcome"], postgresql_where=sa.text("pick_outcome = 'pending'"))
```

### DailyPick Model Updates

```python
# Source: existing DailyPick model [VERIFIED: backend/app/models/daily_pick.py]
# Add to DailyPick class after existing columns:
pick_outcome: Mapped[str] = mapped_column(String(10), nullable=False, server_default="pending")
days_held: Mapped[int | None] = mapped_column(Integer, nullable=True)
hit_stop_loss: Mapped[bool | None] = mapped_column(nullable=True)
hit_take_profit_1: Mapped[bool | None] = mapped_column(nullable=True)
hit_take_profit_2: Mapped[bool | None] = mapped_column(nullable=True)
actual_return_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
```

### Performance Stats SQL Pattern

```python
# Source: project patterns [VERIFIED: trade_service.py get_stats pattern]
# Win rate: count(outcome='winner') / count(outcome IN ('winner','loser','expired'))
# Total P&L: SUM(trades.net_pnl) WHERE trades.daily_pick_id IS NOT NULL AND trades.side = 'SELL'
# Avg R:R: AVG(actual_return_pct / abs((entry_price - stop_loss) / entry_price * 100))
# Streak: ORDER BY pick_date DESC, count consecutive same outcomes from most recent
```

### Frontend Pick History Hook Pattern

```typescript
// Source: existing useTrades pattern [VERIFIED: frontend/src/lib/hooks.ts]
export function usePickHistory(params?: {
  page?: number;
  status?: string;
}) {
  return useQuery({
    queryKey: ["picks", "history", params?.page ?? 1, params?.status ?? "all"],
    queryFn: () => fetchPickHistory(params),
    staleTime: 5 * 60 * 1000,
  });
}

export function usePickPerformance() {
  return useQuery({
    queryKey: ["picks", "performance"],
    queryFn: () => fetchPickPerformance(),
    staleTime: 5 * 60 * 1000,
  });
}
```

### Outcome Badge Component Pattern

```tsx
// Source: existing trades-table.tsx BUY/SELL badge pattern [VERIFIED: codebase]
function OutcomeBadge({ outcome }: { outcome: string }) {
  switch (outcome) {
    case "winner":
      return <Badge className="text-[#26a69a] bg-[#26a69a]/10 border-transparent">Thắng</Badge>;
    case "loser":
      return <Badge className="text-[#ef5350] bg-[#ef5350]/10 border-transparent">Thua</Badge>;
    case "expired":
      return <Badge variant="outline">Hết hạn</Badge>;
    case "pending":
    default:
      return <Badge className="text-blue-600 bg-blue-600/10 border-transparent dark:text-blue-400">Đang theo dõi</Badge>;
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Placeholder get_pick_history() returns basic dict | Paginated response with outcome data | This phase | Full pick history with outcomes |
| Coach page shows only today's picks | Unified dashboard with 4 sections | This phase | Single landing page for daily use |
| No outcome tracking | Auto-computed from DailyPrice data | This phase | Every pick gets tracked regardless of whether traded |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `daily_picks` table has existing rows that need `pick_outcome = 'pending'` default | Migration pattern | Migration fails if no server_default for existing rows — LOW risk, handled by server_default |
| A2 | The existing `useTrades()` hook can be reused with filter for open trades section | Frontend Integration | May need a new API endpoint/param for "open positions only" — MEDIUM risk |
| A3 | DailyPrice data is reliably available for outcome computation within 1-2 days of pick_date | Outcome computation | If price data has gaps, picks stay pending indefinitely — MEDIUM risk, handled by pending fallback |

## Open Questions

1. **Open Trades API filter**
   - What we know: TradeService supports `ticker` and `side` filters. TradeStatsResponse has `open_positions` count computed from lots.
   - What's unclear: There's no existing API filter for "trades with open positions only" (tickers with remaining lots > 0). The open trades section needs this.
   - Recommendation: Add a new `status=open` query param to GET /trades that filters to tickers with remaining lots, OR create a dedicated GET /trades/open endpoint. The former is simpler and follows existing pattern.

2. **TP2 outcome tracking**
   - What we know: CONTEXT.md includes `hit_take_profit_2` column. DailyPick has take_profit_2.
   - What's unclear: Should outcome logic check TP2? CONTEXT.md outcome logic only mentions TP1 for winner determination.
   - Recommendation: Track `hit_take_profit_2` as a boolean flag when close >= take_profit_2, but don't change outcome determination — winner is still based on TP1. TP2 is bonus info.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with pytest-asyncio |
| Config file | backend/pytest.ini (if exists) or pyproject.toml |
| Quick run command | `cd backend && python -m pytest tests/ -x -q --tb=short` |
| Full suite command | `cd backend && python -m pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CDSH-02a | compute_pick_outcome pure function | unit | `python -m pytest tests/test_pick_outcome.py -x` | ❌ Wave 0 |
| CDSH-02b | Scheduler job processes pending picks | unit | `python -m pytest tests/test_pick_outcome.py::test_outcome_check_job -x` | ❌ Wave 0 |
| CDSH-02c | GET /picks/history returns paginated outcomes | unit | `python -m pytest tests/test_pick_history_api.py -x` | ❌ Wave 0 |
| CDSH-03 | GET /picks/performance returns correct stats | unit | `python -m pytest tests/test_pick_performance_api.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_pick_outcome.py tests/test_pick_history_api.py tests/test_pick_performance_api.py -x -q`
- **Per wave merge:** Full backend test suite
- **Phase gate:** All backend tests green + manual UI verification of /coach page

### Wave 0 Gaps
- [ ] `backend/tests/test_pick_outcome.py` — covers CDSH-02 (compute_pick_outcome pure function tests)
- [ ] `backend/tests/test_pick_history_api.py` — covers CDSH-02 API (paginated history endpoint)
- [ ] `backend/tests/test_pick_performance_api.py` — covers CDSH-03 (performance stats endpoint)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user app, no auth |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | Single-user |
| V5 Input Validation | yes | Pydantic schemas validate page/per_page/status params; sort whitelist pattern from Phase 44 |
| V6 Cryptography | no | No secrets in this phase |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Query param injection (sort/filter) | Tampering | Sort/order whitelist (existing T-44-05 pattern) |
| Unbounded pagination | DoS | Cap per_page at 100, cap page × per_page at reasonable limit |
| Integer overflow in stats | Tampering | Pydantic validates numeric types, SQL uses proper Numeric types |

## Sources

### Primary (HIGH confidence)
- [VERIFIED: codebase] — All file inspections performed via Read tool:
  - `backend/app/models/daily_pick.py` — DailyPick model, PickStatus enum
  - `backend/app/models/daily_price.py` — DailyPrice model with OHLCV
  - `backend/app/models/trade.py` — Trade model with daily_pick_id FK
  - `backend/app/services/pick_service.py` — PickService with existing methods
  - `backend/app/api/picks.py` — Existing endpoints including placeholder history
  - `backend/app/scheduler/manager.py` — Job chaining pattern
  - `backend/app/scheduler/jobs.py` — daily_pick_generation job
  - `backend/app/schemas/picks.py` — DailyPickResponse, DailyPicksResponse
  - `backend/app/schemas/trades.py` — TradesListResponse pagination pattern
  - `backend/alembic/versions/` — 020 is latest migration
  - `frontend/src/app/coach/page.tsx` — Current coach page (80 lines)
  - `frontend/src/components/trade-stats-cards.tsx` — Stats card pattern
  - `frontend/src/components/trades-table.tsx` — Paginated table pattern
  - `frontend/src/components/pick-card.tsx` — Pick display pattern
  - `frontend/src/lib/api.ts` — API functions, types, fetchPickHistory placeholder
  - `frontend/src/lib/hooks.ts` — Hook patterns, useTrades/useTradeStats
  - `frontend/src/lib/format.ts` — formatVND, formatDateVN
  - `frontend/src/app/journal/page.tsx` — Journal page layout pattern

### Secondary (MEDIUM confidence)
- [VERIFIED: CONTEXT.md] — All locked decisions and implementation details

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, everything verified in codebase
- Architecture: HIGH — follows exact patterns from Phase 43/44 (model, service, schema, API, hooks, components)
- Pitfalls: HIGH — derived from actual codebase inspection (NULL prices, migration defaults, P&L mixing)
- Outcome logic: HIGH — explicitly specified in CONTEXT.md with concrete formulas

**Research date:** 2026-04-23
**Valid until:** 2026-05-23 (stable patterns, no external dependencies)

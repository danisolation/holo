# Architecture Research: v9.0 UX Rework & Simplification

**Domain:** Feature removal, migration, and UX restructure of existing stock intelligence platform
**Researched:** 2025-07-21
**Confidence:** HIGH — based on direct codebase analysis of all affected components

## Existing System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js App Router)                 │
├─────────────────────────────────────────────────────────────────┤
│  PAGES                                                          │
│  ┌──────────┐ ┌───────────┐ ┌─────────┐ ┌─────────┐            │
│  │ / (Home) │ │ /watchlist │ │ /coach  │ │/journal │            │
│  └──────────┘ └───────────┘ └─────────┘ └─────────┘            │
│  ┌───────────────┐ ┌─────────────────────┐ ┌────────────────┐  │
│  │ /dashboard    │ │ /dashboard/corp-evt  │ │ /dashboard/    │  │
│  │               │ │   X TO REMOVE        │ │   health       │  │
│  └───────────────┘ └─────────────────────┘ └────────────────┘  │
│  ┌────────────────┐                                             │
│  │ /ticker/[sym]  │                                             │
│  └────────────────┘                                             │
│                                                                 │
│  STATE: zustand (watchlist in localStorage) + React Query        │
│  EXCHANGE FILTER: useExchangeStore("all"|"HOSE"|"HNX"|"UPCOM") │
│                          X TO SIMPLIFY                          │
├─────────────────────────────────────────────────────────────────┤
│                     API LAYER (fetch + apiFetch)                 │
├─────────────────────────────────────────────────────────────────┤
│               /api/corporate-events ---- X REMOVE               │
│               /api/tickers (exchange filter) -- X SIMPLIFY      │
│               /api/analysis                                     │
│               /api/picks                                        │
│               /api/trades                                       │
│               /api/behavior                                     │
│               /api/goals                                        │
│               /api/health                                       │
│               /ws/prices                                        │
├─────────────────────────────────────────────────────────────────┤
│                   BACKEND (FastAPI monolith)                     │
├─────────────────────────────────────────────────────────────────┤
│  SCHEDULER (APScheduler)                                        │
│  Chain: price_crawl_hose -> hnx -> upcom                        │
│         -> indicators -> AI -> news -> sentiment -> combined    │
│         -> trading_signal -> hnx_upcom_analysis -> picks        │
│         -> pick_outcome -> consecutive_loss_check               │
│                                                                 │
│  + corporate_action_check (parallel from upcom) -- X REMOVE     │
│                                                                 │
│  SERVICES: AIAnalysisService, PickService, TradeService,        │
│            BehaviorService, GoalService, TickerService,          │
│            PriceService, RealtimePriceService                    │
│                                                                 │
│  CRAWLERS: VnstockCrawler, CorporateEventCrawler -- X REMOVE,  │
│            CafeF crawler                                        │
├─────────────────────────────────────────────────────────────────┤
│                    DATABASE (PostgreSQL / Aiven)                  │
│  tickers (has exchange col), daily_prices,                       │
│  corporate_events --- X DROP TABLE                               │
│  ai_analysis, daily_pick, user_watchlist (Telegram-era),        │
│  trades, lots, behaviors, goals, habits, etc.                   │
└─────────────────────────────────────────────────────────────────┘
```

## Removal Dependency Map — Critical for Safe Ordering

### Corporate Events: Full-Stack Removal

Corporate events is a self-contained vertical slice. The dependency chain is:

```
DB: corporate_events table
  |
  +-- Model: models/corporate_event.py (CorporateEvent)
  |     +-- models/__init__.py (import)
  |
  +-- Crawler: crawlers/corporate_event_crawler.py
  |     +-- scheduler/jobs.py (daily_corporate_action_check fn)
  |     +-- scheduler/manager.py (chain from price_crawl_upcom, _JOB_NAMES)
  |
  +-- API: api/corporate_events.py (router)
  |     +-- api/router.py (include_router)
  |
  +-- Frontend:
        +-- lib/api.ts (CorporateEventResponse type, fetchCorporateEvents fn)
        +-- lib/hooks.ts (useCorporateEvents hook)
        +-- components/corporate-events-calendar.tsx
        +-- app/dashboard/corporate-events/page.tsx
        +-- components/navbar.tsx ("Su kien" nav link)
  
  Tests:
  +-- backend: test_corporate_actions.py, test_corporate_actions_enhancements.py,
  |   test_corporate_events_api.py
  +-- e2e: api-errors.spec.ts, api-smoke.spec.ts, page-smoke.spec.ts
```

**No other feature depends on corporate events.** Safe to remove as isolated unit.

### HNX/UPCOM: Distributed Removal (More Complex)

HNX/UPCOM is not isolated — it threads through the entire stack:

**Backend touchpoints:**
- `config.py` — `realtime_priority_exchanges: ["HOSE","HNX","UPCOM"]`
- `crawlers/vnstock_crawler.py` — `_EXCHANGE_MAP` includes HNX/UPCOM
- `services/ticker_service.py` — `EXCHANGE_MAX_TICKERS: HNX=200, UPCOM=200`
- `services/price_service.py` — `crawl_daily(exchange=None)` crawls all
- `api/tickers.py` — `ALLOWED_EXCHANGES = {"HOSE","HNX","UPCOM"}`, exchange filter on all endpoints
- `scheduler/manager.py` — 3 staggered crawl jobs (HOSE 15:30, HNX 16:00, UPCOM 16:30), chain triggers from `daily_price_crawl_upcom`, `daily_hnx_upcom_analysis` chain step
- `scheduler/jobs.py` — `VALID_EXCHANGES`, `daily_price_crawl_for_exchange`, `daily_hnx_upcom_analysis()`
- `services/analysis/prompts.py` — "HOSE/HNX/UPCOM" in system instructions
- `services/ai_analysis_service.py` — `analyze_watchlisted_tickers()` method
- `models/ticker.py` — `exchange` column (keep, default="HOSE")

**Frontend touchpoints:**
- `lib/store.ts` — `Exchange` type, `useExchangeStore`
- `components/exchange-filter.tsx` — Tab buttons for all exchanges
- `components/exchange-badge.tsx` — Badge styling per exchange
- `components/watchlist-table.tsx` — Uses ExchangeBadge, exchange filtering
- `app/page.tsx` — ExchangeFilter on home page
- `app/dashboard/page.tsx` — ExchangeFilter on dashboard
- `app/watchlist/page.tsx` — ExchangeFilter on watchlist
- `app/ticker/[symbol]/page.tsx` — AnalyzeNowButton (HNX/UPCOM specific), ExchangeBadge
- `layout.tsx` — metadata mentions "HOSE, HNX, UPCOM"

**Tests:**
- `test_ai_analysis_tiered.py` (HNX/UPCOM analysis tests)
- `test_ticker_service_multi.py` (multi-exchange tests)
- E2E tests referencing exchange filters

## Component Responsibilities — What Changes

| Component | Current Responsibility | v9.0 Change | Impact |
|-----------|----------------------|-------------|--------|
| `corporate_events` DB table | Store dividend/rights events | **DROP TABLE** via Alembic | Data loss (acceptable) |
| `CorporateEvent` model | ORM for corporate events | **DELETE file** | Cascades to imports |
| `CorporateEventCrawler` | VNDirect API scraper | **DELETE file** | Remove from scheduler |
| `corporate_events.py` API | REST endpoint | **DELETE file** | Remove from router |
| `corporate-events-calendar.tsx` | Calendar UI component | **DELETE file** | Remove from page |
| `/dashboard/corporate-events/` | Page directory | **DELETE directory** | Remove from navbar |
| `scheduler/manager.py` | Job chaining | **MODIFY** — remove corp chain, HNX/UPCOM crawls | Critical: must rechain |
| `scheduler/jobs.py` | Job functions | **MODIFY** — remove 3 functions | |
| `ticker_service.py` | Multi-exchange mgmt | **SIMPLIFY** — HOSE only | |
| `vnstock_crawler.py` | Exchange map | **SIMPLIFY** | Minor |
| `config.py` | Exchange priority list | **SIMPLIFY** | Minor |
| `api/tickers.py` | ALLOWED_EXCHANGES | **SIMPLIFY** | Minor |
| `store.ts` | Exchange type + store | **REMOVE** exchange store | Cascading UI changes |
| `exchange-filter.tsx` | Tab UI for exchange | **DELETE file** | Remove from all pages |
| `exchange-badge.tsx` | Exchange label badge | **DELETE file** | Remove from components |
| `user_watchlist` DB table | Telegram chat_id watchlist | **DROP** (replaced) | New table created |
| `useWatchlistStore` (zustand) | localStorage watchlist | **REPLACE** with API hook | New API endpoints needed |
| Coach page | Display-only sections | **REDESIGN** for interactivity | Major UI rework |
| AI prompts | Short reasoning (2-3 sentences) | **EXPAND** output length | Prompt engineering |
| Navbar | 7 navigation links | **RESTRUCTURE** | Reorder + rename + reduce |

## Safe Removal Order — Dependency-Aware Sequence

### Phase 1: Corporate Events Removal (Isolated, Low Risk)

**Principle: Remove consumers before producers. Frontend → API → Scheduler → Model → DB.**

```
Step 1: Frontend removal (no backend dependency)
  - Delete /dashboard/corporate-events/page.tsx (page)
  - Delete corporate-events-calendar.tsx (component)
  - Remove nav link from navbar.tsx ("Su kien" entry)
  - Remove CorporateEventResponse type from api.ts
  - Remove fetchCorporateEvents function from api.ts
  - Remove useCorporateEvents hook from hooks.ts
  - Remove E2E tests referencing corporate-events

Step 2: Backend API removal
  - Remove corporate_events.py from api/
  - Remove import + include_router from api/router.py
  - Remove corporate_events_api tests

Step 3: Scheduler removal
  - Remove daily_corporate_action_check from jobs.py
  - Remove chaining from _on_job_executed in manager.py
    (the parallel branch from daily_price_crawl_upcom)
  - Remove _JOB_NAMES entries for corporate jobs
  - Remove corporate action tests

Step 4: Crawler + Model removal
  - Delete crawlers/corporate_event_crawler.py
  - Delete models/corporate_event.py
  - Remove CorporateEvent from models/__init__.py
  - Remove from __all__ in models/__init__.py
  - Check if resilience.vndirect_breaker is only used here (remove if so)

Step 5: Alembic migration — DROP TABLE
  - Create migration: op.drop_table("corporate_events")
  - Include full downgrade (recreate table) for reversibility
```

**Why this order:** Frontend first = users see no broken links. API second = no 404s. Scheduler third = no jobs referencing deleted code. Model/crawler fourth = clean imports. DB last = irreversible data deletion only after all code references removed.

### Phase 2: HNX/UPCOM Removal (Distributed, Medium Risk)

```
Step 1: Scheduler simplification (CRITICAL — controls data pipeline)
  - Remove daily_price_crawl_hnx and daily_price_crawl_upcom from configure_jobs()
  - RECHAIN: in _on_job_executed, change trigger from "daily_price_crawl_upcom"
    to "daily_price_crawl_hose" for the indicator chain
  - Remove daily_hnx_upcom_analysis job + chain step
  - RECHAIN: daily_trading_signal -> daily_pick_generation (skip hnx_upcom)
  - Remove HNX/UPCOM entries from _JOB_NAMES
  - Update pipeline logging string

Step 2: Backend service simplification
  - ticker_service.py: Remove HNX/UPCOM from EXCHANGE_MAX_TICKERS (HOSE=400 only)
  - vnstock_crawler.py: Simplify _EXCHANGE_MAP to just HOSE
  - price_service.py: Default to HOSE (or remove exchange param)
  - config.py: Set realtime_priority_exchanges to ["HOSE"] only
  - api/tickers.py: Remove or simplify exchange filter (HOSE-only)
  - analysis/prompts.py: Remove "HNX/UPCOM" from system instructions
  - Remove ai_analysis_service.analyze_watchlisted_tickers() method

Step 3: Frontend exchange removal
  - Delete components/exchange-filter.tsx
  - Delete components/exchange-badge.tsx
  - Remove useExchangeStore from store.ts, remove Exchange type
  - Remove ExchangeFilter from app/page.tsx, app/dashboard/page.tsx,
    app/watchlist/page.tsx
  - Remove ExchangeBadge from watchlist-table.tsx, ticker/[symbol]/page.tsx
  - Remove AnalyzeNowButton entirely from ticker/[symbol]/page.tsx
    (was only for HNX/UPCOM tickers without daily analysis)
  - Update layout.tsx metadata
  - Clean up api.ts: remove exchange params from fetchTickers/fetchMarketOverview

Step 4: Data cleanup
  - Deactivate HNX/UPCOM tickers: UPDATE tickers SET is_active=false
    WHERE exchange IN ('HNX','UPCOM')
  - DO NOT DELETE rows — foreign keys from daily_prices, ai_analysis etc.
  - Optional Alembic migration for the data update

Step 5: Test cleanup
  - Remove/update test_ai_analysis_tiered.py
  - Remove/update test_ticker_service_multi.py
  - Update E2E tests referencing exchange filters
  - Update test_scheduler.py chain expectations
```

**CRITICAL WARNING: Rechain the scheduler FIRST.** The entire daily pipeline (indicators → AI → picks) chains from `daily_price_crawl_upcom` completion. If the UPCOM crawl job is removed without updating the chain trigger, the pipeline silently stops. The fix: change the trigger to fire from `daily_price_crawl_hose` completion BEFORE removing the other crawl jobs.

**DO NOT delete HNX/UPCOM ticker rows.** FK constraints from daily_prices, ai_analysis, technical_indicators, news_articles will cascade-delete historical data or throw violations. Use `is_active=false` — queries already filter by `is_active = true`.

## Watchlist Migration Architecture: localStorage → PostgreSQL

### Current Architecture

```
useWatchlistStore (zustand + persist middleware)
  watchlist: string[]   -->  localStorage("holo-watchlist")
  addToWatchlist(symbol)
  removeFromWatchlist(symbol)
  isInWatchlist(symbol)
     |
     consumed by: watchlist-table.tsx, ticker/[symbol]/page.tsx
```

### Target Architecture

```
React Query hooks (server state) + optimistic mutations

useWatchlist() ---- GET /api/watchlist --> ["VNM","FPT","HPG",...]
                    staleTime: 5 min

useAddToWatchlist() ---- POST /api/watchlist {symbol: "VNM"}
                         onMutate: optimistic add to cache
                         onError: rollback
                         onSettled: invalidate ["watchlist"]

useRemoveFromWatchlist() ---- DELETE /api/watchlist/VNM
                              onMutate: optimistic remove
                              onError: rollback
                              onSettled: invalidate ["watchlist"]
     |
     v
Backend: /api/watchlist (NEW router)
  GET    /           -> list of symbols
  POST   /           -> add (idempotent)
  DELETE /{symbol}   -> remove
  POST   /import     -> bulk import (one-time migration)
     |
     v
DB: watchlist table (NEW, replaces user_watchlist)
  id, ticker_id (FK->tickers), added_at
  UNIQUE(ticker_id)  -- single-user, no user_id needed
```

### Database Migration

```python
# Alembic migration: create watchlist, drop user_watchlist

def upgrade():
    # Create new simple watchlist table
    op.create_table(
        "watchlist",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ticker_id", sa.Integer, sa.ForeignKey("tickers.id"), nullable=False),
        sa.Column("added_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("ticker_id", name="uq_watchlist_ticker"),
    )
    # Drop old Telegram-era watchlist (no longer used since Telegram bot removed in v7.0)
    op.drop_table("user_watchlist")

def downgrade():
    # Recreate user_watchlist for reversibility
    op.create_table("user_watchlist", ...)
    op.drop_table("watchlist")
```

### Frontend Migration — localStorage to API (One-Time)

```typescript
// Called once on app mount, migrates existing localStorage data
async function migrateLocalWatchlist() {
  const stored = localStorage.getItem("holo-watchlist");
  if (!stored) return;

  const { state } = JSON.parse(stored);
  if (!state?.watchlist?.length) return;

  // Bulk import to backend
  await apiFetch("/watchlist/import", {
    method: "POST",
    body: JSON.stringify({ symbols: state.watchlist }),
  });

  // Clear localStorage after successful migration
  localStorage.removeItem("holo-watchlist");
}
```

**Reversibility:** Keep localStorage read as fallback for 1 release cycle. If API fails, fall back to cached localStorage data. Remove fallback in next milestone.

### Backend Endpoints (New File: api/watchlist.py)

```python
router = APIRouter(prefix="/watchlist", tags=["watchlist"])

@router.get("/", response_model=list[str])
async def get_watchlist():
    """Return list of watched ticker symbols."""

@router.post("/", status_code=201)
async def add_to_watchlist(body: WatchlistAdd):
    """Add ticker to watchlist. Idempotent (no error if already exists)."""

@router.delete("/{symbol}", status_code=204)
async def remove_from_watchlist(symbol: str):
    """Remove ticker from watchlist."""

@router.post("/import", status_code=200)
async def bulk_import(body: WatchlistImport):
    """One-time migration endpoint: import symbols from localStorage."""
```

## Navigation Restructure

### Current Navigation (navbar.tsx NAV_LINKS)

```
Tong quan        -> /                        (market heatmap)
Danh muc         -> /watchlist               (watchlist)
Bang dieu khien  -> /dashboard               (dashboard stats)
Huan luyen       -> /coach                   (AI coach — daily picks)
Nhat ky          -> /journal                 (trade journal)
Su kien          -> /dashboard/corporate-evt (X REMOVE)
He thong         -> /dashboard/health        (system health)
```

### Target Navigation

```
Tong quan   -> /                   (market heatmap, no exchange filter)
Goi y       -> /coach              (renamed from "Huan luyen" — clearer purpose)
Nhat ky     -> /journal            (trade journal)
Danh muc    -> /watchlist          (watchlist — now DB-backed)
He thong    -> /dashboard/health   (system health — for power user)
```

**Changes:**
1. **Remove** "Su kien" — corporate events page deleted
2. **Remove** "Bang dieu khien" (/dashboard) — overlaps with Home heatmap (has pie chart + top movers, redundant). Either merge top movers into `/` or keep accessible by URL only.
3. **Rename** "Huan luyen" → "Goi y" — user sees "suggestions today" not abstract "coaching"
4. **Reorder** — flow follows user journey: overview → suggestions → act (journal) → track (watchlist) → system
5. **5 links instead of 7** — reduced cognitive load

## Coach Page Redesign Architecture

### Current Structure (Single Long Page)

```
CoachPage (one scrollable page, ~10 sections)
  - RiskSuggestionBanner
  - Header + ProfileSettingsCard
  - PickPerformanceCards
  - Today's Picks (PickCard grid)
  - AlmostSelectedList
  - Open Trades (TradesTable BUY filter)
  - PickHistoryTable
  - Goals & Reviews (MonthlyGoalCard, WeeklyPromptCard, WeeklyReviewCard)
  - Behavior Insights (HabitDetectionCard, ViewingStatsCard, SectorPreferencesCard)
```

**Problems:** Too many sections dumped on one page. No clear "what do I do next?" after seeing picks. Display-only — no inline actions. User must navigate to /journal to act on a pick.

### Target: Tab-Based Interactive Layout

```
CoachPage (tabbed sections)
  Header + ProfileSettingsCard (always visible)
  |
  +-- Tab: "Goi y hom nay" (default)
  |     PickPerformanceCards (summary row)
  |     Today's Picks (PickCard grid)
  |       Each PickCard: NEW "Ghi lenh" button -> TradeEntryDialog
  |                      (pre-filled with pick's entry/SL/TP/quantity)
  |     AlmostSelectedList
  |     RiskSuggestionBanner
  |
  +-- Tab: "Vi the & Lich su"
  |     Open Trades (TradesTable, BUY filter)
  |       Each trade row: "Dong vi the" quick action
  |     PickHistoryTable
  |
  +-- Tab: "Phan tich hanh vi"
        MonthlyGoalCard (interactive — set/update)
        WeeklyReviewCard
        HabitDetectionCard
        SectorPreferencesCard
```

### Key Interactivity: Pick → Trade in One Click

```
PickCard (data from DailyPick)
  |
  | user clicks "Ghi lenh"
  v
TradeEntryDialog (pre-filled)
  ticker_symbol: pick.ticker_symbol
  side: "BUY"
  entry_price: pick.entry_price
  quantity: pick.position_size_shares
  note: "Tu goi y ngay {pick.pick_date}"
  |
  | user confirms
  v
POST /api/trades (createTrade mutation)
  |
  | invalidates ["trades"]
  v
Tab 2 TradesTable refreshes with new position
```

**Implementation:** Add optional `prefill` prop to existing `TradeEntryDialog`. PickCard renders a button that opens the dialog with `prefill={pick}`. No new components needed — just wiring existing ones together.

## AI Prompt Architecture for Longer Output

### Current Prompt Constraints

| Analysis Type | Reasoning Limit | Temperature |
|---------------|-----------------|-------------|
| Technical | "2-3 cau" (~50 words) | 0.1 |
| Fundamental | "2-3 cau" (~50 words) | 0.2 |
| Sentiment | "2-3 cau" (~50 words) | 0.3 |
| Combined | "toi da 200 tu" | 0.2 |
| Trading Signal | "toi da 300 ky tu" | 0.2 |

### Target: Expanded Reasoning

**Changes to `services/analysis/prompts.py`:**

| Analysis Type | Current | Target | What to Include |
|---------------|---------|--------|-----------------|
| Technical | "2-3 cau" | "4-6 cau, phan tich chi tiet" | Trend, momentum, S/R context |
| Fundamental | "2-3 cau" | "4-6 cau, danh gia chi tiet" | Peer comparison, growth, risks |
| Sentiment | "2-3 cau" | "3-5 cau, neu ro tin nao" | Which news matters, market context |
| Combined | "toi da 200 tu" | "300-500 tu" | Action rationale, risk, timing |
| Trading Signal | "toi da 300 ky tu" | "toi da 500 ky tu" | Specific levels, scenarios |

**Config changes:**

```python
# config.py — may need new settings
gemini_combined_max_tokens: int = 32768  # Up from default
gemini_analysis_max_tokens: int = 16384  # For tech/fund/sent

# Batch size impact: larger output per ticker = fewer tickers per batch
# May need to reduce gemini_batch_size from 25 to 15-20 for analysis types
```

**No schema migration needed:** `reasoning` field in `ai_analysis` table is `TEXT` (unlimited). Pydantic schema uses `str`. Only prompt text changes.

## Architectural Patterns to Follow

### Pattern 1: Outside-In Removal

**What:** Remove consumers before producers. Frontend → API → Scheduler → Model → DB.
**When to use:** Any feature removal involving full-stack vertical slices.
**Trade-offs:** Slightly more steps, but each step is independently safe and deployable. At each step, no code references the removed feature.

### Pattern 2: Alembic Migration for All DDL

**What:** Always use Alembic migrations for schema changes. Never raw SQL on production.
**When to use:** Dropping `corporate_events`, creating `watchlist`, dropping `user_watchlist`.
**Trade-offs:** Slower than raw SQL, but provides audit trail and reversibility.

```python
# Always include reversible downgrade
def upgrade():
    op.drop_table("corporate_events")
def downgrade():
    op.create_table("corporate_events", ...)  # full schema for reversibility
```

### Pattern 3: Optimistic Mutation with React Query

**What:** Update UI immediately on user action, sync with server in background, rollback on error.
**When to use:** Watchlist add/remove — user expects instant star toggle.
**Trade-offs:** More complex mutation code, but vastly better perceived performance.

```typescript
useMutation({
  mutationFn: (symbol) => addToWatchlist(symbol),
  onMutate: async (symbol) => {
    await queryClient.cancelQueries({ queryKey: ["watchlist"] });
    const previous = queryClient.getQueryData<string[]>(["watchlist"]);
    queryClient.setQueryData(["watchlist"], old => [...(old ?? []), symbol]);
    return { previous };
  },
  onError: (_err, _sym, ctx) => {
    queryClient.setQueryData(["watchlist"], ctx?.previous);
  },
  onSettled: () => {
    queryClient.invalidateQueries({ queryKey: ["watchlist"] });
  },
});
```

### Pattern 4: Scheduler Rechain Safety

**What:** When removing a chain step, verify trigger source AND next target.
**When to use:** Removing HNX/UPCOM crawls and hnx_upcom_analysis from pipeline.

```
BEFORE: hose -> hnx -> upcom -> indicators -> ... -> signal -> hnx_upcom -> picks
AFTER:  hose -> indicators -> ... -> signal -> picks

Two critical rechain points in _on_job_executed:
1. "daily_price_crawl_upcom" trigger -> change to "daily_price_crawl_hose"
2. "daily_trading_signal_triggered" -> skip hnx_upcom, chain to picks directly
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Removing DB Table Before Code References

**What people do:** Create Alembic migration first, then fix code.
**Why it's wrong:** If migration runs on deploy before code update, `from app.models.corporate_event import CorporateEvent` fails at module load = application crash.
**Do this instead:** Remove ALL code references first. Migration is the absolute last step.

### Anti-Pattern 2: Hard-Deleting HNX/UPCOM Ticker Rows

**What people do:** `DELETE FROM tickers WHERE exchange IN ('HNX', 'UPCOM')`.
**Why it's wrong:** FK constraints from daily_prices, ai_analysis, technical_indicators cascade-delete or throw violations. Years of historical data lost.
**Do this instead:** `UPDATE tickers SET is_active = false WHERE exchange != 'HOSE'`. Data stays. All queries already filter by `is_active = true`.

### Anti-Pattern 3: Breaking the Scheduler Chain

**What people do:** Remove a chain step without updating the trigger mapping.
**Why it's wrong:** Entire downstream pipeline stops. No indicators, no AI analysis, no daily picks. Silent failure — no error, just no new data each day.
**Do this instead:** Update `_on_job_executed` BEFORE removing any scheduled job. Test chain manually. Verify with `scheduler.get_jobs()`.

### Anti-Pattern 4: Simultaneous Frontend + Backend Deploy for Removals

**What people do:** Deploy backend (removes `/api/corporate-events`) and frontend (still calls it) at the same time.
**Why it's wrong:** Brief window of 404 errors.
**Do this instead:** Deploy frontend removal first (stops calling endpoint). Then deploy backend. For single-user app the window is tiny, but the principle prevents bugs.

## Integration Points

### External Services Affected

| Service | Integration | v9.0 Impact |
|---------|-------------|-------------|
| VNDirect API | `CorporateEventCrawler` REST calls | **REMOVE** — crawler deleted |
| VCI (vnstock) | `VnstockCrawler` via `asyncio.to_thread()` | **SIMPLIFY** — HOSE only |
| Google Gemini | `GeminiClient` structured output | **MODIFY** — longer prompts |
| PostgreSQL (Aiven) | asyncpg via SQLAlchemy async | **MIGRATE** — new table, drop tables |

### Internal Boundaries Affected

| Boundary | Current Communication | v9.0 Change |
|----------|----------------------|-------------|
| Scheduler → CorporateEventCrawler | Direct fn call via chain | **REMOVE** chain step |
| Scheduler → hnx_upcom_analysis | Direct fn call via chain | **REMOVE** + rechain |
| Frontend watchlist → localStorage | zustand persist middleware | **REPLACE** with REST API |
| Frontend ↔ Backend watchlist | None currently | **NEW** `/api/watchlist` |
| Coach PickCard → Journal | Separate pages, no link | **NEW** in-page dialog trigger |

### Database Migration Sequence

```
Migration 024: Drop corporate_events table
Migration 025: Create watchlist table, drop user_watchlist
Migration 026: (optional) Deactivate HNX/UPCOM tickers via data migration

Can be combined into fewer migrations if done in same phase.
```

## Scaling Impact (Positive)

| Metric | Before v9.0 | After v9.0 |
|--------|-------------|------------|
| Daily pipeline duration | ~45 min (3 exchanges) | ~15 min (HOSE only) |
| Gemini API calls/day | ~800 tickers × 5 types | ~400 tickers × 5 types |
| DB row growth rate | 800 tickers/day | 400 tickers/day |
| Scheduler complexity | 3 parallel crawl chains | 1 linear chain |
| VNDirect API calls | Corporate events for 800 tickers | Eliminated |

## Sources

- Direct codebase analysis of all files referenced in this document (HIGH confidence)
- Alembic migration history: 23 existing migrations in `alembic/versions/` (HIGH confidence)
- APScheduler 3.11 job chaining from `scheduler/manager.py` (HIGH confidence)
- React Query optimistic update pattern — TanStack docs (HIGH confidence)

---
*Architecture research for: v9.0 UX Rework & Simplification*
*Researched: 2025-07-21*

# Phase 55: Discovery Frontend - Research

**Researched:** 2025-07-18
**Domain:** Next.js frontend page + FastAPI backend endpoint for stock discovery results
**Confidence:** HIGH

## Summary

This phase builds a Discovery page that surfaces daily AI-scored tickers from the existing `discovery_results` table (Phase 52) and lets users add them to their watchlist with one click. The backend needs a new `/api/discovery` endpoint that queries `discovery_results` JOIN `tickers` with filtering by sector and signal type. The frontend needs a new Next.js page at `/discovery` with a table/card view showing composite scores, signal breakdowns, sector filters, and add-to-watchlist buttons.

The entire stack is already established in the codebase: FastAPI async endpoints with `async_session`, Pydantic response schemas, `apiFetch<T>()` typed client, `@tanstack/react-query` hooks, `@tanstack/react-table` for sortable data tables, and `shadcn/ui` components. The `SectorCombobox`, `useSectors`, `useAddToWatchlist`, and `useWatchlist` hooks from Phases 49/54 are directly reusable. No new libraries are needed.

**Primary recommendation:** Follow the exact patterns of the watchlist router + watchlist-table component. Backend: new `discovery.py` router with GET `/discovery` accepting sector, signal_type, and limit query params. Frontend: new `/discovery/page.tsx` with a `DiscoveryTable` component using `@tanstack/react-table`, score breakdown bars, sector filter via `SectorCombobox`, signal-type filter via a simple select, and per-row "Thêm vào danh mục" button that calls the existing `addWatchlistItem()` API function.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- All decisions at agent's discretion (no locked choices from discuss-phase)
- UI should follow existing shadcn/ui + Tailwind patterns
- Discovery page accessible from main navigation

### Agent's Discretion
- Full discretion on all implementation details

### Deferred Ideas (OUT OF SCOPE)
- None specified
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DPAGE-01 | Discovery page shows top-scored tickers with composite score and signal breakdown | Backend GET `/api/discovery` returning DiscoveryItem[] with all 6 dimension scores + total_score + ticker info. Frontend table with score bar components for each dimension. |
| DPAGE-02 | User can add any discovery ticker to watchlist with single button click, sector auto-suggested from ICB | Reuse existing `addWatchlistItem(symbol)` → POST `/api/watchlist` which already auto-populates `sector_group` from ICB. Frontend button per row calling `useAddToWatchlist` hook. Cross-check with `useWatchlist` data for "already added" state. |
| DPAGE-03 | User can filter discovery results by sector and signal type | Backend accepts `sector` and `signal_type` query params. SectorCombobox from Phase 54 for sector filter. Custom select/buttons for signal type filter (RSI oversold, MACD bullish, etc.). |
</phase_requirements>

## Standard Stack

### Core (already installed — no new dependencies)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 16.2.3 | App Router page at `/discovery` | Already installed, project framework [VERIFIED: package.json] |
| @tanstack/react-table | ^8.21.3 | Sortable/filterable discovery results table | Already used in watchlist-table.tsx [VERIFIED: codebase] |
| @tanstack/react-query | ^5.99.0 | Data fetching hook for discovery results | Already used throughout hooks.ts [VERIFIED: codebase] |
| shadcn/ui | 4.x (base-ui) | Card, Badge, Button, Table, Skeleton, Command components | Already installed and used project-wide [VERIFIED: package.json] |
| FastAPI | ~0.135 | Backend API endpoint | Already the backend framework [VERIFIED: codebase] |
| SQLAlchemy | ~2.0 | Async queries on discovery_results + tickers | Already used in all services [VERIFIED: codebase] |

### Reusable Components (already built)
| Component/Hook | Location | Reuse Strategy |
|---------------|----------|----------------|
| `SectorCombobox` | `src/components/sector-combobox.tsx` | Direct reuse for sector filter dropdown [VERIFIED: codebase] |
| `useSectors()` | `src/lib/hooks.ts` | Fetches ICB sector list for filter [VERIFIED: codebase] |
| `useAddToWatchlist()` | `src/lib/hooks.ts` | Mutation hook for adding to watchlist [VERIFIED: codebase] |
| `useWatchlist()` | `src/lib/hooks.ts` | Fetch current watchlist to show "already added" state [VERIFIED: codebase] |
| `addWatchlistItem(symbol)` | `src/lib/api.ts` | POST `/api/watchlist` with auto ICB sector [VERIFIED: codebase] |
| `fetchSectors()` | `src/lib/api.ts` | GET `/api/tickers/sectors` for ICB names [VERIFIED: codebase] |
| `ScoreBar` | `src/components/analysis-card.tsx` | Visual score bar component (0-10 scale) [VERIFIED: codebase] |
| `Badge` | `src/components/ui/badge.tsx` | Signal labels and score badges [VERIFIED: codebase] |
| `Skeleton` | `src/components/ui/skeleton.tsx` | Loading states [VERIFIED: codebase] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| @tanstack/react-table | Simple HTML table | react-table already in use, provides sorting for free |
| SectorCombobox (existing) | New filter component | Existing component is proven and tested |
| Server-side filtering | Client-side filtering | ~400 tickers max → client-side is viable, but server-side is cleaner for pagination and reduces payload when filtering by sector |

**Installation:** No new packages needed. All dependencies already in `package.json`.

## Architecture Patterns

### Backend: New Discovery Router

```
backend/app/
├── api/
│   ├── discovery.py        # NEW — GET /api/discovery endpoint
│   └── router.py           # ADD discovery_router import
├── schemas/
│   └── discovery.py        # NEW — DiscoveryItemResponse Pydantic schema
├── models/
│   └── discovery_result.py # EXISTS — DiscoveryResult model (Phase 52)
└── services/
    └── discovery_service.py # EXISTS — scoring engine (Phase 52)
```

### Frontend: New Discovery Page

```
frontend/src/
├── app/
│   └── discovery/
│       └── page.tsx         # NEW — Discovery page route
├── components/
│   ├── discovery-table.tsx  # NEW — table with scores + add-to-watchlist
│   └── sector-combobox.tsx  # EXISTS — reuse for filter
└── lib/
    ├── api.ts              # ADD: fetchDiscovery(), DiscoveryItem type
    └── hooks.ts            # ADD: useDiscovery() hook
```

### Pattern 1: Backend Router (following watchlist.py pattern)
**What:** New GET endpoint at `/api/discovery` that queries latest discovery_results with ticker info
**When to use:** Always — this is the data source for the entire page
**Example:**
```python
# Source: Codebase pattern from backend/app/api/watchlist.py
# Pattern: router with prefix, async_session context manager, Pydantic response

router = APIRouter(prefix="/discovery", tags=["discovery"])

@router.get("/", response_model=list[DiscoveryItemResponse])
async def get_discovery_results(
    sector: str | None = Query(None, description="Filter by ICB sector"),
    signal_type: str | None = Query(None, description="Filter by signal: rsi, macd, adx, volume, pe, roe"),
    min_score: float = Query(0, ge=0, le=10, description="Minimum total_score"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
):
    async with async_session() as session:
        # Query discovery_results JOIN tickers for latest score_date
        ...
```

### Pattern 2: Frontend API + Hook (following hooks.ts pattern)
**What:** TypeScript type, fetch function, and React Query hook
**When to use:** Standard pattern for every data source in this codebase
**Example:**
```typescript
// Source: Codebase pattern from frontend/src/lib/api.ts + hooks.ts

// In api.ts:
export interface DiscoveryItem {
  symbol: string;
  name: string;
  sector: string | null;
  score_date: string;
  rsi_score: number | null;
  macd_score: number | null;
  adx_score: number | null;
  volume_score: number | null;
  pe_score: number | null;
  roe_score: number | null;
  total_score: number;
  dimensions_scored: number;
}

export async function fetchDiscovery(params?: {
  sector?: string;
  signal_type?: string;
  min_score?: number;
  limit?: number;
}): Promise<DiscoveryItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.sector) searchParams.set("sector", params.sector);
  // ...
  const qs = searchParams.toString();
  return apiFetch<DiscoveryItem[]>(`/discovery${qs ? `?${qs}` : ""}`);
}

// In hooks.ts:
export function useDiscovery(params?: { sector?: string; signal_type?: string }) {
  return useQuery({
    queryKey: ["discovery", params?.sector ?? "all", params?.signal_type ?? "all"],
    queryFn: () => fetchDiscovery(params),
    staleTime: 5 * 60 * 1000,  // 5 min — same as market overview
  });
}
```

### Pattern 3: Discovery Table (following watchlist-table.tsx pattern)
**What:** Data table with @tanstack/react-table, sortable columns, score visuals
**When to use:** Main display component for discovery results
**Key elements:**
- `useReactTable` with `getCoreRowModel` + `getSortedRowModel`
- Column definitions as `ColumnDef<DiscoveryItem>[]`
- Score bars for each dimension (reuse `ScoreBar` from analysis-card.tsx)
- "Thêm vào danh mục" button per row using `useAddToWatchlist()`
- Row click navigates to `/ticker/{symbol}` (same as watchlist-table)
- Skeleton loading state pattern

### Pattern 4: Navigation Integration
**What:** Add "Khám phá" link to navbar NAV_LINKS array
**Where:** `src/components/navbar.tsx` line 22-28
**Example:**
```typescript
// Source: Codebase pattern from frontend/src/components/navbar.tsx
const NAV_LINKS = [
  { href: "/", label: "Tổng quan" },
  { href: "/discovery", label: "Khám phá" },  // NEW
  { href: "/watchlist", label: "Danh mục" },
  { href: "/coach", label: "Huấn luyện" },
  { href: "/journal", label: "Nhật ký" },
  { href: "/dashboard/health", label: "Hệ thống" },
];
```

### Anti-Patterns to Avoid
- **Don't fetch all discovery_results without date filter:** The table has up to 14 days of history (~400 tickers × 14 days = 5,600 rows). Always filter to latest `score_date` on the backend. [VERIFIED: DiscoveryService.RETENTION_DAYS = 14]
- **Don't build a custom sector filter:** SectorCombobox already exists and works with `useSectors()` hook. [VERIFIED: codebase]
- **Don't use zustand for filter state:** URL query params or simple `useState` is sufficient for sector/signal filters. No global state needed. [VERIFIED: project pattern — watchlist page uses no zustand for filters]
- **Don't hand-roll score visualization:** Reuse `ScoreBar` from analysis-card.tsx or use simple Tailwind width-based bars. [VERIFIED: codebase has ScoreBar]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sector filter dropdown | Custom searchable select | `SectorCombobox` + `useSectors()` | Already built, tested, consistent UX [VERIFIED: codebase] |
| Add to watchlist | Custom API call + state management | `useAddToWatchlist()` hook | Handles mutation + cache invalidation [VERIFIED: codebase] |
| "Already in watchlist" check | Custom tracking state | `useWatchlist()` data + Set lookup | Watchlist query already cached, just check if symbol exists [VERIFIED: codebase] |
| Score bar visualization | Canvas/SVG bars | Tailwind `w-[${pct}%]` div bars or `ScoreBar` component | Consistent with existing analysis card pattern [VERIFIED: codebase] |
| Sortable table | Custom sort logic | `@tanstack/react-table` `getSortedRowModel()` | Already the standard in this project [VERIFIED: codebase] |
| Data fetching + caching | `fetch` + `useState` + `useEffect` | `useQuery` from `@tanstack/react-query` | Project standard, handles stale/loading/error states [VERIFIED: codebase] |

**Key insight:** This phase is almost entirely assembly of existing patterns and components. The only genuinely new code is the backend query (JOIN discovery_results + tickers, filter by sector/signal) and the frontend table column definitions with score bars.

## Common Pitfalls

### Pitfall 1: Fetching Wrong Date's Discovery Results
**What goes wrong:** Query returns empty or stale results because score_date doesn't match expectations.
**Why it happens:** `DiscoveryService.score_all_tickers()` uses `date.today()` which depends on server timezone. The discovery pipeline may not have run yet today.
**How to avoid:** Backend query should select the MAX(score_date) from discovery_results and use that as the filter, not `date.today()`. This ensures the latest available results are always shown.
**Warning signs:** Empty discovery page on days when pipeline hasn't run yet.

### Pitfall 2: Decimal Serialization in FastAPI
**What goes wrong:** `Decimal` fields from SQLAlchemy (rsi_score, total_score, etc.) fail JSON serialization or produce unexpected string representations.
**Why it happens:** `DiscoveryResult` uses `Numeric(4,2)` mapped to Python `Decimal`. FastAPI/Pydantic v2 handles this, but response model must use `float` not `Decimal`.
**How to avoid:** Pydantic response schema should use `float | None` for all score fields with explicit `float()` conversion in the response builder — same pattern used in `tickers.py` for `market_cap`.
**Warning signs:** 500 error on serialization or scores showing as strings like "7.50" in JSON.

### Pitfall 3: N+1 Query for Ticker Symbol/Name
**What goes wrong:** Querying discovery_results then looping to fetch ticker info for each result.
**Why it happens:** DiscoveryResult only has `ticker_id` FK, not symbol/name.
**How to avoid:** Single JOIN query: `SELECT dr.*, t.symbol, t.name, t.sector FROM discovery_results dr JOIN tickers t ON dr.ticker_id = t.id`. [VERIFIED: same JOIN pattern used in watchlist.py]
**Warning signs:** Slow API response, many DB queries in logs.

### Pitfall 4: Signal Type Filter Logic
**What goes wrong:** "Filter by signal type" is ambiguous — what defines a signal?
**Why it happens:** Scores are continuous 0-10, not binary signals. Need threshold logic to determine what counts as "RSI oversold" vs just "has RSI score."
**How to avoid:** Define clear thresholds in the backend. E.g., `rsi_score >= 7` = "RSI oversold signal", `macd_score >= 7` = "MACD bullish". The signal_type filter should check if the relevant score exceeds a threshold. Document these thresholds in the response.
**Warning signs:** Users confused about what "filter by RSI" means.

### Pitfall 5: Watchlist Button State Race Condition
**What goes wrong:** User clicks "Add to watchlist" but button doesn't update to "Đã thêm" state.
**Why it happens:** `useAddToWatchlist` invalidates the watchlist query, but if the discovery page doesn't re-derive the "already added" Set, the button state is stale.
**How to avoid:** Derive `watchlistSymbols` Set from `useWatchlist()` data in a `useMemo`. The button state is `watchlistSymbols.has(symbol)`. When watchlist invalidates and refetches, the Set updates automatically.
**Warning signs:** Button says "Thêm" even after successful add.

### Pitfall 6: Next.js 16 App Router Caveats
**What goes wrong:** Using patterns from Next.js 13-15 that are deprecated or changed in 16.
**Why it happens:** The project uses Next.js 16.2.3 which has breaking changes from training data.
**How to avoid:** The page component is client-side ("use client") like all other pages in this project. Follow the exact same pattern as `watchlist/page.tsx` — a simple "use client" page that imports and renders components. [VERIFIED: all existing pages use "use client"]
**Warning signs:** AGENTS.md explicitly warns: "This is NOT the Next.js you know" — read docs in node_modules if unsure.

## Code Examples

### Backend: Discovery Router (complete pattern)
```python
# Source: Codebase pattern from backend/app/api/watchlist.py + tickers.py
"""Discovery page API — top-scored tickers with filtering."""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select, func

from app.database import async_session
from app.models.discovery_result import DiscoveryResult
from app.models.ticker import Ticker


class DiscoveryItemResponse(BaseModel):
    symbol: str
    name: str
    sector: str | None = None
    score_date: str
    rsi_score: float | None = None
    macd_score: float | None = None
    adx_score: float | None = None
    volume_score: float | None = None
    pe_score: float | None = None
    roe_score: float | None = None
    total_score: float
    dimensions_scored: int


router = APIRouter(prefix="/discovery", tags=["discovery"])


@router.get("/", response_model=list[DiscoveryItemResponse])
async def get_discovery(
    sector: str | None = Query(None),
    signal_type: str | None = Query(None),
    min_score: float = Query(0, ge=0, le=10),
    limit: int = Query(50, ge=1, le=200),
):
    async with async_session() as session:
        # Get latest score_date
        max_date_stmt = select(func.max(DiscoveryResult.score_date))
        max_date_result = await session.execute(max_date_stmt)
        latest_date = max_date_result.scalar_one_or_none()
        if latest_date is None:
            return []

        # Build main query
        stmt = (
            select(
                Ticker.symbol,
                Ticker.name,
                Ticker.sector,
                DiscoveryResult.score_date,
                DiscoveryResult.rsi_score,
                DiscoveryResult.macd_score,
                DiscoveryResult.adx_score,
                DiscoveryResult.volume_score,
                DiscoveryResult.pe_score,
                DiscoveryResult.roe_score,
                DiscoveryResult.total_score,
                DiscoveryResult.dimensions_scored,
            )
            .join(Ticker, DiscoveryResult.ticker_id == Ticker.id)
            .where(DiscoveryResult.score_date == latest_date)
            .where(DiscoveryResult.total_score >= min_score)
        )

        if sector:
            stmt = stmt.where(Ticker.sector == sector)

        # Signal type filter: score >= 7 means "active signal"
        SIGNAL_THRESHOLD = 7.0
        signal_column_map = {
            "rsi": DiscoveryResult.rsi_score,
            "macd": DiscoveryResult.macd_score,
            "adx": DiscoveryResult.adx_score,
            "volume": DiscoveryResult.volume_score,
            "pe": DiscoveryResult.pe_score,
            "roe": DiscoveryResult.roe_score,
        }
        if signal_type and signal_type in signal_column_map:
            col = signal_column_map[signal_type]
            stmt = stmt.where(col.isnot(None), col >= SIGNAL_THRESHOLD)

        stmt = stmt.order_by(DiscoveryResult.total_score.desc()).limit(limit)
        result = await session.execute(stmt)
        rows = result.all()

    return [
        DiscoveryItemResponse(
            symbol=row.symbol,
            name=row.name,
            sector=row.sector,
            score_date=row.score_date.isoformat(),
            rsi_score=float(row.rsi_score) if row.rsi_score is not None else None,
            # ... same pattern for all score fields
            total_score=float(row.total_score),
            dimensions_scored=row.dimensions_scored,
        )
        for row in rows
    ]
```

### Frontend: Discovery Table Add-to-Watchlist Button
```typescript
// Source: Codebase pattern from watchlist-table.tsx + hooks.ts

// Derive "already in watchlist" set
const { data: watchlistData } = useWatchlist();
const addMutation = useAddToWatchlist();
const watchlistSymbols = useMemo(
  () => new Set(watchlistData?.map((w) => w.symbol) ?? []),
  [watchlistData],
);

// In column definition:
{
  id: "actions",
  header: "",
  cell: ({ row }) => {
    const symbol = row.original.symbol;
    const inWatchlist = watchlistSymbols.has(symbol);
    return (
      <Button
        size="xs"
        variant={inWatchlist ? "secondary" : "default"}
        disabled={inWatchlist || addMutation.isPending}
        onClick={(e) => {
          e.stopPropagation();
          addMutation.mutate(symbol);
        }}
      >
        {inWatchlist ? "Đã thêm" : "Thêm"}
      </Button>
    );
  },
}
```

### Frontend: Score Bar Component
```typescript
// Source: Codebase pattern — simple Tailwind-based score bar
function ScoreCell({ value, label }: { value: number | null; label: string }) {
  if (value == null) return <span className="text-xs text-muted-foreground">—</span>;
  const pct = Math.min(100, (value / 10) * 100);
  const color = value >= 7 ? "bg-[#26a69a]" : value >= 4 ? "bg-amber-500" : "bg-[#ef5350]";
  return (
    <div className="flex items-center gap-1.5 min-w-[80px]">
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-xs w-6 text-right">{value.toFixed(1)}</span>
    </div>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Client-side data storage (localStorage) | Server-backed queries (PostgreSQL + React Query) | Phase 49 | Watchlist + discovery use same server pattern |
| Next.js 15 App Router | Next.js 16.2.3 App Router | Recent upgrade | AGENTS.md warns of breaking changes — follow existing page patterns exactly |
| shadcn/ui v2 (Radix) | shadcn/ui v4 (Base UI / @base-ui/react) | Project v4 | Use `@base-ui/react` primitives, not Radix. PopoverTrigger uses `render` prop pattern [VERIFIED: sector-combobox.tsx] |

**Important:** The project uses `@base-ui/react` (shadcn/ui v4), NOT Radix UI. Component APIs differ — e.g., `PopoverTrigger` uses `render={<button />}` instead of `asChild`. [VERIFIED: sector-combobox.tsx line 28-29]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Signal type threshold of ≥7 is meaningful for "active signal" filtering | Common Pitfalls / Code Examples | Users may get too few or too many filtered results. Can be tuned post-launch. |
| A2 | "Khám phá" is the appropriate Vietnamese label for "Discovery" in nav | Architecture Patterns | Minor UX issue — can be renamed easily |
| A3 | Discovery results only need latest date, not historical comparison | Architecture Patterns | If users want to see score trends over time, this needs a different endpoint |

## Open Questions

1. **Signal type threshold value**
   - What we know: Scores are 0-10 continuous. Need a cutoff to define "active signal."
   - What's unclear: What score threshold means "this signal is firing." 7.0 is a reasonable default (top 30%).
   - Recommendation: Start with 7.0, make it a constant that's easy to adjust.

2. **Score date display**
   - What we know: Discovery runs daily after pipeline. May not have today's data yet.
   - What's unclear: Should UI show the date prominently? What if data is 2+ days old?
   - Recommendation: Show score_date in page subtitle (e.g., "Dữ liệu ngày 18/07/2025"). If >1 business day old, show a warning badge.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright 1.59.1 |
| Config file | `frontend/playwright.config.ts` |
| Quick run command | `cd frontend && npx playwright test e2e/page-smoke.spec.ts --project=chromium` |
| Full suite command | `cd frontend && npx playwright test --project=chromium` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DPAGE-01 | Discovery page renders with scores table | e2e smoke | `npx playwright test e2e/page-smoke.spec.ts` | ❌ Wave 0 (need to add /discovery route) |
| DPAGE-02 | Add-to-watchlist button works from discovery | e2e interaction | `npx playwright test e2e/interact-discovery.spec.ts` | ❌ Wave 0 |
| DPAGE-03 | Filter by sector and signal type | e2e interaction | `npx playwright test e2e/interact-discovery.spec.ts` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd frontend && npx playwright test e2e/page-smoke.spec.ts --project=chromium`
- **Per wave merge:** `cd frontend && npx playwright test --project=chromium`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] Add `/discovery` to `APP_ROUTES` in `e2e/fixtures/test-helpers.ts` — covers DPAGE-01 smoke
- [ ] `e2e/interact-discovery.spec.ts` — covers DPAGE-02, DPAGE-03
- [ ] Backend smoke: ensure GET `/api/discovery` returns 200 (add to `api-smoke.spec.ts`)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Single-user, no auth (per project constraints) |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No RBAC needed |
| V5 Input Validation | yes | Pydantic `Query()` params with `ge`/`le` constraints for limit, min_score. Sector string validated against DB values. |
| V6 Cryptography | no | No sensitive data |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SQL Injection via sector/signal_type params | Tampering | SQLAlchemy parameterized queries (ORM prevents injection) [VERIFIED: all existing routers use SQLAlchemy] |
| Excessive limit param causing resource exhaustion | Denial of Service | `Query(50, ge=1, le=200)` Pydantic constraint [VERIFIED: pattern from tickers.py] |

## Sources

### Primary (HIGH confidence)
- `backend/app/models/discovery_result.py` — DiscoveryResult model with all 6 dimension scores
- `backend/app/services/discovery_service.py` — scoring logic and retention policy (14 days)
- `backend/app/api/watchlist.py` — router pattern with async_session, JOIN queries, Pydantic responses
- `backend/app/api/tickers.py` — sectors endpoint, market-overview JOIN pattern
- `frontend/src/lib/api.ts` — apiFetch<T>() pattern, type definitions, all API functions
- `frontend/src/lib/hooks.ts` — useQuery/useMutation patterns, useWatchlist, useAddToWatchlist, useSectors
- `frontend/src/components/watchlist-table.tsx` — @tanstack/react-table pattern with sorting, sector combobox, actions column
- `frontend/src/components/sector-combobox.tsx` — reusable sector filter component
- `frontend/src/components/navbar.tsx` — NAV_LINKS array for navigation
- `frontend/src/app/watchlist/page.tsx` — page component pattern
- `frontend/package.json` — verified all dependency versions
- `frontend/AGENTS.md` — Next.js 16 breaking changes warning
- `frontend/playwright.config.ts` — e2e test setup
- `frontend/e2e/fixtures/test-helpers.ts` — APP_ROUTES, test helpers

### Secondary (MEDIUM confidence)
- `frontend/src/components/analysis-card.tsx` — ScoreBar component for score visualization

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already installed and patterns established in codebase
- Architecture: HIGH — following exact existing patterns (watchlist router, watchlist-table, hooks)
- Pitfalls: HIGH — identified from reading actual codebase code (Decimal serialization, date filtering, N+1 queries)

**Research date:** 2025-07-18
**Valid until:** 2025-08-18 (stable — no external dependencies changing)

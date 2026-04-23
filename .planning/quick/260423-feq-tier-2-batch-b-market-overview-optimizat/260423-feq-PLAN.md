---
phase: quick
plan: 260423-feq
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/api/tickers.py
  - backend/app/crawlers/cafef_crawler.py
  - backend/app/services/realtime_price_service.py
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
  - frontend/src/app/page.tsx
autonomous: true
requirements: []
must_haves:
  truths:
    - "Market overview API accepts sort, order, top query params and returns sorted/limited results"
    - "CafeF crawler retries transient failures (timeout, connect, 5xx) up to 2 times with exponential backoff"
    - "Realtime price polling only broadcasts symbols whose prices actually changed"
    - "Home page shows inline error card with retry button when market overview fails"
  artifacts:
    - path: "backend/app/api/tickers.py"
      provides: "market-overview endpoint with sort/order/top params"
      contains: "sort.*order.*top"
    - path: "backend/app/crawlers/cafef_crawler.py"
      provides: "tenacity retry decorator on _fetch_news_raw"
      contains: "@retry"
    - path: "backend/app/services/realtime_price_service.py"
      provides: "diff detection before broadcast"
      contains: "changed"
    - path: "frontend/src/app/page.tsx"
      provides: "error state with retry button for market overview"
      contains: "Thử lại"
  key_links:
    - from: "frontend/src/lib/api.ts"
      to: "/tickers/market-overview"
      via: "fetchMarketOverview with sort/order/top params"
    - from: "frontend/src/app/page.tsx"
      to: "useMarketOverview"
      via: "destructured error + refetch for error state"
---

<objective>
Implement Tier 2 Batch B: 4 targeted improvements — market overview API sorting/limiting, CafeF crawler retry logic, realtime polling diff detection, and home page error states.

Purpose: Improve API flexibility, crawler resilience, WebSocket efficiency, and user-facing error handling.
Output: Updated backend endpoints/services + frontend API layer + error UI.
</objective>

<execution_context>
@~/.copilot/get-shit-done/workflows/execute-plan.md
@~/.copilot/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@backend/app/api/tickers.py (market_overview endpoint lines 127-217)
@backend/app/crawlers/cafef_crawler.py (_fetch_news_raw method lines 94-108)
@backend/app/services/realtime_price_service.py (poll_and_broadcast lines 85-110)
@frontend/src/lib/api.ts (fetchMarketOverview lines 206-219)
@frontend/src/lib/hooks.ts (useMarketOverview lines 93-99)
@frontend/src/app/page.tsx (full home page)
@frontend/src/app/ticker/[symbol]/page.tsx (SectionError pattern lines 126-141)
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend — Market overview sort/order/top, CafeF retry, realtime diff</name>
  <files>backend/app/api/tickers.py, backend/app/crawlers/cafef_crawler.py, backend/app/services/realtime_price_service.py</files>
  <action>
**1a. Market overview API sorting/limiting** (`backend/app/api/tickers.py` lines 127-217):

Add 3 new Query params to `market_overview()`:
```python
sort: str | None = Query("change_pct", description="Sort by: change_pct, market_cap, symbol"),
order: str | None = Query("desc", description="Order: desc, asc"),
top: int | None = Query(None, description="Limit to top N results", ge=1, le=500),
```

Validate `sort` is one of `{"change_pct", "market_cap", "symbol"}` — raise 400 if invalid.
Validate `order` is one of `{"desc", "asc"}` — raise 400 if invalid.

Keep the existing SQL query and post-processing for `items` list unchanged. AFTER the existing `items` list is built (after the for loop at line 216), add Python-level sorting:

```python
# Sort
if sort == "change_pct":
    items.sort(key=lambda t: (t.change_pct is None, t.change_pct or 0), reverse=(order == "desc"))
elif sort == "market_cap":
    items.sort(key=lambda t: (t.market_cap is None, t.market_cap or 0), reverse=(order == "desc"))
elif sort == "symbol":
    items.sort(key=lambda t: t.symbol, reverse=(order == "desc"))

# Limit
if top is not None:
    items = items[:top]
```

The sort key uses `(is_none, value)` tuple so None values always sort last regardless of order direction.

Remove the existing `stmt = stmt.order_by(Ticker.symbol)` at line 194 since sorting is now done in Python post-processing (this avoids complex SQL for change_pct which is computed in Python).

**1b. CafeF crawler retry with tenacity** (`backend/app/crawlers/cafef_crawler.py`):

Add imports at top of file (after existing imports):
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
```

Add a retry predicate function before the class:
```python
def _is_retryable(exc: BaseException) -> bool:
    """Retry on transient HTTP failures only."""
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500:
        return True
    return False
```

Decorate `_fetch_news_raw()` method (line 94) with:
```python
@retry(
    stop=stop_after_attempt(3),  # initial + 2 retries
    wait=wait_exponential(multiplier=2, min=2, max=8),
    retry=retry_if_exception(_is_retryable),
    before_sleep=lambda retry_state: logger.debug(
        f"CafeF retry {retry_state.attempt_number} for {retry_state.args[2] if len(retry_state.args) > 2 else '?'}: "
        f"{retry_state.outcome.exception()}"
    ),
    reraise=True,
)
```

Note: `retry_state.args[2]` is the `symbol` param (args = [self, client, symbol]).

**1c. Realtime price polling diff detection** (`backend/app/services/realtime_price_service.py`):

In `poll_and_broadcast()` (lines 85-110), REPLACE lines 105-110 (the cache update + broadcast block) with diff detection logic:

```python
# Diff detection: only broadcast changed prices
changed: dict[str, dict] = {}
for sym, price_data in prices.items():
    cached = self._latest_prices.get(sym)
    if cached != price_data:
        changed[sym] = price_data

# Always update full cache (for get_latest_prices endpoint)
self._latest_prices.update(prices)

if changed:
    logger.debug(f"{len(changed)} of {len(prices)} symbols changed — broadcasting")
    await self._connection_manager.broadcast(changed)
else:
    logger.debug(f"0 of {len(prices)} symbols changed — skipping broadcast")
```

This compares each symbol's entire price dict; dict equality catches any field change. Full cache is always updated so `get_latest_prices` still returns current data.
  </action>
  <verify>
    <automated>cd backend && python -c "from app.api.tickers import market_overview; print('tickers import OK')" && python -c "from app.crawlers.cafef_crawler import CafeFCrawler, _is_retryable; print('cafef import OK')" && python -c "from app.services.realtime_price_service import RealtimePriceService; print('realtime import OK')"</automated>
  </verify>
  <done>
    - market_overview endpoint accepts sort (change_pct|market_cap|symbol), order (desc|asc), top (int) params
    - Invalid sort/order values return 400
    - CafeF _fetch_news_raw has tenacity retry: 2 retries, exponential backoff from 2s, only on transient errors
    - 4xx errors NOT retried
    - Realtime poll_and_broadcast compares prices before broadcasting, only sends changed symbols
    - If no changes, broadcast is skipped entirely
  </done>
</task>

<task type="auto">
  <name>Task 2: Frontend — API params + home page error states</name>
  <files>frontend/src/lib/api.ts, frontend/src/lib/hooks.ts, frontend/src/app/page.tsx</files>
  <action>
**2a. Update fetchMarketOverview** (`frontend/src/lib/api.ts` lines 216-219):

Add an options parameter to `fetchMarketOverview`:
```typescript
export interface MarketOverviewParams {
  exchange?: string;
  sort?: "change_pct" | "market_cap" | "symbol";
  order?: "desc" | "asc";
  top?: number;
}

export async function fetchMarketOverview(params?: MarketOverviewParams): Promise<MarketTicker[]> {
  const searchParams = new URLSearchParams();
  if (params?.exchange && params.exchange !== "all") {
    searchParams.set("exchange", params.exchange);
  }
  if (params?.sort) searchParams.set("sort", params.sort);
  if (params?.order) searchParams.set("order", params.order);
  if (params?.top) searchParams.set("top", String(params.top));
  const qs = searchParams.toString();
  return apiFetch<MarketTicker[]>(`/tickers/market-overview${qs ? `?${qs}` : ""}`);
}
```

Remove the old `fetchMarketOverview` function — replace it entirely with the above.

**2b. Update useMarketOverview hook** (`frontend/src/lib/hooks.ts` lines 93-99):

Update to accept the new params interface:
```typescript
export function useMarketOverview(exchange?: string, opts?: { sort?: "change_pct" | "market_cap" | "symbol"; order?: "desc" | "asc"; top?: number }) {
  return useQuery({
    queryKey: ["market-overview", exchange ?? "all", opts?.sort ?? "change_pct", opts?.order ?? "desc", opts?.top ?? "all"],
    queryFn: () => fetchMarketOverview({ exchange, ...opts }),
    staleTime: 5 * 60 * 1000,
  });
}
```

Import `MarketOverviewParams` is NOT needed — the opts are inlined to keep the hook signature simple. The queryKey includes all params so React Query caches different sort/order/top combinations separately.

**2c. Home page error states** (`frontend/src/app/page.tsx`):

Add `RefreshCw` to the lucide-react imports (alongside existing TrendingUp, TrendingDown, BarChart3):
```typescript
import { TrendingUp, TrendingDown, BarChart3, RefreshCw } from "lucide-react";
```

Add `Button` import:
```typescript
import { Button } from "@/components/ui/button";
```

Destructure `refetch` from the `useMarketOverview` hook (line 13):
```typescript
const { data, isLoading, error, refetch } = useMarketOverview(exchange);
```

Wrap the Market Stats section (lines 42-89) with error handling. Replace the current `{isLoading ? (...) : (...)}` block for market stats with:
```tsx
{isLoading ? (
  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
    {Array.from({ length: 4 }).map((_, i) => (
      <Skeleton key={i} className="h-20 rounded-xl" />
    ))}
  </div>
) : error ? (
  <Card className="mb-6">
    <CardContent className="flex items-center justify-between py-4">
      <p className="text-sm text-destructive">
        Không thể tải dữ liệu thị trường
      </p>
      <Button variant="ghost" size="sm" onClick={() => refetch()} className="gap-1 text-destructive">
        <RefreshCw className="size-3" />
        Thử lại
      </Button>
    </CardContent>
  </Card>
) : (
  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
    {/* ... existing 4 stat cards unchanged ... */}
  </div>
)}
```

Keep the existing heatmap error state (lines 101-111) as-is. Also add the "Thử lại" retry button to the existing heatmap error card. Replace the heatmap error block (lines 101-111) with:
```tsx
) : error ? (
  <Card>
    <CardContent className="flex flex-col items-center justify-center py-12">
      <p className="text-destructive font-medium mb-2">
        Không thể tải dữ liệu thị trường
      </p>
      <p className="text-sm text-muted-foreground mb-4">
        {error instanceof Error ? error.message : "Lỗi không xác định"}
      </p>
      <Button variant="ghost" size="sm" onClick={() => refetch()} className="gap-1 text-destructive">
        <RefreshCw className="size-3" />
        Thử lại
      </Button>
    </CardContent>
  </Card>
)
```

This gives both the stats section and heatmap section error states with retry capability, matching the SectionError pattern from the ticker detail page.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit 2>&1 | Select-Object -First 20</automated>
  </verify>
  <done>
    - fetchMarketOverview accepts sort/order/top params via MarketOverviewParams interface
    - useMarketOverview hook accepts optional sort/order/top and includes them in queryKey
    - Home page shows inline error card with "Không thể tải dữ liệu thị trường" + "Thử lại" button when market overview API fails
    - Error state shown for both market stats section AND heatmap section
    - Retry button calls refetch() to re-attempt the query
    - Existing loading states preserved
  </done>
</task>

</tasks>

<verification>
1. Backend imports all compile: `cd backend && python -c "from app.api.tickers import router; from app.crawlers.cafef_crawler import CafeFCrawler; from app.services.realtime_price_service import RealtimePriceService; print('All OK')"`
2. Frontend type-checks: `cd frontend && npx tsc --noEmit`
3. Manual: `GET /api/tickers/market-overview?sort=change_pct&order=desc&top=20` returns 20 items sorted by change_pct descending
4. Manual: Home page shows error card with retry button when API is unreachable
</verification>

<success_criteria>
- Market overview API supports sort/order/top params with validation
- CafeF crawler retries transient failures with tenacity (2 retries, exponential backoff)
- Realtime polling diffs prices before broadcasting, skips if no changes
- Home page shows error states with retry for both stats and heatmap sections
- All TypeScript compiles, all Python imports resolve
</success_criteria>

<output>
After completion, create `.planning/quick/260423-feq-tier-2-batch-b-market-overview-optimizat/260423-feq-SUMMARY.md`
</output>

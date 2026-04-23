---
phase: quick
plan: 260423-fuy
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/api/tickers.py
  - backend/app/crawlers/types.py
  - backend/app/crawlers/cafef_crawler.py
  - backend/app/crawlers/vnstock_crawler.py
  - backend/app/services/realtime_price_service.py
  - backend/app/config.py
  - frontend/src/components/news-list-skeleton.tsx
  - frontend/src/app/ticker/[symbol]/page.tsx
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
autonomous: true
requirements: [TIER-2-BATCH-C]
must_haves:
  truths:
    - "GET /tickers/ accepts limit and offset query params and returns paginated results"
    - "Crawler return types are annotated with TypedDict instead of bare dict"
    - "Realtime symbol selection sorts by exchange priority instead of plain alphabetical"
    - "News section on ticker page shows article-shaped skeleton lines while loading"
  artifacts:
    - path: "backend/app/crawlers/types.py"
      provides: "CrawlResult and PriceBoardResult TypedDicts"
    - path: "frontend/src/components/news-list-skeleton.tsx"
      provides: "5-row article skeleton component"
  key_links:
    - from: "frontend/src/app/ticker/[symbol]/page.tsx"
      to: "frontend/src/components/news-list-skeleton.tsx"
      via: "import NewsListSkeleton for newsLoading state"
    - from: "backend/app/crawlers/cafef_crawler.py"
      to: "backend/app/crawlers/types.py"
      via: "import NewsCrawlResult TypedDict"
---

<objective>
TIER 2 Batch C: Four focused improvements — news skeleton loader, tickers pagination, crawler type hints, exchange-aware realtime symbol limits.

Purpose: Better loading UX for news, paginated tickers API, type-safe crawler returns, fairer realtime symbol selection across exchanges.
Output: Modified backend endpoints + new frontend skeleton component.
</objective>

<execution_context>
@~/.copilot/get-shit-done/workflows/execute-plan.md
@~/.copilot/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@backend/app/api/tickers.py
@backend/app/crawlers/cafef_crawler.py
@backend/app/crawlers/vnstock_crawler.py
@backend/app/services/realtime_price_service.py
@backend/app/config.py
@frontend/src/components/news-list.tsx
@frontend/src/app/ticker/[symbol]/page.tsx
@frontend/src/lib/api.ts
@frontend/src/lib/hooks.ts
@frontend/src/components/ui/skeleton.tsx

<interfaces>
<!-- Key types and contracts the executor needs -->

From backend/app/api/tickers.py (current list_tickers signature):
```python
@router.get("/", response_model=list[TickerResponse])
async def list_tickers(
    sector: str | None = Query(None, description="Filter by sector"),
    exchange: str | None = Query(None, description="Filter by exchange: HOSE, HNX, UPCOM"),
):
```

From backend/app/crawlers/cafef_crawler.py (crawl_all_tickers return):
```python
async def crawl_all_tickers(self) -> dict:
    # Returns: {success: int, failed: int, total_articles: int, failed_symbols: list[str]}
```

From backend/app/services/realtime_price_service.py (symbol selection, line 97):
```python
symbols_list = sorted(symbols)[:settings.realtime_max_symbols]
```

From backend/app/config.py (realtime settings):
```python
realtime_max_symbols: int = 50
```

From frontend/src/lib/api.ts:
```typescript
export async function fetchTickers(sector?: string, exchange?: string): Promise<Ticker[]> {
  const params = new URLSearchParams();
  if (sector) params.set("sector", sector);
  if (exchange && exchange !== "all") params.set("exchange", exchange);
  const qs = params.toString();
  return apiFetch<Ticker[]>(`/tickers/${qs ? `?${qs}` : ""}`);
}
```

From frontend/src/lib/hooks.ts:
```typescript
export function useTickers(sector?: string, exchange?: string) {
  return useQuery({
    queryKey: ["tickers", sector ?? "all", exchange ?? "all"],
    queryFn: () => fetchTickers(sector, exchange),
    staleTime: 5 * 60 * 1000,
  });
}
```

From frontend/src/components/ui/skeleton.tsx:
```typescript
function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div data-slot="skeleton" className={cn("animate-pulse rounded-md bg-muted", className)} {...props} />
  )
}
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend — tickers pagination, crawler TypedDicts, exchange-aware realtime</name>
  <files>
    backend/app/api/tickers.py
    backend/app/crawlers/types.py
    backend/app/crawlers/cafef_crawler.py
    backend/app/crawlers/vnstock_crawler.py
    backend/app/services/realtime_price_service.py
    backend/app/config.py
  </files>
  <action>
**1. Tickers pagination** — In `backend/app/api/tickers.py` `list_tickers()` (line 52-84):
- Add two Query params: `limit: int = Query(100, ge=1, le=500)` and `offset: int = Query(0, ge=0)`
- After the existing `.order_by(Ticker.symbol)` on the stmt (line 69), chain `.offset(offset).limit(limit)`
- The response_model stays `list[TickerResponse]` (no wrapper needed for this quick improvement)

**2. Crawler type hints** — Create `backend/app/crawlers/types.py`:
```python
"""Type definitions for crawler return values."""
from typing import TypedDict


class NewsCrawlResult(TypedDict):
    """Return type for CafeFCrawler.crawl_all_tickers()."""
    success: int
    failed: int
    total_articles: int
    failed_symbols: list[str]
```
- In `backend/app/crawlers/cafef_crawler.py`: import `NewsCrawlResult` from `app.crawlers.types`, change `crawl_all_tickers` return annotation from `-> dict` to `-> NewsCrawlResult`
- In `backend/app/crawlers/vnstock_crawler.py`: The main crawl methods (`fetch_listing`, `fetch_ohlcv`, `fetch_financial_ratios`, `fetch_industry_classification`, `fetch_price_board`) already return `pd.DataFrame` or `dict[str, dict]` which are fine. No changes needed — vnstock crawler methods already have clear return types. Only add type annotation to `fetch_price_board` if it currently says `-> dict` (check: it says `-> dict[str, dict]` which is already typed, so skip).

**3. Exchange-aware realtime limits** — In `backend/app/services/realtime_price_service.py`:
- Add `realtime_priority_exchanges: list[str] = ["HOSE", "HNX", "UPCOM"]` to `Settings` in `backend/app/config.py` (after `realtime_max_symbols` line 82)
- In `RealtimePriceService.__init__` (line 80), add parameter `exchange_map: dict[str, str] | None = None` and store as `self._exchange_map: dict[str, str] = exchange_map or {}`
- Add a method `def set_exchange_map(self, exchange_map: dict[str, str]) -> None:` that updates `self._exchange_map`
- In `poll_and_broadcast()`, replace line 97 (`symbols_list = sorted(symbols)[:settings.realtime_max_symbols]`) with:
```python
# Sort by exchange priority, then alphabetically within each exchange
priority = settings.realtime_priority_exchanges
def _sort_key(sym: str) -> tuple[int, str]:
    exc = self._exchange_map.get(sym, "")
    try:
        rank = priority.index(exc)
    except ValueError:
        rank = len(priority)  # unknown exchange goes last
    return (rank, sym)

symbols_list = sorted(symbols, key=_sort_key)[:settings.realtime_max_symbols]
```
- In `get_realtime_price_service()` singleton factory (line 131-146): no changes needed — exchange_map defaults to empty dict, will be populated lazily when ticker data is available
  </action>
  <verify>
    <automated>cd backend && python -c "from app.crawlers.types import NewsCrawlResult; print('types OK')" && python -c "from app.services.realtime_price_service import RealtimePriceService; print('realtime OK')" && python -c "from app.api.tickers import router; print('tickers OK')"</automated>
  </verify>
  <done>
    - GET /tickers/ accepts limit (1-500, default 100) and offset (>=0, default 0) query params
    - NewsCrawlResult TypedDict exists in backend/app/crawlers/types.py
    - CafeFCrawler.crawl_all_tickers() annotated with -> NewsCrawlResult
    - RealtimePriceService sorts symbols by exchange priority (HOSE > HNX > UPCOM) before truncating
    - realtime_priority_exchanges config field added to Settings
  </done>
</task>

<task type="auto">
  <name>Task 2: Frontend — news skeleton loader + fetchTickers pagination params</name>
  <files>
    frontend/src/components/news-list-skeleton.tsx
    frontend/src/app/ticker/[symbol]/page.tsx
    frontend/src/lib/api.ts
    frontend/src/lib/hooks.ts
  </files>
  <action>
**1. News skeleton component** — Create `frontend/src/components/news-list-skeleton.tsx`:
```tsx
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Newspaper } from "lucide-react";

export function NewsListSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Newspaper className="size-4" />
          Tin tức gần đây
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-start gap-3 p-2">
            <div className="flex-1 space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-3 w-20" />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
```
This mirrors the NewsList layout — each row has a title line (full width h-4) and a short date line (w-20 h-3).

**2. Wire into ticker page** — In `frontend/src/app/ticker/[symbol]/page.tsx`:
- Add import: `import { NewsListSkeleton } from "@/components/news-list-skeleton";`
- Replace the news loading state (lines 439-440, currently `<Skeleton className="h-[200px] rounded-xl" />`):
  Change to: `<NewsListSkeleton />`

**3. fetchTickers pagination** — In `frontend/src/lib/api.ts`, update `fetchTickers`:
```typescript
export async function fetchTickers(
  sector?: string,
  exchange?: string,
  limit?: number,
  offset?: number,
): Promise<Ticker[]> {
  const params = new URLSearchParams();
  if (sector) params.set("sector", sector);
  if (exchange && exchange !== "all") params.set("exchange", exchange);
  if (limit !== undefined) params.set("limit", String(limit));
  if (offset !== undefined) params.set("offset", String(offset));
  const qs = params.toString();
  return apiFetch<Ticker[]>(`/tickers/${qs ? `?${qs}` : ""}`);
}
```

**4. useTickers hook** — In `frontend/src/lib/hooks.ts`, update `useTickers`:
```typescript
export function useTickers(sector?: string, exchange?: string, limit?: number, offset?: number) {
  return useQuery({
    queryKey: ["tickers", sector ?? "all", exchange ?? "all", limit ?? "default", offset ?? 0],
    queryFn: () => fetchTickers(sector, exchange, limit, offset),
    staleTime: 5 * 60 * 1000,
  });
}
```
Existing callers pass no limit/offset → defaults apply → backwards compatible.
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit 2>&1 | Select-String -Pattern "error TS" | Select-Object -First 10</automated>
  </verify>
  <done>
    - NewsListSkeleton component exists with 5 article-shaped skeleton rows (title line + date line)
    - Ticker detail page uses NewsListSkeleton instead of generic Skeleton for news loading
    - fetchTickers() accepts optional limit and offset params
    - useTickers() accepts optional limit and offset params, includes them in queryKey
    - All existing callers remain backwards compatible (no args = no pagination params sent)
  </done>
</task>

</tasks>

<verification>
1. Backend imports validate: `cd backend && python -c "from app.crawlers.types import NewsCrawlResult; from app.api.tickers import router; from app.services.realtime_price_service import RealtimePriceService; print('ALL OK')"`
2. Frontend TypeScript compiles: `cd frontend && npx tsc --noEmit`
3. Manual: visit ticker detail page → news section shows 5 article-shaped skeleton lines while loading
</verification>

<success_criteria>
- Tickers API accepts limit/offset and applies them to the DB query
- NewsCrawlResult TypedDict replaces bare dict annotation on cafef crawl_all_tickers
- Realtime price service sorts symbols by exchange priority before truncating
- News loading state shows 5 article-shaped skeleton rows matching NewsList layout
- Frontend fetchTickers/useTickers accept optional pagination params, backwards compatible
</success_criteria>

<output>
After completion, create `.planning/quick/260423-fuy-tier-2-batch-c-news-skeleton-home-page-e/260423-fuy-SUMMARY.md`
</output>

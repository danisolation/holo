---
type: quick
description: "TIER 1 upgrades: clean stale config, add news on ticker page, add trading signal label, clean stale scheduler refs"
autonomous: true
files_modified:
  - backend/app/config.py
  - backend/app/scheduler/jobs.py
  - backend/app/api/analysis.py
  - backend/app/schemas/analysis.py
  - frontend/src/components/analysis-card.tsx
  - frontend/src/components/news-list.tsx
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
  - frontend/src/app/ticker/[symbol]/page.tsx
---

<objective>
Tier 1 quality upgrades: remove stale Telegram config fields, clean stale scheduler docstring references, add missing `trading_signal` label to analysis card, and add a news list section to the ticker detail page (new backend endpoint + frontend component).

Purpose: Post-feature-removal cleanup + minor UX improvements to ticker page.
Output: Cleaner config, complete analysis type labels, news displayed on ticker page.
</objective>

<context>
@CLAUDE.md
@backend/app/config.py
@backend/app/api/analysis.py
@backend/app/models/news_article.py
@backend/app/scheduler/jobs.py
@frontend/src/components/analysis-card.tsx
@frontend/src/lib/api.ts
@frontend/src/lib/hooks.ts
@frontend/src/app/ticker/[symbol]/page.tsx
</context>

<tasks>

<task type="auto">
  <name>Task 1: Backend cleanup + news endpoint</name>
  <files>
    backend/app/config.py
    backend/app/scheduler/jobs.py
    backend/app/api/analysis.py
    backend/app/schemas/analysis.py
  </files>
  <action>
**1a. Remove stale Telegram config fields** in `backend/app/config.py`:
- Delete lines 68-70 (the `telegram_bot_token` and `telegram_chat_id` fields + the `# Telegram Bot (Phase 4)` comment)
- On the line with `holo_test_mode` (currently line 94), update the comment from `"skip scheduler + telegram in tests"` to `"skip scheduler in tests"`

**1b. Clean stale scheduler docstring** in `backend/app/scheduler/jobs.py`:
- Line 10: Change `"D-10: Complete failure raises → EVENT_JOB_ERROR → Telegram alert"` to `"D-10: Complete failure raises → EVENT_JOB_ERROR → logged as CRITICAL"`

**1c. Add news response schema** in `backend/app/schemas/analysis.py`:
- Add a new Pydantic model at the end (before the SummaryResponse class, or after it):
```python
class NewsArticleResponse(BaseModel):
    """API response for a single news article."""
    title: str
    url: str
    published_at: str
```

**1d. Add news endpoint** in `backend/app/api/analysis.py`:
- Add import for `NewsArticle` model: `from app.models.news_article import NewsArticle`
- Add import for `NewsArticleResponse` schema: add `NewsArticleResponse` to the existing import from `app.schemas.analysis`
- Add new endpoint BEFORE the helpers section (before `# --- Helpers ---`):

```python
@router.get("/{symbol}/news", response_model=list[NewsArticleResponse])
async def get_ticker_news(symbol: str, limit: int = 10):
    """Get latest news articles for a ticker from CafeF.

    Args:
        symbol: Ticker symbol (e.g., 'VNM', 'FPT')
        limit: Number of articles to return (default 10, max 50)
    """
    limit = min(limit, 50)
    async with async_session() as session:
        ticker = await _get_ticker_by_symbol(session, symbol)
        result = await session.execute(
            select(NewsArticle)
            .where(NewsArticle.ticker_id == ticker.id)
            .order_by(NewsArticle.published_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            NewsArticleResponse(
                title=row.title,
                url=row.url,
                published_at=row.published_at.isoformat(),
            )
            for row in rows
        ]
```

**IMPORTANT — `import re` in ai_analysis_service.py**: DO NOT REMOVE. It IS used at line 562 (`re.search`). The audit item was wrong.
  </action>
  <verify>
    <automated>cd backend && python -c "from app.config import Settings; s = Settings.__fields__; assert 'telegram_bot_token' not in s; assert 'telegram_chat_id' not in s; print('Config clean')" && python -c "from app.schemas.analysis import NewsArticleResponse; print('Schema OK')" && python -c "from app.api.analysis import router; routes = [r.path for r in router.routes]; assert '/{symbol}/news' in routes; print('News endpoint registered')"</automated>
  </verify>
  <done>
    - telegram_bot_token and telegram_chat_id removed from Settings class
    - holo_test_mode comment updated (no "telegram" reference)
    - Scheduler jobs.py docstring no longer references "Telegram alert"
    - GET /analysis/{symbol}/news endpoint returns NewsArticleResponse[] from news_articles table
  </done>
</task>

<task type="auto">
  <name>Task 2: Frontend — trading signal label + news component + ticker page</name>
  <files>
    frontend/src/components/analysis-card.tsx
    frontend/src/components/news-list.tsx
    frontend/src/lib/api.ts
    frontend/src/lib/hooks.ts
    frontend/src/app/ticker/[symbol]/page.tsx
  </files>
  <action>
**2a. Add `trading_signal` to TYPE_LABELS** in `frontend/src/components/analysis-card.tsx`:
- Add `Target` to the lucide-react import (line 6-14 import block)
- Add entry to TYPE_LABELS dict after the `combined` entry:
```typescript
trading_signal: { label: "Kế hoạch giao dịch", icon: <Target className="size-4" /> },
```

**2b. Add news API type + fetch function** in `frontend/src/lib/api.ts`:
- Add type after the existing types section (e.g., after `AnalysisSummary`):
```typescript
export interface NewsArticleResponse {
  title: string;
  url: string;
  published_at: string;
}
```
- Add fetch function after `fetchAnalysisSummary`:
```typescript
export async function fetchTickerNews(
  symbol: string,
  limit: number = 10,
): Promise<NewsArticleResponse[]> {
  return apiFetch<NewsArticleResponse[]>(
    `/analysis/${encodeURIComponent(symbol)}/news?limit=${limit}`,
  );
}
```

**2c. Add `useTickerNews` hook** in `frontend/src/lib/hooks.ts`:
- Add `fetchTickerNews` to the import from `@/lib/api`
- Add hook after `useAnalysisSummary`:
```typescript
/**
 * Fetch recent news articles for a ticker.
 * staleTime: 10 minutes — news updates infrequently.
 */
export function useTickerNews(symbol: string | undefined) {
  return useQuery({
    queryKey: ["ticker-news", symbol],
    queryFn: () => fetchTickerNews(symbol!),
    enabled: !!symbol,
    staleTime: 10 * 60 * 1000,
  });
}
```

**2d. Create `news-list.tsx` component** at `frontend/src/components/news-list.tsx`:
```tsx
"use client";

import { Newspaper } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { NewsArticleResponse } from "@/lib/api";

interface NewsListProps {
  articles: NewsArticleResponse[];
}

export function NewsList({ articles }: NewsListProps) {
  if (articles.length === 0) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-muted-foreground text-sm">
          Chưa có tin tức cho mã này.
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Newspaper className="size-4" />
          Tin tức gần đây
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {articles.map((article, i) => (
          <a
            key={`${article.url}-${i}`}
            href={article.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-3 p-2 -mx-2 rounded-md hover:bg-muted/50 transition-colors group"
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm leading-snug group-hover:text-primary transition-colors line-clamp-2">
                {article.title}
              </p>
              <p className="text-[10px] text-muted-foreground/60 mt-1">
                {new Date(article.published_at).toLocaleDateString("vi-VN", {
                  day: "2-digit",
                  month: "2-digit",
                  year: "numeric",
                })}
              </p>
            </div>
          </a>
        ))}
      </CardContent>
    </Card>
  );
}
```

**2e. Add news section to ticker page** in `frontend/src/app/ticker/[symbol]/page.tsx`:
- Add import for `useTickerNews` in the hooks import (line 44-50 area)
- Add import for `NewsList`: `import { NewsList } from "@/components/news-list";`
- Add import for `Skeleton` is already there (line 17)
- After the existing data hooks block (around line 149, after `useTradingSignal`), add:
```typescript
const { data: newsArticles, isLoading: newsLoading } = useTickerNews(upperSymbol);
```
- Add news section AFTER the analysis cards grid `</section>` (before the closing `</div>`), as the last section on the page:
```tsx
{/* Recent News from CafeF */}
<section>
  <h2 className="text-lg font-semibold mb-3">Tin tức CafeF</h2>
  {newsLoading ? (
    <Skeleton className="h-[200px] rounded-xl" />
  ) : newsArticles && newsArticles.length > 0 ? (
    <NewsList articles={newsArticles} />
  ) : null}
</section>
```
  </action>
  <verify>
    <automated>cd frontend && npx tsc --noEmit 2>&1 | Select-String -Pattern "error TS" | Select-Object -First 10</automated>
  </verify>
  <done>
    - `trading_signal` entry in TYPE_LABELS with Target icon and "Kế hoạch giao dịch" label
    - NewsList component renders news articles with Vietnamese date format and external links
    - Ticker detail page shows "Tin tức CafeF" section at the bottom with latest 10 news articles
    - All TypeScript compiles with no errors
  </done>
</task>

</tasks>

<verification>
1. Backend: `cd backend && python -c "from app.config import settings; print('OK')"` — no crash, no telegram fields
2. Backend: `curl http://localhost:8000/api/analysis/VNM/news` — returns JSON array (may be empty if no news)
3. Frontend: `cd frontend && npx tsc --noEmit` — no type errors
4. Frontend: Visit `/ticker/VNM` — see "Kế hoạch giao dịch" label on trading signal card, news section at bottom
</verification>

<success_criteria>
- Stale telegram config fields removed from Settings
- Stale "Telegram alert" reference removed from scheduler jobs docstring
- `trading_signal` has proper Vietnamese label + Target icon in analysis card
- GET /analysis/{symbol}/news endpoint working
- Ticker detail page shows recent news section
</success_criteria>

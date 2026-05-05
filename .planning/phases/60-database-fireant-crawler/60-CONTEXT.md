# Phase 60: Database & Fireant Crawler - Context

**Gathered:** 2026-05-05
**Status:** Ready for planning

<domain>
## Phase Boundary

System can ingest and store community posts from Fireant.vn for watchlist tickers. Creates `rumors` table via Alembic migration, `FireantCrawler` class mirroring CafeFCrawler patterns, with deduplication and Vietnamese content encoding.

</domain>

<decisions>
## Implementation Decisions

### Fireant API Integration
- JWT token stored as config setting via env var `FIREANT_TOKEN` — mirrors existing API key pattern
- Crawl scope: watchlist tickers only via `_get_watchlist_ticker_map()` — consistent with v10.0 AI gating decision
- Rate limiting: 1s delay between tickers — same as CafeF delay pattern
- Posts per ticker per crawl: `limit=20, offset=0` (latest 20 posts) — covers daily volume

### Database Schema
- Table name: `rumors` — distinct from `news_articles`, clear purpose
- Dedup: UniqueConstraint on `post_id` (Fireant's postID) + ON CONFLICT DO NOTHING — mirrors news_articles pattern
- Retention: 30 days (delete older on crawl) — rumor relevance decays fast
- Store cleaned text via `html.unescape()` at crawl time — no need to re-parse later

### Error Handling & Resilience
- New `fireant_breaker` circuit breaker — separate from `cafef_breaker` to isolate failures
- Retry: tenacity 3 attempts, exponential backoff 2-8s — identical to CafeF pattern
- Token expiry fallback: log error + skip crawl cycle (token expires 2029)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CafeFCrawler` (backend/app/crawlers/cafef_crawler.py) — exact pattern to mirror: httpx.AsyncClient, tenacity retry, circuit breaker, asyncio.sleep
- `NewsArticle` model (backend/app/models/news_article.py) — schema pattern for the new `Rumor` model
- `NewsCrawlResult` TypedDict (backend/app/crawlers/types.py) — return type pattern
- `TickerService.get_ticker_id_map()` — for ticker symbol→ID mapping
- `cafef_breaker` in `app/resilience.py` — circuit breaker pattern to duplicate for Fireant
- `_get_watchlist_ticker_map()` — watchlist-gated ticker filtering

### Established Patterns
- SQLAlchemy 2.0 mapped_column with type annotations
- Alembic auto-generated migrations
- postgresql.insert with ON CONFLICT DO NOTHING for dedup
- loguru structured logging
- Settings via pydantic-settings (app/config.py)

### Integration Points
- `backend/app/crawlers/` — new `fireant_crawler.py` alongside existing crawlers
- `backend/app/models/` — new `rumor.py` model
- `backend/app/models/__init__.py` — register new model
- `backend/app/crawlers/__init__.py` — export new crawler
- `backend/app/crawlers/types.py` — add `RumorCrawlResult` TypedDict
- `backend/app/resilience.py` — add `fireant_breaker`
- `backend/app/config.py` — add `fireant_token` and `fireant_delay_seconds` settings

</code_context>

<specifics>
## Specific Ideas

- Fireant REST API: `GET https://restv2.fireant.vn/posts?symbol={SYMBOL}&offset={N}&limit={N}`
- Auth header: `Authorization: Bearer {FIREANT_TOKEN}`
- Response fields: postID, content, date, sentiment, totalLikes, totalReplies, user.name, user.isAuthentic, taggedSymbols
- Content has HTML entities (e.g., `&#233;`) — use `html.unescape()` from Python stdlib
- No BeautifulSoup needed — response is clean JSON

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

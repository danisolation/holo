# Architecture Patterns — v12.0 Rumor Intelligence

**Domain:** Community rumor crawling & AI scoring for Vietnamese stock market
**Researched:** 2025-07-21

## Recommended Architecture

Mirror the existing CafeF news → sentiment analysis pipeline exactly. No new architectural patterns needed.

```
┌─────────────────────────────────────────────────────────────┐
│                    APScheduler Job Chain                      │
│  prices → indicators → cafef_news → AI_analysis              │
│                                   → fireant_crawl (NEW)      │
│                                     → rumor_scoring (NEW)    │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼──────────────────────┐
        ▼                     ▼                      ▼
┌──────────────┐   ┌──────────────────┐   ┌─────────────────┐
│ FireantCrawler│   │RumorScoringService│   │ FastAPI Endpoints│
│              │   │                  │   │                 │
│ httpx client │   │ GeminiClient     │   │ GET /rumor/{id} │
│ guest JWT    │   │ Pydantic schema  │   │ GET /rumors     │
│ retry+CB     │   │ batch processing │   │                 │
└──────┬───────┘   └────────┬─────────┘   └────────┬────────┘
       │                    │                      │
       ▼                    ▼                      ▼
┌──────────────┐   ┌──────────────────┐   ┌─────────────────┐
│community_posts│   │  rumor_scores    │   │  Next.js Frontend│
│   (table)    │   │   (table)        │   │  Rumor panel     │
│              │   │                  │   │  Feed timeline   │
│ post_id (PK) │   │ ticker_id + date │   │  Watchlist badge │
│ ticker_id    │   │ credibility 1-10 │   │                 │
│ content      │   │ impact 1-10     │   │                 │
│ posted_at    │   │ direction        │   │                 │
│ likes/replies│   │ reasoning        │   │                 │
└──────────────┘   └──────────────────┘   └─────────────────┘
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `FireantCrawler` | Fetch posts from Fireant API, store in DB | Fireant REST API → community_posts table |
| `RumorScoringService` | Read posts, batch to Gemini, store scores | community_posts → GeminiClient → rumor_scores |
| `fireant_breaker` | Circuit breaker for Fireant API | FireantCrawler (wraps API calls) |
| API endpoints | Serve rumor data to frontend | rumor_scores → JSON responses |
| Frontend components | Display rumor scores, feed, badges | API endpoints → React components |

### Data Flow

1. **Crawl:** APScheduler triggers `FireantCrawler.crawl_watchlist_tickers()`
2. **Store:** Posts stored in `community_posts` with ON CONFLICT DO NOTHING on `post_id`
3. **Score:** `RumorScoringService` reads unscored posts, groups by ticker, batches to Gemini
4. **Persist:** Rumor scores stored in `rumor_scores` table
5. **Serve:** FastAPI endpoints query `rumor_scores` joined with ticker data
6. **Display:** Next.js frontend renders scores on ticker detail page + watchlist

## Patterns to Follow

### Pattern 1: Crawler Class (mirror CafeFCrawler)

**What:** Single-responsibility crawler class with httpx client, retry, circuit breaker
**When:** Any external data source
**Example:**

```python
class FireantCrawler:
    API_URL = "https://restv2.fireant.vn/posts"
    
    def __init__(self, session: AsyncSession, delay: float | None = None):
        self.session = session
        self.delay = delay if delay is not None else settings.fireant_delay_seconds
        self.headers = {
            "Authorization": f"Bearer {FIREANT_GUEST_TOKEN}",
            "User-Agent": "Mozilla/5.0 ...",
        }
    
    async def crawl_watchlist_tickers(self) -> CrawlResult:
        # Get watchlist tickers (not all 400 — only user's watchlist)
        # Loop with asyncio.sleep(self.delay) between requests
        # Store via _store_posts() with ON CONFLICT DO NOTHING
        ...
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(...))
    async def _fetch_posts_raw(self, client, symbol) -> list[dict]:
        ...
    
    async def _fetch_posts(self, client, symbol) -> list[dict]:
        return await fireant_breaker.call(self._fetch_posts_raw, client, symbol)
```

### Pattern 2: Batch AI Scoring (mirror AIAnalysisService)

**What:** Group data by ticker, batch to Gemini with structured output
**When:** Any Gemini-powered analysis
**Example:**

```python
class RumorScoringService:
    async def score_ticker_rumors(self, ticker_id: int, posts: list[dict]) -> RumorScoreResult:
        prompt = self._build_prompt(posts)  # Include content, likes, replies, isAuthentic
        async with _gemini_lock:            # Serialize Gemini access
            result = await self.gemini_client._call_gemini(
                prompt=prompt,
                response_schema=RumorBatchResponse,
                system_instruction=RUMOR_SYSTEM_INSTRUCTION,
            )
        await self._store_scores(ticker_id, result)
```

### Pattern 3: Watchlist-Gated Crawling (mirror v10.0 discovery)

**What:** Only crawl tickers on user's watchlist, not all 400
**When:** Expensive per-ticker operations (API calls, AI tokens)
**Rationale:** Fireant crawling + Gemini scoring is expensive per ticker. Watchlist gating (established in v10.0) keeps scope manageable — typically 15-30 tickers vs 400.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Scraping HTML When API Exists
**What:** Using Selenium/Playwright to render Fireant pages
**Why bad:** 100x slower, fragile CSS selectors, needs headless browser runtime
**Instead:** Use the REST JSON API at `restv2.fireant.vn/posts`

### Anti-Pattern 2: NLP Preprocessing Before Gemini
**What:** Running underthesea/spaCy tokenization before sending to Gemini
**Why bad:** Gemini handles Vietnamese natively. Preprocessing removes context (emojis, slang, tone) that helps Gemini understand sentiment. Adds complexity and dependencies.
**Instead:** Send raw post content to Gemini with metadata (likes, replies, isAuthentic)

### Anti-Pattern 3: Scoring Every Post Individually
**What:** One Gemini API call per Fireant post
**Why bad:** 15 RPM rate limit. 20 posts × 30 tickers = 600 calls = 40 minutes
**Instead:** Batch all posts for a ticker into one Gemini call. Output: one score per ticker.

### Anti-Pattern 4: Storing Token in Database
**What:** Persisting the Fireant guest JWT in PostgreSQL
**Why bad:** It's a static public token, not a user secret. DB storage adds unnecessary complexity.
**Instead:** Hardcode in settings or .env. Add auto-refresh fallback for resilience.

## Scalability Considerations

Not really applicable — this is a single-user personal app. But for completeness:

| Concern | Current (1 user, ~30 tickers) | If Scaled |
|---------|-------------------------------|-----------|
| Fireant API calls | ~30 calls/crawl, 1.5s delay = ~45s | Rate limit unknown, would need throttling |
| Gemini API calls | ~4-6 batches (8 tickers/batch) | 15 RPM is the hard ceiling |
| Storage | ~600 posts/day, ~30 scores/day | Partition community_posts by month if >100K rows |
| Frontend | Single dashboard consumer | N/A for personal use |

## Sources

- Existing codebase: `cafef_crawler.py`, `ai_analysis_service.py`, `resilience.py`, `scheduler/manager.py`
- Fireant.vn API: Live tested response structure
- v10.0 watchlist-gating pattern: PROJECT.md

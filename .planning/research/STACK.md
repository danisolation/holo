# Technology Stack — v12.0 Rumor Intelligence

**Project:** Holo — Stock Intelligence Platform
**Milestone:** v12.0 Rumor Intelligence
**Researched:** 2025-07-21
**Scope:** Stack additions for Fireant.vn crawling, CafeF forum scraping, AI rumor scoring

## Key Discovery: CafeF Forum Is Dead

**CRITICAL FINDING:** CafeF's forum/Q&A section (`/hoi-dap/`) returns 404. The `s.cafef.vn/hoi-dap/` redirects to `cafef.vn/du-lieu/hoi-dap/` which is a dead page. CafeF has removed their community discussion feature. **Do NOT plan for CafeF forum scraping — it doesn't exist anymore.**

**Pivot recommendation:** Focus on Fireant.vn community posts (verified working, rich JSON API) as the primary rumor source. CafeF news articles are already crawled — their article *titles* can feed into rumor context but there's no forum to scrape.

## What Already Works (DO NOT Add)

These are already in requirements.txt and battle-tested across 560 tests:

| Existing | Version | Role in v12.0 |
|----------|---------|---------------|
| httpx | >=0.28 | HTTP client for Fireant API calls |
| beautifulsoup4 | >=4.12 | HTML entity decoding in Fireant content |
| google-genai | >=1.73 | Gemini AI for rumor scoring |
| tenacity | >=9.1 | Retry logic for Fireant API |
| loguru | >=0.7 | Logging |
| cachetools | >=5.5 | TTL caching |
| SQLAlchemy | >=2.0.49 | ORM for new rumor tables |
| asyncpg | >=0.31 | Async PostgreSQL |

## Recommended Stack Additions

### Answer: Almost Nothing New Needed

The existing stack handles this milestone with zero or near-zero new dependencies. Here's why:

### Fireant.vn API Access (NO new libraries needed)

**Verified via live testing (HIGH confidence):**

- **Endpoint:** `GET https://restv2.fireant.vn/posts?symbol={SYMBOL}&offset={N}&limit={N}`
- **Auth:** Static guest JWT token embedded in Fireant's `__NEXT_DATA__` on every page load
  - `client_id: "fireant.tradestation"`, expires **November 17, 2029**
  - Scopes include `posts-read`, `symbols-read` — exactly what we need
- **Response:** Clean JSON (not HTML). No BeautifulSoup needed for parsing.
- **Pagination:** offset/limit query params, tested working
- **Rate limiting:** No observed rate limiting on guest token, but should self-limit (~1s delay)
- **SSL:** Works with `verify=False` (already patched globally in config.py)

**Response fields useful for rumor scoring:**

| Field | Type | Use |
|-------|------|-----|
| `postID` | int | Deduplication key |
| `content` | string | Rumor text (has HTML entities like `&#233;`) |
| `date` | ISO datetime | Freshness filtering |
| `sentiment` | int | Fireant's own sentiment (0=neutral) |
| `totalLikes` | int | Social proof / engagement signal |
| `totalReplies` | int | Discussion intensity signal |
| `user.name` | string | Author tracking |
| `user.isAuthentic` | bool | Verified user flag — credibility signal |
| `taggedSymbols` | array | Confirms ticker relevance |

**Integration:** New `FireantCrawler` class following exact same pattern as `CafeFCrawler` — uses httpx.AsyncClient, tenacity retry, circuit breaker, asyncio.sleep for rate limiting.

### HTML Entity Decoding (NO new library needed)

Fireant content contains HTML entities (`&#233;` → `é`). Use Python stdlib:

```python
import html
clean_text = html.unescape(raw_content)  # stdlib, no dependency
```

BeautifulSoup is available if needed for edge cases but `html.unescape()` is sufficient for entity decoding.

### AI Rumor Scoring (NO new library needed)

Use existing `google-genai` SDK with structured Pydantic output — the exact pattern already used for 5 analysis types (technical, fundamental, sentiment, combined, trading signals).

**New Pydantic schema needed (not a library, just code):**

```python
class RumorScore(BaseModel):
    ticker: str
    credibility: int        # 1-10
    potential_impact: int   # 1-10
    direction: str          # "bullish" / "bearish" / "neutral"
    reasoning: str          # Vietnamese explanation
    key_claims: list[str]   # Extracted factual claims
```

**Prompt strategy:** Send batch of Fireant posts per ticker to Gemini with instructions to:
1. Filter noise (memes, one-word posts, spam)
2. Identify substantive rumors/claims
3. Score credibility (source quality, specificity, corroboration)
4. Assess potential market impact
5. Classify bullish/bearish/neutral

This follows the existing `GeminiClient._call_gemini()` → structured output pattern.

### Database (NO new library needed)

New tables via Alembic migration (existing toolchain):

- `community_posts` — raw Fireant posts (dedup on post_id)
- `rumor_scores` — AI-scored rumors per ticker per date

## Supporting Libraries — What to Consider

### Only If Needed: `dateutil` for timezone parsing

Fireant returns ISO datetime with timezone: `"2026-05-05T14:29:18.08+07:00"`. Python's `datetime.fromisoformat()` handles this in Python 3.11+ (we're on 3.12). **No additional library needed.**

### Only If Needed: Rate Limiter

If Fireant starts rate-limiting, consider `aiolimiter` (async token-bucket rate limiter):

| Library | Version | Purpose | When to Add |
|---------|---------|---------|-------------|
| aiolimiter | 1.2.1 | Async rate limiting | Only if Fireant starts returning 429s |

**Current approach:** Simple `asyncio.sleep(1.0)` between requests (same as CafeF pattern). This is enough for a personal app crawling ~20-40 watchlist tickers.

## Installation

```bash
# NO new dependencies needed for v12.0
# Existing requirements.txt covers everything:
# - httpx for Fireant API calls
# - google-genai for rumor scoring
# - tenacity for retries
# - SQLAlchemy/asyncpg/alembic for new tables
```

If rate limiting becomes necessary later:
```bash
pip install aiolimiter>=1.2,<2
```

## Integration Points

### 1. Fireant Crawler → Existing Patterns

```
FireantCrawler (new)
├── Uses: httpx.AsyncClient (existing)
├── Uses: tenacity @retry (existing)
├── Uses: AsyncCircuitBreaker (add fireant_breaker to resilience.py)
├── Uses: asyncio.sleep() for rate limiting (existing pattern)
├── Stores: community_posts table (new model + migration)
└── Follows: CafeFCrawler pattern exactly
```

### 2. Rumor Scoring → Existing AI Pipeline

```
RumorScoringService (new)
├── Uses: GeminiClient._call_gemini() (existing)
├── Uses: Pydantic structured output (existing pattern)
├── Uses: _gemini_lock for rate limit serialization (existing)
├── Input: community_posts grouped by ticker
├── Output: rumor_scores table
└── Follows: AIAnalysisService batch pattern
```

### 3. Scheduler Integration

```
Existing chain: prices → indicators → news → AI analysis
New addition:   ... → fireant_crawl → rumor_scoring
```

Add to APScheduler job chain via `EVENT_JOB_EXECUTED` listener (existing pattern in `scheduler/manager.py`).

### 4. Config Additions

```python
# New settings in config.py
fireant_delay_seconds: float = 1.5    # Between ticker requests
fireant_post_limit: int = 20          # Posts per ticker per crawl
fireant_post_days: int = 3            # Only score recent posts
```

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Fireant access | REST API + guest JWT | Selenium/Playwright scraping | API returns clean JSON, no rendering needed |
| HTML entity decoding | `html.unescape()` (stdlib) | BeautifulSoup `.get_text()` | Stdlib is simpler, no parsing overhead |
| Rate limiting | `asyncio.sleep()` | aiolimiter / ratelimit | Over-engineering for ~30 requests/crawl |
| NLP preprocessing | None (send raw to Gemini) | underthesea / pyvi / spaCy | Gemini handles Vietnamese natively, preprocessing adds complexity with no benefit |
| Rumor source #2 | CafeF news titles (already crawled) | CafeF forum | Forum is dead (404). News titles already available |
| Task queue | APScheduler in-process | Celery + Redis | Single user, no need for distributed processing |
| Caching | cachetools TTLCache (existing) | Redis | Over-engineering for single-user app |

## What NOT to Use

| Don't Add | Why Not |
|-----------|---------|
| **Selenium / Playwright** | Fireant has a REST JSON API — no browser rendering needed |
| **underthesea / pyvi** | Vietnamese NLP preprocessing is unnecessary — Gemini understands Vietnamese natively. Adding tokenization/NER adds complexity without improving scoring quality |
| **spaCy** | Heavy NLP library (200MB+ models). Gemini handles all NLP tasks |
| **Scrapy** | Framework overkill for 2 simple API/scraping targets |
| **Celery + Redis** | Single-user app with APScheduler already working. No distributed queue needed |
| **newspaper3k / trafilatura** | Article extraction libraries — we only need post text from JSON API |
| **aiohttp** | httpx already handles async HTTP. Don't add a second HTTP client |
| **Redis** | No caching layer needed beyond in-memory cachetools for single user |
| **MongoDB** | PostgreSQL handles unstructured-ish data fine with JSONB if needed |

## Fireant.vn API Reference (Verified)

**Confidence: HIGH** — tested live, all endpoints return 200 with data.

### Authentication
```
Header: Authorization: Bearer {GUEST_JWT_TOKEN}
Token source: Embedded in https://fireant.vn page HTML → __NEXT_DATA__ → initialState.auth.accessToken
Token expiry: 2029-11-17 (long-lived guest/anonymous token)
Client ID: fireant.tradestation
Scopes: posts-read, posts-write, symbols-read, users-read, search, etc.
```

### Posts by Symbol
```
GET https://restv2.fireant.vn/posts?symbol={SYMBOL}&offset={N}&limit={N}
Response: JSON array of post objects
Tested: symbol=VNM, offset=0/20, limit=3/20 — all working
```

### Token Refresh Strategy
The guest token expires in 2029. If it ever stops working:
1. Fetch `https://fireant.vn` homepage
2. Parse `__NEXT_DATA__` JSON from `<script id="__NEXT_DATA__">`
3. Extract `props.initialState.auth.accessToken`
4. This can be automated as a fallback in the crawler

## CafeF Forum Status (Verified Dead)

**Confidence: HIGH** — tested live.

| URL Pattern | Result |
|-------------|--------|
| `s.cafef.vn/hoi-dap/VNM.chn` | 301 → cafef.vn/du-lieu/hoi-dap/vnm.chn → 404 |
| `s.cafef.vn/Hoi-dap/VNM.chn` | 301 → same 404 |
| `cafef.vn/hoi-dap/VNM.chn` | 404 |
| `s.cafef.vn/hoi-dap.chn` | 301 → 404 |
| `cafef.vn/du-lieu/hoi-dap/vnm.chn` | 404 ("This content has been removed") |

CafeF's Q&A/forum feature has been fully removed. All URLs redirect to a generic 404 page with message "This content has been removed or does not exist."

**Existing CafeF news scraping** (AJAX endpoint at `cafef.vn/du-lieu/Ajax/Events_RelatedNews_New.aspx`) still works and is already integrated. News article titles can supplement rumor analysis as a secondary signal.

## Sources

- Fireant.vn REST API: Live tested `restv2.fireant.vn/posts` endpoint (2025-07-21)
- Fireant.vn JWT: Decoded from page HTML `__NEXT_DATA__` (exp: 1889622530 = 2029-11-17)
- CafeF forum: Live tested all known URL patterns — all return 404 (2025-07-21)
- Existing codebase: `backend/app/crawlers/cafef_crawler.py`, `backend/app/resilience.py`, `backend/app/config.py`
- Python 3.12 `datetime.fromisoformat()`: Handles ISO 8601 with timezone offsets natively
- Python stdlib `html.unescape()`: Handles HTML entity decoding

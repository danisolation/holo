# Phase 3: Sentiment & Combined Intelligence - Research

**Researched:** 2026-04-15
**Domain:** CafeF news scraping, Gemini Vietnamese sentiment analysis, multi-dimensional recommendation engine
**Confidence:** HIGH

## Summary

This phase adds news sentiment analysis and a combined buy/sell/hold recommendation engine to the existing Gemini-powered analysis pipeline. Research confirms CafeF news scraping is viable via a well-structured AJAX endpoint that returns HTML fragments with article titles, dates, and URLs — all parseable with BeautifulSoup. Vietnamese text encoding (UTF-8) works correctly with httpx. The existing `AIAnalysisService` pattern (batched Gemini calls, structured Pydantic output, tenacity retry, upsert storage) maps cleanly to both sentiment and combined analysis types.

The main technical risks are: (1) the PostgreSQL native ENUM `analysis_type` needs `ALTER TYPE ... ADD VALUE` for 'combined' — a non-reversible DDL operation requiring a careful Alembic migration, (2) low news density for some tickers (1-2 articles per 7 days for mid-cap stocks) means graceful degradation is essential, and (3) CafeF SSL certificates sometimes fail verification, requiring `verify=False` in httpx configuration.

**Primary recommendation:** Use the CafeF AJAX endpoint (`/du-lieu/Ajax/Events_RelatedNews_New.aspx`) for smaller response payloads. Extend `AIAnalysisService` with `run_sentiment_analysis()` and `run_combined_analysis()` methods following the exact same batching, retry, and storage patterns already established. Add `beautifulsoup4` explicitly to requirements.txt (currently only installed as vnstock transitive dependency).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- CafeF (cafef.vn) — largest VN financial news. Scrape article titles + snippets via httpx + BeautifulSoup. Titles sufficient for sentiment (no full-text).
- Scrape recent 7-day news per ticker. New `news_articles` table (ticker_id, title, url, published_at, source). Map ticker symbols to CafeF stock pages.
- Scraping schedule: After daily crawl (chained). Not real-time — batch daily is sufficient.
- Sentiment: Feed 7-day Vietnamese news titles directly to Gemini (no translation). Batch 10 tickers per call with their news. Returns `SentimentBatchResponse` with score per ticker.
- Combined: Single Gemini call per batch: technical signal + fundamental score + sentiment → holistic mua/bán/giữ. Not a weighted formula — Gemini reasons across all dimensions.
- Store combined in `ai_analyses` table with `analysis_type='combined'`. Add COMBINED + SENTIMENT to AnalysisType enum.
- Confidence: Gemini assesses based on signal alignment (3 agree = high), data freshness, news volume. Explicit prompt instruction.
- Vietnamese explanation: System prompt respond in Vietnamese. Include key factors. Max ~200 words. Natural language.
- Pipeline chain: crawl → indicators → tech/fund AI → news scrape → sentiment AI → combined AI. Via EVENT_JOB_EXECUTED listener.
- API endpoints: GET `/api/analysis/{symbol}/sentiment`, `/api/analysis/{symbol}/combined`, `/api/analysis/{symbol}/summary` (all 4 dimensions).
- News scraping failure: If CafeF fails for a ticker, produce combined with tech + fund only (sentiment=neutral). Partial data > no data.
- CafeF rate limiting: 1-second delay between requests. Proper User-Agent header. Graceful degradation if blocked.

### Locked Decisions (Upstream Context)
- Phase 1: 400 HOSE tickers, OHLCV, financials in PostgreSQL
- Phase 2: Technical indicators computed, Gemini technical + fundamental scoring in `ai_analyses` table
- `AIAnalysisService` pattern: batched Gemini calls, structured output, tenacity retry
- `AnalysisType` enum already includes SENTIMENT value (forward-designed in Phase 2)
- Existing schemas: `TechnicalBatchResponse`, `FundamentalBatchResponse` — follow same pattern

### Agent's Discretion
None specified — all decisions locked.

### Deferred Ideas (OUT OF SCOPE)
None specified for this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AI-03 | Sentiment analysis — Gemini phân tích tin tức tiếng Việt → sentiment score | CafeF AJAX endpoint verified for news scraping; Vietnamese UTF-8 encoding confirmed working; Gemini handles Vietnamese natively |
| AI-04 | Combined 3-dimensional recommendation — kết hợp kỹ thuật + cơ bản + sentiment → mua/bán/giữ | Existing `_run_batched_analysis()` pattern supports adding new analysis types; needs COMBINED enum value in PostgreSQL |
| AI-05 | Confidence level — mức độ tin cậy 1-10 cho mỗi recommendation | Existing `score` column (1-10) in `ai_analyses` reusable; confidence assessment via Gemini prompt engineering |
| AI-06 | Natural language explanation — giải thích recommendation bằng tiếng Việt | Existing `reasoning` column (TEXT) in `ai_analyses` reusable; Gemini Vietnamese output verified working |
</phase_requirements>

## Standard Stack

### Core (already installed)
| Library | Version | Purpose | Verified |
|---------|---------|---------|----------|
| httpx | 0.28.1 | Async HTTP client for CafeF scraping | `pip show httpx` — already in requirements.txt [VERIFIED: pip show] |
| beautifulsoup4 | 4.14.3 | HTML parsing for CafeF news | Installed via vnstock dep, **NOT in requirements.txt — must add** [VERIFIED: pip show] |
| google-genai | 1.73.1 | Gemini API for sentiment + combined analysis | Already in requirements.txt [VERIFIED: pip show] |
| tenacity | 9.1.x | Retry logic for Gemini + scraping | Already in requirements.txt [VERIFIED: codebase] |
| sqlalchemy | 2.0.49+ | ORM for news_articles table + AIAnalysis queries | Already in requirements.txt [VERIFIED: codebase] |
| alembic | 1.18.x | Database migration for new table + enum | Already in requirements.txt [VERIFIED: codebase] |

### Missing from requirements.txt
```
beautifulsoup4>=4.14,<5
```
**Why:** Currently only installed as a transitive dependency of vnstock. Since Phase 3 directly imports and uses BeautifulSoup for CafeF parsing, it must be an explicit dependency. [VERIFIED: `Required-by: vnstock` in pip show, absent from requirements.txt]

### Not Needed
| Library | Why Not |
|---------|---------|
| lxml | `html.parser` (built-in) is sufficient for parsing ~30 small HTML elements per page. lxml's speed advantage is negligible at this scale. [VERIFIED: lxml not installed] |
| newspaper3k | Overkill — we only need titles, not full article extraction. BeautifulSoup is simpler. [ASSUMED] |
| langdetect | Unnecessary — all CafeF content is Vietnamese by definition. [VERIFIED: all titles Vietnamese on CafeF] |

## Architecture Patterns

### CafeF Scraping Architecture

**AJAX Endpoint (Recommended):** [VERIFIED: live HTTP test]
```
GET https://cafef.vn/du-lieu/Ajax/Events_RelatedNews_New.aspx
    ?symbol={TICKER_UPPERCASE}
    &floorID=0
    &configID=0
    &PageIndex=1
    &PageSize=30
    &Type=2
```

Returns HTML fragment (~21KB) vs full page (~78KB). Same parsing structure, 3x smaller payload.

**Alternative (Full Page):** [VERIFIED: live HTTP test]
```
GET https://cafef.vn/du-lieu/tin-doanh-nghiep/{ticker_lowercase}/Event.chn
```

Returns full HTML page with same article listing embedded. Use as fallback if AJAX endpoint fails.

### HTML Parsing Selectors [VERIFIED: live parsing test]

```python
# Each article is in a <li> element containing:
# - <span class="timeTitle">DD/MM/YYYY HH:MM</span>  — publication date
# - <a class="docnhanhTitle" href="..." title="...">Title</a>  — article title + URL

from bs4 import BeautifulSoup
from datetime import datetime

soup = BeautifulSoup(html, "html.parser")
for li in soup.find_all("li"):
    time_span = li.find("span", class_="timeTitle")
    link = li.find("a", class_="docnhanhTitle")
    if time_span and link:
        pub_date = datetime.strptime(time_span.get_text(strip=True), "%d/%m/%Y %H:%M")
        title = link.get_text(strip=True)
        url = link["href"]
        # url may be relative (/du-lieu/...) or absolute
```

### Article Types on CafeF [VERIFIED: live categorization test]

Two types appear in the news listing:
1. **Editorial news** (paths like `/vinamilk-len-ke-hoach-...chn`) — journalist-written market analysis, company stories. **Higher sentiment value.**
2. **Corporate disclosures** (paths like `/du-lieu/VNM-2663170/vnm-....chn`) — official filings, insider trades, HĐQT resolutions. **Factual events, useful for sentiment context.**

Both types carry sentiment signal. Include both.

### News Density per Ticker (7-day window) [VERIFIED: live count test]

| Ticker | 7-day articles | 30-day articles | Notes |
|--------|---------------|-----------------|-------|
| FPT | 5 | 19 | High-profile tech stock |
| HPG | 4 | 11 | Major industrial stock |
| MBB | 2 | 14 | Banking stock |
| VNM | 1 | 10 | Dairy blue-chip |

**Implication:** Many tickers will have 0-2 articles in a 7-day window. The sentiment analysis must handle sparse data gracefully. When a ticker has 0 news articles, sentiment should default to "neutral" (not "unknown").

### Recommended Project Structure

```
backend/app/
├── crawlers/
│   ├── vnstock_crawler.py    # (existing)
│   └── cafef_crawler.py      # NEW: CafeF news scraping
├── models/
│   ├── ai_analysis.py        # MODIFY: Add COMBINED to AnalysisType enum
│   └── news_article.py       # NEW: NewsArticle model
├── schemas/
│   └── analysis.py           # MODIFY: Add SentimentBatchResponse, CombinedBatchResponse
├── services/
│   └── ai_analysis_service.py # MODIFY: Add sentiment + combined analysis methods
├── scheduler/
│   ├── jobs.py               # MODIFY: Add daily_news_crawl, daily_sentiment, daily_combined jobs
│   └── manager.py            # MODIFY: Extend job chaining
└── api/
    └── analysis.py           # MODIFY: Add sentiment, combined, summary endpoints
```

### Pattern: Extending AIAnalysisService

Follow the exact pattern established in Phase 2:

```python
# 1. New Pydantic schemas (in schemas/analysis.py)
class SentimentLevel(str, Enum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"

class TickerSentimentAnalysis(BaseModel):
    ticker: str
    sentiment: SentimentLevel
    score: int = Field(ge=1, le=10, description="Sentiment score 1-10")
    reasoning: str

class SentimentBatchResponse(BaseModel):
    analyses: list[TickerSentimentAnalysis]

# 2. New analysis method (in ai_analysis_service.py)
async def run_sentiment_analysis(self) -> dict:
    # Same pattern as run_technical_analysis():
    # gather context → batch → call Gemini → store
    ...

# 3. New prompt builder
def _build_sentiment_prompt(self, ticker_data: dict[str, dict]) -> str:
    # ticker_data = {symbol: {"news_titles": [...], "news_count": N}}
    ...

# 4. Combined recommendation
class Recommendation(str, Enum):
    MUA = "mua"       # buy
    BAN = "ban"       # sell
    GIU = "giu"       # hold

class TickerCombinedAnalysis(BaseModel):
    ticker: str
    recommendation: Recommendation
    confidence: int = Field(ge=1, le=10)
    explanation: str  # Vietnamese, max ~200 words
    reasoning: str    # Internal reasoning (for raw_response)

class CombinedBatchResponse(BaseModel):
    analyses: list[TickerCombinedAnalysis]
```

### Pattern: CafeF Crawler Service

```python
# backend/app/crawlers/cafef_crawler.py
import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from loguru import logger

class CafeFCrawler:
    BASE_URL = "https://cafef.vn"
    AJAX_URL = f"{BASE_URL}/du-lieu/Ajax/Events_RelatedNews_New.aspx"
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "vi-VN,vi;q=0.9",
        }
    
    async def fetch_news(self, symbol: str, days: int = 7) -> list[dict]:
        """Fetch recent news articles for a ticker from CafeF."""
        async with httpx.AsyncClient(
            headers=self.headers,
            timeout=15,
            follow_redirects=True,
            verify=False,  # CafeF SSL certs may fail verification
        ) as client:
            params = {
                "symbol": symbol.upper(),
                "floorID": "0",
                "configID": "0",
                "PageIndex": "1",
                "PageSize": "30",
                "Type": "2",
            }
            resp = await client.get(self.AJAX_URL, params=params)
            resp.raise_for_status()
            
            return self._parse_articles(resp.text, days=days)
    
    def _parse_articles(self, html: str, days: int = 7) -> list[dict]:
        """Parse HTML fragment for article titles, dates, URLs."""
        cutoff = datetime.now() - timedelta(days=days)
        soup = BeautifulSoup(html, "html.parser")
        articles = []
        
        for li in soup.find_all("li"):
            time_span = li.find("span", class_="timeTitle")
            link = li.find("a", class_="docnhanhTitle")
            if not (time_span and link):
                continue
            
            try:
                pub_date = datetime.strptime(
                    time_span.get_text(strip=True), "%d/%m/%Y %H:%M"
                )
            except ValueError:
                continue
            
            if pub_date < cutoff:
                continue  # Outside 7-day window
            
            title = link.get_text(strip=True)
            url = link.get("href", "")
            if not url.startswith("http"):
                url = f"{self.BASE_URL}{url}"
            
            articles.append({
                "title": title,
                "url": url,
                "published_at": pub_date,
                "source": "cafef",
            })
        
        return articles
```

### Pattern: Job Chaining Extension

```python
# In manager.py _on_job_executed():
# Current chain: crawl → indicators → AI (tech+fund)
# New chain:     crawl → indicators → AI (tech+fund) → news → sentiment → combined

elif event.job_id in ("daily_ai_analysis_triggered", "daily_ai_analysis_manual"):
    logger.info("Chaining: daily_ai_analysis → daily_news_crawl")
    scheduler.add_job(daily_news_crawl, id="daily_news_crawl_triggered", ...)

elif event.job_id in ("daily_news_crawl_triggered", "daily_news_crawl_manual"):
    logger.info("Chaining: daily_news_crawl → daily_sentiment_analysis")
    scheduler.add_job(daily_sentiment_analysis, id="daily_sentiment_triggered", ...)

elif event.job_id in ("daily_sentiment_triggered", "daily_sentiment_manual"):
    logger.info("Chaining: daily_sentiment → daily_combined_analysis")
    scheduler.add_job(daily_combined_analysis, id="daily_combined_triggered", ...)
```

### Anti-Patterns to Avoid

- **Don't translate Vietnamese to English before sending to Gemini.** Gemini handles Vietnamese natively. Translation adds latency, cost, and loses nuance. [VERIFIED: CONTEXT.md locked decision]
- **Don't build a weighted formula for combining signals.** The whole point is Gemini reasoning across dimensions holistically. A `0.4*tech + 0.3*fund + 0.3*sent` formula loses context. [VERIFIED: CONTEXT.md locked decision]
- **Don't use `response.text` without checking encoding.** CafeF returns UTF-8, but always use `resp.text` (httpx auto-decodes) not `resp.content.decode()`. [VERIFIED: httpx returns correct UTF-8]
- **Don't scrape full article text.** Titles are sufficient for sentiment per CONTEXT.md. Full-text scraping would hit rate limits and add complexity. [VERIFIED: CONTEXT.md locked decision]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTML parsing | regex-based extraction | BeautifulSoup with `html.parser` | CafeF HTML has inconsistent formatting; regex breaks on edge cases |
| Retry logic for scraping | custom try/except loops | tenacity decorators | Already used in project; consistent retry patterns |
| Date parsing from CafeF | manual string splitting | `datetime.strptime("%d/%m/%Y %H:%M")` | CafeF date format is consistent [VERIFIED] |
| Deduplication | complex hash-based dedup | PostgreSQL UNIQUE constraint on (ticker_id, url) | DB-level dedup is atomic and race-condition-free |
| Vietnamese sentiment scoring | custom NLP pipeline | Gemini API with Vietnamese prompt | LLM handles Vietnamese nuance better than rule-based NLP |

## Common Pitfalls

### Pitfall 1: PostgreSQL Native ENUM Migration
**What goes wrong:** Adding a new value to a PostgreSQL ENUM type is not a standard ALTER COLUMN operation. The migration 002 created `analysis_type` as a native PostgreSQL ENUM with `('technical', 'fundamental', 'sentiment')`. Adding 'combined' requires `ALTER TYPE analysis_type ADD VALUE 'combined'`.
**Why it happens:** The SQLAlchemy model uses `native_enum=False`, which makes it seem like no DB migration is needed. But the migration DDL actually created a native PG enum.
**How to avoid:** Create a new Alembic migration 003 with raw SQL: `ALTER TYPE analysis_type ADD VALUE IF NOT EXISTS 'combined';`. Note: `ALTER TYPE ... ADD VALUE` cannot run inside a transaction in PostgreSQL < 12. For PostgreSQL 12+, it works inside transactions.
**Warning signs:** `DataError: invalid input value for enum analysis_type: "combined"` at runtime.
[VERIFIED: migration 002 DDL inspection + model code inspection]

### Pitfall 2: CafeF SSL Certificate Issues
**What goes wrong:** httpx raises `SSL: CERTIFICATE_VERIFY_FAILED` when connecting to CafeF.
**Why it happens:** CafeF's SSL certificate chain includes intermediate certificates that may not be trusted by the default Python certifi bundle.
**How to avoid:** Use `verify=False` in httpx client configuration. This is acceptable for a scraping client fetching public news data (not submitting credentials).
**Warning signs:** `httpx.ConnectError` with SSL mention in production.
[VERIFIED: initial connection test failed without verify=False]

### Pitfall 3: Sparse News Data for Many Tickers
**What goes wrong:** Combined recommendation for a ticker has no sentiment input because CafeF returned 0 articles in the 7-day window.
**Why it happens:** Mid/small-cap HOSE tickers rarely appear in CafeF news. Even blue-chips like VNM only had 1 article in 7 days.
**How to avoid:** Design sentiment analysis to handle empty news lists gracefully — score as "neutral" with low confidence. Combined recommendation should work with 2 of 3 dimensions when news is absent.
**Warning signs:** Majority of tickers getting "neutral" sentiment.
[VERIFIED: live news density measurement across 4 tickers]

### Pitfall 4: Duplicate News Articles Across Daily Runs
**What goes wrong:** The same article appears in consecutive daily scrapes (7-day rolling window), causing duplicate INSERT errors.
**Why it happens:** Each daily scrape fetches the last 7 days. Articles from yesterday will appear in both yesterday's and today's scrape.
**How to avoid:** Use `INSERT ... ON CONFLICT DO NOTHING` on a UNIQUE constraint of `(ticker_id, url)`. The URL is a natural dedup key. Alternatively, use `published_at + title` hash, but URL is cleaner.
[VERIFIED: confirmed overlapping 7-day windows would produce duplicates]

### Pitfall 5: CafeF URL Completeness
**What goes wrong:** Article URLs from CafeF are relative paths (e.g., `/du-lieu/VNM-2663170/...`), and stored as-is, making them unusable in API responses.
**Why it happens:** The AJAX endpoint returns relative URLs, not absolute ones.
**How to avoid:** Normalize URLs by prepending `https://cafef.vn` when the URL starts with `/`. Check both AJAX and full-page responses — the `utm_source=du-lieu` query parameter can also be stripped.
[VERIFIED: live parsing showed relative URLs]

### Pitfall 6: Combined Analysis Needs Prior Analyses to Exist
**What goes wrong:** Combined recommendation runs but can't find technical/fundamental analysis for a ticker (e.g., it was a newly listed ticker with no indicator data).
**Why it happens:** The combined analysis reads the latest technical/fundamental/sentiment results from `ai_analyses` table. If prior pipeline stages skipped a ticker (no indicator data, no financial data), there's nothing to combine.
**How to avoid:** Query for existing analyses before building the combined prompt. Skip tickers that don't have at least technical OR fundamental analysis. Log which tickers were skipped.
[ASSUMED — based on pipeline architecture analysis]

## Code Examples

### CafeF AJAX Endpoint [VERIFIED: live HTTP test]

```python
import httpx

async with httpx.AsyncClient(
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    timeout=15,
    follow_redirects=True,
    verify=False,
) as client:
    resp = await client.get(
        "https://cafef.vn/du-lieu/Ajax/Events_RelatedNews_New.aspx",
        params={
            "symbol": "VNM",
            "floorID": "0",
            "configID": "0",
            "PageIndex": "1",
            "PageSize": "30",
            "Type": "2",
        },
    )
    # Returns ~21KB HTML fragment with <li> elements
    # Parse with BeautifulSoup as shown above
```

### Vietnamese Sentiment Prompt Pattern [ASSUMED — based on existing prompt patterns]

```python
def _build_sentiment_prompt(self, ticker_data: dict[str, dict]) -> str:
    lines = [
        "Bạn là chuyên gia phân tích tâm lý thị trường chứng khoán Việt Nam (HOSE). "
        "Phân tích tiêu đề tin tức gần đây cho các mã cổ phiếu sau.",
        "",
        "Cho mỗi mã, đánh giá:",
        "- sentiment: very_positive, positive, neutral, negative, very_negative",
        "- score: 1-10 (1 = rất tiêu cực, 10 = rất tích cực)",
        "- reasoning: giải thích ngắn gọn bằng tiếng Việt (2-3 câu)",
        "",
        "Lưu ý: Nếu không có tin tức, sentiment = neutral, score = 5.",
        "",
        "Các mã cổ phiếu:",
    ]
    
    for symbol, data in ticker_data.items():
        news_titles = data.get("news_titles", [])
        lines.append(f"\n--- {symbol} ({len(news_titles)} tin tức) ---")
        if news_titles:
            for i, title in enumerate(news_titles, 1):
                lines.append(f"{i}. {title}")
        else:
            lines.append("Không có tin tức gần đây.")
    
    return "\n".join(lines)
```

### Combined Recommendation Prompt Pattern [ASSUMED — based on existing prompt patterns]

```python
def _build_combined_prompt(self, ticker_data: dict[str, dict]) -> str:
    lines = [
        "Bạn là chuyên gia tư vấn đầu tư chứng khoán Việt Nam (HOSE). "
        "Dựa trên 3 chiều phân tích (kỹ thuật, cơ bản, tâm lý thị trường), "
        "đưa ra khuyến nghị tổng hợp cho các mã sau.",
        "",
        "Cho mỗi mã, cung cấp:",
        "- recommendation: mua, ban, giu",
        "- confidence: 1-10 (dựa trên sự đồng thuận giữa 3 chiều, độ tươi dữ liệu, lượng tin)",
        "- explanation: giải thích bằng tiếng Việt, tối đa 200 từ, ngôn ngữ tự nhiên",
        "",
        "Quy tắc confidence:",
        "- 8-10: Cả 3 chiều đồng thuận, dữ liệu đầy đủ và mới",
        "- 5-7: 2/3 chiều đồng thuận, hoặc dữ liệu không đầy đủ",
        "- 1-4: Tín hiệu mâu thuẫn, hoặc thiếu dữ liệu nghiêm trọng",
        "",
        "Các mã cổ phiếu:",
    ]
    
    for symbol, data in ticker_data.items():
        lines.append(f"\n--- {symbol} ---")
        lines.append(f"Kỹ thuật: signal={data.get('tech_signal', 'N/A')}, strength={data.get('tech_score', 'N/A')}")
        lines.append(f"Cơ bản: health={data.get('fund_signal', 'N/A')}, score={data.get('fund_score', 'N/A')}")
        lines.append(f"Tâm lý: sentiment={data.get('sent_signal', 'neutral')}, score={data.get('sent_score', 5)}")
    
    return "\n".join(lines)
```

### news_articles Table Schema [ASSUMED — based on CONTEXT.md spec + existing model patterns]

```python
# backend/app/models/news_article.py
class NewsArticle(Base):
    __tablename__ = "news_articles"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ticker_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickers.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="cafef"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now()
    )
    
    __table_args__ = (
        UniqueConstraint("ticker_id", "url", name="uq_news_articles_ticker_url"),
    )
```

### Alembic Migration 003 [VERIFIED: PostgreSQL ENUM extension pattern]

```python
# 003_sentiment_tables.py
def upgrade() -> None:
    # Add 'combined' to existing analysis_type enum
    # NOTE: ALTER TYPE ... ADD VALUE cannot be in a transaction in PG < 12
    # For PG 12+, this works inside transactions
    op.execute("ALTER TYPE analysis_type ADD VALUE IF NOT EXISTS 'combined';")
    
    # Create news_articles table
    op.execute("""
        CREATE TABLE news_articles (
            id BIGSERIAL PRIMARY KEY,
            ticker_id INTEGER NOT NULL REFERENCES tickers(id),
            title TEXT NOT NULL,
            url VARCHAR(500) NOT NULL,
            published_at TIMESTAMPTZ NOT NULL,
            source VARCHAR(20) NOT NULL DEFAULT 'cafef',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            CONSTRAINT uq_news_articles_ticker_url UNIQUE (ticker_id, url)
        );
        CREATE INDEX idx_news_articles_ticker_published
            ON news_articles (ticker_id, published_at DESC);
    """)

def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS news_articles CASCADE;")
    # NOTE: PostgreSQL does not support DROP VALUE from ENUM types
    # To remove 'combined', would need to recreate the type
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate API calls for each analysis dimension | Single batched Gemini call with structured output | Established in Phase 2 | Pattern should be reused for sentiment + combined |
| Text-based Gemini output parsing | Pydantic `response_schema` for structured JSON | Phase 2 (google-genai 1.73+) | Type-safe output, no regex parsing needed |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 + pytest-asyncio 0.26.0 |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && .venv/Scripts/python.exe -m pytest tests/ -x --tb=short` |
| Full suite command | `cd backend && .venv/Scripts/python.exe -m pytest tests/ --tb=short` |

**Note:** Tests require `DATABASE_URL` env var set (even if dummy). Use `$env:DATABASE_URL="postgresql+asyncpg://dummy:dummy@localhost/dummy"` for unit tests that mock DB.

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AI-03 | CafeF scraping returns articles for a ticker | unit (mock httpx) | `pytest tests/test_cafef_crawler.py -x` | ❌ Wave 0 |
| AI-03 | Sentiment prompt contains news titles | unit | `pytest tests/test_ai_analysis_service.py::TestSentimentPrompt -x` | ❌ Wave 0 |
| AI-03 | Sentiment batch response schema validates | unit | `pytest tests/test_ai_analysis_service.py::TestSentimentSchema -x` | ❌ Wave 0 |
| AI-04 | Combined prompt includes all 3 dimensions | unit | `pytest tests/test_ai_analysis_service.py::TestCombinedPrompt -x` | ❌ Wave 0 |
| AI-04 | Combined response has mua/ban/giu recommendation | unit | `pytest tests/test_ai_analysis_service.py::TestCombinedSchema -x` | ❌ Wave 0 |
| AI-05 | Confidence field is 1-10 in combined response | unit | `pytest tests/test_ai_analysis_service.py::TestCombinedSchema -x` | ❌ Wave 0 |
| AI-06 | Combined explanation field is non-empty string | unit | `pytest tests/test_ai_analysis_service.py::TestCombinedSchema -x` | ❌ Wave 0 |
| ALL | Job chaining extends to news→sentiment→combined | unit | `pytest tests/test_scheduler.py::TestPhase3Chaining -x` | ❌ Wave 0 |
| ALL | New API endpoints return 200 | unit | `pytest tests/test_api.py::TestPhase3Endpoints -x` | ❌ Wave 0 |
| ALL | Graceful degradation when news fails | unit | `pytest tests/test_ai_analysis_service.py::TestGracefulDegradation -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && $env:DATABASE_URL="postgresql+asyncpg://d:d@l/d"; .venv/Scripts/python.exe -m pytest tests/ -x --tb=short`
- **Per wave merge:** Full suite
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cafef_crawler.py` — covers AI-03 scraping
- [ ] New test classes in `tests/test_ai_analysis_service.py` — covers AI-03 through AI-06 schemas/prompts
- [ ] New test classes in `tests/test_scheduler.py` — covers Phase 3 job chaining
- [ ] New test classes in `tests/test_api.py` — covers Phase 3 API endpoints

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — no user auth in this phase |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A — public API endpoints |
| V5 Input Validation | Yes | Pydantic schema validation for API inputs; ticker symbol validation |
| V6 Cryptography | No | N/A |
| V13 API Security | Yes | Rate limiting on trigger endpoints (existing pattern) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSRF via CafeF scraping | Spoofing | Hardcoded base URL `cafef.vn` — no user-controlled URLs |
| Prompt injection via news titles | Tampering | News titles are read-only data fed to Gemini; no user-crafted input enters prompts |
| API endpoint abuse (trigger spam) | Denial of Service | Background task pattern already in place; add rate limiting if needed |
| SQL injection via ticker symbol | Tampering | Parameterized queries via SQLAlchemy ORM (existing pattern) |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Vietnamese sentiment prompt structure will produce accurate sentiment from Gemini | Code Examples - Sentiment Prompt | Low — Gemini handles Vietnamese well; prompt can be iterated |
| A2 | Combined recommendation prompt will produce consistent mua/ban/giu output | Code Examples - Combined Prompt | Low — Pydantic response_schema constrains output format |
| A3 | `html.parser` performance is sufficient for 400 tickers × 30 articles | Standard Stack - Not Needed | Low — parsing 30 small HTML elements is trivial; lxml unneeded |
| A4 | Pitfall 6 (combined needs prior analyses) is correct architecture concern | Common Pitfalls | Medium — if skipped tickers are common, combined analysis coverage drops |
| A5 | news_articles table schema covers all needed fields | Code Examples | Low — minimal schema per CONTEXT.md spec |

## Open Questions

1. **CafeF AJAX endpoint stability**
   - What we know: The AJAX endpoint works today and returns consistent HTML
   - What's unclear: Whether CafeF changes this endpoint frequently (it's not a documented API)
   - Recommendation: Implement fallback to full-page scraping if AJAX returns 404. Log parsing failures so we detect changes early.

2. **PostgreSQL version for ENUM migration**
   - What we know: `ALTER TYPE ... ADD VALUE` has different transaction behavior pre/post PG 12
   - What's unclear: Which PostgreSQL version is running on Aiven (the production database)
   - Recommendation: Use `IF NOT EXISTS` clause and test migration. Aiven typically provides PG 14+.

3. **Gemini token usage for Vietnamese text**
   - What we know: Vietnamese uses more tokens per word than English due to diacritics and encoding
   - What's unclear: Exact token cost per batch of 10 tickers with ~5 news titles each
   - Recommendation: Monitor token usage in first runs. The existing 4-second batch delay should accommodate the 15 RPM free tier.

## Sources

### Primary (HIGH confidence)
- CafeF website (cafef.vn) — live HTTP requests verified URL patterns, HTML structure, encoding, response times, article density [VERIFIED: multiple live tests in this session]
- Existing codebase — `ai_analysis_service.py`, `analysis.py` schemas, `manager.py` job chaining, `002_analysis_tables.py` migration [VERIFIED: file inspection]
- pip package versions — httpx 0.28.1, beautifulsoup4 4.14.3, google-genai 1.73.1 [VERIFIED: pip show]

### Secondary (MEDIUM confidence)
- PostgreSQL `ALTER TYPE ADD VALUE` behavior — standard PG documentation [ASSUMED but well-documented]

### Tertiary (LOW confidence)
- None — all critical claims verified via live testing or code inspection

## Metadata

**Confidence breakdown:**
- CafeF scraping patterns: HIGH — verified via live HTTP requests and HTML parsing
- Architecture patterns: HIGH — extending well-established Phase 2 patterns
- Pitfalls: HIGH — most verified via code inspection or live testing
- Gemini Vietnamese prompts: MEDIUM — prompt structure is assumed, but Gemini Vietnamese support is well-known

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (30 days — CafeF HTML structure could change without notice)

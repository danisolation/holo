# Phase 3: Sentiment & Combined Intelligence — Context & Decisions

**Date:** 2026-04-15
**Phase Goal:** AI delivers a unified buy/sell/hold recommendation combining technical, fundamental, and sentiment dimensions with confidence level and Vietnamese explanation
**Requirements:** AI-03, AI-04, AI-05, AI-06

## Grey Area 1: News Scraping & Sentiment Source

| # | Question | Decision | Status |
|---|----------|----------|--------|
| 1 | Where to get news data? | CafeF (cafef.vn) — largest VN financial news. Scrape article titles + snippets via httpx + BeautifulSoup. Titles sufficient for sentiment (no full-text). | 🔒 Locked |
| 2 | Scope and storage? | Scrape recent 7-day news per ticker. New `news_articles` table (ticker_id, title, url, published_at, source). Map ticker symbols to CafeF stock pages. | 🔒 Locked |
| 3 | Scraping schedule? | After daily crawl (chained). Not real-time — batch daily is sufficient for recommendations. | 🔒 Locked |
| 4 | Sentiment analysis method? | Feed 7-day Vietnamese news titles directly to Gemini (no translation). Batch 10 tickers per call with their news. Returns `SentimentBatchResponse` with score per ticker. | 🔒 Locked |

## Grey Area 2: Combined Recommendation Engine

| # | Question | Decision | Status |
|---|----------|----------|--------|
| 1 | How to combine 3 dimensions? | Single Gemini call per batch: technical signal + fundamental score + sentiment → holistic mua/bán/giữ. Not a weighted formula — Gemini reasons across all dimensions. | 🔒 Locked |
| 2 | Where to store combined results? | `ai_analyses` table with `analysis_type='combined'`. Add COMBINED + SENTIMENT to AnalysisType enum. Fields: recommendation, confidence(1-10), Vietnamese explanation. | 🔒 Locked |
| 3 | How to calculate confidence? | Gemini assesses based on signal alignment (3 agree = high), data freshness, news volume. Explicit prompt instruction. | 🔒 Locked |
| 4 | Vietnamese explanation format? | System prompt: respond in Vietnamese. Include key factors from each dimension. Max ~200 words. Natural language, not bullet points. | 🔒 Locked |

## Grey Area 3: Pipeline Integration

| # | Question | Decision | Status |
|---|----------|----------|--------|
| 1 | How to chain into daily pipeline? | Extend chain: crawl → indicators → tech/fund AI → news scrape → sentiment AI → combined AI. Via EVENT_JOB_EXECUTED listener. | 🔒 Locked |
| 2 | API endpoints? | GET `/api/analysis/{symbol}/sentiment`, `/api/analysis/{symbol}/combined`, `/api/analysis/{symbol}/summary` (all 4 dimensions). | 🔒 Locked |
| 3 | News scraping failure handling? | If CafeF fails for a ticker, produce combined recommendation with technical + fundamental only (sentiment=neutral). Partial data > no data. | 🔒 Locked |
| 4 | CafeF rate limiting? | 1-second delay between requests. Proper User-Agent header. Graceful degradation if blocked. | 🔒 Locked |

## Upstream Context

- Phase 1: 400 HOSE tickers, OHLCV, financials in PostgreSQL
- Phase 2: Technical indicators computed (RSI, MACD, SMA, EMA, BB), Gemini technical + fundamental scoring in `ai_analyses` table
- `AIAnalysisService` pattern: batched Gemini calls, structured output, tenacity retry
- `AnalysisType` enum already includes SENTIMENT value (forward-designed in Phase 2)
- Existing schemas: `TechnicalBatchResponse`, `FundamentalBatchResponse` — follow same pattern
- httpx + beautifulsoup4 already in requirements.txt (listed in STACK.md)

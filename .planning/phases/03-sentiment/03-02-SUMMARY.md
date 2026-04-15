---
phase: 03-sentiment
plan: 02
subsystem: sentiment-crawler-analysis
tags: [crawler, scraping, sentiment, combined, gemini, vietnamese-nlp]
dependency_graph:
  requires: [03-01-PLAN]
  provides: [CafeFCrawler, sentiment-analysis, combined-analysis]
  affects: [03-03-PLAN]
tech_stack:
  added: []
  patterns: [AJAX-scraping, BeautifulSoup-parsing, ON-CONFLICT-DO-NOTHING, Vietnamese-Gemini-prompts, graceful-degradation]
key_files:
  created:
    - backend/app/crawlers/cafef_crawler.py
  modified:
    - backend/app/services/ai_analysis_service.py
decisions:
  - "Single httpx.AsyncClient reused across all tickers for connection pooling (not per-ticker instantiation)"
  - "on_conflict_do_nothing for news dedup (not on_conflict_do_update) — duplicate articles don't need updating"
  - "result.rowcount tracks actual inserts (0 for conflicts) for accurate reporting"
  - "Combined analysis uses analysis.explanation field (not reasoning) for Vietnamese response storage"
  - "Tickers with 0 news get empty list in sentiment prompt — Gemini scores neutral per instruction"
metrics:
  duration: 10m
  completed: 2026-04-15
  tasks: 2
  files: 2
---

# Phase 3 Plan 2: CafeF Crawler + Sentiment & Combined Analysis Summary

CafeF AJAX news scraper with BeautifulSoup parsing and AIAnalysisService extension for Vietnamese sentiment analysis and holistic mua/bán/giữ combined recommendation via Gemini structured output.

## What Was Done

### Task 1: CafeF News Crawler Service
Created `backend/app/crawlers/cafef_crawler.py` with `CafeFCrawler` class that:
- Scrapes CafeF AJAX endpoint (`/du-lieu/Ajax/Events_RelatedNews_New.aspx?symbol={TICKER}`) for all active tickers
- Parses HTML fragments with BeautifulSoup using `html.parser`: `span.timeTitle` for dates, `a.docnhanhTitle` for title+URL
- Filters articles to configured 7-day window via `settings.cafef_news_days`
- Stores articles in `news_articles` table with `INSERT ON CONFLICT DO NOTHING` on `(ticker_id, url)` unique constraint
- Normalizes relative URLs to absolute (`https://cafef.vn` prefix)
- Uses `verify=False` for SSL (CafeF cert chain issues), proper User-Agent, 1-second delay between requests
- Per-ticker exception handling: failures logged and skipped, doesn't cascade
- Returns stats: `{success, failed, total_articles, failed_symbols}`

### Task 2: AIAnalysisService Sentiment + Combined Extension
Extended `backend/app/services/ai_analysis_service.py` with 8 new methods:

**Public methods:**
- `run_sentiment_analysis()` — Reads news titles from `news_articles`, batches tickers to Gemini with Vietnamese prompt. Tickers with 0 news included (Gemini scores neutral per prompt instruction).
- `run_combined_analysis()` — Reads latest tech+fund+sentiment from `ai_analyses`, produces holistic mua/bán/giữ recommendation with confidence (1-10) and Vietnamese explanation (max ~200 words).
- `analyze_all_tickers()` — Updated to support `'sentiment'`, `'combined'`, and `'all'` types (backward-compatible `'both'` preserved).

**Internal methods:**
- `_analyze_sentiment_batch()` / `_analyze_combined_batch()` — Gemini API callers following established pattern
- `_get_sentiment_context()` — Queries news_articles for recent titles; always returns dict (never None)
- `_get_combined_context()` — Queries ai_analyses for 3 prior dimensions; returns None if no tech AND no fund
- `_build_sentiment_prompt()` / `_build_combined_prompt()` — Vietnamese prompts per CONTEXT.md

**Key updates to `_run_batched_analysis()`:**
- Added SENTIMENT and COMBINED branches for signal/score extraction
- Combined type uses `analysis.explanation` (not `analysis.reasoning`) for Vietnamese explanation
- Added fallback `else: signal="unknown", score=5` for safety

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `bdccdac` | CafeF news crawler with AJAX endpoint, HTML parsing, DB dedup |
| 2 | `9ec9c59` | Extend AIAnalysisService with sentiment + combined analysis methods |

## Verification Results

- CafeFCrawler._parse_articles() correctly extracts title, url, published_at from sample HTML ✅
- Old articles (outside 7-day window) filtered ✅
- Relative URLs normalized to absolute ✅
- Empty/missing title articles filtered ✅
- Sentiment prompt includes ticker symbols and news titles in Vietnamese ✅
- Empty news prompt shows "Không có tin tức gần đây" ✅
- Combined prompt includes tech_signal, fund_signal, sent_signal for each ticker ✅
- All 23 functions present in service file (AST verified) ✅
- No syntax errors ✅

## Known Stubs

None — all methods are fully implemented with real logic.

## Self-Check: PASSED

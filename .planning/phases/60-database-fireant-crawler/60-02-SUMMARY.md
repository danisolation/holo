---
phase: 60-database-fireant-crawler
plan: 02
subsystem: backend
tags: [crawler, fireant, rumor, dedup, circuit-breaker, retry]
dependency_graph:
  requires: [rumors-table, fireant-config, fireant-breaker, rumor-crawl-result-type]
  provides: [fireant-crawler]
  affects: [backend/app/crawlers, backend/tests]
tech_stack:
  added: []
  patterns: [circuit-breaker-wrap, tenacity-retry, on-conflict-do-nothing, html-unescape, watchlist-gated-crawling]
key_files:
  created:
    - backend/app/crawlers/fireant_crawler.py
    - backend/tests/test_fireant_crawler.py
  modified: []
decisions:
  - "Inline watchlist query instead of importing _get_watchlist_ticker_map to avoid circular imports"
  - "Mirror CafeFCrawler pattern exactly — constructor, retry decorator, circuit breaker wrap, store loop"
  - "_parse_posts as pure synchronous method for easy unit testing without DB mocks"
metrics:
  duration: ~4min
  completed: 2026-05-05
  tasks_completed: 2
  tasks_total: 2
---

# Phase 60 Plan 02: Fireant Crawler Implementation Summary

FireantCrawler class fetching Fireant.vn REST API posts for watchlist tickers with html.unescape() Vietnamese content cleaning, ON CONFLICT DO NOTHING dedup, circuit breaker + tenacity retry resilience, and 30-day retention cleanup.

## Task Completion

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Implement FireantCrawler class | 8d3224c | backend/app/crawlers/fireant_crawler.py |
| 2 | Create unit tests for FireantCrawler | 75b49e2 | backend/tests/test_fireant_crawler.py |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Missing httpx import in test file**
- **Found during:** Task 2
- **Issue:** Test file used `httpx.TimeoutException`, `httpx.ConnectError`, etc. without importing httpx
- **Fix:** Added `import httpx` to test imports
- **Files modified:** backend/tests/test_fireant_crawler.py
- **Commit:** 75b49e2

## Verification Results

All verification checks passed:
- `from app.crawlers.fireant_crawler import FireantCrawler` — import succeeds
- `FireantCrawler.API_URL == "https://restv2.fireant.vn/posts"` — confirmed
- `FireantCrawler.MIN_CONTENT_LENGTH == 20` — confirmed
- grep confirms: `on_conflict_do_nothing`, `html.unescape`, `fireant_breaker.call`, `asyncio.sleep`, `settings.fireant_token`
- 174 lines in fireant_crawler.py (> 80 minimum)
- 15 test functions (> 6 minimum), all passing
- `pytest tests/test_fireant_crawler.py` — 15 passed in 0.91s

## Known Stubs

None — FireantCrawler is a fully functional class. Token is configured via env var (settings.fireant_token), not hardcoded.

## Self-Check: PASSED

# Plan 06-03 Summary: Circuit Breaker Integration

## Status: COMPLETE

## What Was Done
Integrated circuit breakers into all three external service callers:

### VnstockCrawler (vnstock_breaker)
- Renamed 4 public methods to `_*_with_retry` (private, keeps @retry)
- Created new public methods wrapping with `vnstock_breaker.call()`
- Methods: fetch_listing, fetch_ohlcv, fetch_financial_ratios, fetch_industry_classification

### CafeFCrawler (cafef_breaker)
- Renamed `_fetch_news` to `_fetch_news_raw` (no tenacity — single HTTP call)
- Created new `_fetch_news` wrapper with `cafef_breaker.call()`

### AIAnalysisService (gemini_breaker)
- Renamed `_call_gemini` to `_call_gemini_with_retry` (keeps @retry on ServerError)
- Created new `_call_gemini` wrapper with `gemini_breaker.call()`

### Pattern
Circuit breaker wraps OUTSIDE tenacity retries (Pitfall 1 from research):
- tenacity retries N times on transient errors
- If all retries fail, that counts as 1 circuit breaker failure
- After `circuit_breaker_fail_max` (3) such sequences, circuit opens
- CircuitOpenError propagates immediately, no wasted retries

## Commits
- `8728d1f` — feat(06-03): integrate circuit breakers into crawlers and AI service

## Test Results
- 106/106 tests pass (no regressions)

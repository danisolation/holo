---
phase: 12-multi-market-foundation
reviewed: 2025-07-19T12:00:00Z
depth: deep
files_reviewed: 24
files_reviewed_list:
  - backend/app/api/analysis.py
  - backend/app/api/tickers.py
  - backend/app/scheduler/jobs.py
  - backend/app/scheduler/manager.py
  - backend/app/services/ai_analysis_service.py
  - backend/app/services/price_service.py
  - backend/app/services/ticker_service.py
  - backend/tests/test_ai_analysis_tiered.py
  - backend/tests/test_api.py
  - backend/tests/test_scheduler.py
  - backend/tests/test_telegram.py
  - backend/tests/test_ticker_service_multi.py
  - frontend/src/app/dashboard/page.tsx
  - frontend/src/app/globals.css
  - frontend/src/app/layout.tsx
  - frontend/src/app/page.tsx
  - frontend/src/app/ticker/[symbol]/page.tsx
  - frontend/src/app/watchlist/page.tsx
  - frontend/src/components/exchange-badge.tsx
  - frontend/src/components/exchange-filter.tsx
  - frontend/src/components/heatmap.tsx
  - frontend/src/components/ticker-search.tsx
  - frontend/src/components/watchlist-table.tsx
  - frontend/src/lib/api.ts
  - frontend/src/lib/hooks.ts
  - frontend/src/lib/store.ts
findings:
  critical: 0
  high: 2
  medium: 4
  low: 2
  total: 8
status: issues_found
---

# Phase 12: Multi-Market Foundation — Code Review

**Reviewed:** 2025-07-19  
**Depth:** Deep (cross-file call chain analysis)  
**Files Reviewed:** 24  
**Commits:** `0f522e9`..`71fe741` (8 feat/test commits)  
**Status:** Issues found — 2 HIGH, 4 MEDIUM, 2 LOW

## Summary

Phase 12 adds multi-exchange (HOSE/HNX/UPCOM) support across the full stack: ticker service parameterization, staggered exchange scheduler jobs, tiered AI analysis, on-demand analysis endpoint, and frontend exchange filter UI.

**The #1 risk area — per-exchange deactivation scoping — is correctly implemented.** The deactivation query in `ticker_service.py:103-109` properly includes `Ticker.exchange == exchange` in the WHERE clause, preventing cross-exchange data corruption. This is well-tested (`test_ticker_service_multi.py:73-103`).

Key concerns are around the on-demand analysis endpoint lacking server-side rate limiting (DoS vector against Gemini API), lock starvation in sequential single-ticker analysis, and hardcoded scheduler times that were previously configurable.

---

## High Issues

### HIGH-01: On-demand analysis endpoint has no server-side rate limiting

**File:** `backend/app/api/analysis.py:29-60`  
**Issue:** The `POST /{symbol}/analyze-now` endpoint triggers 4 sequential Gemini API calls (technical, fundamental, sentiment, combined) per invocation with no server-side throttle. The frontend enforces a 60-second cooldown (`ticker/[symbol]/page.tsx:48-51`), but this is trivially bypassed via direct API calls. An attacker or misbehaving client could:
- Exhaust the Gemini 1500 RPD free-tier budget rapidly
- Queue many lock-acquisitions that block the daily pipeline
- Create a backlog of background tasks

**Fix:** Add a server-side per-symbol cooldown or global rate limiter. Minimal approach — check for recent analysis before triggering:

```python
@router.post("/{symbol}/analyze-now", response_model=AnalysisTriggerResponse)
async def trigger_on_demand_analysis(
    symbol: str,
    background_tasks: BackgroundTasks,
):
    async with async_session() as session:
        ticker = await _get_ticker_by_symbol(session, symbol.upper())
        ticker_id = ticker.id
        ticker_symbol = ticker.symbol

        # Server-side cooldown: reject if analysis exists within last 5 minutes
        from datetime import datetime, timedelta, timezone
        recent = await session.execute(
            select(AIAnalysis)
            .where(
                AIAnalysis.ticker_id == ticker_id,
                AIAnalysis.created_at >= datetime.now(timezone.utc) - timedelta(minutes=5),
            )
            .limit(1)
        )
        if recent.scalar_one_or_none():
            raise HTTPException(status_code=429, detail="Analysis recently completed. Try again later.")

    # ... rest of handler
```

### HIGH-02: `analyze_single_ticker` acquires lock 4 separate times — starvation risk

**File:** `backend/app/services/ai_analysis_service.py:428-447`  
**Issue:** `analyze_single_ticker` calls `analyze_all_tickers` in a loop for each of the 4 analysis types. Each call independently acquires and releases `_gemini_lock`. Between releases, the daily pipeline (analyzing 400+ HOSE tickers) can grab the lock and hold it for 30+ minutes per analysis type. This means on-demand analysis for a single HNX ticker could take **hours** to complete all 4 types if it overlaps with the daily schedule.

The frontend's 5-second `setTimeout` query invalidation (`hooks.ts:94-96`) and the user-facing "Đang phân tích..." state assume fast completion, creating a misleading UX.

**Fix:** Run all 4 types under a single lock acquisition:

```python
async def analyze_single_ticker(self, ticker_id: int, symbol: str) -> dict:
    logger.info(f"On-demand analysis for {symbol} (id={ticker_id})")
    ticker_filter = {symbol: ticker_id}
    results = {}
    async with _gemini_lock:
        for analysis_type in ["technical", "fundamental", "sentiment", "combined"]:
            try:
                # Call the underlying methods directly, bypassing analyze_all_tickers lock
                if analysis_type == "technical":
                    results[analysis_type] = await self.run_technical_analysis(ticker_filter=ticker_filter)
                elif analysis_type == "fundamental":
                    results[analysis_type] = await self.run_fundamental_analysis(ticker_filter=ticker_filter)
                elif analysis_type == "sentiment":
                    results[analysis_type] = await self.run_sentiment_analysis(ticker_filter=ticker_filter)
                elif analysis_type == "combined":
                    results[analysis_type] = await self.run_combined_analysis(ticker_filter=ticker_filter)
            except Exception as e:
                logger.error(f"On-demand {analysis_type} failed for {symbol}: {e}")
                results[analysis_type] = {"error": str(e)}
    return results
```

---

## Medium Issues

### MED-01: Hardcoded scheduler times replace previously configurable settings

**File:** `backend/app/scheduler/manager.py:174-178`  
**Issue:** The original `daily_price_crawl` used `settings.daily_crawl_hour` and `settings.daily_crawl_minute` from config. The new staggered schedule hardcodes times:
```python
EXCHANGE_CRAWL_SCHEDULE = {
    "HOSE":  {"hour": 15, "minute": 30},
    "HNX":   {"hour": 16, "minute": 0},
    "UPCOM": {"hour": 16, "minute": 30},
}
```
Changing crawl times now requires a code change. If the VNDirect data source changes their EOD processing time, this can't be adjusted via environment variables.

**Fix:** Add config settings for the HOSE base time and compute offsets:
```python
EXCHANGE_CRAWL_SCHEDULE = {
    "HOSE":  {"hour": settings.daily_crawl_hour, "minute": settings.daily_crawl_minute},
    "HNX":   {"hour": settings.daily_crawl_hour + (1 if settings.daily_crawl_minute + 30 >= 60 else 0),
              "minute": (settings.daily_crawl_minute + 30) % 60},
    # ... or define per-exchange settings
}
```

### MED-02: `analyze_watchlisted_tickers` returns misleading "analyzed" count

**File:** `backend/app/services/ai_analysis_service.py:411-425`  
**Issue:** The `for analysis_type in ["technical", "fundamental"]` loop catches and logs exceptions but doesn't track whether analyses actually succeeded. The returned `{"analyzed": N}` reflects tickers *selected*, not tickers *successfully analyzed*. If all Gemini calls fail, the method reports `{"analyzed": 50}` while nothing was actually analyzed. The downstream job (`daily_hnx_upcom_analysis`) logs this as a success.

**Fix:** Track failures from `analyze_all_tickers` results:
```python
total_success = 0
total_failed = 0
for analysis_type in ["technical", "fundamental"]:
    try:
        result = await self.analyze_all_tickers(
            analysis_type=analysis_type, ticker_filter=ticker_id_map
        )
        type_result = result.get(analysis_type, {})
        total_success += type_result.get("success", 0)
        total_failed += type_result.get("failed", 0)
    except Exception as e:
        logger.error(f"Failed {analysis_type} analysis for watchlisted: {e}")
        total_failed += len(symbols_to_analyze)

return {
    "analyzed": len(symbols_to_analyze),
    "analysis_success": total_success,
    "analysis_failed": total_failed,
    "skipped": skipped,
    "exchanges": exchanges,
}
```

### MED-03: `weekly_ticker_refresh` has partial commit risk

**File:** `backend/app/scheduler/jobs.py:170-198`  
**Issue:** The loop calls `fetch_and_sync_tickers()` for each exchange sequentially, and each call internally commits (`ticker_service.py:115`). If HOSE sync succeeds and commits, but HNX sync raises an exception, the job is marked as "failed" in `job_executions` — but the HOSE changes are already persisted. A subsequent retry would re-process HOSE unnecessarily (harmless due to upserts, but misleading in monitoring).

**Fix:** Consider moving the commit out of `fetch_and_sync_tickers` and into the caller, or accept this as intentional (each exchange is independent) and document it. At minimum, the job status should reflect partial success:

```python
combined_result = {}
failed_exchanges = []
for exchange in VALID_EXCHANGES:
    try:
        result = await service.fetch_and_sync_tickers(exchange=exchange)
        combined_result[exchange] = result
    except Exception as e:
        logger.error(f"Failed to sync {exchange}: {e}")
        failed_exchanges.append(exchange)

status = "success" if not failed_exchanges else "partial"
```

### MED-04: `fetch_and_sync_tickers` doesn't validate exchange parameter

**File:** `backend/app/services/ticker_service.py:33`  
**Issue:** The method accepts any string as `exchange`, silently defaulting to 200 max tickers for unknown exchanges via `EXCHANGE_MAX_TICKERS.get(exchange, 200)`. While callers (scheduler jobs, API endpoints) validate the exchange, the service itself should enforce the invariant as defense-in-depth.

**Fix:** Add validation at the service level:
```python
async def fetch_and_sync_tickers(self, exchange: str = "HOSE") -> dict:
    if exchange not in self.EXCHANGE_MAX_TICKERS:
        raise ValueError(f"Invalid exchange: {exchange}. Must be one of {list(self.EXCHANGE_MAX_TICKERS.keys())}")
    max_tickers = self.EXCHANGE_MAX_TICKERS[exchange]
    ...
```

---

## Low Issues

### LOW-01: Unused `import functools` in jobs.py

**File:** `backend/app/scheduler/jobs.py:15`  
**Issue:** `import functools` was added at the module level but is not used anywhere in `jobs.py`. It's used in `manager.py` (imported locally inside `configure_jobs`), not here.

**Fix:** Remove the unused import:
```python
# Remove line 15: import functools
```

### LOW-02: Frontend `useTriggerAnalysis` uses naive 5-second timeout for cache invalidation

**File:** `frontend/src/lib/hooks.ts:91-96`  
**Issue:** After triggering on-demand analysis, the hook invalidates the query cache immediately AND after a 5-second delay:
```typescript
queryClient.invalidateQueries({ queryKey: ["analysis-summary", symbol] });
setTimeout(() => {
    queryClient.invalidateQueries({ queryKey: ["analysis-summary", symbol] });
}, 5000);
```
The 5-second timeout assumes the background analysis completes quickly, but per HIGH-02, it could take much longer. The `setTimeout` also runs even if the component unmounts (though `invalidateQueries` on a global client is harmless).

**Fix:** Consider a polling strategy that checks until data appears, or use a WebSocket/SSE notification:
```typescript
onSuccess: (_data, symbol) => {
    // Poll every 10s for up to 2 minutes
    let attempts = 0;
    const poll = setInterval(() => {
        queryClient.invalidateQueries({ queryKey: ["analysis-summary", symbol] });
        attempts++;
        if (attempts >= 12) clearInterval(poll);
    }, 10000);
},
```

---

## Positive Observations

1. **Deactivation scoping is correct and well-tested** — The critical `Ticker.exchange == exchange` filter in the deactivation query prevents cross-exchange data corruption. The dedicated test (`TestDeactivationScoping`) verifies the compiled SQL contains the exchange filter.

2. **Exchange validation on API boundary** — Both `list_tickers` and `market_overview` endpoints validate exchange against `ALLOWED_EXCHANGES` with clear 400 error messages.

3. **Scheduler chaining updated correctly** — Chain now triggers from `daily_price_crawl_upcom` (the last staggered crawl), ensuring all exchange data is available before indicators and AI analysis run.

4. **Frontend state management is clean** — `useExchangeStore` with persist correctly shares exchange filter state across pages. Exchange filter is properly passed through to API hooks.

5. **ExchangeBadge/ExchangeFilter are well-componentized** — Clean separation, CSS variables for theming with proper dark mode support, and reused consistently across heatmap, watchlist, ticker detail, and search.

6. **`on_conflict_do_update` now includes `exchange` field** — The upsert correctly updates the exchange field when a ticker already exists, handling the case where a ticker moves between exchanges.

---

_Reviewed: 2025-07-19_  
_Reviewer: the agent (gsd-code-reviewer)_  
_Depth: deep_

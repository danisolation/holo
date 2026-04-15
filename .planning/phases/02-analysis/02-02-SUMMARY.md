---
phase: 02-analysis
plan: "02"
subsystem: analysis-services
tags: [indicator-service, ai-analysis, gemini, ta-library, technical-indicators, fundamental-analysis]
dependency_graph:
  requires: [02-01 (TechnicalIndicator ORM, AIAnalysis ORM, Pydantic schemas, config, ta + google-genai deps)]
  provides: [IndicatorService (12 technical indicators), AIAnalysisService (Gemini technical + fundamental scoring)]
  affects: [02-03 (scheduler jobs + API endpoints consume these services)]
tech_stack:
  added: []
  patterns: [ta individual indicator classes with fillna=False, google-genai async structured output via response.parsed, tenacity retry on ClientError/ServerError, INSERT ON CONFLICT DO UPDATE upsert pattern]
key_files:
  created:
    - backend/app/services/indicator_service.py
    - backend/app/services/ai_analysis_service.py
  modified: []
decisions:
  - "Instantiate ta classes once per ticker (MACD, BB reused for multiple outputs) for computation efficiency"
  - "Round float to 6 decimal places before Decimal conversion to avoid IEEE 754 precision artifacts"
  - "Rate limit delay only between batches (not after last batch) — saves 4s per analysis run"
  - "Financial.quarter.desc().nullslast() ordering ensures quarterly reports sorted before annual (NULL quarter)"
metrics:
  duration: ~7m
  completed: 2026-04-15
---

# Phase 2 Plan 02: Core Analysis Services Summary

**One-liner:** IndicatorService computes 12 technical indicators via ta library; AIAnalysisService scores tickers via Gemini structured output with batching, retry, and rate limiting.

## What Was Built

### Task 1: IndicatorService (`backend/app/services/indicator_service.py`)

Technical indicator computation engine that reads daily prices and produces 12 indicator values per ticker per date:

- **Indicators:** RSI(14), MACD(12,26,9) line/signal/histogram, SMA(20/50/200), EMA(12/26), BB(20,2) upper/middle/lower
- **Computation:** Uses `ta` library individual classes with `fillna=False` — NaN warm-up values stored as NULL in PostgreSQL
- **Incremental:** Queries `MAX(date)` from `technical_indicators` per ticker, only computes new dates
- **Safety:** Skips tickers with < 20 data points, warns on < 200 (SMA(200) will be NULL)
- **Storage:** INSERT ... ON CONFLICT DO UPDATE on `uq_technical_indicators_ticker_date` constraint
- **Precision:** `_safe_decimal()` uses `round(value, 6)` before `Decimal(str(...))` to avoid float artifacts

**Key methods:**
- `compute_all_tickers()` → orchestrates all active tickers, returns {success, failed, skipped}
- `compute_for_ticker(ticker_id, symbol)` → single ticker computation, returns rows stored
- `_compute_indicators(close)` → pure computation, returns dict of 12 pd.Series

### Task 2: AIAnalysisService (`backend/app/services/ai_analysis_service.py`)

Gemini-powered analysis service that scores tickers on technical and fundamental dimensions:

- **API:** Async via `client.aio.models.generate_content()` — never blocks FastAPI event loop
- **Structured output:** `response_schema=TechnicalBatchResponse/FundamentalBatchResponse`, accessed via `response.parsed`
- **Batching:** 10 tickers per Gemini call (configurable via `settings.gemini_batch_size`)
- **Rate limiting:** `asyncio.sleep(settings.gemini_delay_seconds)` (4s) between batches for 15 RPM safety
- **Retry:** tenacity decorator — 3 attempts, exponential backoff (2x, min=4s, max=30s), retries `ClientError` + `ServerError`
- **Resilience:** Failed batches logged and skipped — partial analysis beats no analysis
- **Security:** API key validated at init, never logged (T-02-06 mitigation)

**Technical context gathering:** Last 5 days of indicators + RSI zone (oversold/overbought/neutral) + MACD crossover detection (bullish/bearish/none)

**Fundamental context gathering:** Latest financial period — P/E, P/B, EPS, ROE, ROA, revenue/profit growth, current ratio, debt-to-equity

**Key methods:**
- `analyze_all_tickers(analysis_type)` → orchestrates both or either analysis type
- `run_technical_analysis()` / `run_fundamental_analysis()` → per-type runners
- `_call_gemini(prompt, response_schema)` → retry-decorated async Gemini call
- `_build_technical_prompt()` / `_build_fundamental_prompt()` → structured prompt generation
- `_store_analysis()` → upsert to `ai_analyses` with model_version and raw_response JSONB

## Verification Results

- ✅ IndicatorService importable, computes 12 indicators from 250-row close Series
- ✅ SMA(200) correctly produces 199 NaN values (warm-up period)
- ✅ `_safe_decimal(NaN)` returns None, `_safe_decimal(0.3)` returns Decimal('0.3')
- ✅ AIAnalysisService importable, all 12 methods present
- ✅ `_call_gemini` uses `client.aio.models.generate_content` (async)
- ✅ Technical and fundamental prompts generate correctly with formatted data
- ✅ `_store_analysis` uses INSERT ON CONFLICT DO UPDATE on correct constraint
- ✅ 24 existing tests pass (no regressions)

## Threat Model Compliance

| Threat ID | Mitigation | Status |
|-----------|-----------|--------|
| T-02-04 (Tampering) | Gemini output constrained by response_schema with Pydantic enum types. response.parsed validates before storage | ✅ Implemented |
| T-02-05 (DoS) | 4s delay via asyncio.sleep, tenacity exponential backoff (min=4s, max=30s), configurable batch size | ✅ Implemented |
| T-02-06 (Info Disclosure) | API key from settings, validated at init with ValueError if empty, never logged | ✅ Implemented |

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `11bf5f5` | feat(02-02): add IndicatorService for technical indicator computation |
| 2 | `95537c8` | feat(02-02): add AIAnalysisService for Gemini-powered technical/fundamental scoring |

## Self-Check: PASSED

All created files exist. All commit hashes verified in git log.

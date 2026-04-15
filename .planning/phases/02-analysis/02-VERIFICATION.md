---
phase: 02-analysis
verified: 2025-07-17T07:45:00Z
status: human_needed
score: 3/3 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Run full pipeline with real Gemini API key"
    expected: "Gemini returns structured TechnicalBatchResponse/FundamentalBatchResponse with valid signals, scores, and reasoning for real tickers"
    why_human: "Cannot invoke Gemini API in automated verification — requires a valid GEMINI_API_KEY and network access"
  - test: "Run scheduler chain end-to-end with real database"
    expected: "daily_price_crawl completion triggers daily_indicator_compute, which triggers daily_ai_analysis; technical_indicators and ai_analyses tables are populated"
    why_human: "Requires running PostgreSQL database with migrated schema and actual price/financial data"
---

# Phase 2: Technical & Fundamental Analysis Verification Report

**Phase Goal:** Every ticker has computed technical indicators and AI-powered scoring for technical signals and fundamental health
**Verified:** 2025-07-17T07:45:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Each ticker has RSI, MACD, MA, and Bollinger Bands computed and stored after each daily crawl | ✓ VERIFIED | `IndicatorService._compute_indicators()` produces 12 indicators (RSI-14, MACD line/signal/histogram, SMA-20/50/200, EMA-12/26, BB upper/middle/lower). Behavioral check confirmed all 12 return real numeric values from 300-point sample. Job chaining `daily_price_crawl → daily_indicator_compute` wired via `EVENT_JOB_EXECUTED` listener in `manager.py:17-44`. Storage via `INSERT ON CONFLICT DO UPDATE` to `technical_indicators` table. |
| 2 | Gemini produces a bullish/bearish/neutral technical signal with reasoning for any ticker | ✓ VERIFIED | `AIAnalysisService._analyze_technical_batch()` calls Gemini with `response_schema=TechnicalBatchResponse`. `TechnicalSignal` enum defines strong_buy/buy/neutral/sell/strong_sell. `_build_technical_prompt()` includes 5-day indicator window, RSI zone, MACD crossover detection. `_store_analysis()` persists signal, score (1-10), reasoning, model_version, raw_response JSONB via upsert. Retry (3x exponential backoff) and rate limiting (4s delay) enforced. |
| 3 | Gemini produces a fundamental health score based on actual financial metrics for any ticker | ✓ VERIFIED | `AIAnalysisService._get_fundamental_context()` queries `Financial` model for P/E, P/B, EPS, ROE, ROA, revenue/profit growth, current ratio, debt-to-equity. `FundamentalHealth` enum: strong/good/neutral/weak/critical. `_build_fundamental_prompt()` includes all 10 financial metrics. `FundamentalBatchResponse` used as `response_schema`. Same upsert, retry, and rate limiting as technical. |

**Score:** 3/3 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/models/technical_indicator.py` | TechnicalIndicator ORM with 12 indicator columns | ✓ VERIFIED | 58 lines. `class TechnicalIndicator(Base)` with rsi_14, macd_line/signal/histogram, sma_20/50/200, ema_12/26, bb_upper/middle/lower. UniqueConstraint on (ticker_id, date). |
| `backend/app/models/ai_analysis.py` | AIAnalysis ORM with AnalysisType enum | ✓ VERIFIED | 57 lines. `class AIAnalysis(Base)` with signal, score, reasoning, model_version, raw_response (JSONB). `AnalysisType` enum: technical/fundamental/sentiment. `native_enum=False`. |
| `backend/app/schemas/analysis.py` | Pydantic schemas for Gemini structured output | ✓ VERIFIED | 98 lines. 7 schemas: TechnicalSignal, TickerTechnicalAnalysis, TechnicalBatchResponse, FundamentalHealth, TickerFundamentalAnalysis, FundamentalBatchResponse, AnalysisResultResponse, AnalysisTriggerResponse, IndicatorResponse. All importable — behavioral check confirmed. |
| `backend/alembic/versions/002_analysis_tables.py` | Migration creating technical_indicators + ai_analyses + analysis_type enum | ✓ VERIFIED | 75 lines. Creates `analysis_type` ENUM, `technical_indicators` table (12 indicator columns, BIGSERIAL PK, unique constraint), `ai_analyses` table (signal, score 1-10 CHECK, reasoning, JSONB). Proper revision chain 001→002. Downgrade drops both tables and ENUM. |
| `backend/app/config.py` | Extended Settings with Gemini config | ✓ VERIFIED | 6 new fields: `gemini_api_key`, `gemini_model`, `gemini_batch_size`, `gemini_delay_seconds`, `gemini_max_retries`, `indicator_compute_days`. All with sensible defaults. |
| `backend/app/services/indicator_service.py` | Technical indicator computation and storage | ✓ VERIFIED | 183 lines. `class IndicatorService` with `compute_all_tickers()`, `compute_for_ticker()`, `_compute_indicators()`, `_safe_decimal()`. Uses ta library (RSIIndicator, MACD, SMAIndicator, EMAIndicator, BollingerBands). Incremental via `MAX(date)` query. INSERT ON CONFLICT DO UPDATE. |
| `backend/app/services/ai_analysis_service.py` | Gemini AI analysis for technical and fundamental scoring | ✓ VERIFIED | 492 lines. `class AIAnalysisService` with full pipeline: context gathering, prompt building, batched Gemini calls, result parsing, upsert storage. Async via `client.aio.models.generate_content`. `@retry` decorator with tenacity (3x, exponential backoff, min=4s, max=30s). 4s rate limiting. API key validated at init. |
| `backend/app/scheduler/jobs.py` | Job functions: daily_indicator_compute, daily_ai_analysis | ✓ VERIFIED | 105 lines. Both async job functions with own DB sessions, lazy imports to avoid circular deps. `daily_ai_analysis` catches `ValueError` gracefully when API key not set. |
| `backend/app/scheduler/manager.py` | Event listener for job chaining | ✓ VERIFIED | 111 lines. `_on_job_executed()` chains `daily_price_crawl → daily_indicator_compute_triggered → daily_ai_analysis_triggered`. Skips on failure (`event.exception` check). Listener registered via `scheduler.add_listener(_on_job_executed, events.EVENT_JOB_EXECUTED)`. |
| `backend/app/api/analysis.py` | Analysis trigger and result endpoints | ✓ VERIFIED | 189 lines. 5 endpoints: POST trigger/indicators, POST trigger/ai (with type validation, 400 on invalid), GET {symbol}/indicators (limit 5, max 60), GET {symbol}/technical, GET {symbol}/fundamental. All use async_session, BackgroundTasks pattern, proper 404 handling. |
| `backend/app/api/router.py` | Updated router including analysis sub-router | ✓ VERIFIED | 10 lines. `analysis_router` imported and included via `api_router.include_router(analysis_router)`. |
| `backend/tests/test_indicator_service.py` | Unit tests for indicator computation | ✓ VERIFIED | 87 lines. 8 tests: 12 indicators returned, series length, RSI warm-up NaN, SMA-200 warm-up NaN, safe_decimal normal/NaN/None, skip low-data tickers. |
| `backend/tests/test_ai_analysis_service.py` | Unit tests for AI analysis with mocked Gemini | ✓ VERIFIED | 81 lines. 3 tests: ValueError without API key, technical prompt includes symbols, fundamental prompt includes financial data. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `models/__init__.py` | `technical_indicator.py` | `from app.models.technical_indicator import TechnicalIndicator` | ✓ WIRED | Line 12: explicit import + export in `__all__` |
| `models/__init__.py` | `ai_analysis.py` | `from app.models.ai_analysis import AIAnalysis, AnalysisType` | ✓ WIRED | Line 13: explicit import + export in `__all__` |
| `indicator_service.py` | `daily_price.py` | `SELECT close prices for ta computation` | ✓ WIRED | Lines 26, 79-81: imports DailyPrice, queries .date and .close |
| `indicator_service.py` | `technical_indicator.py` | `INSERT ON CONFLICT DO UPDATE` | ✓ WIRED | Lines 27, 123-126: imports TechnicalIndicator, upserts rows |
| `ai_analysis_service.py` | `analysis.py` schemas | `TechnicalBatchResponse/FundamentalBatchResponse as response_schema` | ✓ WIRED | Line 32: imports both, used in `_call_gemini()` at lines 267, 278 |
| `ai_analysis_service.py` | `ai_analysis.py` | `INSERT ON CONFLICT DO UPDATE` | ✓ WIRED | Lines 29, 472-491: imports AIAnalysis + AnalysisType, upserts results |
| `ai_analysis_service.py` | `technical_indicator.py` | `SELECT recent indicators for prompt context` | ✓ WIRED | Lines 31, 296-301: imports TechnicalIndicator, queries last 5 days |
| `ai_analysis_service.py` | `financial.py` | `SELECT latest financials for fundamental prompt` | ✓ WIRED | Lines 30, 366-369: imports Financial, queries with year/quarter ordering |
| `manager.py` | `jobs.py` | `_on_job_executed chains daily_indicator_compute and daily_ai_analysis` | ✓ WIRED | Lines 28-44: lazy imports + scheduler.add_job for both chained jobs |
| `jobs.py` | `indicator_service.py` | `IndicatorService.compute_all_tickers()` | ✓ WIRED | Lines 76-78: lazy import + instantiation + await compute_all_tickers() |
| `jobs.py` | `ai_analysis_service.py` | `AIAnalysisService.analyze_all_tickers()` | ✓ WIRED | Lines 95-97: lazy import + instantiation + await analyze_all_tickers("both") |
| `api/analysis.py` | `indicator_service.py` | `IndicatorService used for on-demand trigger` | ✓ WIRED | Lines 33-35: lazy import in background task |
| `api/analysis.py` | `ai_analysis_service.py` | `AIAnalysisService used for on-demand trigger` | ✓ WIRED | Lines 61-63: lazy import in background task |
| `router.py` | `api/analysis.py` | `include_router(analysis_router)` | ✓ WIRED | Lines 5, 9: import + include_router |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `indicator_service.py` | indicator Series (12 indicators) | `ta` library classes (RSIIndicator, MACD, SMAIndicator, EMAIndicator, BollingerBands) | Yes — behavioral check confirmed 12 numeric Series with real values from 300-point close price input | ✓ FLOWING |
| `ai_analysis_service.py` | technical_context dict | `TechnicalIndicator` DB query (last 5 days) | Yes — queries real DB rows, builds dict with RSI zone + MACD crossover classification | ✓ FLOWING (DB-dependent) |
| `ai_analysis_service.py` | fundamental_context dict | `Financial` DB query (latest period) | Yes — queries real DB rows, extracts P/E, P/B, EPS, ROE, ROA, growth metrics | ✓ FLOWING (DB-dependent) |
| `api/analysis.py` | indicator/analysis results | DB queries on TechnicalIndicator and AIAnalysis | Yes — queries real DB rows, maps to Pydantic response schemas | ✓ FLOWING (DB-dependent) |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| IndicatorService importable with all methods | `from app.services.indicator_service import IndicatorService` | class type, compute_all_tickers: True, _compute_indicators: True | ✓ PASS |
| AIAnalysisService importable with all methods | `from app.services.ai_analysis_service import AIAnalysisService` | class type, analyze_all_tickers: True, _call_gemini: True | ✓ PASS |
| All 7 Pydantic schemas importable | `from app.schemas.analysis import ...` | "All 7 schemas imported OK" | ✓ PASS |
| Models importable from __init__ | `from app.models import TechnicalIndicator, AIAnalysis, AnalysisType` | OK, AnalysisType values: ['technical', 'fundamental', 'sentiment'] | ✓ PASS |
| _compute_indicators produces 12 real indicators | Run with 300-point Series | 12 indicators, all with real numeric values (RSI=100.0, SMA-200=199.75, etc.) | ✓ PASS |
| _safe_decimal NaN→None handling | `_safe_decimal(float('nan'))` returns None, `_safe_decimal(42.12)` returns Decimal | Correct behavior confirmed | ✓ PASS |
| API key validation raises ValueError | `AIAnalysisService(session)` with empty key | "GEMINI_API_KEY is required" ValueError raised | ✓ PASS |
| All 44 tests pass | `pytest tests/ -v` | 44 passed in 14.71s, 0 failures, 0 regressions | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AI-01 | 02-01, 02-02, 02-03 | Technical analysis scoring — RSI, MACD, MA crossovers → tín hiệu bullish/bearish/neutral | ✓ SATISFIED | `IndicatorService` computes RSI, MACD, SMA, EMA, BB. `AIAnalysisService.run_technical_analysis()` sends indicator context to Gemini, returns `TechnicalSignal` (strong_buy/buy/neutral/sell/strong_sell) with reasoning. Job chaining auto-triggers after daily crawl. API endpoints expose results. 8 indicator tests + 3 AI tests + 3 API tests pass. |
| AI-02 | 02-01, 02-02, 02-03 | Fundamental analysis scoring — P/E, tăng trưởng, sức khỏe tài chính → health score | ✓ SATISFIED | `AIAnalysisService._get_fundamental_context()` queries P/E, P/B, EPS, ROE, ROA, revenue/profit growth, current ratio, D/E from Financial model. `run_fundamental_analysis()` sends to Gemini with `FundamentalBatchResponse` schema, returns `FundamentalHealth` (strong/good/neutral/weak/critical) + score 1-10 + reasoning. Same retry/rate-limiting/upsert as technical. Tests verify prompt includes financial data. |

**Orphaned requirements:** None — REQUIREMENTS.md maps only AI-01 and AI-02 to Phase 2, and both are claimed by all 3 plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | None found | — | — |

No TODO, FIXME, PLACEHOLDER, empty returns, stub patterns, or hardcoded empty data found in any of the 10 Phase 2 source files.

### Human Verification Required

### 1. Gemini API End-to-End Integration

**Test:** Configure a real `GEMINI_API_KEY` in `.env`, run `POST /api/analysis/trigger/ai?analysis_type=both`, then query `GET /api/analysis/VNM/technical` and `GET /api/analysis/VNM/fundamental` for a ticker that has price and financial data.
**Expected:** Both endpoints return non-empty JSON with valid signal (from enum values), score (1-10), reasoning (non-empty string), and model_version. The `ai_analyses` table should have rows for both analysis types.
**Why human:** Cannot invoke Gemini API in automated verification — requires a valid GEMINI_API_KEY, network access, and the free tier rate limit means this must be done carefully.

### 2. Scheduler Chain Execution

**Test:** Start the application with a configured database, trigger `POST /api/crawl/daily`, and observe logs for the automatic chain: `daily_price_crawl → daily_indicator_compute → daily_ai_analysis`.
**Expected:** Log messages show each step completing in sequence. `technical_indicators` table populated with indicator values for active tickers. `ai_analyses` table populated with technical and fundamental results.
**Why human:** Requires running PostgreSQL with migrated schema, actual ticker/price/financial data, and watching log output over several minutes (rate limiting adds ~4s per Gemini batch).

### Gaps Summary

No code-level gaps found. All 3 roadmap success criteria are fully implemented with substantive, wired, and flowing artifacts. All 44 tests pass. Both requirements (AI-01, AI-02) are satisfied.

The only remaining verification is human confirmation that the Gemini API integration works with real API keys and that the scheduler chain executes correctly against a live database — these cannot be tested without external infrastructure.

---

_Verified: 2025-07-17T07:45:00Z_
_Verifier: the agent (gsd-verifier)_

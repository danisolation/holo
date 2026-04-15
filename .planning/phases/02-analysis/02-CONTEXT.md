# Phase 2: Technical & Fundamental Analysis — Context & Decisions

**Date:** 2026-04-15
**Phase Goal:** Every ticker has computed technical indicators and AI-powered scoring for technical signals and fundamental health
**Requirements:** AI-01, AI-02

## Grey Area 1: Indicator Computation & Storage

| # | Question | Decision | Status |
|---|----------|----------|--------|
| 1 | Where to store computed indicators? | New `technical_indicators` table — one row per ticker per date. Columns: RSI(14), MACD line/signal/histogram, SMA(20/50/200), EMA(12/26), BB upper/middle/lower. Separate from `daily_prices` (different update cadence, nullable). | 🔒 Locked |
| 2 | When to compute indicators? | Automatically after daily price crawl completes — scheduler chains: crawl → compute. Also expose API endpoint for on-demand recomputation. | 🔒 Locked |
| 3 | How many data points for warm-up? | SMA(200) needs 200 days. Backfill from 2023-07-01 provides ~500 trading days (ample). Compute for most recent 60 days per run. Store all, compute only new/missing dates. | 🔒 Locked |
| 4 | Which indicator parameters? | Standard: RSI(14), MACD(12,26,9), SMA(20/50/200), EMA(12/26), Bollinger(20,2). Hardcoded in v1 — no user configurability. | 🔒 Locked |

## Grey Area 2: Gemini AI Integration Pattern

| # | Question | Decision | Status |
|---|----------|----------|--------|
| 1 | Which Gemini model? | `gemini-2.0-flash` — 15 RPM free tier, structured JSON output. Upgrade to Pro only if quality insufficient. | 🔒 Locked |
| 2 | Rate limit handling for 400 tickers? | Batch 5-10 tickers per prompt → ~40-80 calls. 2-second delay between calls. Run async post-crawl, not real-time. | 🔒 Locked |
| 3 | What data to feed Gemini? | Pre-computed indicators (not raw OHLCV). Technical: 5-day indicator values, price vs MAs, MACD crossover state, RSI zone. Fundamental: P/E, P/B, ROE, ROA, revenue/profit growth, D/E, current ratio. | 🔒 Locked |
| 4 | AI output structure? | JSON via `response_schema`. Technical: `{signal, strength(1-10), reasoning}`. Fundamental: `{health, score(1-10), reasoning}`. Store in `ai_analyses` table with type, JSONB result, model version. | 🔒 Locked |

## Grey Area 3: Analysis Pipeline & Storage

| # | Question | Decision | Status |
|---|----------|----------|--------|
| 1 | AI result storage? | New `ai_analyses` table: ticker_id, analysis_type enum (technical/fundamental/sentiment), analysis_date, signal, score(1-10), reasoning text, model_version, raw_response JSONB. One row per ticker per type per date. | 🔒 Locked |
| 2 | When to trigger Gemini? | After indicator computation (chained from daily crawl). Once daily post-market. Manual trigger API endpoint available. | 🔒 Locked |
| 3 | Error handling for Gemini? | Retry 3x with exponential backoff (tenacity). Failed batches logged and skipped — partial analysis > none. Store last_analysis_date per ticker. Don't block pipeline on individual failures. | 🔒 Locked |
| 4 | Phase 2→3 transition design? | `ai_analyses` table uses `analysis_type` enum to accommodate sentiment (Phase 3). Phase 3 adds `combined_recommendation` table referencing individual analyses. Clean separation. | 🔒 Locked |

## Upstream Context

- Phase 1 output: 400 HOSE tickers in `tickers` table, OHLCV in `daily_prices` (partitioned by year), financial ratios in `financials`
- vnstock crawler wraps sync calls via `asyncio.to_thread()`
- APScheduler runs daily crawl at 15:30 UTC+7
- `ta` library chosen for indicators (pure Python, no C deps)
- `google-genai` SDK (new, not legacy)
- Config via pydantic-settings (.env)

# Research Summary: Holo — Vietnam Stock Market Intelligence Platform

**Domain:** Financial data crawling + AI-powered trading assistant
**Researched:** 2025-07-17
**Overall confidence:** HIGH

## Executive Summary

The Vietnam stock market data ecosystem has matured significantly around the `vnstock` library (v3.5.1), which serves as the de-facto Python interface for HOSE data — wrapping VNDirect and SSI APIs into a unified, maintained package. This eliminates the historically painful task of reverse-engineering undocumented Vietnamese broker APIs. The core data pipeline (crawl → store → analyze → alert) maps cleanly to a Python-first architecture with FastAPI backend, PostgreSQL storage, and Google Gemini for AI analysis.

The AI/LLM landscape has a critical version split: Google has released `google-genai` (v1.73) as the new unified SDK, superseding the legacy `google-generativeai` (v0.8.6). Any new project must use the new SDK. Gemini 2.0 Flash offers the best cost/performance ratio for financial analysis tasks — fast enough for real-time analysis, cheap enough for 400 tickers daily.

The technical analysis library landscape narrowed: `pandas-ta` has been removed from PyPI entirely, and `ta-lib` still requires painful C library installation. The pure Python `ta` library (v0.11.0) covers all standard indicators (RSI, MACD, Bollinger, MA families) and works directly with pandas DataFrames — making it the clear winner for this stack.

For the frontend dashboard, TradingView's open-source `lightweight-charts` library (v5.1.0) is purpose-built for exactly this use case — candlestick charts, volume histograms, and technical overlays with 60fps canvas rendering. Combined with Next.js, shadcn/ui, and TanStack Query for data fetching, this creates a professional financial dashboard with minimal custom code.

## Key Findings

**Stack:** Python 3.12 + FastAPI + vnstock + google-genai + PostgreSQL (Aiven) + Next.js + lightweight-charts + python-telegram-bot
**Architecture:** Monorepo with backend (FastAPI + APScheduler) and frontend (Next.js). Single-process backend embeds scheduler — no external broker needed.
**Critical pitfall:** vnstock's `vnai` telemetry dependency and potential API breakage when VNDirect/SSI change their undocumented APIs.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Data Foundation** — Database schema + vnstock integration + basic crawling
   - Addresses: OHLCV data crawling, PostgreSQL storage, ticker listing management
   - Avoids: Over-engineering before understanding vnstock's actual data quality/completeness
   - Rationale: Everything depends on having reliable data first

2. **Technical Analysis Engine** — `ta` library integration + indicator computation
   - Addresses: MA, RSI, MACD, Bollinger Bands computation and storage
   - Avoids: Starting AI before having clean indicator data to feed it
   - Rationale: Technical indicators are deterministic — can validate correctness before adding AI

3. **AI Analysis Layer** — Gemini integration for multi-dimensional analysis
   - Addresses: Technical analysis interpretation, fundamental analysis, sentiment analysis
   - Avoids: Prompt engineering without ground truth data
   - Rationale: Needs both price data (Phase 1) and indicator data (Phase 2) to generate meaningful signals

4. **Alerts & Bot** — Telegram bot for trading signal delivery
   - Addresses: Real-time alerts, command-based queries, signal notifications
   - Avoids: Building notification without signals to notify about
   - Rationale: Depends on AI signals from Phase 3

5. **Dashboard** — Next.js frontend with charts and portfolio tracking
   - Addresses: Visual data exploration, watchlist management, historical analysis
   - Avoids: Building UI before API endpoints are stable
   - Rationale: Frontend consumes API — build API first, then UI. Personal use means Telegram bot may be the primary interface initially.

6. **Polish & Scheduling** — Production scheduling, error handling, data quality monitoring
   - Addresses: Automated daily crawls, market-hours polling, retry logic, monitoring
   - Avoids: Premature optimization
   - Rationale: Refinement phase after core features work

**Phase ordering rationale:**
- Data → Analysis → AI → Alerts → Dashboard follows the data flow direction
- Each phase produces testable, usable output (not just infrastructure)
- Telegram bot before Dashboard because mobile alerts have higher personal utility than a web dashboard for trading
- Dashboard last because it's the most effort and least critical for personal use (Telegram bot covers the alert use case)

**Research flags for phases:**
- Phase 1: Needs deeper research on vnstock v3.5 API surface — which endpoints are reliable, rate limits, data freshness
- Phase 3: Needs prompt engineering research — optimal prompts for financial analysis with Gemini
- Phase 5: Standard patterns, unlikely to need research (Next.js + lightweight-charts is well-documented)

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified via pip/npm. Active maintenance confirmed for all packages. |
| Features | HIGH | Well-understood domain. Table stakes are clear from competitor analysis (TradingView, FireAnt). |
| Architecture | HIGH | FastAPI + PostgreSQL + Next.js is a proven pattern. Single-user simplifies significantly. |
| Pitfalls | MEDIUM | vnstock API stability and vnai telemetry are concerns. CafeF scraping fragility is real. Gemini rate limits need runtime testing. |

## Gaps to Address

- **vnstock v3.5 API completeness:** Need hands-on testing to verify which data points are actually available and fresh for all 400 tickers
- **Gemini rate limits and costs:** Need to calculate actual API costs for analyzing 400 tickers daily with Gemini 2.0 Flash
- **CafeF scraping legality/stability:** CafeF may block scrapers or change HTML structure. Need fallback strategy.
- **Aiven PostgreSQL connection limits:** Free tier may have connection pool limits that affect APScheduler + FastAPI concurrent access
- **Real-time data freshness:** vnstock's intraday data may have delays — need to test during actual market hours (9:00-14:45 VN time)

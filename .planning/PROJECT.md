# Holo — Stock Intelligence Platform

## What This Is

AI-powered stock intelligence platform for 400 HOSE tickers. Crawls daily OHLCV prices and financial data via vnstock, computes 12 technical indicators, then uses Google Gemini to produce multi-dimensional analysis (technical + fundamental + sentiment) with Vietnamese buy/sell/hold recommendations. Delivered via Telegram bot alerts and Next.js web dashboard with interactive candlestick charts. Personal use.

## Core Value

AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu HOSE real-time để gợi ý trading chính xác và kịp thời qua Telegram.

## Current State

**Shipped:** v1.0 (2026-04-15)
**Code:** ~9,400 LOC (Python 6,050 + TypeScript 3,350)
**Tests:** 96 backend unit tests
**Stack:** FastAPI + PostgreSQL + APScheduler + Google Gemini + python-telegram-bot + Next.js + lightweight-charts

## Requirements

### Validated

- ✓ DATA-01: Crawl OHLCV 400 mã HOSE via vnstock — v1.0
- ✓ DATA-02: Scheduled automated crawling — v1.0
- ✓ DATA-03: Historical backfill 1-2 năm — v1.0
- ✓ DATA-04: Crawl báo cáo tài chính — v1.0
- ✓ AI-01: Technical analysis scoring (RSI, MACD, MA, BB) — v1.0
- ✓ AI-02: Fundamental analysis scoring — v1.0
- ✓ AI-03: Sentiment analysis từ tin tức CafeF — v1.0
- ✓ AI-04: Combined 3D recommendation (mua/bán/giữ) — v1.0
- ✓ AI-05: Confidence level 1-10 — v1.0
- ✓ AI-06: Vietnamese explanation — v1.0
- ✓ BOT-01: Trading signal alerts via Telegram — v1.0
- ✓ BOT-02: Price alert triggers — v1.0
- ✓ BOT-03: Daily market summary — v1.0
- ✓ DASH-01: Candlestick charts (lightweight-charts) — v1.0
- ✓ DASH-02: Technical indicator overlays — v1.0
- ✓ DASH-03: Watchlist management — v1.0
- ✓ DASH-04: Ticker detail page — v1.0
- ✓ DASH-05: Responsive mobile layout — v1.0
- ✓ DASH-06: Market overview heatmap — v1.0

### Active

(Defining requirements for v1.1)

## Current Milestone: v1.1 Reliability & Portfolio

**Goal:** Harden data pipeline with corporate actions handling and error recovery, add personal portfolio tracking with full P&L, and improve AI analysis quality — all visible across both dashboard and Telegram.

**Target features:**
- Corporate Actions — Handle splits, dividends, bonus shares, rights issues; adjust historical prices
- AI Improvements — Better prompts with structured output, more consistent/accurate recommendations
- Error Recovery — Auto-retry on failures, graceful degradation, dead-letter handling
- Portfolio Tracking — Manual trade entry (buy/sell), holdings view, position management
- Full P&L — Realized + unrealized gains, cost basis (FIFO), dividend income tracking
- Portfolio on Telegram — /portfolio command, daily P&L notifications, alerts on owned positions
- System Health Dashboard — Data freshness, last crawl status, error rates, job monitoring

### Out of Scope

- Tự động giao dịch (auto-trade) — rủi ro pháp lý và tài chính, chỉ gợi ý
- Mobile app — web responsive + Telegram bot đã cover
- Multi-user / authentication — chỉ một người dùng
- Dữ liệu sàn HNX/UPCOM — tập trung HOSE trước
- Nguồn dữ liệu trả phí — vnstock miễn phí là đủ
- ML price prediction — tạo false confidence, dùng Gemini qualitative analysis
- WebSocket real-time streaming — polling 5 phút đủ cho cá nhân
- Backtesting engine — phức tạp, là sản phẩm riêng

## Constraints

- **AI Model**: Google Gemini (gemini-2.0-flash) — 15 RPM free tier, 4s delay between batches
- **Database**: PostgreSQL trên Aiven — pool_size=5, max_overflow=3
- **Backend**: Python 3.12 + FastAPI + APScheduler (in-process, no Celery)
- **Frontend**: Next.js 16 + TypeScript + Tailwind CSS 4 + shadcn/ui
- **Bot**: python-telegram-bot 22.7 — long polling mode
- **Data Sources**: vnstock 3.5.1 (VCI source), CafeF AJAX scraping
- **Scope**: Dùng cá nhân — không cần auth phức tạp hay multi-tenancy

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| vnstock 3.5.1 as data backbone | De-facto VN stock library, wraps VNDirect/SSI | ✓ Good |
| Async-first monolith (FastAPI + APScheduler) | Single user, no need for Celery/Redis | ✓ Good |
| asyncio.to_thread() for vnstock calls | vnstock is sync, avoids blocking event loop | ✓ Good |
| `ta` library for indicators | Pure Python, no C deps, 12 indicators | ✓ Good |
| `google-genai` new SDK | Async support, structured Pydantic output | ✓ Good |
| PostgreSQL yearly partitioning | daily_prices scalability for 400 tickers × years | ✓ Good |
| Job chaining via EVENT_JOB_EXECUTED | Not cron — dependent jobs chain sequentially | ✓ Good |
| CafeF AJAX endpoint for news | Structured data, no JS rendering needed | ✓ Good |
| HTML parse_mode for Telegram | Avoids MarkdownV2 escaping complexity | ✓ Good |
| localStorage watchlist on frontend | Single user, no sync needed, faster UX | ⚠️ Revisit — dual watchlist with Telegram DB |
| Bot before Dashboard in build order | Telegram has higher personal utility | ✓ Good |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-16 — v1.1 milestone started*

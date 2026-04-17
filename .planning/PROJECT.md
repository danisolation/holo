# Holo — Stock Intelligence Platform

## What This Is

AI-powered stock intelligence platform for 400 HOSE tickers. Crawls daily OHLCV prices and financial data via vnstock, computes 12 technical indicators, then uses Google Gemini to produce multi-dimensional analysis (technical + fundamental + sentiment) with Vietnamese buy/sell/hold recommendations. Delivered via Telegram bot alerts and Next.js web dashboard with interactive candlestick charts. Personal use.

## Core Value

AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu HOSE real-time để gợi ý trading chính xác và kịp thời qua Telegram.

## Current State

**Shipped:** v1.0 (2026-04-15), v1.1 (2026-04-17)
**Code:** ~9,400+ LOC (Python + TypeScript)
**Tests:** 96+ backend unit tests
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
- ✓ ERR-01: Auto-retry failed AI analysis batches — v1.1
- ✓ ERR-02: Dead letter table for permanently failed items — v1.1
- ✓ ERR-03: Graceful degradation on partial failures — v1.1
- ✓ ERR-04: Job execution logging — v1.1
- ✓ ERR-05: Telegram notification on crawler failure — v1.1
- ✓ ERR-06: Circuit breaker for external APIs — v1.1
- ✓ ERR-07: Auto-retry failed jobs after delay — v1.1
- ✓ CORP-01: Adjusted historical prices for splits/dividends — v1.1
- ✓ CORP-02: Corporate event crawling from VCI — v1.1
- ✓ CORP-03: Cumulative adjustment factors — v1.1
- ✓ CORP-04: Daily corporate action check — v1.1
- ✓ CORP-05: Correct VN market formulas per event type — v1.1
- ✓ PORT-01: Manual buy/sell trade entry — v1.1
- ✓ PORT-02: Holdings view with P&L — v1.1
- ✓ PORT-03: FIFO cost basis — v1.1
- ✓ PORT-04: Realized P&L — v1.1
- ✓ PORT-05: Unrealized P&L — v1.1
- ✓ PORT-06: Portfolio summary — v1.1
- ✓ PORT-07: Trade history — v1.1
- ✓ AI-07: system_instruction persona separation — v1.1
- ✓ AI-08: Few-shot examples — v1.1
- ✓ AI-09: Scoring rubric with anchors — v1.1
- ✓ AI-10: Close price + SMA percentages in prompts — v1.1
- ✓ AI-11: Consistent language per analysis type — v1.1
- ✓ AI-12: Structured output retry — v1.1
- ✓ AI-13: Temperature tuning per type — v1.1
- ✓ HEALTH-01: Data freshness dashboard — v1.1
- ✓ HEALTH-02: Job status (green/yellow/red) — v1.1
- ✓ HEALTH-03: Error rate per job — v1.1
- ✓ HEALTH-04: DB connection pool status — v1.1
- ✓ HEALTH-05: Health page at /dashboard/health — v1.1
- ✓ HEALTH-06: Scheduler status with last run result — v1.1
- ✓ HEALTH-07: Manual job triggers from dashboard — v1.1
- ✓ TBOT-01: /buy command — v1.1
- ✓ TBOT-02: /sell command with realized P&L — v1.1
- ✓ TBOT-03: /portfolio command — v1.1
- ✓ TBOT-04: Daily portfolio P&L notification — v1.1
- ✓ TBOT-05: /pnl command — v1.1
- ✓ TBOT-06: Daily summary highlights owned tickers — v1.1

### Active

(Defining requirements for v2.0)

## Current Milestone: v2.0 Full Coverage & Real-Time

**Goal:** Expand from HOSE-only to multi-market (HNX/UPCOM), add real-time WebSocket price streaming, enhance portfolio with dividend tracking and CSV import, and add advanced system monitoring — completing all deferred v1.1 features.

**Target features:**
- Market Coverage — HNX/UPCOM crawling, exchange filter on dashboard
- Real-Time — WebSocket price updates, sub-minute polling during market hours
- Portfolio Enhancements — Dividend income tracking, performance chart, allocation pie chart, trade edit/delete, broker CSV import
- Health Enhancements — Gemini API usage tracker, pipeline execution timeline, Telegram health notifications
- Corporate Actions Enhancements — Rights issue tracking, ex-date Telegram alerts, event calendar view, adjusted/raw price toggle

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
*Last updated: 2026-04-17 — v2.0 milestone started*

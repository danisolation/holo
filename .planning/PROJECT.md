# Holo — Stock Intelligence Platform

## What This Is

AI-powered stock intelligence platform covering 800+ tickers across HOSE, HNX, and UPCOM exchanges. Crawls daily OHLCV prices and financial data via vnstock, computes 12 technical indicators, then uses Google Gemini to produce multi-dimensional analysis (technical + fundamental + sentiment) with Vietnamese buy/sell/hold recommendations. Delivered via real-time web dashboard with WebSocket price streaming and Telegram bot alerts. Tracks portfolio P&L, corporate actions, dividend income. Personal use.

## Core Value

AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua Telegram.

## Current State

**Shipped:** v1.0 (2026-04-15), v1.1 (2026-04-17), v2.0 (2026-04-17)
**Code:** ~15,600 LOC (8,200 Python + 7,400 TypeScript)
**Tests:** 395 backend unit tests
**Stack:** FastAPI + PostgreSQL + APScheduler + WebSocket + Google Gemini + python-telegram-bot + Next.js + lightweight-charts + Recharts

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
- ✓ ERR-01 through ERR-07: Resilience foundation — v1.1
- ✓ CORP-01 through CORP-05: Corporate actions — v1.1
- ✓ PORT-01 through PORT-07: Portfolio core — v1.1
- ✓ AI-07 through AI-13: AI prompt improvements — v1.1
- ✓ HEALTH-01 through HEALTH-07: System health dashboard — v1.1
- ✓ TBOT-01 through TBOT-06: Telegram portfolio — v1.1
- ✓ MKT-01 through MKT-04: Multi-market (HOSE/HNX/UPCOM) — v2.0
- ✓ PORT-08 through PORT-12: Portfolio enhancements (dividends, charts, CSV) — v2.0
- ✓ CORP-06 through CORP-09: Corporate actions enhancements — v2.0
- ✓ HEALTH-08 through HEALTH-10: Health monitoring enhancements — v2.0
- ✓ RT-01 through RT-03: Real-time WebSocket — v2.0

### Active

(Defining requirements for v3.0)

## Current Milestone: v3.0 Smart Trading Signals

**Goal:** Nâng cấp hệ thống gợi ý từ mua/bán/giữ đơn giản thành full trading plan với dual-direction analysis (LONG + SHORT), entry/exit/stop-loss targets, risk/reward ratio, position sizing, và timeframe recommendations — hiển thị trên dashboard.

**Target features:**
- Dual-direction analysis — phân tích cả LONG và SHORT cho mỗi mã, gợi ý direction tốt nhất
- Full trading plan — entry price, stop-loss, take-profit targets cụ thể
- Risk/reward ratio + position sizing gợi ý
- Timeframe recommendation (scalp/swing/position)
- Dashboard Trading Plan panel trên ticker detail page
- Gemini prompt restructure cho structured trading plan output

### Out of Scope

- Tự động giao dịch (auto-trade) — rủi ro pháp lý và tài chính, chỉ gợi ý
- Mobile app — web responsive + Telegram bot đã cover
- Multi-user / authentication — chỉ một người dùng
- Nguồn dữ liệu trả phí — vnstock miễn phí là đủ
- ML price prediction — tạo false confidence, dùng Gemini qualitative analysis
- Backtesting engine — phức tạp, là sản phẩm riêng
- Grafana/Prometheus — overkill for single-user, use built-in health page
- True exchange WebSocket — no free VN market feed; 30s polling sufficient

## Constraints

- **AI Model**: Google Gemini (gemini-2.5-flash-lite) — 15 RPM free tier, 4s delay between batches
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
| localStorage watchlist on frontend | Single user, no sync needed, faster UX | ⚠️ Revisit |
| HNX/UPCOM top 200 by market cap | Manageable scope, covers most liquid tickers | ✓ Good |
| 30s VCI polling for real-time | No free WebSocket, 30s latency acceptable | ✓ Good |
| In-memory price cache for WebSocket | Single-user, no persistence needed for RT data | ✓ Good |
| GeminiUsage table for API tracking | Per-call granularity enables breakdown analytics | ✓ Good |

---
*Last updated: 2026-04-20 — v3.0 milestone started*
# Holo — Stock Intelligence Platform

## What This Is

AI-powered stock intelligence platform covering 800+ tickers across HOSE, HNX, and UPCOM exchanges. Crawls daily OHLCV prices and financial data via vnstock, computes 27 technical indicators (including ATR, ADX, Stochastic, pivot points, Fibonacci), then uses Google Gemini to produce multi-dimensional analysis (technical + fundamental + sentiment) with dual-direction trading plans (LONG + BEARISH) featuring concrete entry/SL/TP targets, risk/reward ratios, and position sizing. Delivered via real-time web dashboard with WebSocket price streaming, interactive chart overlays, and Telegram bot alerts. Tracks portfolio P&L, corporate actions, dividend income. Personal use.

## Core Value

AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua Telegram.

## Current State

**Shipped:** v1.0 (2026-04-15), v1.1 (2026-04-17), v2.0 (2026-04-17), v3.0 (2026-04-20), v4.0 (2025-07-20)
**Code:** ~30,000+ LOC (Python + TypeScript)
**Tests:** 560 backend unit tests
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
- ✓ SIG-01 through SIG-05: Signal foundation (ATR, ADX, Stochastic, S/R, Fibonacci) — v3.0
- ✓ PLAN-01 through PLAN-06: AI trading plan (dual-direction, entry/SL/TP, R:R, timeframe, sizing) — v3.0
- ✓ DISP-01: Trading Plan dashboard panel — v3.0
- ✓ DISP-02: Chart price line overlays — v3.0
- ✓ PT-01 through PT-09: Paper trading engine (auto-track, state machine, P&L, manual follow) — v4.0
- ✓ AN-01 through AN-09: Core analytics (win rate, equity curve, drawdown, R:R, sector) — v4.0
- ✓ UI-01 through UI-08: Analytics dashboard (calendar heatmap, streaks, periodic tables, settings) — v4.0

### Active

(No active milestone — run `/gsd-new-milestone` to start next)

## Previous Milestone: v4.0 Paper Trading & Signal Verification (SHIPPED)

**Delivered:** Paper trading simulation system — auto-tracks AI signals as virtual trades, monitors positions daily for TP/SL/timeout, full analytics dashboard with equity curve, calendar heatmap, streak tracking, sector analysis, and manual follow capability. 26/26 requirements complete.

## Previous Milestone: v3.0 Smart Trading Signals (SHIPPED)

**Delivered:** Dual-direction trading plans (LONG + BEARISH) with entry/SL/TP targets, R:R ratio, position sizing, timeframe — displayed on ticker dashboard panel with chart overlay price lines.

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
| BEARISH framing (not SHORT) | VN retail cannot short sell — reframe as bearish outlook | ✓ Good |
| 3-level nested Pydantic for trading signals | google-genai structured output handles nested schemas | ✓ Good |
| Post-validation: entry ±5%, SL ≤3×ATR, TP ≤5×ATR | Prevents Gemini hallucinated prices; invalid → score=0 | ✓ Good |
| Batch size 15 for trading signals | 5x larger output per ticker vs other analysis types | ✓ Good |
| Series-level createPriceLine() | lightweight-charts v5 native API, auto-cleanup on chart destroy | ✓ Good |

---

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
*Last updated: 2026-04-20 — v4.0 milestone started*
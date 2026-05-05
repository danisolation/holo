# Holo — Stock Intelligence Platform

## What This Is

AI-powered stock intelligence platform covering 800+ tickers across HOSE, HNX, and UPCOM exchanges. Crawls daily OHLCV prices and financial data via vnstock, computes 27 technical indicators (including ATR, ADX, Stochastic, pivot points, Fibonacci), then uses Google Gemini to produce multi-dimensional analysis (technical + fundamental + sentiment) with dual-direction trading plans (LONG + BEARISH) featuring concrete entry/SL/TP targets, risk/reward ratios, and position sizing. Delivered via real-time web dashboard with WebSocket price streaming, interactive chart overlays, and news integration. Personal use.

## Core Value

AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua Telegram.

## Current State

**Shipped:** v1.0 (2026-04-15), v1.1 (2026-04-17), v2.0 (2026-04-17), v3.0 (2026-04-20), v4.0 (2025-07-20), v9.0 (2026-05-04), v10.0 (2026-05-05), v11.0 (2026-05-05), v12.0 (2026-05-05)
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
- ✓ DISC-01, DISC-02: Discovery engine scoring ~400 HOSE tickers daily — v10.0
- ✓ WL-01, WL-02: Watchlist-gated AI pipeline — v10.0
- ✓ TAG-01, TAG-02, TAG-03: Sector grouping & heatmap rework — v10.0
- ✓ DPAGE-01, DPAGE-02, DPAGE-03: Discovery frontend with filters & add-to-watchlist — v10.0
- ✓ PERF-01 through PERF-04: API performance & keep-alive — v11.0
- ✓ SRCH-01, SRCH-02: Search fix & recent searches — v11.0
- ✓ AI-14 through AI-16: Morning AI refresh chain & freshness indicator — v11.0
- ✓ UX-09 through UX-11: VN30 preset, empty states, nav descriptions — v11.0

- ✓ RUMOR-01 through RUMOR-11: Rumor intelligence (Fireant crawler, AI scoring, dashboard display, scheduler) — v12.0

### Active

(No active milestone — ready for v13.0)

## Previous Milestone: v12.0 Rumor Intelligence (SHIPPED)

**Delivered:** Fireant.vn community post crawler with engagement metrics, F319.com RSS feed crawler, CafeF news integration into scoring, Gemini AI credibility/impact scoring with Vietnamese prompts, batch scoring optimization (6 tickers/call), RumorScorePanel on ticker page, watchlist rumor badges, scheduler chain integration. 4 phases, 7 plans. Watchlist expanded to 30 VN30 tickers.

## Previous Milestone: v11.0 UX & Reliability Overhaul (SHIPPED)

**Delivered:** API performance from ~3 min to <3s (date-bounded query + composite index + TTL cache), keep-alive documentation, search fix for all ~400 HOSE tickers (removed .slice truncation), recent searches with localStorage, morning AI refresh chain (8:30 AM CronTrigger, shortened 4-step chain), freshness badges in watchlist, VN30 preset for new users, empty state guidance on 3 pages, navigation descriptions/tooltips. 4 phases, 6 plans.

## Previous Milestone: v10.0 Watchlist-Centric & Stock Discovery (SHIPPED)

**Delivered:** Discovery engine scores ~400 HOSE tickers daily on 6 dimensions (RSI, MACD, ADX, volume, P/E, ROE), AI pipeline gated to watchlist only (~70% Gemini API reduction), sector grouping with ICB auto-suggest, watchlist-only heatmap, Discovery page with scored tickers + filters + one-click add-to-watchlist. 4 phases, 7 plans.

## Previous Milestone: v9.0 UX Rework & Simplification (SHIPPED)

**Delivered:** Removed corporate events & HNX/UPCOM (HOSE-only pipeline), simplified navigation (5 items), watchlist migrated localStorage→PostgreSQL, Coach page tab-based layout with one-click trade recording, AI analysis structured sections with visual hierarchy. 4 phases, 8 plans.

## Previous Milestone: v8.0 AI Trading Coach (SHIPPED)

**Delivered:** Daily Picks (AI chọn 3-5 mã/ngày), Trade Journal (ghi lệnh mua/bán + P&L), Behavior Tracking (thói quen xem/giao dịch), Adaptive Strategy (điều chỉnh gợi ý theo kết quả), Goals & Weekly Reviews (mục tiêu + AI review hàng tuần). 5 phases, 14 plans.

## Previous Milestone: v7.0 Consolidation & Quality Upgrade (SHIPPED)

**Delivered:** Audit toàn diện — xóa dead features (price_alerts, unused columns, DilutionBadge), consolidate duplicates (analytics, trade tables, charts, format utils), refactor AIAnalysisService & BacktestEngine into modular packages, AI anti-hallucination validation, WebSocket off-hours guard, chart lazy-loading. Post-milestone: removed backtest, portfolio, paper trading, and Telegram bot features; added news endpoint, pagination, GZip, error states.

## Previous Milestone: v6.0 AI Backtesting Engine (SHIPPED)

**Delivered:** Backtest engine duyệt phiên lịch sử, gọi Gemini AI, mô phỏng lệnh ảo với position sizing/SL/TP/timeout, benchmark equity curve vs VN-Index, dashboard riêng /backtest với equity chart, drawdown, win rate, checkpoint/resume. 3 phases, 7 plans.

## Previous Milestone: v5.0 E2E Testing & Quality Assurance (SHIPPED)

**Delivered:** 119 Playwright E2E tests covering all 8 routes, 22 API endpoints, user interactions, visual regression, and 8 critical user flows. All tests pass in 1.5 minutes.

## Previous Milestone: v4.0 Paper Trading & Signal Verification (SHIPPED)

**Delivered:** Paper trading simulation system — auto-tracks AI signals as virtual trades, monitors positions daily for TP/SL/timeout, full analytics dashboard with equity curve, calendar heatmap, streak tracking, sector analysis, and manual follow capability. 26/26 requirements complete.

## Previous Milestone: v3.0 Smart Trading Signals (SHIPPED)

**Delivered:** Dual-direction trading plans (LONG + BEARISH) with entry/SL/TP targets, R:R ratio, position sizing, timeframe — displayed on ticker dashboard panel with chart overlay price lines.

### Out of Scope

- Tự động giao dịch (auto-trade) — rủi ro pháp lý và tài chính, chỉ gợi ý
- Mobile app — web responsive đã cover
- Multi-user / authentication — chỉ một người dùng
- Nguồn dữ liệu trả phí — vnstock miễn phí là đủ
- ML price prediction — tạo false confidence, dùng Gemini qualitative analysis
- Grafana/Prometheus — overkill for single-user, use built-in health page
- True exchange WebSocket — no free VN market feed; 30s polling sufficient
- Telegram bot — removed v7.0 post-milestone, web dashboard is primary channel
- Portfolio/Paper trading/Backtest — removed v7.0 post-milestone, replaced by Trade Journal in v8.0

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
*Last updated: 2026-05-05 after starting v12.0 milestone*
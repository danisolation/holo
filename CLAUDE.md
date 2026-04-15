<!-- GSD:project-start source:PROJECT.md -->
## Project

**Holo — Stock Intelligence Platform**

Ứng dụng crawl dữ liệu chứng khoán sàn HOSE cho 400 mã nổi bật nhất, kết hợp AI (Google Gemini) để phân tích kỹ thuật, cơ bản và sentiment — đưa ra gợi ý trading qua web dashboard và Telegram bot. Dành cho sử dụng cá nhân.

**Core Value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu HOSE real-time để gợi ý trading chính xác và kịp thời qua Telegram.

### Constraints

- **AI Model**: Google Gemini — người dùng đã có API key
- **Database**: PostgreSQL trên Aiven — đã có connection URL
- **Backend**: Python (FastAPI) — mạnh cho data processing & AI
- **Frontend**: React / Next.js — dashboard interactivity
- **Bot**: Telegram Bot API — kênh thông báo chính
- **Data Sources**: Chỉ nguồn miễn phí (VNDirect API, SSI API, CafeF)
- **Scope**: Dùng cá nhân — không cần auth phức tạp hay multi-tenancy
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Vietnam Stock Market Data Layer
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **vnstock** | 3.5.1 | Primary data source for HOSE OHLCV, financials, company info | The de-facto Python library for VN stock data. Wraps VNDirect & SSI APIs into a clean interface. Actively maintained (jumped from 0.x→3.x). Already depends on pandas, pydantic, beautifulsoup4. Eliminates need to reverse-engineer VNDirect/SSI endpoints yourself. | HIGH |
| **httpx** | 0.28.1 | HTTP client for CafeF scraping & custom API calls | Modern async-first HTTP client. Drop-in replacement for `requests` but with native `async/await`. Essential for CafeF news scraping that vnstock doesn't cover. | HIGH |
| **beautifulsoup4** | 4.14.3 | HTML parsing for CafeF news/events scraping | Industry standard for web scraping. vnstock already depends on it, so zero extra weight. Use with `lxml` parser for speed. | HIGH |
#### Data Source Strategy
### Core Framework (Backend)
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Python** | 3.12 | Runtime | Already installed on system. Mature async support, excellent data science ecosystem. 3.12 has significant performance improvements over 3.11. | HIGH |
| **FastAPI** | ~0.135 | Web framework & API server | Async-first, auto-generates OpenAPI docs, native Pydantic integration. Perfect for financial data APIs where type safety matters. | HIGH |
| **uvicorn** | ~0.44 | ASGI server | Standard FastAPI deployment server. Use `uvicorn[standard]` for better performance (includes uvloop on Linux, httptools). | HIGH |
| **Pydantic** | ~2.13 | Data validation & serialization | FastAPI's built-in validation layer. Use for all API models, config, and data schemas. v2 is 5-50x faster than v1. | HIGH |
| **pydantic-settings** | ~2.13 | Configuration management | Reads from .env files + environment variables. Type-safe config with validation. Better than raw python-dotenv. | HIGH |
### Database
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **PostgreSQL** (Aiven) | — | Primary data store | Already provisioned. Managed service = zero ops. PostgreSQL excels at time-series financial data with proper indexing. | HIGH |
| **SQLAlchemy** | ~2.0 | ORM & query builder | Industry standard Python ORM. v2.0 has native async support, modern type annotations, and excellent PostgreSQL dialect. | HIGH |
| **asyncpg** | ~0.31 | Async PostgreSQL driver | Fastest Python PostgreSQL driver. Required for SQLAlchemy async engine. 3-5x faster than psycopg2 for async workloads. | HIGH |
| **Alembic** | ~1.18 | Database migrations | SQLAlchemy's official migration tool. Auto-generates migrations from model changes. Non-negotiable for schema evolution. | HIGH |
### AI / LLM Integration
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **google-genai** | ~1.73 | Google Gemini API SDK | **The NEW unified SDK** — replaces the legacy `google-generativeai` package. Actively maintained with weekly releases (1.0→1.73 in ~6 months). Supports Gemini 2.0+, structured output, function calling, system instructions. | HIGH |
#### Gemini Integration Pattern
# Structured output for trading signals
### Technical Analysis
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **ta** | 0.11.0 | Technical indicators (RSI, MACD, Bollinger, MA, etc.) | Pure Python — zero C dependencies, zero install issues. Covers ALL standard indicators: 40+ indicators across momentum, volume, volatility, trend. Works directly with pandas DataFrames. | HIGH |
| **pandas** | ~2.2 | Data manipulation & analysis | Core data processing. Pin to 2.2.x (not 3.0) — pandas 3.0 has breaking changes and vnstock may not be fully compatible yet. | HIGH |
| **numpy** | ~2.1 | Numerical computing | Pandas dependency. Pin to 2.1.x for stability with pandas 2.2.x. | HIGH |
### Scheduling & Background Tasks
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **APScheduler** | 3.11.2 | Job scheduling (daily crawls, market-hours polling) | Embeds directly into FastAPI process — no external broker needed. Supports cron-like schedules, interval jobs, and one-off jobs. Perfect for single-user app. | HIGH |
#### Scheduling Strategy
# Market hours: 9:00-11:30 & 13:00-14:45 (UTC+7)
# Daily EOD crawl: after market close
# Weekly fundamental data refresh
### Telegram Bot
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **python-telegram-bot** | 22.7 | Telegram bot for trading alerts | Largest community, best documentation, mature v20+ async rewrite. Handles message formatting, inline keyboards, and command handling. For an alert bot (not a complex conversational bot), this is the simpler choice. | HIGH |
### Frontend Framework
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **Next.js** | ~15.x | React framework for dashboard | App Router, server components, API routes. v15.x is the battle-tested stable line. v16 exists (16.2.3) but is very new — prefer 15.x for stability in a personal project. | HIGH |
| **TypeScript** | ~5.7 | Type safety | Non-negotiable for any frontend project. Pin to 5.7.x — TS 6.0 is brand new and ecosystem (Next.js, libraries) may not fully support it yet. | MEDIUM |
| **Tailwind CSS** | ~4.x | Utility-first CSS | v4 is the latest with significant performance and DX improvements. shadcn/ui v4 supports it. | HIGH |
| **Node.js** | 22.x | Runtime | LTS version already installed on system (v22.17.0). | HIGH |
### Frontend Charting & UI
| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| **lightweight-charts** | 5.1.0 | Candlestick/OHLCV financial charts | **TradingView's own open-source library.** Purpose-built for financial charts: candlesticks, line, area, histogram. 60fps canvas rendering. Zero dependencies. This IS the standard for financial chart UIs. | HIGH |
| **shadcn/ui** | 4.x | UI component library | Copy-paste components (not a dependency). Full control. Built on Radix primitives + Tailwind. Dashboard tables, cards, buttons, dialogs — all covered. | HIGH |
| **@tanstack/react-query** | ~5.x | Server state management / data fetching | Auto-caching, background refetching, stale-while-revalidate. Perfect for frequently-updating stock data. Replaces manual fetch + useState patterns. | HIGH |
| **@tanstack/react-table** | ~8.x | Data tables for stock listings, watchlists | Headless table with sorting, filtering, pagination. Renders 400 tickers efficiently. | HIGH |
| **Recharts** | ~3.x | Non-financial charts (portfolio stats, P&L distribution) | For bar charts, pie charts, area charts that aren't candlestick data. Simpler API than D3. | HIGH |
| **zustand** | ~5.x | Client state management | Minimal boilerplate. Stores watchlist state, UI preferences, filter state. Much simpler than Redux for a personal app. | HIGH |
| **lucide-react** | ~1.x | Icons | shadcn/ui's default icon library. Consistent with the component system. | HIGH |
| **date-fns** | ~4.x | Date manipulation | Lightweight, tree-shakeable. Essential for formatting VN market times, chart axis labels. | HIGH |
| **clsx** + **class-variance-authority** | ~2.1 / ~0.7 | Conditional CSS classes | Required by shadcn/ui. Tiny utilities for composing Tailwind classes. | HIGH |
| **next-themes** | ~0.4 | Dark/light mode toggle | SSR-safe theme switching. Works with Tailwind's dark mode. | HIGH |
### Supporting Libraries (Backend)
| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| **loguru** | 0.7.3 | Structured logging | Always. Drop-in replacement for stdlib logging with zero config. Color output, file rotation, structured JSON logs. | HIGH |
| **tenacity** | 9.1.4 | Retry logic with backoff | Every HTTP call to external APIs. vnstock already depends on it. Use for CafeF scraping, Gemini API calls. | HIGH |
| **python-dotenv** | 1.2.2 | .env file loading | Development only. pydantic-settings handles this in production, but dotenv is useful for quick scripts. | HIGH |
| **websockets** | 16.0 | WebSocket client/server | If implementing real-time price push to dashboard during market hours. Optional — polling with React Query may be sufficient for personal use. | MEDIUM |
| **orjson** | latest | Fast JSON serialization | Optional performance optimization. 3-10x faster than stdlib json. FastAPI can use it as response class. | MEDIUM |
## Alternatives Considered
| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| VN Data | vnstock 3.5.1 | vnquant 0.1.23 | Only 2 releases ever. Barely maintained. vnstock is far more comprehensive. |
| VN Data | vnstock 3.5.1 | ssi-fc-data 2.2.2 | SSI-only, narrow scope. vnstock already wraps SSI + VNDirect + more. |
| VN Data | vnstock 3.5.1 | Direct API reverse-engineering | Fragile, undocumented APIs that change. vnstock maintainers handle breakage. |
| AI SDK | google-genai 1.73 | google-generativeai 0.8.6 | Legacy SDK being phased out. New SDK is the official path forward. |
| AI SDK | google-genai | LangChain | Massive overkill for single-model usage. Adds abstraction layers with no benefit when you're only using Gemini. |
| Tech Analysis | ta 0.11.0 | ta-lib 0.6.8 | Requires C library install. Nightmare on Windows. `ta` covers same indicators in pure Python. |
| Tech Analysis | ta 0.11.0 | pandas-ta | **Removed from PyPI.** Cannot be installed. Dead project. |
| Scheduler | APScheduler 3.11 | Celery 5.6 | Requires Redis/RabbitMQ broker + worker process. Overkill for single-user cron-like scheduling. |
| Scheduler | APScheduler 3.11 | Built-in asyncio.create_task | No persistence, no cron expressions, no job management. APScheduler handles all of this. |
| Telegram | python-telegram-bot 22.7 | aiogram 3.27 | More complex (middleware, FSM, routers). Overkill for an alert bot. Fine for complex conversational bots. |
| HTTP Client | httpx 0.28 | requests 2.33 | No native async support. FastAPI is async-first; mixing sync HTTP calls blocks the event loop. |
| HTTP Client | httpx 0.28 | aiohttp 3.13 | Works, but httpx has cleaner API, better typing, and is the modern standard. |
| Frontend Charts | lightweight-charts 5.1 | recharts | Recharts can't do candlestick charts properly. lightweight-charts is built for financial data. |
| Frontend Charts | lightweight-charts 5.1 | @tradingview/charting_library | Commercial TradingView library. Requires paid license. lightweight-charts is the free OSS version. |
| Frontend Charts | lightweight-charts 5.1 | D3.js | Low-level SVG charting. Huge effort to build candlestick charts from scratch. |
| State Mgmt | zustand 5 | Redux Toolkit | Massive boilerplate for a personal dashboard. zustand achieves the same with 90% less code. |
| State Mgmt | zustand 5 | Jotai | Fine alternative, but zustand's store pattern is more intuitive for app-wide state like watchlists. |
| DB Driver | asyncpg 0.31 | psycopg2 | Sync-only. Blocks FastAPI's async event loop. asyncpg is purpose-built for async PostgreSQL. |
| Pandas | pandas ~2.2 | polars | Polars is faster but vnstock outputs pandas DataFrames. Converting between the two adds friction for no real gain at 400 tickers. |
## Version Pinning Strategy
# requirements.txt (backend)
## Installation
### Backend
# Create virtual environment
# Core
# AI & Analysis
# Bot & Scheduling
# HTTP & Scraping
# Data
# Utilities
# Optional
### Frontend
# Initialize Next.js project
# UI Components
# Charting
# Data fetching & state
# Charts (non-financial)
# Utilities
## Project Structure (Recommended)
## Key Integration Notes
### vnstock Usage Pattern
# OHLCV historical data
# Financial statements
# Company info
# List all HOSE tickers
### FastAPI + APScheduler Integration
### PostgreSQL Connection (Aiven + asyncpg)
# Aiven PostgreSQL URL: postgresql+asyncpg://user:pass@host:port/db?ssl=require
## Runtime Requirements
| Requirement | Status | Notes |
|-------------|--------|-------|
| Python 3.12 | ✅ Installed | System has 3.12.7 |
| Node.js 22.x | ✅ Installed | System has 22.17.0 |
| PostgreSQL (Aiven) | ✅ Provisioned | Connection URL available |
| Gemini API Key | ✅ Available | User has key |
| Telegram Bot Token | ⚠️ Need to create | Via @BotFather on Telegram |
| No Redis needed | ✅ | APScheduler doesn't require external broker |
| No Docker needed | ✅ | Can run natively on Windows for personal use |
## Sources & Verification
| Claim | Source | Confidence |
|-------|--------|------------|
| vnstock 3.5.1 is latest | `pip index versions vnstock` — verified 2025-07-17 | HIGH |
| google-genai replaces google-generativeai | Package naming + rapid release cadence (0.1→1.73 = new primary SDK) | HIGH |
| pandas-ta removed from PyPI | `pip index versions pandas-ta` → ERROR: No matching distribution | HIGH |
| APScheduler v4 never released | `pip index versions apscheduler` → only 3.x versions exist on PyPI | HIGH |
| ta-lib requires C dependency | Training data + known community issue. Pure `ta` avoids this. | HIGH |
| lightweight-charts is TradingView OSS | npm description: "Performant financial charts built with HTML5 canvas" | HIGH |
| All version numbers | Verified via `pip index versions` and `npm view X version` | HIGH |
| vnstock vnai telemetry concern | Observed in `pip install --dry-run` dependency: `vnai>=2.4.3` | MEDIUM |
| pandas 3.0 compatibility risk with vnstock | Inferred: vnstock built against pandas 2.x, 3.0 has breaking changes | MEDIUM |
| TypeScript 6.0 ecosystem readiness | TS 6.0.2 on npm but very new — ecosystem may lag | LOW |
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->

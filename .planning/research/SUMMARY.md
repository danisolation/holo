# Project Research Summary

**Project:** Holo — Stock Intelligence Platform (v4.0 Paper Trading & Signal Verification)
**Domain:** Paper trading simulation + AI signal quality analytics (Vietnamese stock market)
**Researched:** 2026-04-21
**Confidence:** HIGH

## Executive Summary

Holo v4.0 adds a **paper trading engine** that automatically converts every AI trading signal into a trackable virtual trade, then monitors daily prices to detect TP/SL hits and compute analytics that answer the core question: *"Are Holo's AI signals actually profitable?"* This is fundamentally a **verification system**, not a generic trading simulator — the distinction drives every design decision. The recommended approach is a lightweight domain-logic layer built entirely on the existing stack (SQLAlchemy + APScheduler + FastAPI + Recharts), requiring **zero new Python packages** and only **one new frontend package** (`react-activity-calendar@^3.2.0` for the calendar heatmap). The paper trading engine follows the exact same scheduler-chaining and service-layer patterns already proven across 10+ jobs and 12+ models in the codebase.

The architecture adds one new model (PaperTrade), one config table (SimulationConfig), one service (PaperTradingService), one API router, and two scheduler jobs that inject into the existing pipeline at two points: after trading signal generation (auto-track) and after daily price crawl (position monitor). No existing code is structurally modified. The single-table PaperTrade model with an explicit state machine (PENDING → ACTIVE → PARTIAL_TP → CLOSED) handles the full trade lifecycle including the critical partial TP logic (50% at TP1, move SL to breakeven, 50% at TP2). Analytics are computed on-demand via SQL aggregates — no pre-materialized tables needed for a single-user app with at most ~100K trades after a year.

The highest-risk areas are **P&L calculation accuracy** and **VN market-specific edge cases**. Daily-only OHLCV data creates fill-price ambiguity when both SL and TP breach in the same bar — the mandatory mitigation is a conservative fill rule (SL always wins on ambiguous bars). Gap-through fills must use the open price, not the target price. Entry timing must use next-day open (not signal-day close) to avoid lookahead bias. Position timeouts must count trading days, not calendar days, due to Vietnamese holidays. These pitfalls are well-understood with clear prevention strategies, but each requires disciplined implementation — they're the kind of subtle bugs that silently corrupt analytics without obvious symptoms.

## Key Findings

### Recommended Stack

The stack delta for v4.0 is remarkably small: one npm package and zero pip packages. Paper trading is a domain logic problem, not a library problem.

**Core technologies (all existing):**
- **SQLAlchemy 2.0** — PaperTrade + SimulationConfig models with Mapped[] pattern matching all 12 existing models
- **APScheduler 3.11** — Two new chained jobs (auto-track after signals, position monitor after price crawl) using proven EVENT_JOB_EXECUTED pattern
- **FastAPI + Pydantic** — New `/api/paper-trading` router with CRUD + analytics endpoints, identical to existing portfolio pattern
- **Recharts 3.8.1** — All analytics charts (equity curve, P&L bars, drawdown, sector breakdown, AI score correlation) — every chart type already used in the codebase
- **@tanstack/react-table 8.21** — Paper trade history table, same pattern as existing trade-history.tsx
- **python-telegram-bot 22.7** — TP/SL/timeout notifications via existing send_message() pattern

**One new dependency:**
- **react-activity-calendar ^3.2.0** — GitHub-style calendar heatmap for daily P&L visualization. React 19 compatible, uses date-fns ^4 (already installed), ~15KB. Only actively maintained option.

**Explicitly rejected:** numpy/pandas for analytics (overkill for basic arithmetic), backtrader/zipline (backtesting frameworks — wrong tool), second charting library (Recharts covers everything), redis (single-user — PostgreSQL is sufficient), WebSocket for real-time monitoring (daily check sufficient for swing/position trades).

### Expected Features

**Must have (table stakes):**
- Auto-track all valid AI signals as virtual trades — the backbone of the verification system
- Virtual trade lifecycle with state machine: PENDING → ACTIVE → PARTIAL_TP → CLOSED
- Partial TP logic: 50% close at TP1, move SL to breakeven, remaining 50% targets TP2
- Timeout: auto-close after 15 trading days (swing) / 45 trading days (position)
- Daily TP/SL check job chained after price crawl (SL-first priority on ambiguous bars)
- Configurable virtual capital (default 100M VND), round positions to 100-share lots
- Overall win rate, total P&L, win rate by direction (LONG vs BEARISH)
- AI score correlation: do high-confidence signals outperform low-confidence? (The unique value proposition)
- Equity curve + max drawdown
- Telegram notifications on TP/SL/timeout hits

**Should have (differentiators):**
- Sector analysis (win rate by sector — identifies AI blind spots)
- Manual "follow signal" paper trade with customizable entry/SL/TP
- Calendar heatmap (daily P&L visualization, temporal pattern recognition)
- Streak tracking (consecutive wins/losses with visual warnings)
- Timeframe analysis (swing vs position signal accuracy)
- Signal outcome history on ticker detail page
- Monthly/weekly performance summary
- Profit factor, expected value per trade
- R-multiple normalization for equity curve (signal quality independent of position sizing)

**Defer (v2+) — explicit anti-features:**
- Slippage/commission simulation (false precision for verification purpose, VN fees ~0.2% are noise vs 3-10% TP/SL)
- Limit/market order types (requires tick data we don't have)
- Short selling simulation (VN retail can't short — creates unrealizable expectations)
- Real-time WebSocket paper trade updates (daily check sufficient for swing/position timeframes)
- Historical backtesting (out of scope, requires bias handling that's a separate product)
- Multiple virtual accounts (single user, single AI model)

### Architecture Approach

The paper trading system is a **parallel subsystem** that hooks into two existing pipeline stages without modifying their structure. It adds two scheduler jobs, one service, one API router, and two database tables. The design philosophy prioritizes simplicity: single PaperTrade table with state machine (no separate PaperPosition table), on-demand analytics via SQL aggregates (no pre-computed rollups), daily-only position monitoring (no real-time), and single-user assumptions throughout.

**Major components:**
1. **PaperTrade model** — Single table covering full trade lifecycle with denormalized ai_confidence, ai_score, sector for fast analytics queries
2. **SimulationConfig model** — Single-row config for virtual capital, auto-track settings, partial TP toggle
3. **PaperTradingService** — All business logic: create, monitor, close, analytics computation. Never-raise pattern for scheduler jobs.
4. **Auto-track scheduler job** — Chained after trading_signal job: creates PaperTrades from valid signals (score > 0, deduped by ai_analysis_id)
5. **Position monitor scheduler job** — Chained after price_crawl: checks all open positions against today's OHLCV, executes state transitions
6. **Paper Trading API** — REST endpoints under `/api/paper-trading/` for trades, config, analytics, positions
7. **Frontend dashboard** — `/dashboard/paper-trading` with tabs: Overview, Active, History, Analytics, Config
8. **Telegram integration** — `/paper` and `/paper_status` commands + auto-notifications on trade events

### Critical Pitfalls

1. **SL/TP fill price ambiguity with daily data** — When both SL and TP breach in the same candle, always assume SL hit first (conservative/pessimistic bias). Record fill type as `ambiguous_bar` for analytics filtering. This is THE most important implementation detail — getting it wrong silently corrupts all analytics.

2. **Partial TP state machine explosion** — States multiply when combined with timeouts, gap-throughs, and ambiguous bars. Prevention: explicit enum for every state, immutable trade legs for P&L calculation, unit test every state transition path (minimum 8-10 test cases).

3. **Invalid signals creating ghost paper trades** — Auto-tracking must filter `score > 0 AND signal != 'invalid'`. Add unique constraint on `(ai_analysis_id)` for deduplication on job retry.

4. **Gap-through fills at wrong price** — Check open price BEFORE checking H/L. If open already breaches SL/TP, fill at open price. VN market has ±7% HOSE / ±10% HNX / ±15% UPCOM daily limits, so gaps are bounded but common.

5. **Lookahead bias in entry timing** — Signal generated after market close on day D must enter at day D+1 open, NOT day D close. Using signal-day close as entry systematically inflates returns. Also handle PENDING state for signals where entry hasn't been reached yet.

6. **Connection pool exhaustion** — Position monitor must batch-load ALL positions + ALL prices in 2 queries, process in-memory, batch-update in one transaction. NO per-position queries (N+1). Aiven pool is only 5+3.

7. **Trading-day vs calendar-day timeouts** — Count distinct trading dates from `daily_prices`, not `timedelta(days=N)`. Vietnamese holidays create 4-5 day non-trading stretches that would cause premature timeouts.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Data Foundation & Trade Engine
**Rationale:** Everything depends on the PaperTrade model and core P&L logic. The state machine must be correct before any data flows through it. This is the highest-risk phase because subtle P&L bugs propagate silently through all analytics.
**Delivers:** Database tables (paper_trades, simulation_config), PaperTrade model with full state machine, PaperTradingService core (create, close, calculate_pnl), Alembic migration.
**Addresses:** PT-01 data model, partial TP logic, P&L calculation with VN-specific fees
**Avoids:** Pitfall 2 (state machine explosion — solved by explicit enum + unit tests), Pitfall 7 (VN P&L errors — solved by configurable fee structure + Decimal everywhere), Pitfall 9 (conflating paper/real trades — solved by separate tables from day 1)

### Phase 2: Scheduler Jobs & Position Monitoring
**Rationale:** The auto-track and position monitor jobs are the heartbeat of the system. They must be correct and resilient before any frontend or analytics work begins. Depends on Phase 1 models being stable.
**Delivers:** Auto-track job (signal → PaperTrade), position monitor job (daily TP/SL/timeout check), entry fill logic, gap-through handling, conservative SL-first fill rule, never-raise error handling.
**Addresses:** PT-02 auto-track, PT-03 daily TP/SL check, entry fill, timeout logic
**Avoids:** Pitfall 1 (ambiguous bar — SL-first rule), Pitfall 3 (ghost trades — score > 0 filter + dedup), Pitfall 4 (gap fills — open price check first), Pitfall 5 (lookahead — next-day open entry), Pitfall 8 (calendar vs trading days), Pitfall 10 (pool exhaustion — batch queries), Pitfall 13 (stale positions — track last_checked_date), Pitfall 14 (duplicate trades — unique constraint + idempotency)

### Phase 3: API & Core Analytics
**Rationale:** After ~2 weeks of Phase 2 running, there's enough closed trade data to make analytics meaningful. API endpoints must exist before the frontend can be built.
**Delivers:** Full REST API under `/api/paper-trading/`, analytics computation (win rate, total P&L, drawdown, direction breakdown, AI score correlation, equity curve), manual paper trade creation.
**Addresses:** PT-06 analytics, API endpoints, manual follow feature
**Avoids:** Pitfall 11 (insufficient sample size — show n=X on all metrics, grey out n<30), Pitfall 6 (survivorship bias — track signal-to-position conversion rate)

### Phase 4: Frontend Dashboard
**Rationale:** Visualization layer. Depends on stable API from Phase 3. All chart types map to existing Recharts components — no new patterns needed.
**Delivers:** `/dashboard/paper-trading` page with 5 tabs (Overview, Active, History, Analytics, Config), summary cards, equity curve chart, trade tables, analytics breakdown charts, calendar heatmap (react-activity-calendar), streak display, simulation config form, "Follow Signal" button on ticker detail.
**Addresses:** PT-07 dashboard, calendar heatmap, sector analysis, streak tracking
**Avoids:** Pitfall 12 (equity curve distortion — R-multiple normalization), Pitfall 15 (timezone confusion — DATE type + string rendering), Pitfall 16 (streak counting — consecutive profitable trades, not calendar days)

### Phase 5: Telegram & Polish
**Rationale:** Notification layer. Depends on trade events from Phase 2 and formatting. Lowest risk — reuses existing send_message() pattern entirely.
**Delivers:** `/paper` and `/paper_status` Telegram commands, auto-notifications for TP/SL/timeout events, Vietnamese message formatting, end-to-end integration testing.
**Addresses:** Telegram TP/SL notifications, paper status command
**Avoids:** Pitfall 17 (misleading BEARISH trades — clear labeling as "xu hướng giảm" simulation, separate analytics section)

### Phase Ordering Rationale

- **Phases 1→2 are strictly sequential:** Models must be stable before jobs process data through them. The state machine + P&L logic in Phase 1 is the most critical code — getting it wrong corrupts everything downstream.
- **Phase 2 needs real time to pass:** After Phase 2 deploys, the system needs 2+ weeks of actual market data flowing to produce meaningful closed trades for analytics. This natural delay is WHY frontend/analytics are Phase 3-4.
- **Phases 3→4 follow API-first pattern:** Frontend is built against a tested API, not against backend code in flux.
- **Phase 5 is independent:** Telegram notifications could technically happen in Phase 2, but deferring to Phase 5 keeps the scheduler jobs simpler during initial development and testing.
- **BEARISH handling is cross-cutting:** Every phase must respect that VN retail can't short sell. BEARISH paper trades track prediction accuracy, not realizable profit.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Deep-dive on exact state transition matrix (8-10 paths) and P&L edge cases (partial TP + timeout, partial TP + breakeven SL, gap-through on TP1 day). Recommend `/gsd-research-phase` for the state machine specification.
- **Phase 2:** Scheduler chain timing — verify that position monitor doesn't overlap with AI pipeline on days when price crawl runs late. May need to review `_on_job_executed` ordering in detail.

Phases with standard patterns (skip research-phase):
- **Phase 3:** API endpoints follow existing portfolio pattern exactly. Analytics queries are straightforward SQL aggregates.
- **Phase 4:** All Recharts chart types already used in codebase. @tanstack/react-table pattern exists. react-activity-calendar has clear API docs.
- **Phase 5:** Telegram integration extends existing MessageFormatter with new static methods. Zero new patterns.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new backend deps, one verified frontend dep. Every technology already in use. All claims verified against installed packages. |
| Features | HIGH | Feature set derived from codebase analysis (existing signal schema, scheduler patterns) + industry-standard paper trading practices. Clear prioritization with strong anti-feature rationale. |
| Architecture | HIGH | All integration points verified against actual codebase (line-level references). Job chaining, service layer, API patterns all match proven existing patterns. Single-user assumptions simplify significantly. |
| Pitfalls | HIGH (code) / MEDIUM (VN market) | Code-level pitfalls verified against codebase. VN market mechanics (price bands, holidays, fees, lot sizes) based on domain knowledge — specific holiday dates and fee rates should be validated. |

**Overall confidence:** HIGH

### Gaps to Address

- **VN holiday calendar:** Timeout logic counts trading days, but there's no holiday calendar in the codebase. Solution: count actual `daily_prices` rows (if no price crawled, it wasn't a trading day). No calendar data structure needed.
- **BEARISH P&L framing:** Research suggests tracking as "predicted price drop accuracy" rather than synthetic short P&L, but the exact UX copy and analytics presentation need design-time decisions.
- **Auto-track minimum confidence threshold:** STACK.md suggests `min_score=1` (track all), ARCHITECTURE.md suggests `min_confidence=7`. This is a config value — default to tracking all valid signals (score > 0) with the threshold configurable. Analytics should show performance by score bracket regardless.
- **Entry fill timing:** Two valid approaches exist (next-day open vs AI's suggested price with fill window). Recommend next-day open for simplicity and bias avoidance. Needs explicit decision during Phase 1.
- **Partial TP lot rounding:** 50/50 split on odd quantities (e.g., 300 shares). Research recommends ignoring lot constraints for the split (paper simulation), only applying 100-share rounding on initial position sizing.
- **Fee simulation:** FEATURES.md lists fee simulation as anti-feature, but PITFALLS.md details VN fee structure (0.15% + 0.1% selling tax) as important for P&L accuracy. Recommendation: include configurable fees in P&L calculation but default to 0% with a note in UI. The fees are noise (0.4% round-trip) compared to TP/SL magnitudes (3-10%), but users who want precision can enable them.

## Sources

### Primary (HIGH confidence)
- `backend/app/models/` — All 12 existing SQLAlchemy model patterns verified
- `backend/app/scheduler/manager.py` — Job chaining via `_on_job_executed`, 50+ job IDs, pool_size constraints
- `backend/app/services/portfolio_service.py` — P&L calculation pattern, FIFO lots, service layer architecture
- `backend/app/schemas/analysis.py` — `TickerTradingSignal`, `TradingPlanDetail`, `Timeframe` enum, `Direction` enum
- `backend/app/config.py` — Aiven PostgreSQL pool_size=5/max_overflow=3, timezone settings
- `frontend/package.json` — React 19.2.4, Recharts 3.8.1, date-fns 4.1.0, @tanstack/react-table 8.21.3
- `npm view react-activity-calendar` — Version 3.2.0, React 19 peer dep, date-fns ^4, published 2026-04-15
- `frontend/src/components/performance-chart.tsx` — Existing Recharts AreaChart pattern (reusable for equity curve)

### Secondary (MEDIUM confidence)
- VN market mechanics — Price bands (±7%/±10%/±15%), T+2 settlement, 0.1% selling tax, 100-share lots, no retail short selling
- Paper trading domain patterns — SL-first priority, partial TP with breakeven move, R-multiple normalization, equity curve + drawdown calculation

### Tertiary (LOW confidence)
- VN brokerage fee rates (0.15-0.25%) — Varies by broker, needs validation against user's actual broker
- Specific VN holiday dates — Vary annually, mitigated by counting actual price data rows instead of calendar

---
*Research completed: 2026-04-21*
*Ready for roadmap: yes*

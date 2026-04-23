# Project Research Summary

**Project:** Holo v8.0 — AI Trading Coach
**Domain:** Personal AI trading coach for Vietnamese stock market (HOSE/HNX/UPCOM), targeting beginners with < 50M VND capital
**Researched:** 2025-07-24
**Confidence:** HIGH

## Executive Summary

Holo v8.0 transforms an existing stock intelligence platform (800+ tickers, Gemini AI analysis, 27 technical indicators, trading signals) into a personal AI trading coach. The expert approach is **extension over modification**: daily picks are derived from the existing analysis pipeline output — not a parallel system — and new coach features (trade journal, behavior tracking, adaptive strategy, weekly reviews) layer on top as new modules consuming existing data. The existing stack covers 90% of needs; only 5 new frontend npm packages and zero new Python packages are required. This is an integration project, not a greenfield build.

The recommended approach follows a strict dependency chain: database schema first → daily picks engine (the core value) → trade journal with VN-market-aware P&L → coach dashboard → behavior tracking + adaptive strategy → goals and weekly reviews. Each phase completes one link in the coaching loop (AI picks → user trades → results tracked → AI adapts). The critical architectural decision is that daily picks must be a **ranking/selection** of pre-analyzed tickers, not a re-analysis — this keeps Gemini API usage under budget (adds <1% to daily calls) and avoids competing with the existing 800-ticker pipeline.

The primary risks are Vietnam-specific: incorrect P&L calculations from ignoring T+2 settlement, lot sizes, price steps, and the mandatory 0.1% sell tax; AI-hallucinated tickers or impossible prices that beginners would blindly trust; and over-trading recommendations that burn small capital through accumulated fees. All three are preventable with upfront validation layers (a `VNMarketRules` utility class, hard ticker/price validation against the database, and capital-aware pick counts). The secondary risk is the adaptive strategy creating dangerous feedback loops from small sample sizes — mitigated by requiring 20+ completed trades before activation and hard safety rails that adaptation can never override.

## Key Findings

### Recommended Stack

The existing stack is the stack. No architectural changes, no new backend dependencies, no new database technology. The only additions are 5 frontend packages from the shadcn/ui ecosystem and 8 copy-paste shadcn components.

**Core technologies (all existing):**
- **FastAPI + SQLAlchemy 2.0 + asyncpg**: New `/api/coach/*` router group, 5-6 new models with JSONB columns, same async session pattern
- **APScheduler 3.11**: 2 new chained jobs (daily picks after pipeline, weekly review Sunday cron)
- **google-genai (Gemini)**: 2 new prompt types (pick reasoning, weekly coaching review) — adds ~8 calls/week total
- **Next.js 16 + React 19 + TanStack Query**: New route group `/coach`, `/journal`, `/goals` with standard data fetching patterns
- **Recharts + lightweight-charts**: P&L visualization and pick entry/SL overlay on existing charts

**New frontend dependencies (5 packages):**
- `react-hook-form` ^7.73 — multi-field trade journal and goal forms (shadcn/ui standard)
- `zod` ^3.25 — schema validation for forms and API requests (**use 3.x, not 4.x** — too new)
- `@hookform/resolvers` ^5.2 — bridge between react-hook-form and zod
- `react-day-picker` ^9.14 — date picker for trade entries (shadcn/ui Calendar dependency)
- `sonner` ^2.0 — toast notifications for trade actions (~3KB)

**New backend dependencies: None.** Existing SQLAlchemy, Alembic, Pydantic, APScheduler, and google-genai handle all v8.0 needs.

### Expected Features

**Must have (table stakes) — without these, it's just another signal dashboard:**
- Daily Picks (3-5 stocks/day) — the core promise; curated from existing analysis, not re-analyzed
- Capital-aware filtering (< 50M VND) — picks must be actually buyable at 100-share lot sizes
- Safety-first scoring — penalize high-ATR, low-ADX, low-volume tickers
- Educational Vietnamese explanations per pick — "buy VNM because..." teaches, bare signals don't
- Entry/SL/TP per pick — inherited from existing trading signal pipeline
- Trade Journal with auto P&L — bridges AI picks to reality; FIFO matching, VN fee/tax included
- Pick history and performance tracking — "did yesterday's picks work?" builds trust
- Coach dashboard — single page: today's picks, active trades, performance summary

**Should have (differentiators) — transforms from "picks app" to "personal coach":**
- Pick-to-trade linkage — optional FK enables "followed picks win rate vs. deviation win rate"
- Behavior tracking — viewing patterns, trading habits, sector biases
- Adaptive strategy — risk level state machine (1-5 scale), sector preference learning
- Weekly AI-generated performance review — Gemini as personal coach, Vietnamese
- Goal setting — process-based goals preferred over P&L targets
- Position sizing for small capital — show absolute VND amounts, not just percentages
- "Why not this stock?" explanations — prevents FOMO

**Defer (v2+):**
- AI chat / conversational interface — massive complexity, minimal value for structured coaching
- Gamification / badges — creates wrong incentives for beginners (overtrading)
- Real-time pick alerts / notifications — encourages impulsive action
- Complex portfolio analytics (Sharpe, beta) — removed in v7.0 for good reason

**Anti-features (explicitly never build):**
- Auto-trading / order execution — legal risk, no VN broker API, out of scope
- Social features — single-user app, social comparison creates FOMO
- Intraday/scalping picks — VN T+2 settlement makes this irrelevant
- Technical indicator customization — beginners don't need knobs, they need conclusions

### Architecture Approach

The architecture follows the existing monolith pattern with clear service separation: ContextBuilder → GeminiClient → Storage. New coach features are **new modules alongside existing ones** — DailyPickGenerator reads from `ai_analyses` and `trading_signal` tables, TradeJournalService manages CRUD with VN-aware P&L, BehaviorTracker aggregates events, AdaptiveStrategyEngine suggests (never auto-applies) risk adjustments, and GoalReviewService generates weekly coaching via Gemini. All new Gemini calls acquire the existing `_gemini_lock`. The single-user constraint eliminates auth, multi-user scoping, and RBAC entirely.

**Major components:**
1. **DailyPickGenerator** — ranks 800+ tickers from existing analysis → selects top 3-5 via composite scoring + Gemini reasoning. Chains after `daily_hnx_upcom_analysis` in scheduler
2. **TradeJournalService** — CRUD for manual trades, auto-links to daily picks, calculates realized P&L with VN fees/tax. Each entry is one buy→sell cycle (no complex lot matching)
3. **PnLEngine** — pure logic: VN fee calculation (0.15% buy + 0.15% sell + 0.1% sell tax), lot size rounding, price step normalization. Unrealized P&L computed on-the-fly, never stored
4. **BehaviorTracker** — records aggregated daily summaries (not raw events), weekly aggregation feeds into adaptive strategy. 90-day retention with monthly cleanup
5. **AdaptiveStrategyEngine** — evaluates 4-week lookback of trading performance, SUGGESTS risk profile changes → user must CONFIRM. Hard safety rails (max 20% position, max 3 concurrent, min volume 50K) can never be overridden
6. **GoalReviewService** — monthly targets + weekly AI-generated coaching reviews (Gemini, Vietnamese). Sunday 20:00 cron job
7. **Coach API Router** — `/api/coach/*` with sub-routes: `/picks`, `/journal`, `/behavior`, `/profile`, `/goals`, `/reviews`, `/adjustments`

### Critical Pitfalls

1. **AI-hallucinated stock picks** — Gemini may invent tickers, generate impossible prices (outside ±7% HOSE limits), or suggest stop-losses at invalid price steps. **Prevention:** Hard validation — every ticker must exist in DB, prices within daily limit band, auto-round to valid price steps, liquidity gate (volume > 10K). Use structured Pydantic output schema.

2. **VN-market P&L calculation errors** — Simple (sell-buy)×qty ignores T+2 settlement, 100-share lot sizes, price steps, 0.15% broker fees, and 0.1% sell tax. A 100K "profit" is really 66,950 VND after costs. **Prevention:** Build `VNMarketRules` utility class FIRST with comprehensive unit tests. Always show gross and net P&L separately.

3. **Over-trading recommendations burning small capital** — 5 daily picks × 50M VND capital = impossible to trade all. Fees compound, psychology deteriorates. **Prevention:** "Pick of the Day" primary mode with 1 highlighted pick, 2-4 as "watch only." Position limit warnings. Cooldown after consecutive losses.

4. **Survivorship bias in pick evaluation** — User trades 2 of 5 picks (the "safe" ones), journal shows 100% win rate when reality was 2/5 = 40%. Adaptive strategy then overfits. **Prevention:** Track ALL picks regardless of trading. Display "Traded win rate" AND "All picks win rate." Auto-evaluate untraded picks via daily price data.

5. **Adaptive strategy feedback loop** — 8 trades over a month is noise, not signal. AI "learns" the user likes banking stocks → concentrates recommendations → sector correction wipes out gains. **Prevention:** 20-trade minimum before activation, max 2 picks from same sector per week, weekly adjustment cadence only, hard diversification constraints.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Data Foundation & VN Market Utilities
**Rationale:** Everything depends on the database schema and VN market rules. Pitfall 12 (schema sprawl) demands all tables be created in one migration batch. Pitfall 3 (P&L errors) demands VNMarketRules be built and tested before any trade logic.
**Delivers:** 6 new DB tables (daily_picks, trade_journal, user_risk_profile, behavior_events, goals, weekly_reviews), SQLAlchemy models, Pydantic schemas, Alembic migrations, `VNMarketRules` utility with unit tests, user_risk_profile with defaults.
**Addresses:** Schema foundation for all features; VN fee/tax/lot/price-step calculations
**Avoids:** Pitfall 3 (P&L errors), Pitfall 12 (schema sprawl), Pitfall 14 (VN calendar edge cases)

### Phase 2: Daily Picks Engine
**Rationale:** This IS the core feature. Without picks, there's no "coach." Depends only on Phase 1 schema + existing analysis pipeline output. Generates data that all downstream features consume.
**Delivers:** DailyPickContextBuilder, DailyPickGenerator service, composite scoring algorithm, Gemini pick reasoning prompt, scheduler chain integration, pick validation layer (anti-hallucination), pick storage, API endpoints (`GET /coach/picks/today`, `/history`), frontend `/coach` page with pick cards.
**Addresses:** Daily picks, capital-aware filtering, safety-first scoring, educational explanations, entry/SL/TP
**Avoids:** Pitfall 1 (hallucinated picks), Pitfall 5 (rate limit exhaustion — derive from existing data, single Gemini call)

### Phase 3: Trade Journal & P&L
**Rationale:** Bridges AI picks to reality. Must follow picks phase so trades can link to picks. P&L depends on VNMarketRules from Phase 1.
**Delivers:** TradeJournalService (CRUD), PnLEngine (realized P&L with VN fees/tax, unrealized P&L on-the-fly), auto-link to daily picks, trade form with validation (price within OHLCV range, valid trading day), API endpoints (CRUD trades, summary), frontend `/journal` page with react-hook-form + react-table.
**Addresses:** Trade journal, auto P&L, pick-to-trade linkage, performance summary
**Avoids:** Pitfall 3 (P&L errors — uses VNMarketRules), Pitfall 7 (entry timing mismatch — validate against OHLCV), Pitfall 11 (position sizing — show actual VND and % of capital)

### Phase 4: Coach Dashboard & Pick Performance
**Rationale:** Ties Phases 2+3 together into the primary user experience. Pick performance tracking needs picks to exist and daily prices to evaluate outcomes. Dashboard is the daily landing page.
**Delivers:** Pick performance tracking (auto-evaluate TP/SL hits against market data), pick track record with "All picks" vs "Traded picks" win rates, coach dashboard page (today's picks, active trades, P&L summary, pick accuracy), performance summary cards.
**Addresses:** Coach dashboard, pick history/track record, performance summary, dual win-rate display
**Avoids:** Pitfall 2 (survivorship bias — tracks all picks), Pitfall 9 (false confidence — shows actual accuracy metrics + bear case), Pitfall 4 (over-trading — capital-aware pick count display)

### Phase 5: Behavior Tracking & Adaptive Strategy
**Rationale:** Requires journal data to exist (Phase 3) and meaningful trade history (~20 trades). This is the intelligence layer that makes the coach "personal." Must be built together because adaptive strategy consumes behavior data.
**Delivers:** BehaviorTracker (aggregated daily summaries, not raw events), frontend event tracking (batch POST, fire-and-forget), AdaptiveStrategyEngine (4-week lookback, suggest-then-confirm flow), risk profile adjustment UI, sector preference learning, strategy adjustment banner, behavior cleanup scheduled job.
**Addresses:** Behavior tracking (viewing patterns, trading habits), adaptive risk scaling, sector preference, position limit enforcement
**Avoids:** Pitfall 6 (feedback loop — 20-trade minimum, sector diversification constraint, weekly cadence), Pitfall 8 (storage bloat — frontend aggregation + daily summaries + 90-day retention)

### Phase 6: Goals & Weekly Reviews
**Rationale:** Polish layer requiring all previous phases. Weekly review needs journal data, behavior metrics, and adaptive strategy evaluation. Goals need P&L history to track progress.
**Delivers:** GoalReviewService, monthly goal setting (process-based preferred), weekly AI-generated coaching review (Gemini, Vietnamese, Sunday cron), goal progress display, weekly review cards, risk tolerance review prompt, circuit breaker for capital drawdown.
**Addresses:** Goal setting, weekly performance review, weekly risk tolerance review
**Avoids:** Pitfall 10 (goal pressure — process goals over outcome goals, no "catch up" framing, drawdown circuit breaker)

### Phase Ordering Rationale

- **Dependency chain is strict:** Schema → Picks → Journal → Dashboard → Behavior → Goals. Each phase produces data the next phase consumes.
- **Core coaching loop first:** Phases 2-4 complete the minimum viable coaching experience (AI picks → user trades → results visible). This is usable and valuable before behavior/adaptation exist.
- **Adaptive features delayed intentionally:** They need ~20 trades of data to be meaningful. Building them early creates empty features. Building journal first lets data accumulate naturally.
- **VNMarketRules as phase 1 foundation** because P&L errors compound silently and are hard to fix retroactively. Getting fees/tax/lots right from day 1 prevents phantom P&L that destroys user trust.
- **All tables in one migration** per Pitfall 12 — avoids fragile migration ordering with cross-table FKs.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Daily Picks):** Complex Gemini prompt engineering for Vietnamese pick reasoning. Composite scoring weights (0.35 combined + 0.30 signal + 0.20 volume + 0.15 sector) need tuning. Validation rules for VN price steps are exchange-specific (HOSE vs HNX vs UPCOM). Worth a `/gsd-research-phase` to nail the pick generation algorithm and prompt design.
- **Phase 5 (Adaptive Strategy):** Risk level state machine transitions, minimum sample sizes for adaptation, sector diversification constraints. Novel territory — no established library patterns. Needs careful design research.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Data Foundation):** Standard Alembic migrations + SQLAlchemy models. Existing codebase has 10+ tables as patterns. Well-documented.
- **Phase 3 (Trade Journal):** CRUD + P&L calculation is straightforward once VNMarketRules is built. react-hook-form + zod is extensively documented in shadcn/ui.
- **Phase 4 (Dashboard):** Standard React page composition with TanStack Query. Follows existing dashboard patterns.
- **Phase 6 (Goals & Reviews):** Simple CRUD for goals + Gemini prompt for review. Weekly cron follows existing APScheduler pattern.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | Versions verified via npm/pip registries. Existing codebase audited. Zero speculative dependencies. All new packages are shadcn/ui ecosystem standards with React 19 support confirmed. |
| Features | **MEDIUM** | Feature landscape derived from domain knowledge of trading apps (Edgewonk, Tradervue, MarketSmith) + existing codebase analysis. No external search tools used. VN market rules are well-established. Anti-features are opinionated but well-reasoned. |
| Architecture | **HIGH** | Based on direct codebase inspection. Extends proven patterns (ContextBuilder → GeminiClient → Storage, job chaining, structured output). Minimal changes to existing components. Build order derived from clear dependency analysis. |
| Pitfalls | **HIGH** | Critical pitfalls (hallucination, P&L errors, rate limits) are based on direct code analysis and VN market regulations. Behavioral pitfalls (over-trading, survivorship bias, goal pressure) are well-established in trading psychology. Detection and prevention strategies are concrete and actionable. |

**Overall confidence:** HIGH

### Gaps to Address

- **Gemini pick prompt tuning:** The composite scoring weights and pick reasoning prompt need iterative testing with real analysis data. Start with proposed weights, validate against recent trading signal quality.
- **VN market holiday calendar:** T+2 calculation works for weekdays but holidays (Tết, Sep 2, Apr 30) need a maintained holiday list. Start with weekday-only, add holiday config before first Tết cycle.
- **Aiven storage limits:** Behavior tracking retention policy (90 days) assumes adequate storage. Verify actual Aiven plan limits before Phase 5.
- **Broker fee rate variability:** Default 0.15% but ranges 0.15-0.35% across brokers. Make configurable in user settings from Phase 1.
- **Composite scoring weight calibration:** The 0.35/0.30/0.20/0.15 weights for pick ranking are informed estimates. Need backtesting against historical analysis data once picks are generating.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `app/services/analysis/`, `app/schemas/`, `app/config.py`, `app/database.py`, `app/scheduler/`, `frontend/package.json`, `backend/requirements.txt`
- npm registry — react-hook-form 7.73.1, zod 3.25.76, @hookform/resolvers 5.2.2, react-day-picker 9.14.0, sonner 2.0.7 (versions verified 2025-07-23)
- Existing Gemini integration patterns — structured output, post-validation, rate limiting, batch processing
- VN market rules — HOSE/HNX/UPCOM trading regulations (lot sizes, price steps, T+2, daily limits, fee structure)

### Secondary (MEDIUM confidence)
- Trading app domain patterns — Edgewonk, Tradervue, MarketSmith, Simplize, FireAnt, TCInvest feature analysis
- Behavioral finance pitfalls — over-trading, loss aversion, survivorship bias, goal pressure (established trading psychology)
- LLM hallucination patterns in financial contexts — observed in Gemini and other LLMs

### Tertiary (LOW confidence)
- Aiven PostgreSQL storage limits — varies by plan, verify actual limits
- Exact broker commission rates — 0.15-0.35% range, make configurable

---
*Research completed: 2025-07-24*
*Ready for roadmap: yes*

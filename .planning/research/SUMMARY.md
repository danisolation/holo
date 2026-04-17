# Project Research Summary

**Project:** Holo — Stock Intelligence Platform
**Domain:** Vietnamese stock market intelligence (HOSE) — reliability hardening & portfolio tracking (v1.1)
**Researched:** 2026-04-16
**Confidence:** HIGH

## Executive Summary

Holo v1.1 adds four capability areas to an already-functional stock intelligence platform: corporate actions handling (price adjustments for splits/dividends), portfolio tracking (trade entry, FIFO cost basis, P&L), error resilience (circuit breakers, dead-letter retry, job tracking), and system health observability. The critical discovery from stack research is that **zero new backend libraries are needed** — the existing stack (FastAPI + SQLAlchemy + tenacity + google-genai + vnstock 3.5.1) already covers every v1.1 requirement. vnstock's `Company.events()` endpoint provides corporate action data (splits, dividends, bonus shares, rights issues) with structured fields, eliminating the need for fragile Vietnamese-language scraping. Only 3 small frontend dependencies are added (react-hook-form, @hookform/resolvers, zod@3) for trade entry forms.

The recommended approach is to build **corporate actions first, then portfolio tracking**, because portfolio P&L accuracy depends on adjusted prices. Error resilience infrastructure (circuit breakers, job run tracking, dead-letter queue) should be built as a foundation layer before adding new features that exercise external APIs. AI prompt improvements are independent and can be parallelized with any phase. The architecture extends the existing single-process FastAPI pattern with 4 new service classes and 6 new database tables — no infrastructure changes, no new external services.

The top risks are: (1) **corporate action price adjustments cascading incorrectly** — adjusting `adjusted_close` without recomputing downstream indicators and AI analyses creates internally inconsistent data; (2) **FIFO cost basis with partial sells** — developers who skip explicit lot tracking will produce wrong P&L numbers that are hard to debug; (3) **retry logic breaking APScheduler job chaining** — the existing `EVENT_JOB_EXECUTED` listener is fragile and retry/circuit-breaker patterns must work *within* job functions, not around them. All three risks have clear prevention strategies documented in detail.

## Key Findings

### Recommended Stack

The existing stack is remarkably complete for v1.1. No new backend dependencies. The only additions are 3 frontend form libraries needed because shadcn/ui's `<Form>` component is built on react-hook-form. Custom implementations are preferred over libraries for circuit breaker (aiobreaker is Tornado-legacy, pybreaker lacks native asyncio), dead-letter queue (PostgreSQL table beats Redis/RabbitMQ for single-user), and health monitoring (DB table + dashboard beats Prometheus/Grafana).

**Core technologies (no changes):**
- **vnstock 3.5.1**: `Company.events()` returns corporate action data (eventListCode, ratio, value, exrightDate) — no new data source needed
- **FastAPI + SQLAlchemy 2.0 + Alembic**: 6 new tables via standard migrations, 4 new service classes following existing patterns
- **tenacity 9.1.4**: Already on `_call_gemini()` — extend to all external API calls (vnstock, CafeF)
- **google-genai**: `system_instruction` param available but unused — key AI improvement with zero new deps
- **Custom AsyncCircuitBreaker (~30 lines)**: One singleton per external service (VCI, Gemini, CafeF)

**New frontend additions (3 only):**
- **react-hook-form ~7.72** + **@hookform/resolvers ~5.2** + **zod@3**: Trade entry form validation. Use zod 3.x — zod 4.x is too new for @hookform/resolvers compatibility.

**Explicitly NOT adding:** Celery, Redis, Prometheus, Grafana, aiobreaker, pybreaker, LangChain, numeral.js, zod 4.x, WebSockets for health.

### Expected Features

See [FEATURES.md](./FEATURES.md) for full landscape with complexity ratings.

**Must have (table stakes):**
- Corporate actions crawl from VCI + storage in DB (splits, dividends, bonus, rights)
- Historical price adjustment via cumulative adjustment factors on `adjusted_close`
- Manual trade entry (buy/sell) via dashboard form and Telegram commands
- FIFO cost basis with explicit lot tracking + realized/unrealized P&L
- Holdings view with current market value and P&L percentages
- AI prompt improvements: system_instruction, few-shot examples, scoring rubric, price context in technical prompts
- Job execution logging for all scheduler jobs
- Data freshness indicators + basic health dashboard page

**Should have (differentiators):**
- Dividend income tracking (VN dividends yield 3-8%, significant for total return)
- Position-aware AI alerts (elevate priority for held tickers)
- Portfolio P&L on Telegram (`/portfolio`, `/pnl`, daily P&L notification)
- Dead-letter queue with automatic retry for failed operations
- Corporate action Telegram alerts (upcoming ex-dates)
- Adjusted vs raw price toggle on candlestick chart

**Defer (v2+):**
- Portfolio import from CSV/Excel — premature for ~20-50 trades
- Event calendar on dashboard — nice but not critical
- Sector-relative AI context — higher complexity
- Gemini API usage tracker — nice-to-have
- Broker API integration — VN broker APIs not standardized

### Architecture Approach

v1.1 extends the existing single-process FastAPI architecture with a new **resilience layer** (circuit breakers + extended retry) and 4 new domain services, all communicating through the existing SQLAlchemy session pattern. No infrastructure changes — same PostgreSQL on Aiven, same APScheduler in-process, same Telegram long-poll. The key architectural addition is treating error recovery as a cross-cutting concern with module-level circuit breaker singletons and a job-wrapping pattern for health tracking. See [ARCHITECTURE.md](./ARCHITECTURE.md) for full diagrams and data flows.

**Major components (new):**
1. **CorporateActionService** — Crawl VCI events, store, compute adjustment factors, apply to `adjusted_close`, trigger indicator recompute
2. **PortfolioService** — Trade CRUD, FIFO lot management, realized/unrealized P&L, holdings aggregation
3. **JobRunService** — Wrap all scheduler jobs with start/complete/fail tracking for health monitoring
4. **DeadLetterService** — Store failed operations for periodic retry with backoff
5. **ResilienceLayer** — Module-level `AsyncCircuitBreaker` singletons (vci_breaker, gemini_breaker, cafef_breaker) + extended tenacity retry decorators
6. **6 new DB tables** — corporate_actions, trades, trade_lots, dividend_income, job_runs, dead_letter_operations

**Key patterns to follow:**
- Service-per-domain with own DB session (existing pattern)
- Circuit breakers as module-level singletons (NOT per-request)
- Job wrapping for automatic health tracking
- `asyncio.to_thread()` for all vnstock sync calls (existing pattern)
- P&L computed in backend, NOT frontend

**Anti-patterns to avoid:**
- Adjusting raw `close` column (only modify `adjusted_close`)
- Computing FIFO in JavaScript
- Creating circuit breakers per request (defeats state tracking)
- Blocking vnstock calls in async context without `to_thread()`

### Critical Pitfalls

See [PITFALLS.md](./PITFALLS.md) for full analysis with warning signs and recovery strategies.

1. **Corporate action cascade breaks indicators & AI** — Adjusting `adjusted_close` without recomputing indicators/AI creates inconsistent data. **Prevent:** Trigger targeted recompute pipeline per affected ticker after adjustment. NEVER modify raw OHLC columns.

2. **FIFO with partial sells needs explicit lot tracking** — Computing P&L as `(sell - avg_buy) * qty` is average cost, not FIFO. Partial sells that split lots, sells spanning multiple lots, and stock splits modifying lot quantities all break naive implementations. **Prevent:** Model lots explicitly with `remaining_quantity`. Build `replay_lots()` utility from day one.

3. **Retry/circuit-breaker breaks APScheduler job chaining** — The `EVENT_JOB_EXECUTED` listener only sees success/failure. Tenacity retrying at the scheduler level causes the listener to fire on first failure, breaking the chain even if retry succeeds. Circuit breakers that swallow exceptions cause chains to continue on stale data. **Prevent:** Keep retry INSIDE job functions. Return result dicts with status fields. Never wrap job functions with tenacity at the scheduler level.

4. **VN market ex-date vs record-date confusion (T+2 settlement)** — HOSE uses T+2 settlement; ex-date is 2 trading days before record date. Using the wrong date shifts price adjustments by 1-2 days. **Prevent:** Use ex-date (not record date) for price adjustment. Validate by comparing adjusted charts against CafeF/TradingView.

5. **DB connection pool exhaustion** — Current pool is `pool_size=5, max_overflow=3` (8 max) with Aiven's ~20-25 connection limit. v1.1 adds health polling, portfolio queries, P&L computation, daily snapshots — all new session consumers. **Prevent:** Cache health checks for 60s, pre-compute P&L into snapshots table, monitor pool metrics before adding features, set `pool_timeout=10` for fast failure.

## Implications for Roadmap

Based on research, the dependency chain is clear: **resilience infrastructure → corporate actions → portfolio tracking**, with AI improvements and health dashboard as parallel workstreams.

### Phase 1: Resilience Foundation
**Rationale:** Every subsequent feature exercises external APIs or creates new scheduled jobs. Building the resilience layer first means all new code is born reliable rather than retrofitted.
**Delivers:** Circuit breaker module, extended retry decorators, job_runs table + JobRunService wrapper, dead_letter_operations table + DeadLetterService, periodic retry job.
**Addresses:** Error recovery table stakes (granular retry, dead letter, job logging, graceful degradation)
**Avoids:** Pitfall 3 (retry breaking chain) — design the resilience layer to work WITHIN job functions from the start. Pitfall 6 (pool exhaustion) — add pool metrics monitoring in this phase.

### Phase 2: Corporate Actions
**Rationale:** Portfolio P&L requires adjusted prices. AI analysis quality improves with adjusted prices. This is the data foundation everything else builds on.
**Delivers:** corporate_actions table, CorporateActionCrawler (vnstock Company.events()), price adjustment engine with cumulative factors, targeted indicator recompute trigger, scheduled weekly crawl job.
**Addresses:** All corporate action table stakes (fetch, store, cash dividend, stock dividend, split, historical adjustment)
**Avoids:** Pitfall 1 (cascade to indicators/AI) — build recompute trigger as part of the adjustment pipeline, not as an afterthought. Pitfall 4 (ex-date confusion) — use VCI's `exrightDate` directly, validate against known historical events.

### Phase 3: Portfolio Core
**Rationale:** With adjusted prices in place and resilience infrastructure ready, portfolio tracking can produce accurate P&L from day one.
**Delivers:** trades + trade_lots tables, PortfolioService (FIFO lot management, P&L calculation), trade entry API endpoints, holdings aggregation, portfolio summary, trade history. Unify watchlist to DB-backed (prerequisite for position-aware features).
**Addresses:** All portfolio table stakes (trade entry, FIFO, realized/unrealized P&L, holdings view, portfolio summary, trade history)
**Avoids:** Pitfall 2 (FIFO lot tracking) — explicit lot model with `remaining_quantity` from day one. Pitfall 7 (dual watchlist) — migrate to DB-backed watchlist as first step.

### Phase 4: AI Prompt Improvements
**Rationale:** Independent of other features — can be developed in parallel. Low effort, high impact improvements to existing AI pipeline.
**Delivers:** system_instruction separation, few-shot examples, scoring rubric with anchors, price context in technical prompts, prompt versioning, per-ticker validation in batch responses.
**Addresses:** All AI prompt table stakes + key differentiators (structured output retry, temperature tuning)
**Avoids:** Pitfall 5 (schema drift) — implement per-ticker validation and prompt versioning before changing any prompt content.

### Phase 5: System Health Dashboard
**Rationale:** With job_runs table populated (from Phase 1) and corporate action + portfolio jobs running, there's meaningful health data to display.
**Delivers:** `/api/system/health` endpoint (data freshness, error counts, circuit breaker states, pool metrics), frontend `/dashboard/health` page with status cards + error rate chart + job history table.
**Addresses:** All health dashboard table stakes (freshness, last crawl status, error rate, pool status, health page)
**Avoids:** Pitfall 6 (pool exhaustion) — health checks use cached results (60s staleTime), not live DB queries per poll.

### Phase 6: Telegram Portfolio + Polish
**Rationale:** Frontend portfolio views and Telegram commands are the consumption layer — build last when the backend is solid and tested.
**Delivers:** `/buy`, `/sell`, `/portfolio`, `/pnl`, `/trades` Telegram commands, daily P&L notification, dashboard portfolio page (holdings table, P&L chart, allocation pie chart), dividend income tracking, corporate action Telegram alerts, position-aware AI alerts.
**Addresses:** Telegram portfolio table stakes + differentiators (dividend tracking, position-aware alerts, portfolio charts)
**Avoids:** Performance traps — pre-compute P&L in snapshots table, batch Telegram queries to avoid N+1, respect 4096-char message limit with top-5 truncation.

### Phase Ordering Rationale

- **Resilience before features:** Building circuit breakers and job tracking first means all new crawlers and services are automatically resilient and monitored. Retrofitting reliability is harder and error-prone.
- **Corporate actions before portfolio:** The dependency is hard — portfolio P&L on a stock that had a 2:1 split is 50% wrong without adjusted prices. FIFO lot quantities must also adjust for splits.
- **AI improvements in parallel:** No dependency on other phases. Can be developed alongside Phase 2 or 3 without conflicts.
- **Health dashboard after job tracking:** The dashboard is a read-only view of data produced by Phase 1's job_runs table. Building it too early means an empty dashboard.
- **Telegram last:** It's a thin layer over backend services. Building it prematurely means reworking handlers when service APIs change.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2 (Corporate Actions):** VCI `eventListCode` values need mapping to our enum — may require inspecting actual API responses for real tickers. Cumulative adjustment factor computation is mathematically tricky (newest-to-oldest ordering). Recommend `/gsd-research-phase` to validate with real VCI data.
- **Phase 3 (Portfolio Core):** FIFO lot management edge cases (partial sells spanning lots, corporate action lot adjustments, sell-all then rebuy scenarios). Watchlist migration from localStorage to DB needs careful handling to preserve existing user data. Recommend `/gsd-research-phase` for lot management data model.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Resilience):** Circuit breaker and retry patterns are well-documented. Custom implementation is straightforward.
- **Phase 4 (AI Prompts):** Prompt engineering improvements — iterate and test, no deep research needed.
- **Phase 5 (Health Dashboard):** Standard CRUD + charts. Existing patterns from v1.0 dashboard apply directly.
- **Phase 6 (Telegram Portfolio):** Follows existing Telegram handler patterns from v1.0.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | All claims verified via pip/npm version checks and source code inspection. vnstock `Company.events()` confirmed via source inspection. Circuit breaker library limitations confirmed via testing. |
| Features | **HIGH** | Feature landscape grounded in codebase analysis + VN market domain knowledge. Dependency chain clearly mapped. Complexity estimates based on existing code patterns. |
| Architecture | **HIGH** | Extensions follow established v1.0 patterns (service-per-domain, async sessions, job chaining). No new architectural paradigms introduced. |
| Pitfalls | **HIGH** | All pitfalls reference specific code lines (manager.py, database.py, store.ts, daily_price.py). VN market specifics (T+2, tick sizes, HOSE hours) are standard domain knowledge. |

**Overall confidence:** **HIGH** — Research is grounded in actual codebase inspection and verified library capabilities, not theoretical patterns. The v1.1 scope is well-bounded (no new infrastructure, no new external services).

### Gaps to Address

- **VCI `eventListCode` mapping:** Exact event type codes from VCI GraphQL need validation against real API responses. Research identified the fields exist but didn't enumerate all possible code values. Address during Phase 2 planning by fetching events for a few known tickers with recent corporate actions.
- **FIFO lot adjustment for corporate actions:** When a 2:1 split occurs, existing lots must double quantity and halve cost-per-share. The interaction between corporate actions and lot tracking needs explicit test cases. Address during Phase 3 planning.
- **HOSE holiday calendar:** Health monitoring needs to distinguish holidays from crawl failures. No authoritative API for HOSE holiday schedule exists. Address with heuristic: if vnstock returns empty for ALL tickers, treat as holiday.
- **vnstock freemium risk:** vnstock's `vnai` telemetry dependency signals possible commercial direction. Monitor changelogs. Fallback: reduce to top-100 tickers or call VCI API directly. Not blocking for v1.1 but needs ongoing awareness.
- **Watchlist migration:** Moving dashboard watchlist from localStorage to DB requires a one-time migration path for existing data. Needs design during Phase 3 planning.

## Sources

### Primary (HIGH confidence)
- vnstock 3.5.1 source code — `vnstock.explorer.vci.company` Company.events() returns OrganizationEvents with eventListCode, ratio, value, exrightDate
- Existing codebase — all backend modules (main.py, database.py, config.py, scheduler/manager.py, jobs.py, all models/services/crawlers/handlers)
- Library version verification — `pip index versions` and `npm view` for all recommended packages
- aiobreaker/pybreaker source inspection — confirmed Tornado-legacy patterns and asyncio incompatibility
- google-genai SDK — confirmed system_instruction, thinking_config, response_schema support via field inspection

### Secondary (MEDIUM confidence)
- FIFO as Vietnam standard cost basis method — common practice in VN brokerage systems
- VN broker commission range 0.15-0.25% — general market knowledge
- zod 3.x vs 4.x compatibility with @hookform/resolvers — community consensus

### Tertiary (LOW confidence)
- TypeScript 6.0 ecosystem readiness — TS 6.0 is very new, ecosystem lag risk
- vnstock freemium migration timeline — inferred from vnai dependency, no official announcement

---
*Research completed: 2026-04-16*
*Ready for roadmap: yes*

# Phase 12: Multi-Market Foundation - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Expand Holo from HOSE-only to all three Vietnamese stock exchanges (HOSE, HNX, UPCOM). This includes crawling tickers and OHLCV data for HNX/UPCOM, adding exchange filter UI to the dashboard, and implementing tiered AI analysis that prioritizes HOSE while supporting watchlisted HNX/UPCOM tickers on-demand. The existing Ticker model already has an `exchange` column and VnstockCrawler already maps all 3 exchanges — this phase parameterizes the existing code and scales the pipeline.

</domain>

<decisions>
## Implementation Decisions

### Crawl Scope & Scaling
- Top 200 HNX + top 200 UPCOM tickers (matches personal scope, keeps pipeline under 35 min total)
- One parameterized job per exchange — reuses existing crawl logic, stagger via cron offsets
- Stagger timing: HOSE at 15:30, HNX at 16:00, UPCOM at 16:30 — 30-min gaps prevent DB pool contention
- Ticker selection via VCI listing default order (pre-sorted by relevance) — consistent with HOSE approach

### Dashboard UX
- Exchange filter as segmented tabs (HOSE / HNX / UPCOM / All) — always visible, one-click switching, consistent with shadcn Tabs
- Default filter: All — shows complete market view, user narrows as needed
- Single merged heatmap with exchange-colored borders — unified view, exchange filter applies
- Add exchange badge column to stock list — color-coded (HOSE=blue, HNX=green, UPCOM=orange), sortable & filterable

### AI Analysis Tiering
- "Watchlisted" = tickers in user's watchlist (localStorage + Telegram /watch) — consistent with existing watchlist
- On-demand analysis via button on ticker detail page ("Analyze now") — explicit user action, clear UX
- Gemini budget: HOSE full daily (400), watchlisted HNX/UPCOM daily, cap at 50 extra/day — stays within 1500 RPD
- HNX/UPCOM analysis runs after HOSE analysis completes via job chain (EVENT_JOB_EXECUTED pattern)

### the agent's Discretion
None — all decisions captured above.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `VnstockCrawler._EXCHANGE_MAP` already maps HOSE/HNX/UPCOM to VCI codes (HSX/HNX/UPCOM)
- `VnstockCrawler.fetch_listing(exchange=)` already accepts exchange parameter
- `Ticker.exchange` column exists with `server_default="HOSE"` — schema ready
- `Heatmap` component in `frontend/src/components/heatmap.tsx`
- `useMarketOverview` hook in `frontend/src/lib/hooks.ts`
- shadcn Tabs component available

### Established Patterns
- `asyncio.to_thread()` for all vnstock sync calls
- Circuit breaker wrapping external API calls (`vnstock_breaker`, `gemini_breaker`)
- Job chaining via `EVENT_JOB_EXECUTED` listener
- `JobExecutionService` tracks every job run
- Tenacity retry with exponential backoff on all crawl functions

### Integration Points
- `TickerService.fetch_and_sync_tickers()` — currently hardcoded to HOSE, needs exchange parameter
- `TickerService.MAX_TICKERS = 400` — needs per-exchange configuration
- `backend/app/scheduler/jobs.py` — needs exchange-parameterized job functions
- `backend/app/api/` routers — need exchange query parameter on stock/analysis endpoints
- `frontend/src/app/page.tsx` — HOSE-specific text, needs exchange awareness
- `frontend/src/lib/api.ts` — API client needs exchange parameter support

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches based on existing codebase patterns.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

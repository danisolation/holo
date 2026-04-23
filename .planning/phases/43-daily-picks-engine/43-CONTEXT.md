# Phase 43: Daily Picks Engine - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Each trading day, the app selects and displays 3-5 specific stock picks with entry/SL/TP, position sizing, and Vietnamese explanations — filtered for the user's capital and scored for safety. Includes "almost selected" tickers with rejection reasons.

</domain>

<decisions>
## Implementation Decisions

### Pick Selection & Scoring
- Generate daily picks after `daily_trading_signal_analysis` job chain (~17:00) — uses same-day analysis results
- Composite score: trading_signal_confidence×0.4 + combined_score×0.3 + safety_score×0.3 (safety = low ATR + high ADX + adequate volume)
- Filter from top 50 LONG tickers with score>0, then apply capital + safety filters → select top 3-5
- Default capital 50,000,000 VND, configurable in user_risk_profile table

### Pick Display & Explanation
- 200-300 word Vietnamese explanation per pick — 1 Gemini call batching all 3-5 picks with coaching-style prompt
- "Almost selected" displayed as collapsible list, 1 line per ticker: "HPG — RSI overbought (78), chờ pullback"
- Position sizing format: "Mua 200 cổ × 60,000đ = 12,000,000 VND (24% vốn)" — calculated by 100-share lots, round down
- Entry/SL/TP inherited directly from TradingPlanDetail.long_analysis — no recalculation

### Data Model & Storage
- 2 new tables this phase: `daily_picks` + `user_risk_profile` (other tables in later phases)
- daily_picks: pick_date, ticker_id, rank (1-5), composite_score, entry/SL/TP1/TP2/R:R, position_size_shares/vnd/pct, explanation (Text), status (picked/almost), rejection_reason (nullable)
- user_risk_profile: capital (Decimal, default 50M), risk_level (1-5, default 3), broker_fee_pct (default 0.15), created_at, updated_at — single row table
- Explanation stored in daily_picks.explanation column (Text), 1 per pick

### Frontend & API
- New route `/coach` with navbar entry "Huấn luyện"
- API endpoints: GET /api/picks/today, GET /api/picks/history, GET /api/profile, PUT /api/profile
- Pick card layout: symbol + name + explanation on top, entry/SL/TP + position sizing as badges below
- Live price on pick cards via existing WebSocket — shows unrealized P&L from entry

### the agent's Discretion
No items deferred to the agent's discretion — all decisions captured above.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AIAnalysisService.analyze_all_tickers(analysis_type="trading_signal")` — existing pipeline producing trading signals for all tickers
- `ContextBuilder.get_trading_signal_context()` — builds technical context (ATR, ADX, RSI, Stochastic, Pivot, Fibonacci, 52-week)
- `GeminiClient._call_gemini_with_retry()` — retry + circuit breaker for Gemini API calls
- `_validate_trading_signal()` — existing validation (entry ±5%, SL ≤3×ATR, TP ≤5×ATR, 52-week bounds)
- `TradingPlanDetail` schema — entry, SL, TP1, TP2, R:R, position_size_pct, timeframe
- `apiFetch<T>()` — frontend API fetch utility
- React Query hooks pattern — `useQuery` with staleTime config
- WebSocket `RealtimePriceProvider` — existing real-time price streaming

### Established Patterns
- Job chaining via `EVENT_JOB_EXECUTED` listener in `manager.py`
- Module-level `_gemini_lock` serializes all Gemini API calls
- Alembic migrations in `backend/alembic/versions/` (latest: 018)
- SQLAlchemy 2.0 `mapped_column` + `JSONB` pattern
- Frontend: shadcn/ui components + Tailwind + App Router
- API: FastAPI routers in `backend/app/api/`

### Integration Points
- Scheduler: new `daily_pick_generation` job chains after `daily_trading_signal_analysis`
- Backend: new `services/pick_service.py` + `api/picks.py` router
- Frontend: new `/coach` page + pick card components
- Navbar: add "Huấn luyện" link to NAV_LINKS array
- WebSocket: reuse existing RealtimePriceProvider for live prices on pick cards

</code_context>

<specifics>
## Specific Ideas

- Picks are BUY-only (no short selling in VN retail market)
- Only LONG direction from trading signals (ignore bearish analysis for picks)
- Safety scoring penalizes: high ATR (volatile), low ADX (no trend), low volume (illiquid)
- Lot size is 100 shares for HOSE, filter picks where price × 100 > user capital
- Gemini budget impact: 1 extra call/day for pick explanations (within free tier)

</specifics>

<deferred>
## Deferred Ideas

- Trade journal linking to picks (Phase 44)
- Pick outcome tracking with SL/TP hit detection (Phase 45)
- Adaptive pick scoring based on user trade history (Phase 46)
- Risk level adjustment affecting pick aggressiveness (Phase 46-47)

</deferred>

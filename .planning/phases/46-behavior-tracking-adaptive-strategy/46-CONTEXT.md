# Phase 46: Behavior Tracking & Adaptive Strategy - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

The app observes trading habits and viewing patterns, then suggests personalized risk adjustments and sector preferences based on actual trade performance. This phase adds passive data collection (viewing events), active pattern detection (trading habits), risk level management with suggest-then-confirm UX, and sector preference learning that influences future daily picks. No weekly reviews or goals — those come in Phase 47.

</domain>

<decisions>
## Implementation Decisions

### Viewing Behavior Tracking (BEHV-01)
- New `behavior_events` table: id, event_type (ticker_view/search/pick_click), ticker_id (FK nullable), metadata (JSONB), created_at
- Frontend sends POST /api/behavior/event on: ticker detail page view, search result click, pick card click
- Debounce: max 1 event per ticker per 5 minutes to avoid flooding
- Backend aggregates: GET /api/behavior/viewing-stats returns top 10 most-viewed tickers with view count, last viewed, sector
- Display on /coach page as a small "Mã bạn hay xem" section — simple list with view counts, highlights sector concentration
- Privacy: all data stays local (single-user app), no external tracking

### Trading Habit Detection (BEHV-02)
- Analyze trades table to detect 3 patterns:
  1. **Bán sớm khi lãi** (premature profit-taking): SELL with positive P&L where price continued rising >5% after sell_date
  2. **Giữ lâu khi lỗ** (holding losers): open BUY positions with unrealized loss >10% and held >5 trading days
  3. **Trade impulsive** (impulsive trading): BUY trade created within 2 hours of a CafeF news article about the same ticker
- Detection runs as part of weekly analysis (not real-time) — batch job on Sunday
- Results stored in a `habit_detections` table: id, habit_type, ticker_id, trade_id, evidence (JSONB), detected_at
- Display on /coach page as "Thói quen giao dịch" card with habit badges and count

### Risk Level Management (ADPT-01)
- UserRiskProfile already has risk_level (1-5, default 3) from Phase 43
- After 3 consecutive losing trades (net_pnl < 0), system creates a risk suggestion
- New `risk_suggestions` table: id, current_level, suggested_level, reason (text), status (pending/accepted/rejected), created_at, responded_at
- When pending suggestion exists, show a prominent banner on /coach page: "Bạn đã lỗ 3 lần liên tiếp. Giảm mức rủi ro từ {current} xuống {suggested}?"
- Two buttons: "Đồng ý giảm" (accept) and "Giữ nguyên" (reject) — both record the response
- Risk level changes propagate to pick generation — lower risk = more aggressive safety scoring
- Only 1 pending suggestion at a time — don't spam if user already rejected

### Sector Preference Learning (ADPT-02)
- Analyze trades grouped by ticker.sector to compute sector_pnl and sector_win_rate
- New `sector_preferences` table: id, sector (text), total_trades, win_count, loss_count, net_pnl, preference_score (computed), updated_at
- Preference score: (win_rate × 0.6) + (normalized_pnl × 0.4) — higher = user does better in this sector
- Refresh sector preferences weekly (same batch job as habit detection)
- Expose via GET /api/behavior/sector-preferences
- Pick generation in PickService applies sector bias: multiply composite_score by (1 + preference_score × 0.1) for preferred sectors, (1 - penalty × 0.1) for poor sectors
- Display on /coach page as "Ngành bạn giao dịch tốt" section — ranked list of sectors with win rate + P&L
- Minimum 3 trades in a sector before applying any bias (avoid overfitting on 1 trade)

### Frontend & API
- New API routes in backend/app/api/behavior.py:
  - POST /api/behavior/event (log viewing event)
  - GET /api/behavior/viewing-stats (top viewed tickers)
  - GET /api/behavior/habits (detected trading habits)
  - GET /api/behavior/sector-preferences (sector performance)
  - GET /api/behavior/risk-suggestion (current pending suggestion)
  - POST /api/behavior/risk-suggestion/{id}/respond (accept/reject)
- Coach page additions: 3 new sections below pick history
  1. Risk suggestion banner (conditional, above everything when pending)
  2. "Thói quen giao dịch" card
  3. "Mã bạn hay xem" + "Ngành bạn giao dịch tốt" side by side

### Scheduler Jobs
- `weekly_behavior_analysis` job: runs Sunday 20:00, detects habits + refreshes sector preferences
- `check_consecutive_losses` job: runs after each trade creation (or daily after market close) — checks if last 3 trades are losses

### Agent's Discretion
- Exact thresholds for habit detection (5% continued rise, 10% unrealized loss, 2 hours for impulsive) — adjust based on testing
- Sector preference normalization method — simple min-max or z-score
- Whether habit detection needs a dedicated table or can be computed on-the-fly from trades

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `UserRiskProfile` model with risk_level — already exists from Phase 43
- `Trade` model with net_pnl, daily_pick_id, ticker_id — for habit analysis
- `Ticker` model with sector field — for sector grouping
- `DailyPrice` model — for "price continued rising after sell" detection
- `NewsArticle` model with ticker associations — for impulsive trade detection
- `PickService.generate_daily_picks()` — insert sector bias here
- Scheduler chaining pattern — well-established for new jobs

### Integration Points
- `backend/app/api/router.py` — register behavior_router
- `backend/app/models/__init__.py` — export new models
- `frontend/src/app/coach/page.tsx` — add behavior sections
- `frontend/src/lib/api.ts` + `hooks.ts` — add behavior fetch/hooks
- `backend/app/services/pick_service.py` — apply sector bias in scoring

</code_context>

<deferred>
## Deferred Ideas

- **Real-time habit notifications**: Push notification when impulsive pattern detected — defer to future
- **Gamification**: Badges for good trading habits — out of scope
- **ML-based pattern detection**: Use more sophisticated models for habit detection — keep simple rules for now
- **Multi-factor adaptive strategy**: Combine sector + timing + position size learning — keep sector-only for v8.0
</deferred>

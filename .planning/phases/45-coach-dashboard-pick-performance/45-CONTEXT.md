# Phase 45: Coach Dashboard & Pick Performance - Context

**Gathered:** 2026-04-23
**Status:** Ready for planning

<domain>
## Phase Boundary

The /coach page becomes the daily landing page — displaying today's picks, open trades, performance metrics, and full pick history with actual outcome tracking for every pick. This phase unifies Phase 43 (picks) and Phase 44 (trades) into a single coaching dashboard. No new behavior tracking or adaptive strategy — those come in Phase 46.

</domain>

<decisions>
## Implementation Decisions

### Pick Outcome Tracking (CDSH-02)
- Add outcome columns to `daily_picks` table via migration 021: pick_outcome (pending/winner/loser/expired), days_held (int nullable), hit_stop_loss (bool), hit_take_profit_1 (bool), hit_take_profit_2 (bool), actual_return_pct (Decimal nullable)
- Outcome computed automatically from DailyPrice data — daily scheduler job checks all "pending" picks older than 1 day
- Outcome logic: if close <= stop_loss → loser (hit_stop_loss=true); if close >= take_profit_1 → winner (hit_take_profit_1=true); if days_held > 10 trading days → expired
- actual_return_pct = ((latest_close - entry_price) / entry_price) × 100
- Track ALL picks including those the user didn't trade — CDSH-02 explicitly requires this
- For picks the user DID trade (via daily_pick_id FK): also show realized P&L from trades alongside the theoretical outcome

### Performance Cards (CDSH-03)
- 4 performance cards above the main content:
  1. Win Rate: (winners / closed_picks) × 100% — only counts picks with outcome ≠ pending
  2. Total P&L: sum of realized net_pnl from all trades linked to picks — shows actual trading result
  3. Average R:R: mean of (actual_return_pct / abs(entry - stop_loss) × 100) for closed picks — measures risk-adjusted performance
  4. Current Streak: consecutive wins or losses, labeled "🔥 N thắng liên tiếp" or "❄️ N thua liên tiếp"
- Cards show skeleton loading state while data fetches

### Unified Coach Page Layout (CDSH-01)
- Single /coach page with 4 sections in vertical scroll:
  1. **Performance Cards** — 4-card grid (new)
  2. **Today's Picks** — existing pick cards grid (from Phase 43, keep as-is)
  3. **Open Trades** — trades table filtered to open positions only (reuse TradesTable from Phase 44 with filter)
  4. **Pick History** — table of all past picks with outcome columns (new component)
- "Almost Selected" list moves inside Today's Picks section as collapsible (already is)
- Profile settings dialog remains accessible from header

### Pick History Table (CDSH-02)
- Columns: Date, Mã, Rank, Entry, SL, TP1, Outcome badge, Return %, Days Held, Traded? (icon if user has trades linked)
- Outcome badges: "Thắng" (green), "Thua" (red), "Hết hạn" (neutral), "Đang theo dõi" (blue)
- Default sort by date DESC, filterable by outcome status
- Paginated (20 per page)
- Includes ALL picks — not just traded ones

### Backend API
- GET /api/picks/history?page=1&per_page=20&status=all — paginated pick history with outcomes
- GET /api/picks/performance — aggregated performance stats for cards
- Outcome computation: new method in PickService, called by a daily scheduler job after market close
- No manual pick close endpoint — outcomes are auto-computed from price data

### Scheduler Job
- New job `daily_pick_outcome_check` runs after market close (~15:30), checks all pending picks
- Chains after existing `daily_pick_generation` job
- Idempotent — can re-run safely, only updates picks still in "pending" status

### Frontend Integration
- Reuse existing useDailyPicks() for today's section
- Reuse existing useTrades() with filter for open trades section  
- New usePickHistory() and usePickPerformance() hooks
- New fetchPickHistory() and fetchPickPerformance() API functions

### Agent's Discretion
- Pick detail page (click through from history) — build only if straightforward, otherwise defer
- Chart overlay showing price vs entry/SL/TP on pick history — defer to future
- Performance breakdown by rank — include in stats response if simple aggregation

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/app/coach/page.tsx` (80 lines) — existing coach page, will be extended
- `frontend/src/components/pick-card.tsx` — existing pick display, keep as-is
- `frontend/src/components/trades-table.tsx` — reuse for open trades section (filter)
- `frontend/src/components/trade-stats-cards.tsx` — pattern reference for performance cards
- `backend/app/services/pick_service.py` — add outcome methods here
- `backend/app/models/daily_pick.py` — add outcome columns
- `backend/app/models/daily_price.py` — DailyPrice has OHLCV for outcome computation
- `backend/app/scheduler/manager.py` — chain new job after pick generation

### Integration Points
- `backend/app/api/picks.py` — add history and performance endpoints
- `backend/app/schemas/picks.py` — add outcome response schemas
- `frontend/src/lib/api.ts` — add fetch functions
- `frontend/src/lib/hooks.ts` — add hooks
- DailyPick.daily_pick_id FK from Trade model (Phase 44) — query trades linked to picks

</code_context>

<deferred>
## Deferred Ideas

- **Pick detail page with chart**: Detailed view per pick with price chart overlay — could be Phase 46+ or future
- **Outcome notifications**: Telegram/push notification when pick hits SL/TP — future feature
- **AI analysis of performance patterns**: "You tend to lose on banking stocks" — this is Phase 46 territory (ADPT-02)
- **Manual outcome override**: Let user manually mark pick outcome — keep automated only for now
</deferred>

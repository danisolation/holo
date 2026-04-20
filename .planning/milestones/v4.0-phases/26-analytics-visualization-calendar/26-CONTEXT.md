# Phase 26: Analytics Visualization & Calendar — Context

## Phase Goal
Users can visualize trading performance patterns through charts, calendar heatmap, streak indicators, and periodic summaries.

## Requirements
- **UI-02**: Calendar heatmap (GitHub-style) — green win days, red loss days, intensity proportional to magnitude
- **UI-03**: Streak tracking — current and longest win/loss streaks, visual warning when loss streak >5
- **UI-04**: Timeframe comparison (swing vs position) — side-by-side win rate, avg P&L
- **UI-06**: Weekly/monthly performance summary tables — win rate, P&L, trade count, avg R:R per period

## Key Decisions (pre-resolved)

### New npm dependency
- `react-activity-calendar@^3.2.0` — GitHub-style contribution calendar heatmap component
- Already identified in STACK.md as the only new frontend dep for v4.0

### Backend API (already built in Phase 24)
Analytics endpoints we'll consume:
- `GET /api/paper-trading/analytics/summary` — win rate, P&L totals
- `GET /api/paper-trading/analytics/equity-curve` — time-series for chart
- `GET /api/paper-trading/analytics/drawdown` — max drawdown with periods
- `GET /api/paper-trading/analytics/direction` — LONG vs BEARISH breakdown
- `GET /api/paper-trading/analytics/confidence` — LOW/MEDIUM/HIGH brackets
- `GET /api/paper-trading/analytics/risk-reward` — R:R achieved vs predicted
- `GET /api/paper-trading/analytics/profit-factor` — profit factor + EV
- `GET /api/paper-trading/analytics/sector` — sector breakdown

### New backend endpoints needed
- **Streak endpoint**: `GET /api/paper-trading/analytics/streaks` — current win/loss streak, longest win/loss streak, streak history
- **Timeframe comparison**: `GET /api/paper-trading/analytics/timeframe` — swing vs position stats
- **Periodic summary**: `GET /api/paper-trading/analytics/periodic?period=weekly|monthly` — win rate, P&L, trade count, avg R:R per period
- **Calendar data**: `GET /api/paper-trading/analytics/calendar` — daily P&L aggregates for heatmap

### Frontend patterns (same as Phase 25)
- React-query hooks for data fetching
- shadcn/ui components (Card, Table, Badge, Tabs)
- Recharts for bar/area charts (equity curve, drawdown, sector bars)
- Vietnamese labels
- These components fill the "Phân tích" and "Lịch" disabled tabs from Phase 25

### Tab Integration
- Phase 25 created disabled "Phân tích" and "Lịch" tabs
- This phase enables them with real content:
  - **Phân tích tab**: Equity curve chart, drawdown chart, direction/confidence/sector breakdowns, streak cards, timeframe comparison, profit factor + R:R
  - **Lịch tab**: Calendar heatmap + weekly/monthly summary tables

## Constraints
- Only new dep: `react-activity-calendar`
- Need 4 new backend analytics endpoints (streaks, timeframe, periodic, calendar)
- All analytics computed from paper_trades table (CLOSED statuses only)

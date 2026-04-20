---
phase: 24
slug: api-analytics-engine
type: infrastructure
generated: auto
---

# Phase 24 Context: API & Analytics Engine

## Phase Goal
Users can query paper trading data and analytics through a complete REST API that measures AI signal quality.

## Requirements
- **PT-09**: Manual follow — create paper trade with custom entry/SL/TP via API
- **AN-01**: Win rate (overall, by direction, by timeframe)
- **AN-02**: Total realized P&L in VND and % of initial capital
- **AN-03**: Equity curve time-series
- **AN-04**: Max drawdown (VND, %, drawdown periods)
- **AN-05**: Direction analysis (LONG vs BEARISH performance)
- **AN-06**: AI score correlation (confidence bracket → win rate, avg P&L)
- **AN-07**: R:R achieved vs predicted
- **AN-08**: Profit factor (gross profit / gross loss) + expected value per trade
- **AN-09**: Sector analysis (performance by industry group)

## Research-Backed Constraints

### API Structure
- New FastAPI router: `backend/app/api/paper_trading.py`
- Register in `backend/app/main.py` alongside existing routers
- Follow existing API patterns from `backend/app/api/analysis.py`

### Endpoints
1. `GET /api/paper-trading/trades` — list trades with filters (status, direction, timeframe)
2. `GET /api/paper-trading/trades/{id}` — single trade detail
3. `POST /api/paper-trading/trades/follow` — manual follow (PT-09)
4. `GET /api/paper-trading/trades/{id}/close` — manual close (CLOSED_MANUAL)
5. `GET /api/paper-trading/config` — get SimulationConfig
6. `PUT /api/paper-trading/config` — update SimulationConfig
7. `GET /api/paper-trading/analytics/summary` — win rate, total P&L, trade count (AN-01, AN-02)
8. `GET /api/paper-trading/analytics/equity-curve` — time-series data (AN-03)
9. `GET /api/paper-trading/analytics/drawdown` — max drawdown with periods (AN-04)
10. `GET /api/paper-trading/analytics/direction` — LONG vs BEARISH comparison (AN-05)
11. `GET /api/paper-trading/analytics/confidence` — brackets LOW/MEDIUM/HIGH (AN-06)
12. `GET /api/paper-trading/analytics/risk-reward` — achieved vs predicted R:R (AN-07)
13. `GET /api/paper-trading/analytics/profit-factor` — profit factor + EV (AN-08)
14. `GET /api/paper-trading/analytics/sector` — by industry group (AN-09)

### Analytics Computation
- All analytics computed from `paper_trades` table (closed trades only for most metrics)
- Equity curve: cumulative P&L ordered by closed_date
- Drawdown: peak-to-trough from equity curve
- Confidence brackets: 1-3 LOW, 4-6 MEDIUM, 7-10 HIGH
- Sector: join paper_trades → tickers → industry field
- R:R achieved: actual P&L / (entry - SL) vs predicted risk_reward_ratio

### Manual Follow (PT-09)
- Accept: symbol, direction, entry_price, stop_loss, take_profit_1, take_profit_2, timeframe, confidence, position_size_pct
- ai_analysis_id = NULL (not linked to any signal)
- Status = PENDING (will activate at D+1 like auto-tracked trades)
- Use calculate_position_size() for sizing

### Pydantic Schemas
- Create in `backend/app/schemas/paper_trading.py`
- Response models for trades, analytics, config

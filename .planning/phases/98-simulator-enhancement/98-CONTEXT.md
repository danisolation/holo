# Phase 98: Simulator Enhancement - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning
**Mode:** Auto-generated (discuss skipped)

<domain>
## Phase Boundary

Simulator automatically manages positions (auto-sell on SL/TP hit), shows portfolio performance visually, and integrates AI sell signals.

Requirements: SIM-01, SIM-02, SIM-03, SIM-04, SIM-05
- SIM-01: Auto-sell khi giá hit Stop Loss target
- SIM-02: Auto-sell khi giá hit Take Profit target
- SIM-03: Portfolio history chart (equity curve theo thời gian)
- SIM-04: P&L timeline (bảng lịch sử giao dịch với running P&L)
- SIM-05: Sell signal integration (AI phát tín hiệu bán → auto-execute sell)

</domain>

<decisions>
## Implementation Decisions

### Agent's Discretion
All implementation choices are at the agent's discretion. Key context:
- Simulator already has BUY logic, manual SELL, portfolio tracking, FIFO matching
- DailyPrice.close stored in nghìn đồng (×1000 for VND comparison)
- DailyPick.entry_price and SL/TP from Gemini in VND
- Fee structure: 0.15% broker + 0.1% sell tax
- Auto-trade mode already exists (toggle in frontend)
- Need new scheduled job or hook into existing daily flow for SL/TP checks

</decisions>

<code_context>
## Existing Code Insights

### Key Files
- `backend/app/services/simulator_service.py` — Core simulator (buy, sell, fees, FIFO, portfolio)
- `backend/app/services/auto_trade_service.py` — Auto-trade from daily picks
- `backend/app/api/simulator.py` — Simulator API endpoints
- `backend/app/models/simulator.py` — SimulatorPortfolio, SimulatorTrade, SimulatorLot
- `frontend/src/app/simulator/page.tsx` — Simulator dashboard
- `frontend/src/lib/api.ts` — API functions (simulator endpoints already exist)

### Price Units
- DailyPrice.close: nghìn đồng (26.9 = 26,900 VND)
- DailyPick.entry_price, stop_loss, take_profit: VND (actual đồng)
- SimulatorTrade.price: VND
- Need ×1000 conversion when comparing DailyPrice.close to SL/TP targets

</code_context>

<specifics>
## Specific Ideas

- SL/TP check should run daily after market close (use daily prices, not intraday)
- Equity curve needs a new table or computed from trade history
- Sell signal = AI outputs signal "ban" or "giu" for ticker with open position

</specifics>

<deferred>
## Deferred Ideas

None.

</deferred>

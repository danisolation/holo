---
phase: 98-simulator-enhancement
plan: 01
subsystem: simulator
tags: [auto-sell, sl-tp, ai-signals, scheduler]
dependency_graph:
  requires: [simulator_service, auto_trade_service, scheduler]
  provides: [check_sl_tp_hits, execute_sell_signals, daily_simulator_sl_tp_check]
  affects: [simulator_trades, simulator_lots, scheduler_chain]
tech_stack:
  added: []
  patterns: [FIFO sell matching, price unit conversion (nghìn đồng → VND)]
key_files:
  created: []
  modified:
    - backend/app/services/simulator_service.py
    - backend/app/services/auto_trade_service.py
    - backend/app/scheduler/jobs.py
    - backend/app/scheduler/manager.py
    - backend/app/api/simulator.py
decisions:
  - "AI sell signals always execute for open positions (capital protection) — no toggle check"
  - "SL/TP always executes regardless of any toggle (risk management)"
  - "Price conversion: DailyPrice.close × 1000 before comparing to SL/TP values in VND"
metrics:
  duration: ~5min
  completed: 2026-05-14
  tasks_completed: 2
  tasks_total: 2
  tests_passed: 499
---

# Phase 98 Plan 01: SL/TP Auto-Sell + AI Sell Signals Summary

Auto-sell service methods for SL/TP hits and AI bearish signals, with scheduler chaining after daily accuracy tracking and manual trigger endpoint.

## Completed Tasks

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | SL/TP auto-sell service + scheduler job | `04bc82d` | check_sl_tp_hits() in SimulatorService, daily_simulator_sl_tp_check job, chain in manager.py |
| 2 | AI sell signal auto-execution | `624a83c` | execute_sell_signals() in AutoTradeService, POST /simulator/check-auto-sell endpoint |

## Implementation Details

### check_sl_tp_hits() — SimulatorService
- Queries all open lots grouped by ticker_id
- For each ticker, finds linked DailyPick via most recent BUY trade's daily_pick_id
- Gets latest DailyPrice.close, converts `× 1000` (nghìn đồng → VND)
- Compares: `close_vnd <= stop_loss` → SL hit, `close_vnd >= take_profit_1` → TP hit
- Executes sell via existing `create_trade()` with FIFO matching and proper fees
- source="ai_auto", user_notes describes SL or TP trigger

### execute_sell_signals() — AutoTradeService
- Queries open positions, checks latest unified AI analysis for each ticker
- If signal == "ban" → auto-sell all remaining shares at latest close price (× 1000)
- Always executes for capital protection (no auto-trade toggle check)

### Scheduler Chain
- `daily_accuracy_tracking` → `daily_simulator_sl_tp_check` (new link)
- Job runs both SL/TP check AND AI sell signal check
- Added to _JOB_NAMES display dict in manager.py

### Manual Trigger
- POST `/simulator/check-auto-sell` → runs both checks on demand
- Returns `{sl_tp_sells, signal_sells, results}`

## Decisions Made

1. **AI sell signals always execute** — Selling on bearish signals is defensive capital protection. The auto-trade toggle only gates BUY side via frontend.
2. **SL/TP always execute** — Risk management should never be disabled.
3. **Single scheduler job for both** — Combined into `daily_simulator_sl_tp_check` to avoid two separate chain links.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
- [x] check_sl_tp_hits() exists in SimulatorService
- [x] execute_sell_signals() exists in AutoTradeService
- [x] daily_simulator_sl_tp_check job exists in jobs.py
- [x] Chain in manager.py after accuracy_tracking
- [x] Price conversion (* 1000) in both methods
- [x] Manual trigger endpoint at POST /simulator/check-auto-sell
- [x] All 499 tests pass
- [x] Commits: 04bc82d, 624a83c

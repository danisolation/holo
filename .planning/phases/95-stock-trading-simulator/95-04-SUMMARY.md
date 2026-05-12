---
phase: 95-stock-trading-simulator
plan: "04"
subsystem: simulator
tags: [auto-trade, ai-signals, paper-trading]
dependency_graph:
  requires: ["95-02"]
  provides: ["auto-trade-engine", "pending-signals-api", "signal-approval-ui"]
  affects: ["simulator-page", "simulator-api"]
tech_stack:
  added: []
  patterns: ["service-layer auto-trade", "signal filtering with traded-pick exclusion"]
key_files:
  created:
    - backend/app/services/auto_trade_service.py
    - frontend/src/components/simulator/pending-signals.tsx
  modified:
    - backend/app/api/simulator.py
    - backend/app/schemas/simulator.py
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/simulator/page.tsx
decisions:
  - "Used apiFetch helper (not raw fetch) for signal API functions — consistent with existing pattern"
  - "Skip signals MVP: acknowledge count only, signals expire after days_back window"
metrics:
  duration: ~4 minutes
  completed: "2026-05-12"
---

# Phase 95 Plan 04: Auto-Trade Engine Summary

**One-liner:** Auto-trade service reads AI daily picks, filters untraded signals, presents pending UI with execute/skip per signal and bulk execute.

## What Was Built

### Backend: Auto-Trade Service
- **`AutoTradeService`** in `backend/app/services/auto_trade_service.py`:
  - `get_pending_signals(days_back)`: Queries daily_picks with status="picked" from last N days, excludes already-traded picks by checking simulator_trades.daily_pick_id
  - `execute_ai_signals(pick_ids)`: Creates BUY trades via SimulatorService.create_trade with source="ai_auto", links daily_pick_id
  - `skip_signals(pick_ids)`: MVP acknowledgment (signals expire from pending after days_back window)

### Backend: New Endpoints
- `GET /simulator/signals/pending` — Returns pending AI signals with entry_price, stop_loss, take_profit_1, composite_score, rank
- `POST /simulator/signals/execute` — Executes BUY trades for specified pick_ids (validated by Pydantic min_length=1)
- `POST /simulator/signals/skip` — Acknowledges skipped signals

### Backend: New Schemas
- `PendingSignalResponse` — Full signal data for frontend display
- `ExecuteSignalsRequest` — Validated pick_ids list with min_length=1 (mitigates T-95-07)

### Frontend: Pending Signals Component
- **`PendingSignals`** component showing untraded daily picks as a card list
- Each signal row: ticker symbol/name, pick date, entry price, SL, TP1, composite score, rank, position size
- Per-signal "Thực hiện" (execute, green) and "Bỏ qua" (skip, outline) buttons
- "Thực hiện tất cả" bulk execute button in card header
- Auto-trade mode banner when localStorage toggle is on
- Empty state: "Không có tín hiệu AI mới"
- Loading/disabled states during mutations

### Frontend: API & Hooks
- `fetchPendingSignals`, `executeSignals`, `skipSignals` API functions using apiFetch
- `usePendingSignals`, `useExecuteSignals`, `useSkipSignals` TanStack Query hooks
- Invalidates ["simulator"] queries on execute, ["simulator", "signals"] on skip

### Frontend: Page Update
- New "Tín hiệu AI" tab added as first tab in simulator page
- Tab order: Tín hiệu AI | Giao dịch mới | Lịch sử | Độ chính xác AI

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

---
phase: 98-simulator-enhancement
plan: "02"
subsystem: simulator
tags: [equity-curve, pnl-timeline, recharts, visualization]
dependency_graph:
  requires: [simulator-trades, daily-prices]
  provides: [equity-history-api, pnl-timeline-api, equity-chart-component, pnl-timeline-component]
  affects: [simulator-page]
tech_stack:
  added: []
  patterns: [trade-replay-equity-curve, cumulative-pnl-tracking]
key_files:
  created:
    - frontend/src/components/simulator/equity-chart.tsx
    - frontend/src/components/simulator/pnl-timeline.tsx
  modified:
    - backend/app/services/simulator_service.py
    - backend/app/api/simulator.py
    - backend/app/schemas/simulator.py
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/app/simulator/page.tsx
decisions:
  - "Equity curve computed by replaying trades (not stored), using trade prices as approximation for historical market value"
  - "Today's equity point uses actual DailyPrice.close × 1000 for current accuracy"
  - "P&L timeline shows ALL trades (buy + sell) with cumulative only changing on sells"
metrics:
  duration: ~8min
  completed: 2025-05-14
---

# Phase 98 Plan 02: Equity History & P&L Timeline Summary

**One-liner:** Portfolio equity curve via trade replay + P&L timeline table with running cumulative profit/loss, integrated as "Hiệu suất" tab in simulator.

## What Was Built

### Backend (Task 1)
- **Schemas:** `EquityHistoryPoint`, `EquityHistoryResponse`, `PnlTimelineEntry`, `PnlTimelineResponse` in `schemas/simulator.py`
- **Service methods:**
  - `get_equity_history()`: Replays all trades chronologically to reconstruct equity curve. Tracks running cash + market value at each trade date. Final point uses latest DailyPrice × 1000 for VND conversion.
  - `get_pnl_timeline()`: Returns all trades ordered by date with running cumulative P&L. BUY trades show net_pnl=None; SELL trades accumulate into cumulative.
- **Endpoints:** `GET /simulator/equity-history` and `GET /simulator/pnl-timeline`

### Frontend (Task 2)
- **Types & API:** Added `EquityHistoryResponse`, `PnlTimelineResponse` types and fetch functions in `api.ts`
- **Hooks:** `useEquityHistory()` and `usePnlTimeline()` with 60s staleTime
- **EquityChart:** Recharts `LineChart` with interactive tooltip (date + VND value), dashed reference line at starting capital (100M), green/red line based on performance, responsive container
- **PnlTimeline:** Table with columns Ngày/Mã/Loại/Số lượng/Giá/P&L/P&L tích lũy/Nguồn. Color-coded P&L values. Source badges (AI blue, Manual gray). Side badges (MUA green, BÁN red).
- **Simulator page:** New "Hiệu suất" tab (index 3) between "Lịch sử" and "Độ chính xác AI"

## Verification Results

- ✅ Backend: 499 tests pass (`python -m pytest tests/ -x -q`)
- ✅ Frontend: `npx next build` compiles successfully, TypeScript clean
- ✅ Backend imports verified for new service methods and endpoints

## Deviations from Plan

None — plan executed exactly as written.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | `ac69e21` | Backend: equity history + P&L timeline endpoints |
| 2 | `30c81a0` | Frontend: equity chart + P&L timeline components |

## Self-Check: PASSED

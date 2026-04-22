# Phase 34: Backtest Dashboard — Context

## Phase Goal
Users can configure, launch, monitor progress, and review full backtest results through a dedicated /backtest page with interactive visualizations.

## Requirements
- DASH-01: Trang /backtest với form cấu hình (thời gian, vốn, slippage) và nút "Run Backtest"
- DASH-02: Progress bar real-time hiển thị tiến trình backtest đang chạy (% hoàn thành, ETA)
- DASH-03: Equity curve chart (Recharts area chart) — AI vs VN-Index overlay so sánh trực quan
- DASH-04: Bảng thống kê tổng hợp — win rate, total P&L, max drawdown, Sharpe ratio, số lệnh
- DASH-05: Bảng chi tiết từng lệnh — symbol, direction, entry/exit price, P&L, holding time
- DASH-06: Charts breakdown theo ngành, confidence level, timeframe (bar/pie charts)

## Key Decisions

1. **Route**: `/dashboard/backtest` (same pattern as `/dashboard/paper-trading`)
2. **Component Pattern**: Follow paper-trading page — page.tsx with Tabs component, each tab is a separate component
3. **Tab Structure**: 
   - Tab 1 "Cấu hình" — Config form + Run button + Progress bar (DASH-01, DASH-02)
   - Tab 2 "Kết quả" — Equity curve chart + Stats cards (DASH-03, DASH-04)  
   - Tab 3 "Lệnh" — Trade log table (DASH-05)
   - Tab 4 "Phân tích" — Breakdown charts by sector, confidence, timeframe (DASH-06)
4. **Data Fetching**: @tanstack/react-query with polling for progress (refetchInterval while running)
5. **Charts**: Recharts AreaChart for equity curve, BarChart for breakdowns
6. **Polling**: While backtest status="running", poll GET /backtest/runs/latest every 5s
7. **UI Components**: shadcn/ui Card, Table, Badge, Button, Input, Tabs
8. **Vietnamese labels**: All UI text in Vietnamese (consistent with rest of app)
9. **Navbar**: Add "Backtest" link to navbar between Paper Trading and Health

## Backend API Available (from Phases 32-33)
- POST /api/backtest/runs — Start new backtest
- GET /api/backtest/runs/latest — Get latest run status
- GET /api/backtest/runs/{id} — Get specific run
- POST /api/backtest/runs/{id}/cancel — Cancel running backtest
- GET /api/backtest/runs/{id}/trades — Get trade list
- GET /api/backtest/runs/{id}/equity — Get equity snapshots
- GET /api/backtest/runs/{id}/analytics — Performance + breakdowns
- GET /api/backtest/runs/{id}/benchmark — AI vs VN-Index comparison

## Dependencies
- Phase 32 & 33 complete ✅
- Recharts already installed (used in paper-trading)
- shadcn/ui components available
- @tanstack/react-query available

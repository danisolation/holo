---
phase: 16
plan: 16-02
title: "Frontend — WebSocket Hook + ConnectionStatus + PriceFlash"
subsystem: frontend
tags: [websocket, real-time, react-hook, context-provider, animation]
dependency_graph:
  requires: [websocket-endpoint, connection-manager]
  provides: [use-realtime-prices-hook, realtime-price-provider, connection-status-indicator, price-flash-cell]
  affects: [watchlist-table, holdings-table, ticker-detail-page, navbar, app-layout]
tech_stack:
  added: []
  patterns: [react-context-provider, websocket-hook, exponential-backoff, css-transition-flash]
key_files:
  created:
    - frontend/src/lib/use-realtime-prices.ts
    - frontend/src/components/connection-status.tsx
    - frontend/src/components/price-flash-cell.tsx
  modified:
    - frontend/src/app/layout.tsx
    - frontend/src/components/navbar.tsx
    - frontend/src/components/watchlist-table.tsx
    - frontend/src/components/holdings-table.tsx
    - frontend/src/app/ticker/[symbol]/page.tsx
decisions:
  - "Global RealtimePriceProvider wraps app layout — single WebSocket connection shared by all pages"
  - "useRealtimePrices(symbols) subscribes via context — components don't manage WS directly"
  - "WebSocket URL derived at runtime: strip /api from NEXT_PUBLIC_API_URL, replace http→ws, append /ws/prices"
  - "PriceFlashCell uses 100ms timeout + CSS transition-colors duration-1000 for smooth flash-then-fade"
  - "font-bold replaced with font-semibold on ticker detail h1 per typography contract"
metrics:
  duration: "6m"
  completed: "2026-04-17"
  tasks_completed: 4
  tasks_total: 4
  test_count: 0
  total_tests: 395
---

# Phase 16 Plan 02: Frontend — WebSocket Hook + ConnectionStatus + PriceFlash Summary

**One-liner:** React context-based WebSocket hook with auto-reconnect (1s-30s backoff), connection status indicator in navbar (4 states), and CSS transition price flash cells integrated into watchlist/holdings/ticker pages.

## What Was Built

### T-16-03: useRealtimePrices hook + RealtimePriceProvider
- **`use-realtime-prices.ts`**: Full WebSocket lifecycle manager with types (`RealtimePrice`, `ConnectionStatus`, `UseRealtimePricesReturn`)
- **`RealtimePriceProvider`**: React context provider that owns the single WebSocket connection — all pages share one connection
- **`useRealtimePrices(symbols)`**: Hook that subscribes to specific symbols via context, returns `{ prices, status, subscribedCount }`
- WebSocket URL derivation: strips `/api`, replaces `http→ws`, appends `/ws/prices`
- Auto-reconnect with exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s max
- Handles `price_update`, `heartbeat`, `market_status` message types
- Provider added to `layout.tsx` wrapping all children inside `<Providers>`

### T-16-04: ConnectionStatusIndicator component
- **`connection-status.tsx`**: 4-state indicator (connected/reconnecting/disconnected/market_closed)
- Connected: green-500 circle with `animate-pulse` + "Live" label
- Reconnecting: yellow-500 circle + "Đang kết nối..."
- Disconnected: red-500 circle + "Mất kết nối"
- Market closed: muted-foreground circle + "Thị trường đóng"
- Circle: 8px `rounded-full`, label: 12px `text-muted-foreground`
- Title tooltip: "Kết nối WebSocket: ... • X mã đang theo dõi"
- Mobile: icon-only below `sm` breakpoint (label hidden)
- Placed in navbar right side, before theme toggle

### T-16-05: PriceFlashCell component
- **`price-flash-cell.tsx`**: Wrapper that flashes green/red on price changes
- Green flash: `bg-green-100/60 dark:bg-green-900/30` on increase
- Red flash: `bg-red-100/60 dark:bg-red-900/30` on decrease
- CSS `transition-colors duration-1000` for smooth 1s fade
- Wrapper styling: `rounded px-1 -mx-1`
- Respects `prefers-reduced-motion` — skips animation entirely

### T-16-06: Integration into existing pages
- **WatchlistTable**: Subscribes to watchlist symbols via `useRealtimePrices(watchlist)`, wraps price and change% cells with `PriceFlashCell`, falls back to market data when no RT price
- **HoldingsTable**: Subscribes to held symbols, wraps market price (Giá TT) cell with `PriceFlashCell`
- **Ticker detail page**: Subscribes to `[upperSymbol]`, shows live price + change% with flash animation in header next to ticker name
- Typography fix: `font-bold` → `font-semibold` on ticker detail h1

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing] Typography contract enforcement on ticker detail h1**
- **Found during:** Task 4 (T-16-06)
- **Issue:** Ticker detail page h1 used `font-bold` (700), violating the typography contract
- **Fix:** Changed to `font-semibold` (600) per UI-SPEC
- **Files modified:** frontend/src/app/ticker/[symbol]/page.tsx
- **Commit:** f35493f

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| T-16-03 | 36f8a0d | useRealtimePrices hook + RealtimePriceProvider context |
| T-16-04 | ef92654 | ConnectionStatusIndicator component in navbar |
| T-16-05 | d45270b | PriceFlashCell component with flash animation |
| T-16-06 | f35493f | Integrate real-time prices into WatchlistTable, HoldingsTable, ticker detail |

## Self-Check: PASSED

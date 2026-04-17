# Phase 16 — UI Design Contract: Real-Time WebSocket

## Scope

Two new UI elements:
1. **ConnectionStatusIndicator** — Navbar connection state badge
2. **PriceFlashCell** — Real-time price cells with flash animation

Plus integration hook `useRealtimePrices` that merges into existing react-query cache.

## Design System Reference

### Typography Contract
- 4 sizes: 12px / 14px / 18px / 24px
- 2 weights: 400 (regular) / 600 (semibold)
- **NEVER** use `font-bold` (700) — always `font-semibold`

### Color Tokens
- Backgrounds: `bg-card`, `bg-muted`
- Text: `text-foreground`, `text-muted-foreground`
- Flash green: `bg-green-100/60 dark:bg-green-900/30` → transparent (1s transition)
- Flash red: `bg-red-100/60 dark:bg-red-900/30` → transparent (1s transition)

---

## Component 1: ConnectionStatusIndicator

**Location:** Navbar, right side, before theme toggle
**Layout:** Inline flex, icon + text

### Structure
```
┌─────────────────────────────────────────────────────┐
│ Holo  [Dashboard] [Watchlist] [Portfolio]  🟢 Live  │
└─────────────────────────────────────────────────────┘
```

### States
| State | Icon | Label | Color |
|-------|------|-------|-------|
| Connected | 🟢 (circle) | "Live" | green-500 |
| Reconnecting | 🟡 (circle) | "Đang kết nối..." | yellow-500 |
| Disconnected | 🔴 (circle) | "Mất kết nối" | red-500 |
| Market closed | ⚫ (circle) | "Thị trường đóng" | muted-foreground |

### Specs
- Circle: 8px `rounded-full` div with background color
- Label: 12px regular `text-muted-foreground`
- Gap between circle and text: `gap-1.5`
- Connected state: circle pulses with `animate-pulse` CSS
- Tooltip on hover: full details ("Kết nối WebSocket: đang hoạt động • 142 mã đang theo dõi")

---

## Component 2: PriceFlashCell

**Location:** Used in WatchlistTable, portfolio HoldingsTable, and ticker detail price display
**Layout:** Wrapper div around existing price text

### Behavior
- When price value changes (new WebSocket update), cell background flashes:
  - Price increased: green flash (`bg-green-100/60 dark:bg-green-900/30`)
  - Price decreased: red flash (`bg-red-100/60 dark:bg-red-900/30`)
  - No change: no flash
- Flash: immediate color → 1 second CSS transition back to transparent
- Text color remains unchanged (existing up/down coloring stays)

### Specs
- Wrapper: `rounded px-1 -mx-1` (slight padding to contain flash)
- Transition: `transition-colors duration-1000`
- Initial state: `bg-transparent`
- Flash trigger: Set background color class, remove after 1s via useEffect

---

## Hook: useRealtimePrices

### Interface
```typescript
interface RealtimePrice {
  price: number;
  change: number;
  change_pct: number;
  volume: number;
  updated_at: string;
}

interface UseRealtimePricesReturn {
  prices: Record<string, RealtimePrice>;
  status: "connected" | "reconnecting" | "disconnected" | "market_closed";
  subscribedCount: number;
}

function useRealtimePrices(symbols: string[]): UseRealtimePricesReturn
```

### Behavior
- Connects to `ws://host/ws/prices` on mount
- Sends subscribe message: `{ "type": "subscribe", "symbols": [...] }`
- Updates `prices` map on each `price_update` message
- Merges price updates into relevant react-query caches (watchlist, portfolio)
- Auto-reconnects with exponential backoff: 1s → 2s → 4s → 8s → 16s → 30s max
- Disconnects on unmount

---

## Page Layout Updates

### Navbar
Add `ConnectionStatusIndicator` to right side of navbar, before any existing right-side items.

### No other page changes needed
PriceFlashCell wraps existing price displays. The hook integrates via react-query cache merging, so WatchlistTable and HoldingsTable automatically reflect real-time prices.

---

## Accessibility
- Connection status has aria-label with full description
- Flash animation respects `prefers-reduced-motion` — skip flash, just update value
- WebSocket disconnection doesn't break page — falls back to react-query polling

## Responsive Behavior
- ConnectionStatusIndicator: icon-only on mobile (hide text label below sm)
- PriceFlashCell: works at any size

# Phase 25: Dashboard Structure & Trade Management — Context

## Phase Goal
Users can view and manage paper trades through a dedicated dashboard with trade listing, settings, and signal outcome history.

## Requirements
- **UI-01**: Dashboard page at `/dashboard/paper-trading` with tabs: Overview, Trades, Analytics, Calendar, Settings
- **UI-05**: Signal outcome history on ticker detail page — 10 most recent signals with ✅/❌ icons
- **UI-07**: Trade list table (sortable, filterable) — symbol, direction, entry, exit, P&L, status, AI score
- **UI-08**: Settings form — initial capital, auto-track on/off, min confidence threshold

## Key Decisions (pre-resolved)

### Frontend patterns (from codebase)
- **Routing**: Next.js App Router at `src/app/dashboard/paper-trading/page.tsx`
- **Data fetching**: `@tanstack/react-query` hooks in `src/lib/hooks.ts`
- **API client**: `apiFetch<T>()` in `src/lib/api.ts`
- **UI components**: shadcn/ui (Card, Table, Tabs, Badge, Skeleton, Input, Button)
- **State**: zustand for client-side state, react-query for server state
- **Icons**: lucide-react
- **Charts**: Recharts for non-financial, lightweight-charts for candlestick
- **Styling**: Tailwind CSS v4, Vietnamese labels matching existing pages

### Backend API (already built in Phase 24)
- `GET /api/paper-trading/trades` — list with filters (status, direction, timeframe, limit, offset)
- `GET /api/paper-trading/trades/{id}` — single trade detail
- `POST /api/paper-trading/trades/follow` — manual follow (PT-09)
- `POST /api/paper-trading/trades/{id}/close` — manual close
- `GET /api/paper-trading/config` — get simulation config
- `PUT /api/paper-trading/config` — update simulation config
- `GET /api/paper-trading/analytics/summary` — win rate + P&L

### Navigation
- Add "Paper Trading" link to NAV_LINKS in navbar.tsx at `/dashboard/paper-trading`

### Signal outcome on ticker page (UI-05)
- Need a new backend endpoint: `GET /api/paper-trading/trades/by-ticker/{symbol}?limit=10`
- Or reuse existing `GET /api/paper-trading/trades?symbol={symbol}&limit=10` — need to add symbol filter to backend
- Add a small component below the trading plan panel on ticker detail page

### Tab Structure (UI-01)
- Use shadcn `Tabs` component
- Phase 25 implements: Overview (summary cards), Trades (table), Settings
- Phase 26 implements: Analytics (charts), Calendar (heatmap) — but tab headers created now

## Constraints
- No new npm dependencies needed — all shadcn/ui components + Recharts already installed
- Backend API is ready — this is purely frontend work
- Follow existing Vietnamese label conventions
- Mobile-responsive with existing Tailwind patterns

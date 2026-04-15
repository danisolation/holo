# Phase 5: Dashboard & Visualization — Context

## Goal
User can visually explore market data, AI insights, and manage their watchlist through a responsive web dashboard.

## Requirements
- DASH-01: Candlestick charts (lightweight-charts)
- DASH-02: Technical indicator overlays (MA, RSI, MACD, BB)
- DASH-03: Watchlist management
- DASH-04: Ticker detail page (chart + metrics + AI verdict)
- DASH-05: Responsive mobile layout
- DASH-06: Market overview / heatmap by sector

## Success Criteria
1. Interactive candlestick charts with indicator overlays for any ticker
2. Add/remove tickers to watchlist for quick monitoring
3. Ticker detail page: chart + key financials + AI verdict
4. Market overview heatmap of 400 tickers by sector
5. Responsive on mobile browser

## Smart Discuss Decisions (Autonomous Mode)

### Grey Area 1: Frontend Architecture & Data Fetching

**D-1.1: Next.js App Router vs Pages Router**
- Decision: **App Router** (Next.js 15 default)
- Rationale: Modern standard, server components for initial load, client components for interactive charts

**D-1.2: API Communication Pattern**
- Decision: **Direct FastAPI calls via React Query** — no Next.js API routes as proxy
- Rationale: Single-user app, no auth needed, FastAPI already has CORS. Simpler architecture.

**D-1.3: CORS Configuration**
- Decision: **Add CORS middleware to FastAPI** allowing localhost:3000 (dev) and same-origin (prod)
- Rationale: Required for browser-to-API calls from Next.js frontend

**D-1.4: Data Refresh Strategy**
- Decision: **React Query with staleTime: 5min for market data, 30min for analysis** — no WebSocket
- Rationale: Personal use, data updates after market close anyway. Polling sufficient.

### Grey Area 2: Chart & UI Implementation

**D-2.1: Chart Library Integration**
- Decision: **lightweight-charts v5 with React wrapper component** — direct canvas, not a wrapper library
- Rationale: TradingView's own OSS library, purpose-built for financial data. Write a thin React useEffect wrapper.

**D-2.2: Indicator Overlay Strategy**
- Decision: **Separate chart panes** — price + MA/BB on main pane, RSI and MACD on sub-panes below
- Rationale: Standard trading UI pattern. RSI/MACD have different Y-axis scales from price.

**D-2.3: Heatmap Implementation**
- Decision: **Custom CSS Grid heatmap** with colored cells (green/red intensity by daily change %)
- Rationale: 400 cells is trivial for CSS grid. No need for D3 or complex charting library.

**D-2.4: UI Component Library**
- Decision: **shadcn/ui + Tailwind CSS 4** for all non-chart UI
- Rationale: Per STACK.md. Copy-paste components, full control, dark mode via next-themes.

### Grey Area 3: Page Structure & State

**D-3.1: Page Routes**
- Decision: 4 pages: `/` (market overview/heatmap), `/ticker/[symbol]` (detail), `/watchlist`, `/dashboard` (summary/portfolio)
- Rationale: Covers all 6 DASH requirements with clean URL structure

**D-3.2: Watchlist State**
- Decision: **Browser localStorage** via zustand persist — no backend watchlist API
- Rationale: Single user, no sync needed. Faster than API calls. Telegram bot has its own watchlist via DB.

**D-3.3: Dark/Light Mode**
- Decision: **Dark mode default** with toggle via next-themes
- Rationale: Financial dashboards are traditionally dark. Easier on eyes for extended viewing.

**D-3.4: Backend CORS Addition**
- Decision: **Add FastAPI CORSMiddleware in main.py** as part of this phase
- Rationale: Frontend needs it. Minimal backend change, done in Wave 1.

## Upstream Dependencies
- All backend API endpoints from Phases 1-3 (system, analysis, tickers, prices, indicators, AI results)
- No dependency on Phase 4 (Telegram bot)

## Wave Strategy (3 waves)
1. **Wave 1**: Next.js project setup, shadcn/ui, CORS backend fix, API client + React Query hooks, zustand store
2. **Wave 2**: Market overview page (heatmap), ticker detail page (candlestick + indicators + AI verdict)
3. **Wave 3**: Watchlist page, dashboard summary, responsive polish, dark mode

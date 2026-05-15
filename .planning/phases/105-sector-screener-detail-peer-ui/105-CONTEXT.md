# Phase 105: Sector Screener, Detail & Peer UI - Context

**Gathered:** 2026-05-15
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Users can explore sectors through a dedicated screener page with filters, drill into sector detail pages with performance charts, and compare peer tickers side-by-side with radar visualization.

Requirements: SCRN-01, SDET-01, SDET-02, SDET-03, PEER-01, PEER-02

Success Criteria:
1. Screener page at a dedicated route lets user select sector/industry, apply filters, see sortable results
2. Sector detail page shows all tickers with close, % change, volume — each links to ticker detail
3. Sector detail shows performance chart (7D/30D trend)
4. Peer comparison table shows key metrics for same-sector tickers, sorted by selected metric
5. Radar chart visualizes ticker vs sector peer averages across multiple metric dimensions

</domain>

<decisions>
## Implementation Decisions

### Pages & Routes
- /market/screener — dedicated screener page (new route)
- /market/sector/[name] — dynamic sector detail page
- Peer comparison: section on sector detail page (not separate page) — keeps related context together
- Radar chart: shown when user clicks a ticker in peer table

### UI Components
- ScreenerPage: sector/industry dropdown + filter inputs + sortable table
- SectorDetailPage: ticker table + performance line chart (Recharts) + peer radar
- Use existing shadcn/ui components: Table, Select, Input, Card, Button, Tabs
- Recharts LineChart for sector performance trend, RadarChart for peer comparison
- Link each ticker row to /ticker/[symbol] (existing ticker detail page)

### Data Fetching
- Add fetch functions to api.ts matching backend schemas
- React Query hooks with appropriate staleTime
- Sector list from existing useSectorPerformance hook (reuse)

### the agent's Discretion
All remaining UI/UX choices at agent's discretion. Follow existing /market page patterns.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- /market/page.tsx — existing tabs page (Sector, Breadth, Dòng tiền)
- SectorTab, BreadthTab, FlowTab components in components/market/
- api.ts — fetchSectorPerformance, fetchSectorFlow, fetchMarketBreadth already exist
- hooks.ts — useSectorPerformance, useSectorFlow, useMarketBreadth hooks exist
- Recharts: BarChart, RadarChart, LineChart already imported in various components
- navbar.tsx — has "Thị trường" link to /market

### Established Patterns
- useQuery with staleTime 60000-300000ms
- API_BASE + endpoint path for fetch functions
- shadcn/ui Card + Table for data display
- Color scheme: #26a69a (green/positive), #ef5350 (red/negative)

### Integration Points
- Backend APIs: GET /market/screener, /market/sector/{name}, /market/peers/{symbol}
- Backend schemas: ScreenerResponse, SectorDetailResponse, PeerComparisonResponse
- Navigation: add links from existing sector heatmap/ranking to sector detail pages

</code_context>

<specifics>
## Specific Ideas

No specific requirements — follow existing frontend patterns and shadcn/ui components.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

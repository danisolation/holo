# Phase 102: Sector & Breadth Frontend - Context

**Gathered:** 2026-05-14
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous mode)

<domain>
## Phase Boundary

Frontend pages and components for sector and market breadth visualization:
1. Sector Heatmap — colored blocks sized by market cap, color by % change, with sector drill-down
2. Heatmap toggle — switch between price change and volume views
3. Market Breadth Charts — A/D line, % above MA50/MA200, highs/lows as Recharts time-series
4. Sector Radar Chart — 7D vs 30D performance comparison across sectors
5. Sector Ranking Table — sorted by performance with volume change arrows

</domain>

<decisions>
## Implementation Decisions

### Page Structure
- New page: `/market` — contains all sector & breadth visualizations
- Add "Thị trường" to navbar navigation
- Tab layout: "Sector" tab (heatmap + ranking) | "Breadth" tab (A/D, MA breadth, highs/lows) | "Dòng tiền" tab (radar + flow)
- Use existing shadcn/ui Tabs component pattern

### Component Architecture
- `SectorHeatmap` — treemap-style visualization (Recharts Treemap or custom grid)
- `SectorDrilldown` — ticker list modal/panel when clicking sector
- `BreadthCharts` — 3 Recharts LineCharts (A/D, MA breadth, highs/lows)
- `SectorRadar` — Recharts RadarChart comparing 7D vs 30D
- `SectorRanking` — table with sorting, colored arrows for change direction

### Data Fetching
- React Query hooks: useMarketBreadth(), useSectorPerformance(), useSectorFlow()
- API calls to GET /api/market/breadth, GET /api/market/sectors, GET /api/market/sector-flow
- staleTime: 60s (market data changes intraday)

### Styling
- Follow existing shadcn/ui + Tailwind patterns
- Skeleton loading states for all data-fetching components
- Mobile responsive (overflow-x-auto for tables, stacked layout for charts)
- Color scheme: green (#26a69a) for positive, red (#ef5350) for negative

### Agent's Discretion
- Exact treemap vs grid layout for heatmap
- Chart height, axis formatting
- Drill-down: modal vs inline expansion

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/src/components/heatmap.tsx` — existing heatmap component (market overview)
- `frontend/src/lib/api.ts` — apiFetch helper, existing type definitions
- `frontend/src/lib/hooks.ts` — React Query hook patterns
- Recharts already installed (used in equity-chart.tsx)
- shadcn/ui Tabs, Card, Table components available

### Established Patterns
- Pages in `frontend/src/app/{route}/page.tsx`
- API types + fetch functions in `frontend/src/lib/api.ts`
- React Query hooks in `frontend/src/lib/hooks.ts`
- Skeleton states pattern from Phase 99

### Integration Points
- Navbar: add "Thị trường" link in `frontend/src/components/navbar.tsx`
- Types + fetch functions in api.ts
- Hooks in hooks.ts

</code_context>

<specifics>
## Specific Ideas

- Reuse color scheme from existing heatmap component
- Recharts RadarChart for sector rotation visualization
- Date range selector for breadth charts (7D/30D/90D buttons)

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

# Phase 54: Sector Grouping & Heatmap Rework — Context

## Phase Type
UI phase (frontend + backend API changes)

## Goal
User can organize watchlist tickers by sector and the home page heatmap reflects only their curated, sector-grouped watchlist.

## Requirements
- **TAG-01**: User can assign sector/industry group to each watchlist ticker via inline editing
- **TAG-02**: When adding a ticker, sector auto-suggests from vnstock ICB classification data
- **TAG-03**: Heatmap displays only watchlist tickers, grouped by sector

## Success Criteria
1. User can assign sector group to each ticker in watchlist table via inline editing
2. When adding a new ticker, sector field auto-suggests from vnstock ICB data
3. Home page heatmap shows only watchlist tickers, grouped by assigned sector
4. Changing watchlist/sector immediately reflects in heatmap without full page refresh

## Key Context from Research
- `sector_group` column already exists on `user_watchlist` table (added in Phase 52 migration 026)
- Backend needs: API endpoint to update sector_group, endpoint to fetch ICB classification for auto-suggest
- Frontend needs: Inline editable sector field on watchlist table, sector-grouped heatmap component
- Heatmap currently shows all ~400 tickers — needs to be filtered to watchlist only and grouped by sector

## Decisions
- All decisions at agent's discretion (no locked choices from discuss-phase)
- UI should follow existing shadcn/ui + Tailwind patterns in the codebase
- Heatmap uses lightweight-charts or existing charting approach

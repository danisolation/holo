# Phase 55: Discovery Frontend — Context

## Phase Type
UI phase (frontend + backend API)

## Goal
User can browse daily AI-scored stock recommendations on a dedicated Discovery page and add promising tickers to their watchlist with one click.

## Requirements
- **DPAGE-01**: Discovery page shows top-scored tickers with composite score and signal breakdown
- **DPAGE-02**: User can add any discovery ticker to watchlist with single button click, sector auto-suggested from ICB
- **DPAGE-03**: User can filter discovery results by sector and signal type

## Success Criteria
1. Discovery page shows top-scored tickers with composite score and signal breakdown (RSI oversold, MACD cross, volume spike, strong ADX trend)
2. User can add any discovery ticker to their watchlist with single button click, sector auto-suggested from ICB data
3. User can filter discovery results by sector and by signal type
4. Discovery page updates daily after pipeline runs, showing fresh scores each trading day

## Key Context
- Discovery results are in `discovery_results` table (Phase 52) with 6 dimension scores + composite
- Backend needs: API endpoint to query discovery_results with filters (sector, signal type, pagination)
- Frontend needs: Discovery page component with signal cards, filters, add-to-watchlist button
- Reuse SectorCombobox from Phase 54 for sector filtering
- Reuse existing watchlist mutation hooks for add-to-watchlist

## Decisions
- All decisions at agent's discretion (no locked choices from discuss-phase)
- UI should follow existing shadcn/ui + Tailwind patterns
- Discovery page accessible from main navigation

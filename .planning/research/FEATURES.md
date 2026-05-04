# Feature Landscape

**Domain:** Watchlist-centric stock discovery for single-user Vietnamese stock platform
**Researched:** 2025-07-23

## Table Stakes

Features users expect for v10.0 to feel complete. Missing = "this update broke things."

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| AI analysis runs only on watchlist tickers | Core promise of v10.0 — "everything runs on your watchlist" | Medium | `ticker_filter` already supported in AIAnalysisService |
| Daily picks come from watchlist only | Picks should reflect user's curated universe, not random HOSE tickers | Low | Downstream of AI analysis gating — automatic if gating works |
| Heatmap shows only watchlist tickers | Home page should reflect user's focus, not 400 tickers | Medium | Frontend composition of existing APIs |
| Sector grouping on watchlist | User assigns groups for heatmap organization | Medium | New column + inline edit UI |
| Discovery page exists and shows recommendations | The scan result needs a home — can't just exist in DB | Medium | New route + API + card components |
| One-click add from discovery to watchlist | Core discovery-to-watchlist flow must be frictionless | Low | Existing `POST /api/watchlist` + discovery card button |

## Differentiators

Features that make v10.0 genuinely useful beyond "just filtering."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Technical discovery scoring with breakdown | User sees WHY a ticker was recommended (RSI oversold, MACD crossover, volume spike) — builds trust | Medium | Pure computation from existing indicators |
| Auto-suggest sector group from ticker metadata | When user adds ticker, pre-fill sector_group from `Ticker.sector` (vnstock data) | Low | One-line default in API |
| Discovery filters (by signal type, sector) | User can focus discovery on specific sectors or signal types | Low | Query params on discovery API |
| "New since last check" indicator | Badge showing how many new discovery results since user last visited | Low | Track last_viewed timestamp in localStorage |
| Discovery score trend | Show if a ticker's discovery score is improving (today vs yesterday) | Medium | Requires keeping 2+ days of discovery_results |

## Anti-Features

Features to explicitly NOT build in v10.0.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| AI-powered discovery (Gemini scoring all 400) | 15 RPM rate limit makes this impractical; adds 200+ seconds to pipeline | Use indicator-based scoring — RSI zones, MACD crossovers, volume spikes |
| Multi-user watchlists | Single-user app — adds auth complexity for zero value | Keep single-user model |
| Watchlist alerts/notifications | Telegram bot was removed in v7.0; no notification channel exists | Show signals on watchlist page; user checks daily |
| Automatic watchlist curation (auto-add/remove) | User should control their watchlist; auto-changes break trust | Discovery suggests, user decides |
| Custom scoring weights | Over-engineering for single user; change weights in code if needed | Hardcode sensible defaults |
| Historical discovery comparison | Nice but not MVP | Keep 7 days of results for future use, but don't build UI |
| Watchlist ordering/priority | Sort by sector_group or AI score is sufficient | Use table sorting (already exists in watchlist-table.tsx) |
| Sector group CRUD page | Full management page for creating/editing sector groups | Inline editing on watchlist table is enough |

## Feature Dependencies

```
Alembic migration (discovery_results + sector_group)
  |
  +-> Discovery scoring engine (pure functions)
  |     |
  |     +-> Discovery service (orchestration)
  |           |
  |           +-> Discovery scheduler job -> Discovery API -> Discovery page
  |                                                             |
  |                                                       Add-to-watchlist button
  |                                                             |
  |                                                       Sector group assignment
  |
  +-> Watchlist API (sector_group CRUD)
        |
        +-> Watchlist table (inline edit)
              |
              +-> Heatmap rework (group by sector_group)

WatchlistService (get_watchlist_ticker_map)
  |
  +-> Modify AI scheduler jobs (watchlist filter)
        |
        +-> Picks from watchlist only (automatic)
```

## MVP Recommendation

Prioritize:
1. **Watchlist-gated AI pipeline** — This is the architectural core. Without it, the system still wastes resources on 400 tickers. Also reduces pipeline time from ~25min to ~8min.
2. **Discovery scoring engine + scheduler job** — Runs automatically, populates data. No frontend needed for validation.
3. **Discovery page** — Makes discovery results visible and actionable.
4. **Sector grouping + heatmap rework** — Completes the "watchlist-centric" promise visually.

Defer:
- **Discovery filters** — Can use unfiltered list initially; add filters if list is overwhelming
- **Score trend** — Requires 2+ days of data accumulation before it's useful
- **"New since last check" badge** — Nice polish, not core value

## Sources

- v10.0 milestone description in PROJECT.md
- Current scheduler chain analysis (manager.py, jobs.py)
- AIAnalysisService.analyze_all_tickers() ticker_filter support (ai_analysis_service.py line 87)
- Existing heatmap grouping logic (heatmap.tsx lines 41-51)
- Existing watchlist enrichment pattern (api/watchlist.py)

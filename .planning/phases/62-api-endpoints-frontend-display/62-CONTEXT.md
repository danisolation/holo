# Phase 62 — API Endpoints & Frontend Display: Smart Discuss Context

## Grey Areas Resolved

### Area 1: Backend API Design

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | API file | New `backend/app/api/rumors.py` router — separate from existing analysis endpoints | Clean separation, own prefix `/api/rumors` |
| 2 | Endpoints | `GET /api/rumors/{symbol}` (scores + recent posts for ticker), `GET /api/rumors/watchlist/summary` (badge data for all watchlist tickers) | Two endpoints cover all 3 requirements |
| 3 | Response shape for ticker | `{symbol, scored_date, credibility_score, impact_score, direction, key_claims, reasoning, posts: [{content, author_name, is_authentic, total_likes, posted_at}]}` | Single call gets score + feed |
| 4 | Response shape for watchlist | `[{symbol, rumor_count, avg_credibility, avg_impact, dominant_direction}]` | Lightweight badge data |
| 5 | Router registration | Add to `backend/app/api/router.py` like other routers | Standard pattern |

### Area 2: Frontend Components

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 6 | Rumor score panel | New `RumorScorePanel` component on ticker detail page — shows credibility, impact, direction, key claims | RUMOR-09 |
| 7 | Rumor feed timeline | New `RumorFeed` component below score panel — chronological list of scored posts | RUMOR-10 |
| 8 | Watchlist badge | Add rumor count + sentiment color dot to existing `watchlist-table.tsx` columns | RUMOR-11 — minimal change to existing component |
| 9 | Placement on ticker page | After news section, before analysis cards — rumors are supplementary intelligence | Natural reading flow |
| 10 | Empty state | "Chưa có tin đồn" message with muted icon — Vietnamese consistent with app | UX for tickers with no rumors |
| 11 | Color coding | Bullish=green, Bearish=red, Neutral=yellow — standard financial colors | Intuitive |
| 12 | React Query hook | New `useRumorScores(symbol)` and `useWatchlistRumors()` hooks in `lib/hooks.ts` | Consistent with existing usePrices, useIndicators pattern |

### Area 3: Data Fetching

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 13 | Stale time | 5 minutes for rumor data (daily refresh, not real-time) | Avoid unnecessary refetches |
| 14 | API client | Add to existing `lib/api.ts` fetch functions | Standard pattern |

## Code Context

### Reusable Assets
- `backend/app/api/analysis.py` — Router pattern for ticker-specific endpoints
- `backend/app/api/watchlist.py` — Router pattern for watchlist endpoints  
- `frontend/src/lib/hooks.ts` — React Query hook patterns
- `frontend/src/lib/api.ts` — API fetch function patterns
- `frontend/src/components/analysis-card.tsx` — Card component pattern for scores
- `frontend/src/components/news-list.tsx` — List component pattern for feed
- `frontend/src/components/watchlist-table.tsx` — Table to add badge column

### Integration Points
- `frontend/src/app/ticker/[symbol]/page.tsx` — Add RumorScorePanel + RumorFeed
- `frontend/src/app/watchlist/page.tsx` — Uses watchlist-table which gets badge
- `backend/app/api/router.py` — Register rumors router

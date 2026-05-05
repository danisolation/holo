# Phase 53: Watchlist-Gated AI Pipeline — Context

## Phase Type
Infrastructure-only (no user-facing UI changes)

## Goal
AI analysis and daily picks run exclusively on watchlist tickers, reducing Gemini API usage by ~70% and pipeline time by ~3x.

## Requirements
- **WL-01**: AI analysis (Gemini) runs only on watchlist tickers
- **WL-02**: Daily picks selected exclusively from watchlist tickers

## Success Criteria
1. AI analysis (Gemini calls) runs only on tickers present in user's watchlist — non-watchlist tickers receive no AI analysis
2. Daily picks are selected exclusively from watchlist tickers — no picks appear for tickers outside the watchlist
3. Empty watchlist causes AI pipeline to skip gracefully with logged warning — no crashes or stuck jobs
4. Full pipeline completes noticeably faster, proportional to watchlist size (~15-30 tickers) versus previous ~400-ticker run

## Key Context from Research
- `AIAnalysisService.analyze_all_tickers()` already accepts `ticker_filter: dict[str, int]` — watchlist gating is a plumbing change
- `PickService` needs similar filtering to restrict daily picks to watchlist
- Scheduler chain (post-Phase 52): `price_crawl → indicators → discovery_scoring → ai_analysis → news → ...`
- Empty watchlist edge case is critical — must not crash the scheduler chain
- DB pool: pool_size=5, max_overflow=3 on Aiven PostgreSQL — sequential execution required

## Decisions
- All decisions at agent's discretion (no locked choices from discuss-phase)

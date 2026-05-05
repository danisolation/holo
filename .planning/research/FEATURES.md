# Feature Landscape

**Domain:** Stock Intelligence Platform — v11.0 UX & Reliability Overhaul
**Researched:** 2026-05-06

## Table Stakes

Features that MUST work for the app to be usable. Currently broken or degraded.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| API responds in < 5s | App unusable at 3 min load | Medium | Cold start + query optimization |
| Search finds all tickers | Core navigation broken | Low | 2-line frontend fix |
| AI analysis < 12h old | Stale analysis = wrong decisions | Medium | Morning refresh chain |

## Differentiators

Features that improve the experience beyond "it works."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Onboarding for new users | Clear first-use experience | Low | Frontend-only, uses existing data |
| Quick-add popular tickers | Reduce friction to first value | Low | Use discovery endpoint data |
| Feature descriptions in nav | Self-documenting UX | Low | Text/tooltip additions |
| Pre-market AI signals (8:30 AM) | Actionable before market open | Medium | Morning chain + keep-alive |

## Anti-Features

Features to explicitly NOT build for v11.0.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Backend search endpoint | Over-engineering for 400 items | Client-side cmdk filtering |
| Redis caching layer | Infrastructure bloat for 1 user | In-memory Python dict cache |
| Paid Render upgrade | $7/mo when free solutions exist | External pinger (free) |
| Celery worker process | APScheduler handles this in-process | Second cron trigger |
| Full pipeline 2x/day | Wastes Gemini API budget | Morning subset chain (skip discovery/news) |

## Feature Dependencies

```
External Pinger (keep-alive) → Morning AI Refresh (needs process awake)
Search Fix → UX/Onboarding (onboarding guides to search)
Query Optimization → All API features (everything faster)
```

## MVP Recommendation

Priority order by impact:

1. **Keep-alive + query optimization** — Fixes worst UX issue (3 min load)
2. **Search fix** — 2-line change, unblocks ticker discovery
3. **Morning AI refresh** — Fresh signals before market open
4. **Onboarding UX** — Polish for first-use experience

Defer: Nothing. All 4 features are small enough to ship in one milestone.

## Sources

- Production usage observation (milestone context) — HIGH confidence
- Codebase root cause analysis — HIGH confidence

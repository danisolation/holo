# Research Summary: v11.0 UX & Reliability Overhaul

**Domain:** Stock Intelligence Platform — reliability, performance, and UX improvements
**Researched:** 2026-05-06
**Overall confidence:** HIGH

## Executive Summary

The v11.0 overhaul addresses five concrete problems identified through production usage. Through direct codebase analysis, all five have clear root causes and straightforward solutions requiring minimal new infrastructure.

The most impactful finding is that the ~3 minute API response time is caused by TWO compounding issues: Render.com free tier cold start (~30-60s) AND an unfiltered `ROW_NUMBER()` window function scanning 200K+ rows in the market-overview query. Fixing just the cold start won't fix the slowness — the query optimization is equally critical.

The search bug is a 2-line frontend fix: `ticker-search.tsx` hard-caps rendered items to 50 via `.slice(0, 50)`, making most tickers invisible. The AI staleness issue is solvable by adding a morning cron trigger (8:30 AM) running a subset of the daily job chain. The UX improvements are frontend-only polish.

Critically, none of these changes require new infrastructure (no Redis, no Celery, no paid tier). All solutions fit within the existing FastAPI + APScheduler + PostgreSQL architecture.

## Key Findings

**Stack:** No stack changes. Existing tech handles all v11.0 requirements.
**Architecture:** External pinger + query optimization + morning cron chain. No new services.
**Critical pitfall:** Keep-alive pinger MUST be active before morning AI refresh works reliably.

## Implications for Roadmap

1. **Keep-Alive + API Performance** — Eliminate 3-min load time
   - Addresses: Cold start, slow queries
   - Avoids: Premature paid tier, unnecessary Redis

2. **Search Fix** — 2-line frontend fix
   - Addresses: Ticker search missing results
   - Avoids: Over-engineering backend search

3. **AI Analysis Refresh** — Morning job chain
   - Addresses: 18h stale AI analysis
   - Avoids: Celery/worker complexity

4. **UX/Onboarding** — Frontend polish
   - Addresses: New user confusion, empty states
   - Avoids: Backend changes

**Phase ordering rationale:**
- Phase 1 first: All other work is hard to test if app takes 3 min to load
- Phase 2 independent: Can parallel with Phase 1
- Phase 3 depends on Phase 1: Morning cron needs keep-alive
- Phase 4 depends on Phase 2: Onboarding needs working search

**Research flags:**
- Phase 1: Verify Vercel cron limits before attempting Vercel-based keep-alive
- Phase 3: Monitor Gemini usage after doubling analysis frequency

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No changes needed |
| Features | HIGH | All 5 problems have identified root causes |
| Architecture | HIGH | Based on direct code analysis |
| Pitfalls | HIGH | Dependencies well-understood |

## Gaps to Address

- Verify exact Vercel Hobby cron frequency limits
- Monitor Gemini API usage after 2x daily runs
- Test query performance on production Aiven (not just local)

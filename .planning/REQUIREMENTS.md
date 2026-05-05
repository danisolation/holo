# Requirements: Holo v11.0 — UX & Reliability Overhaul

**Defined:** 2026-05-06
**Core Value:** AI phân tích đa chiều trên dữ liệu HOSE real-time để gợi ý trading chính xác và kịp thời

## v11.0 Requirements

### Performance & Reliability (PERF)

- [x] **PERF-01**: Market overview API responds in < 3s (currently ~3 min due to unfiltered ROW_NUMBER scan)
- [x] **PERF-02**: Backend stays awake via external keep-alive ping (UptimeRobot/cron-job.org, every 5-14 min)
- [x] **PERF-03**: Frequently-accessed API endpoints use in-memory TTL cache (cachetools) to reduce DB load
- [x] **PERF-04**: Daily prices query uses date-bounded filter (WHERE date >= CURRENT_DATE - 7) instead of full table scan

### Search (SRCH)

- [x] **SRCH-01**: Ticker search returns all ~400 HOSE tickers (fix .slice(0,50) truncation + API limit=100 cap)
- [x] **SRCH-02**: Search supports recent searches history (client-side, localStorage)

### AI Freshness (AI)

- [x] **AI-01**: AI analysis runs a morning refresh (8:30 AM) for watchlist tickers before market opens
- [x] **AI-02**: Morning refresh runs shortened chain (price → indicators → AI analysis → signals) to respect Gemini 15 RPM limit
- [x] **AI-03**: Dashboard shows analysis freshness indicator (age of last AI run per ticker)

### UX & Onboarding (UX)

- [x] **UX-01**: First-time users see preset watchlist option (VN30 blue-chips one-click add)
- [x] **UX-02**: Empty states show helpful guidance instead of blank screens (heatmap, watchlist, discovery)
- [x] **UX-03**: Navigation includes feature descriptions/tooltips explaining each section

## v12.0+ Requirements (Deferred)

### Advanced UX

- **UX-D01**: AI analysis change tracking (show what changed since last analysis)
- **UX-D02**: Search enrichment with sector/industry context in results
- **UX-D03**: Interactive onboarding tour/wizard

### Advanced AI

- **AI-D01**: Manual "refresh analysis" button per ticker
- **AI-D02**: Intraday mid-session analysis during market hours
- **AI-D03**: AI confidence scoring visible in UI

## Out of Scope

| Feature | Reason |
|---------|--------|
| Redis caching layer | In-memory cachetools sufficient for single-user app |
| Paid Render upgrade | External pinger solves cold start for free |
| Celery/worker process | APScheduler handles scheduling in-process |
| Backend search endpoint | Client-side cmdk filtering sufficient for 400 tickers |
| Full pipeline 2x/day | Would blow Gemini free tier; morning subset chain is safer |
| OAuth/social login | Personal use, no auth complexity needed |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PERF-01 | Phase 56 | Complete |
| PERF-02 | Phase 56 | Complete |
| PERF-03 | Phase 56 | Complete |
| PERF-04 | Phase 56 | Complete |
| SRCH-01 | Phase 57 | Complete |
| SRCH-02 | Phase 57 | Complete |
| AI-01 | Phase 58 | Complete |
| AI-02 | Phase 58 | Complete |
| AI-03 | Phase 58 | Complete |
| UX-01 | Phase 59 | Complete |
| UX-02 | Phase 59 | Complete |
| UX-03 | Phase 59 | Complete |

**Coverage:**
- v11.0 requirements: 12 total
- Mapped to phases: 12 ✓
- Unmapped: 0

---
*Requirements defined: 2026-05-06*
*Last updated: 2026-05-06 after research synthesis*

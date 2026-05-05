# Requirements: Holo v11.0 — UX & Reliability Overhaul

**Defined:** 2026-05-06
**Core Value:** AI phân tích đa chiều trên dữ liệu HOSE real-time để gợi ý trading chính xác và kịp thời

## v11.0 Requirements

### Performance & Reliability (PERF)

- [ ] **PERF-01**: Market overview API responds in < 3s (currently ~3 min due to unfiltered ROW_NUMBER scan)
- [ ] **PERF-02**: Backend stays awake via external keep-alive ping (UptimeRobot/cron-job.org, every 5-14 min)
- [ ] **PERF-03**: Frequently-accessed API endpoints use in-memory TTL cache (cachetools) to reduce DB load
- [ ] **PERF-04**: Daily prices query uses date-bounded filter (WHERE date >= CURRENT_DATE - 7) instead of full table scan

### Search (SRCH)

- [ ] **SRCH-01**: Ticker search returns all ~400 HOSE tickers (fix .slice(0,50) truncation + API limit=100 cap)
- [ ] **SRCH-02**: Search supports recent searches history (client-side, localStorage)

### AI Freshness (AI)

- [ ] **AI-01**: AI analysis runs a morning refresh (8:30 AM) for watchlist tickers before market opens
- [ ] **AI-02**: Morning refresh runs shortened chain (price → indicators → AI analysis → signals) to respect Gemini 15 RPM limit
- [ ] **AI-03**: Dashboard shows analysis freshness indicator (age of last AI run per ticker)

### UX & Onboarding (UX)

- [ ] **UX-01**: First-time users see preset watchlist option (VN30 blue-chips one-click add)
- [ ] **UX-02**: Empty states show helpful guidance instead of blank screens (heatmap, watchlist, discovery)
- [ ] **UX-03**: Navigation includes feature descriptions/tooltips explaining each section

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
| PERF-01 | — | Pending |
| PERF-02 | — | Pending |
| PERF-03 | — | Pending |
| PERF-04 | — | Pending |
| SRCH-01 | — | Pending |
| SRCH-02 | — | Pending |
| AI-01 | — | Pending |
| AI-02 | — | Pending |
| AI-03 | — | Pending |
| UX-01 | — | Pending |
| UX-02 | — | Pending |
| UX-03 | — | Pending |

**Coverage:**
- v11.0 requirements: 12 total
- Mapped to phases: 0 (awaiting roadmap)
- Unmapped: 12 ⚠️

---
*Requirements defined: 2026-05-06*
*Last updated: 2026-05-06 after research synthesis*

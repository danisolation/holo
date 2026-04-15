# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-15)

**Core value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu HOSE real-time để gợi ý trading chính xác và kịp thời qua Telegram.
**Current focus:** Phase 1 — Data Foundation

## Current Position

Phase: 1 of 5 (Data Foundation)
Plan: 0 of ? in current phase
Status: Ready to plan
Last activity: 2025-07-17 — Roadmap created

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- [Roadmap]: vnstock v3.5.1 as data backbone (not raw crawlers for VNDirect/SSI)
- [Roadmap]: `ta` library for indicators (pandas-ta removed from PyPI)
- [Roadmap]: `google-genai` new SDK (not legacy google-generativeai)
- [Roadmap]: Async Python monolith — FastAPI + APScheduler in-process, no Celery
- [Roadmap]: Pre-compute indicators with `ta`, feed structured data to Gemini (not raw OHLCV)
- [Roadmap]: PostgreSQL yearly partitioning for daily_prices table
- [Roadmap]: Bot before Dashboard — Telegram has higher personal utility

### Pending Todos

None yet.

### Blockers/Concerns

- vnstock v3.x moving to freemium — monitor for free tier limitations
- Unadjusted prices from vnstock — need corporate actions handling before indicator computation
- Gemini API rate limits — 400 tickers needs batching strategy (15 RPM on Flash)

## Session Continuity

Last session: 2025-07-17
Stopped at: Roadmap created, ready to plan Phase 1
Resume file: None

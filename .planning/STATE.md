---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: Paper Trading & Signal Verification
status: verifying
last_updated: "2026-04-20T09:44:40.911Z"
last_activity: 2026-04-20
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 10
  completed_plans: 7
  percent: 70
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20)

**Core value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua Telegram.
**Current focus:** v4.0 Paper Trading & Signal Verification — Phase 22 ready to plan

## Current Position

Phase: 25 of 26 (Dashboard Structure & Trade Management)
Plan: 2 of 2
Status: Phase complete — ready for verification
Last activity: 2026-04-20

```
[██░░░░░░░░░░░░░░░░░░] 10%
```

## Shipped Milestones

| Version | Name | Phases | Plans | Date |
|---------|------|--------|-------|------|
| v1.0 | Holo Stock Intelligence Platform | 5 | 15 | 2026-04-15 |
| v1.1 | Reliability & Portfolio | 6 | 20 | 2026-04-17 |
| v2.0 | Full Coverage & Real-Time | 5 | 18 | 2026-04-17 |
| v3.0 | Smart Trading Signals | 5 | 10 | 2026-04-20 |

## Performance Metrics

**Velocity:** (Reset for v4.0)

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 23 | 01 | 2 min | 1 | 3 |

*Updated after each plan completion*
| Phase 23 P02 | 3 min | 1 tasks | 4 files |
| Phase 24 P01 | 3 min | 2 tasks | 5 files |
| Phase 24 P02 | 5 min | 2 tasks | 4 files |
| Phase 25 P01 | 3 min | 2 tasks | 7 files |
| Phase 25 P02 | 3 min | 2 tasks | 5 files |
| Phase 26 P01 | 3 min | 2 tasks | 8 files |

## Accumulated Context

### Decisions

All v1.0–v3.0 decisions archived in PROJECT.md Key Decisions table.

**v4.0 roadmap decisions:**

- 5 phases derived from 26 requirements across 3 categories (PT, AN, UI)
- Phase ordering follows research: Foundation → Scheduler → API → Dashboard → Visualization
- Entry fill at D+1 open (not same-day close) — prevents lookahead bias
- SL-wins on ambiguous daily bars (conservative fill assumption)
- Exclude score=0 invalid signals from auto-tracking
- Batch position queries to respect Aiven pool (pool_size=5, max_overflow=3)
- Calendar heatmap via react-activity-calendar npm package (only new frontend dep)
- BEARISH tracks prediction accuracy, not synthetic short P&L (VN no retail short)
- [Phase 23]: Auto-track chains after daily_trading_signal_triggered parallel with alert/hnx jobs; never-raises pattern
- [Phase 23]: SL checked FIRST on every bar — ambiguous bars resolve to SL (conservative fill assumption)
- [Phase 23]: Gap-through fills at open price, not SL/TP level; timeout uses trading day count from daily_prices
- [Phase 24]: POST /trades/follow placed before GET /trades/{trade_id} to avoid FastAPI path conflict
- [Phase 24]: 12 schema validation tests (no DB mocks) — Pydantic input constraints verified directly
- [Phase 24]: Confidence brackets: 1-3 LOW, 4-6 MEDIUM, 7-10 HIGH per CONTEXT.md
- [Phase 24]: R:R uses abs(entry-SL)*qty for risk — handles both LONG and BEARISH via abs()
- [Phase 24]: Profit factor returns None (not infinity) when gross_loss==0
- [Phase 24]: Sector analysis: coalesce(Ticker.industry, 'Unknown') for NULL industries
- [Phase 25]: [Phase 25]: Trades/Settings tabs placeholder text, replaced in Plan 02; Analytics/Calendar disabled for Phase 26
- [Phase 25]: Server-side filtering via queryKey changes (not client-side) for trade table
- [Phase 25]: PTSignalOutcomes returns null for tickers without paper trades (non-intrusive)
- [Phase 26]: Streak logic: per-trade iteration ordered by (closed_date, id) ASC
- [Phase 26]: Calendar heatmap via react-activity-calendar npm package (only new frontend dep)

### Pending Todos

None yet.

### Blockers/Concerns

- Aiven pool constraint (5+3) — position monitor must batch-load all positions + prices in 2 queries
- Gemini free-tier 1500 RPD — auto-track adds no AI calls but pipeline budget unchanged
- Need ~2 weeks of accumulated trade data before analytics become meaningful

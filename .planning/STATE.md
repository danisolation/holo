---
gsd_state_version: 1.0
milestone: v4.0
milestone_name: Paper Trading & Signal Verification
status: ready_to_plan
last_updated: "2026-04-21T00:00:00.000Z"
last_activity: 2026-04-21
progress:
  total_phases: 5
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20)

**Core value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua Telegram.
**Current focus:** v4.0 Paper Trading & Signal Verification — Phase 22 ready to plan

## Current Position

Phase: 22 of 26 (Paper Trade Foundation)
Plan: —
Status: Ready to plan
Last activity: 2026-04-21 — Roadmap created for v4.0

```
[░░░░░░░░░░░░░░░░░░░░] 0%
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
| — | — | — | — | — |

*Updated after each plan completion*

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

### Pending Todos

None yet.

### Blockers/Concerns

- Aiven pool constraint (5+3) — position monitor must batch-load all positions + prices in 2 queries
- Gemini free-tier 1500 RPD — auto-track adds no AI calls but pipeline budget unchanged
- Need ~2 weeks of accumulated trade data before analytics become meaningful

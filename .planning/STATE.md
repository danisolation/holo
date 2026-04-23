---
gsd_state_version: 1.0
milestone: v8.0
milestone_name: AI Trading Coach
status: verifying
stopped_at: Completed 47-01-PLAN.md
last_updated: "2026-04-23T12:43:49.249Z"
last_activity: 2026-04-23
progress:
  total_phases: 5
  completed_phases: 4
  total_plans: 14
  completed_plans: 12
  percent: 86
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-23)

**Core value:** AI phân tích đa chiều (kỹ thuật + cơ bản + sentiment) trên dữ liệu chứng khoán Việt Nam real-time để gợi ý trading chính xác và kịp thời qua web dashboard.
**Current focus:** Phase 47 — goals-weekly-reviews

## Current Position

Phase: 47
Plan: 1 of 3
Status: Executing phase
Last activity: 2026-04-23

Progress: [████████░░] 86%

## Shipped Milestones

| Version | Name | Phases | Plans | Date |
|---------|------|--------|-------|------|
| v1.0 | Holo Stock Intelligence Platform | 5 | 15 | 2026-04-15 |
| v1.1 | Reliability & Portfolio | 6 | 20 | 2026-04-17 |
| v2.0 | Full Coverage & Real-Time | 5 | 18 | 2026-04-17 |
| v3.0 | Smart Trading Signals | 5 | 10 | 2026-04-20 |
| v4.0 | Paper Trading & Signal Verification | 5 | 10 | 2025-07-20 |
| v5.0 | E2E Testing & Quality Assurance | 5 | 9 | 2025-07-21 |
| v6.0 | AI Backtesting Engine | 3 | 7 | 2026-04-22 |
| v7.0 | Consolidation & Quality Upgrade | 8 | 9 | 2025-07-22 |

## Accumulated Context

### Decisions

All v1.0–v7.0 decisions archived in PROJECT.md Key Decisions table.

- [Phase 44]: lot_matches junction table for SELL reversal tracking
- [Phase 44]: Proportional buy-side broker fee allocation on SELL
- [Phase 44]: Sort/order whitelist mitigates injection (T-44-05)
- [Phase 44]: Sparkles wrapped in span for title tooltip (lucide lacks title prop)
- [Phase 44]: Invalidating queryKey ['trades'] cascades to both list and stats caches
- [Phase 44]: Added id to DailyPickResponse for pick linking (backend + frontend)
- [Phase 44]: Popover+Command combo for ticker autocomplete in trade entry
- [Phase 44]: onCreateFirst prop on TradesTable for empty state CTA
- [Phase 45]: compute_pick_outcome as pure function in pick_service.py, SL check before TP1
- [Phase 45]: Streak treats expired picks as streak-breaker (current_streak=0)
- [Phase 45]: PickPerformanceCards and PickHistoryTable are self-contained (own hooks internally)
- [Phase 45]: Open trades section hidden entirely when no BUY trades exist
- [Phase 45]: Performance cards show dashes on error (graceful degradation, not blocking)
- [Phase 46]: Renamed metadata to event_metadata (SQLAlchemy reserved name)
- [Phase 46]: Centered normalization for sector bias — subtract mean so poor sectors get preference_score < 0
- [Phase 46]: Added get_habit_detections() read method to BehaviorService (plan referenced it but missing from 46-01)
- [Phase 46]: daily_consecutive_loss_check chains from daily_pick_outcome_check (end of daily pipeline)
- [Phase 46]: Sector bias as multiplicative factor (1 + preference_score * 0.1) bounded to +-10% impact
- [Phase 46]: Used event_metadata (not metadata) in BehaviorEventCreate to match 46-01 deviation
- [Phase 46]: Added onClick to PickCard for pick_click tracking (no prior click handler)
- [Phase 47]: Gemini review uses WeeklyReviewOutput Pydantic model for structured output with 3-stage fallback
- [Phase 47]: GoalService follows BehaviorService pattern: module-level pure functions + async class
- [Phase 47]: Include sector preference data in weekly review prompts for richer coaching

### Research Context (v8.0)

- Build VNMarketRules utility FIRST (P&L, picks validation, position sizing depend on it)
- Daily picks = ranking layer on existing AI analysis, NOT re-analysis (~1 Gemini call/day)
- Adaptive strategy needs ~20 trades before activation — build last
- 6 new DB tables: daily_picks, trade_journal, user_risk_profile, behavior_events, goals, weekly_reviews
- Zero new Python packages. 5 new frontend npm packages (react-hook-form, zod, react-day-picker, sonner, @hookform/resolvers)

### Pending Todos

None yet.

### Blockers/Concerns

None.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260423-d83 | Remove entire backtest feature (backend + frontend + DB tables + tests) | 2026-04-23 | 194cad0 | [260423-d83-remove-entire-backtest-feature-backend-f](./quick/260423-d83-remove-entire-backtest-feature-backend-f/) |
| 260423-dqa | Remove portfolio, paper trading, and telegram bot (backend + frontend + DB tables + tests) | 2026-04-23 | c6a0c7a | [260423-dqa-remove-portfolio-paper-trading-and-teleg](./quick/260423-dqa-remove-portfolio-paper-trading-and-teleg/) |
| 260423-epd | Tier 1 upgrades: clean stale config, add news on ticker page, add trading signal label | 2026-04-23 | 3c6a4c5 | [260423-epd-tier-1-upgrades-clean-stale-config-add-d](./quick/260423-epd-tier-1-upgrades-clean-stale-config-add-d/) |
| 260423-f6p | Tier 2 Batch A: staleTime tuning, GZip, N+1 fix, error states, pagination | 2026-04-23 | 16cd356 | [260423-f6p-tier-2-batch-a-staletime-tuning-gzip-ana](./quick/260423-f6p-tier-2-batch-a-staletime-tuning-gzip-ana/) |
| 260423-feq | Tier 2 Batch B: market-overview sort/top, CafeF retry, realtime diff, home errors | 2026-04-23 | fee5e52 | [260423-feq-tier-2-batch-b-market-overview-optimizat](./quick/260423-feq-tier-2-batch-b-market-overview-optimizat/) |
| 260423-fuy | Tier 2 Batch C: news skeleton, tickers pagination, crawler types, exchange-aware realtime | 2026-04-23 | 09c92a8 | [260423-fuy-tier-2-batch-c-news-skeleton-home-page-e](./quick/260423-fuy-tier-2-batch-c-news-skeleton-home-page-e/) |

## Session Continuity

Last session: 2026-04-23T12:43:49.244Z
Stopped at: Completed 47-01-PLAN.md
Resume file: None

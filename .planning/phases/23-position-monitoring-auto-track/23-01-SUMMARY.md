---
phase: 23-position-monitoring-auto-track
plan: "01"
subsystem: scheduler
tags: [paper-trading, auto-track, scheduler-chain, PT-01, PT-08]
dependency_graph:
  requires:
    - "Phase 22: PaperTrade model, TradeStatus/TradeDirection enums, SimulationConfig, calculate_position_size"
    - "Phase 19: AIAnalysis TRADING_SIGNAL type, TickerTradingSignal schema, daily_trading_signal_triggered chain"
  provides:
    - "paper_trade_auto_track job function (auto-creates PENDING paper trades)"
    - "Manager chain: daily_trading_signal → paper_trade_auto_track (parallel with alert/hnx)"
    - "_JOB_NAMES entries for Phase 23 jobs (auto_track + position_monitor)"
  affects:
    - "backend/app/scheduler/jobs.py"
    - "backend/app/scheduler/manager.py"
tech_stack:
  added: []
  patterns:
    - "Never-raises async job pattern (try/except with job_svc.complete, no re-raise)"
    - "Lazy imports inside job function body (matching existing codebase pattern)"
    - "Dedup via SELECT existing ai_analysis_ids before INSERT"
key_files:
  created:
    - "backend/tests/test_paper_trade_auto_track.py"
  modified:
    - "backend/app/scheduler/jobs.py"
    - "backend/app/scheduler/manager.py"
decisions:
  - "Used lazy imports inside function body matching daily_signal_alert_check pattern"
  - "Pre-added paper_position_monitor_triggered to _JOB_NAMES for Plan 02 readiness"
  - "Score=0 excluded by SQL WHERE (AIAnalysis.score > 0) not application filter"
metrics:
  duration: "2 min"
  completed: "2026-04-20T08:11:00Z"
  tasks_completed: 1
  tasks_total: 1
  test_count: 7
  test_pass: 7
---

# Phase 23 Plan 01: Auto-Track Scheduler Job Summary

Auto-track scheduler job that creates PENDING paper trades from valid AI trading signals, chained after daily_trading_signal_triggered with dedup, confidence filtering, and never-raises resilience.

## Task Completion

| Task | Name | Type | Commit | Files |
|------|------|------|--------|-------|
| 1 (RED) | Unit tests for auto-track logic | test | 932a45f | backend/tests/test_paper_trade_auto_track.py |
| 1 (GREEN) | Implement job + manager chain | feat | 6dfc69d | backend/app/scheduler/jobs.py, backend/app/scheduler/manager.py |

## Implementation Details

### paper_trade_auto_track() Job Function (jobs.py)

Async job function appended at end of jobs.py following the established "never-raises" pattern from `daily_signal_alert_check`:

1. **Config check** — Loads `SimulationConfig` (id=1). If `auto_track_enabled=false` or config missing → returns with "skipped" status
2. **Signal query** — Selects today's `AIAnalysis` rows where `analysis_type=TRADING_SIGNAL` and `score > 0` (PT-08: score=0 excluded at SQL level)
3. **Dedup** — Queries existing `PaperTrade.ai_analysis_id` values to skip already-tracked signals (PT-08)
4. **Parse & filter** — For each untracked signal:
   - `TickerTradingSignal.model_validate(raw_response)` with try/except (T-23-01 mitigation)
   - Extracts direction-specific analysis (long_analysis or bearish_analysis)
   - Filters by `min_confidence_threshold`
   - Calculates position size via `calculate_position_size()` — skips if qty=0
5. **Create trade** — Inserts `PaperTrade` with PENDING status, all fields mapped from signal
6. **Summary** — Records created/skipped/total counts in job execution

### Manager Chain (manager.py)

Added chain point inside `elif event.job_id in ("daily_trading_signal_triggered",):` block, after existing HNX/UPCOM chain. Auto-track runs in parallel with signal alerts and HNX analysis.

### _JOB_NAMES (manager.py)

Added two entries:
- `paper_trade_auto_track_triggered` → "Paper Trade Auto-Track"
- `paper_position_monitor_triggered` → "Paper Position Monitor" (pre-added for Plan 02)

## Test Results

7 tests, 7 passed, 0 failed:

| Test | Class | Description |
|------|-------|-------------|
| test_valid_signal_creates_pending_trade | TestAutoTrackSignalParsing | Signal parsing + field mapping |
| test_bearish_signal_parses_correctly | TestAutoTrackSignalParsing | BEARISH direction extraction |
| test_invalid_raw_response_raises | TestAutoTrackSignalParsing | Malformed JSON → exception (job skips) |
| test_position_sizing_called_correctly | TestAutoTrackFiltering | 100M×10%/80K = 100 shares |
| test_zero_quantity_skipped | TestAutoTrackFiltering | Small capital → qty=0 → skip |
| test_confidence_below_threshold_excluded | TestAutoTrackFiltering | conf=3 < threshold=5 → skip |
| test_existing_analysis_ids_detected | TestAutoTrackDedup | Dedup filters already-tracked IDs |

## Acceptance Criteria Verification

All 13 grep checks passed:
- `async def paper_trade_auto_track` in jobs.py ✓
- `paper_trade_auto_track_triggered` in manager.py ✓
- `paper_position_monitor_triggered` in manager.py ✓
- `PAPER TRADE AUTO-TRACK START` in jobs.py ✓
- `Never raises` in jobs.py ✓
- `TickerTradingSignal.model_validate` in jobs.py ✓
- `calculate_position_size` in jobs.py ✓
- `TradeStatus.PENDING` in jobs.py ✓
- `auto_track_enabled` in jobs.py ✓
- `score > 0` in jobs.py ✓
- `ai_analysis_id` in jobs.py ✓
- `min_confidence_threshold` in jobs.py ✓
- `TestAutoTrack` in test file ✓

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all functionality is fully wired. No placeholder data or TODO markers.

## Requirements Coverage

- **PT-01**: Every valid AI trading signal (score > 0, confidence >= threshold) automatically creates a PENDING paper trade ✓
- **PT-08**: Score=0 signals excluded by SQL filter; dedup by ai_analysis_id prevents duplicates on re-runs ✓

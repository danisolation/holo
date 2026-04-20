---
phase: 19-ai-trading-signal-pipeline
plan: 01
name: "Schema contracts + DB migration + config"
status: complete
completed: "2026-04-20T04:23:32Z"
duration: "4.1m"
tasks_completed: 2
tasks_total: 2
subsystem: backend
tags: [pydantic, schemas, migration, config, trading-signal]
dependency_graph:
  requires: []
  provides:
    - "Direction, Timeframe, TradingPlanDetail, DirectionAnalysis, TickerTradingSignal, TradingSignalBatchResponse Pydantic classes"
    - "AnalysisType.TRADING_SIGNAL enum member"
    - "Migration 012: ENUM extension + CHECK constraint update"
    - "Config: trading_signal_batch_size, trading_signal_thinking_budget, trading_signal_max_tokens"
  affects:
    - "backend/app/services/ai_analysis_service.py (ANALYSIS_TEMPERATURES)"
tech_stack:
  added: []
  patterns:
    - "3-level nested Pydantic schema for Gemini response_schema"
    - "Dynamic pg_constraint lookup for safe CHECK constraint migration"
key_files:
  created:
    - backend/alembic/versions/012_trading_signal_type.py
    - backend/tests/test_trading_signal_schemas.py
  modified:
    - backend/app/schemas/analysis.py
    - backend/app/models/ai_analysis.py
    - backend/app/config.py
    - backend/app/services/ai_analysis_service.py
key_decisions:
  - "BEARISH (not SHORT) direction enum for VN market compatibility"
  - "SWING/POSITION timeframes only — no intraday due to T+2.5 settlement"
  - "Temperature 0.2 for trading signals (same as combined analysis)"
metrics:
  duration: "4.1m"
  completed: "2026-04-20T04:23:32Z"
  tasks: 2
  files: 6
---

# Phase 19 Plan 01: Schema Contracts + DB Migration + Config Summary

**One-liner:** 6 new Pydantic classes for dual-direction trading signals with BEARISH/LONG enums, migration 012 extending analysis_type ENUM + relaxing score CHECK to 0-10, and 3 config settings (batch_size=15, thinking_budget=2048, max_tokens=32768).

## What Was Done

### Task 1: Pydantic schemas + AnalysisType enum + config (TDD)

**RED:** Created 11 failing tests covering Direction/Timeframe enums, TradingPlanDetail field bounds (R:R ≥ 0.5, pct 1-100), DirectionAnalysis confidence (1-10), full nested batch structure, AnalysisType enum, and config defaults.

**GREEN:** Added 6 Pydantic classes to `schemas/analysis.py`:
- `Direction(str, Enum)` — LONG, BEARISH (not SHORT per VN market)
- `Timeframe(str, Enum)` — SWING, POSITION (no intraday per T+2.5)
- `TradingPlanDetail(BaseModel)` — entry_price, stop_loss, take_profit_1, take_profit_2, risk_reward_ratio (≥0.5), position_size_pct (1-100), timeframe
- `DirectionAnalysis(BaseModel)` — direction, confidence (1-10), trading_plan, reasoning
- `TickerTradingSignal(BaseModel)` — ticker, recommended_direction, long_analysis, bearish_analysis
- `TradingSignalBatchResponse(BaseModel)` — signals: list[TickerTradingSignal]

Added `TRADING_SIGNAL = "trading_signal"` to AnalysisType enum. Added 3 config settings with correct defaults.

### Task 2: Migration 012 + schema unit tests

Created `012_trading_signal_type.py` migration:
- Adds `trading_signal` to PostgreSQL `analysis_type` ENUM via `ADD VALUE IF NOT EXISTS`
- Dynamically looks up score CHECK constraint name from `pg_constraint` (T-19-01 mitigation — avoids hardcoded name assumption)
- Drops old CHECK (score BETWEEN 1 AND 10), creates new (score BETWEEN 0 AND 10) to allow invalid signal score=0

All 11 schema tests pass. All 415 project tests pass.

## Commits

| # | Hash | Type | Description |
|---|------|------|-------------|
| 1 | `a616a02` | test | Add failing tests for trading signal schemas (TDD RED) |
| 2 | `b8e5576` | feat | Add trading signal Pydantic schemas, AnalysisType enum, config settings (TDD GREEN) |
| 3 | `81a9c3c` | feat | Add migration 012 for trading_signal ENUM + score CHECK update |
| 4 | `0fd6f2e` | fix | Add TRADING_SIGNAL to ANALYSIS_TEMPERATURES dict |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added TRADING_SIGNAL to ANALYSIS_TEMPERATURES dict**
- **Found during:** Task 2 verification (full test suite run)
- **Issue:** Existing `test_temperature_covers_all_types` asserts all `AnalysisType` members have a temperature mapping. Adding `TRADING_SIGNAL` broke this existing test.
- **Fix:** Added `AnalysisType.TRADING_SIGNAL: 0.2` to `ANALYSIS_TEMPERATURES` in `ai_analysis_service.py` (0.2 = same as combined, per CONTEXT.md decision)
- **Files modified:** `backend/app/services/ai_analysis_service.py`
- **Commit:** `0fd6f2e`

## Verification Results

- ✅ All 6 Pydantic classes importable from `schemas/analysis.py`
- ✅ `AnalysisType.TRADING_SIGNAL.value == "trading_signal"`
- ✅ Config settings: batch_size=15, thinking_budget=2048, max_tokens=32768
- ✅ Migration 012 exists with revision chain 011 → 012
- ✅ All 11 schema tests pass
- ✅ All 415 project tests pass (0 failures)

## Self-Check: PASSED

All 7 files verified present. All 4 commits verified in git log.

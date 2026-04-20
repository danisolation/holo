---
phase: 19-ai-trading-signal-pipeline
plan: 02
subsystem: ai-analysis
tags: [gemini, trading-signal, pydantic, post-validation, batch-analysis, vietnamese-prompt]

# Dependency graph
requires:
  - phase: 19-01
    provides: "Trading signal schemas (Direction, Timeframe, TradingPlanDetail, DirectionAnalysis, TickerTradingSignal, TradingSignalBatchResponse), AnalysisType.TRADING_SIGNAL enum, config settings, migration 012"
provides:
  - "run_trading_signal_analysis() — public method for daily pipeline and on-demand"
  - "_analyze_trading_signal_batch() — Gemini batch call with increased token budgets"
  - "_get_trading_signal_context() — context gathering with ATR/ADX/RSI/Stochastic/S-R/Fib/52w data"
  - "_build_trading_signal_prompt() — Vietnamese prompt with indicator data per ticker"
  - "_validate_trading_signal() — post-validation: entry ±5%, SL 3×ATR, TP 5×ATR"
  - "Extended _call_gemini_with_retry with keyword-only max_output_tokens/thinking_budget params"
  - "Extended _run_batched_analysis with batch_size_override param"
  - "analyze_all_tickers includes trading_signal for 'trading_signal' and 'all' types"
  - "analyze_single_ticker includes trading_signal as 5th analysis type"
  - "TRADING_SIGNAL_SYSTEM_INSTRUCTION and TRADING_SIGNAL_FEW_SHOT constants"
affects: [19-03, phase-20, phase-21]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "keyword-only params for backward-compatible method extension"
    - "batch_size_override pattern for per-type batch sizes without shared state mutation"
    - "module-level pure validation function for testability"

key-files:
  created:
    - "backend/tests/test_trading_signal_validation.py"
  modified:
    - "backend/app/services/ai_analysis_service.py"

key-decisions:
  - "Extended _call_gemini_with_retry with keyword-only params (after *) to preserve all existing callers"
  - "batch_size_override as parameter to _run_batched_analysis instead of mutating self.batch_size — prevents leaking to other analysis types"
  - "_validate_trading_signal as module-level function (not method) for direct testability"
  - "Vietnamese system instruction with explicit BEARISH = 'giảm vị thế' framing for VN market"
  - "Post-validation stores invalid signals with score=0, signal='invalid' instead of dropping them"

patterns-established:
  - "Per-type token budgets: max_output_tokens and thinking_budget configurable per analysis type via kwargs"
  - "batch_size_override: analysis types can use different batch sizes without affecting instance state"
  - "Trading signal result field: result.signals (not result.analyses) — special case in _run_batched_analysis"

requirements-completed: [PLAN-01, PLAN-02, PLAN-03, PLAN-04, PLAN-05, PLAN-06]

# Metrics
duration: 6.7min
completed: 2026-04-20
---

# Phase 19 Plan 02: Service Core Summary

**Dual-direction trading signal pipeline with Vietnamese Gemini prompts, ATR/S-R/Fib context gathering, and post-validation enforcing entry ±5%, SL 3×ATR, TP 5×ATR bounds**

## Performance

- **Duration:** 6.7 min
- **Started:** 2026-04-20T04:26:36Z
- **Completed:** 2026-04-20T04:33:19Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Full trading signal pipeline: context gathering → prompt building → Gemini call → post-validation → storage
- Extended _call_gemini_with_retry with configurable max_output_tokens (32768) and thinking_budget (2048) without breaking existing callers
- Post-validation catches hallucinated Gemini targets: entry ±5% of current price, SL within 3×ATR, TP within 5×ATR
- Invalid signals stored with signal="invalid", score=0 for audit trail
- analyze_all_tickers and analyze_single_ticker both include trading_signal as 5th type
- 8 validation tests + 11 schema tests (19 total) all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend Gemini methods + add trading signal constants, context, and prompt builder** - `4860b6b` (feat)
2. **Task 2: Add trading signal orchestration, batch analyzer, and validation tests** - `2ba7dd4` (feat)

## Files Created/Modified
- `backend/app/services/ai_analysis_service.py` - Extended with trading signal constants, system instruction, few-shot example, _validate_trading_signal, _get_trading_signal_context, _build_trading_signal_prompt, _analyze_trading_signal_batch, run_trading_signal_analysis, and updates to analyze_all_tickers/analyze_single_ticker/_run_batched_analysis/_call_gemini_with_retry/_call_gemini
- `backend/tests/test_trading_signal_validation.py` - 8 tests for post-validation logic: valid signal, entry ±5%, SL 3×ATR, TP 5×ATR, bearish validation, edge case at exactly 5%, zero ATR skip, invalid structure check

## Decisions Made
- Extended _call_gemini_with_retry with keyword-only params (after `*`) so existing 4 callers pass defaults unchanged
- Used batch_size_override parameter instead of mutating self.batch_size — scoped to single call, no shared state
- _validate_trading_signal placed at module level (pure function) for direct test imports without async setup
- Vietnamese system instruction follows CONTEXT.md guidance: BEARISH = "giảm vị thế" or "tránh mua", NOT short-selling
- Invalid signals stored with score=0 and reasoning="Validation failed: {reason}" rather than silently dropped

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed edge case test for exactly 5% boundary**
- **Found during:** Task 2 (validation tests)
- **Issue:** Test set entry=86100 (exactly 5% above 82000) but left default sl=79500 which is 6600 from entry, exceeding 3×ATR (6000) with ATR=2000
- **Fix:** Adjusted test to use sl=82000 (within 3×ATR bound) alongside the edge-case entry
- **Files modified:** backend/tests/test_trading_signal_validation.py
- **Verification:** All 8 tests pass
- **Committed in:** 2ba7dd4

---

**Total deviations:** 1 auto-fixed (1 bug in test)
**Impact on plan:** Test data fix only — no logic changes, no scope creep.

## Issues Encountered
None — plan executed smoothly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Trading signal service core complete — ready for Plan 03 (scheduler integration + API endpoint)
- All 5 analysis types now have context gathering, prompt building, batch analysis, and storage
- Post-validation ensures Gemini's price targets are grounded against real indicator data

---
*Phase: 19-ai-trading-signal-pipeline*
*Completed: 2026-04-20*

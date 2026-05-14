---
phase: 96-data-quality-test-stability
plan: "02"
subsystem: testing
tags: [unit-tests, simulator, pick-pipeline, pure-functions]
dependency_graph:
  requires: []
  provides: [simulator-unit-tests, pick-pipeline-unit-tests]
  affects: [backend/tests/]
tech_stack:
  added: []
  patterns: [pure-function-testing, no-db-mocking]
key_files:
  created:
    - backend/tests/test_simulator_service.py
    - backend/tests/test_pick_pipeline.py
  modified: []
decisions:
  - "Pure function tests only — no DB fixtures needed for these service modules"
metrics:
  duration: "3m"
  completed: "2026-05-14"
---

# Phase 96 Plan 02: Simulator Service + Pick Pipeline Unit Tests Summary

**One-liner:** 39 pure-function unit tests covering simulator fee/FIFO math and pick pipeline extraction/outcome/safety/sizing/rejection logic.

## What Was Done

### Task 1: Simulator Service Unit Tests (16 tests)
- **TestCalculateBuyFee** (5 tests): standard calc, odd numbers, small trade, rounding, large trade
- **TestCalculateSellFees** (4 tests): returns tuple, standard calc, independent rates, small values
- **TestFifoMatch** (7 tests): exact match, FIFO ordering, partial match, insufficient raises ValueError, total cost calc, empty lots

### Task 2: Pick Pipeline Unit Tests (23 tests)
- **TestExtractTradingPlan** (5 tests): unified format, defaults, single-direction, legacy dual-direction, missing fields
- **TestComputePickOutcome** (7 tests): stop loss hit, TP1 hit, TP2 hit, expired after 10 days, pending empty, pending not enough days, unsorted closes
- **TestComputeSafetyScore** (3 tests): safe stock high score, risky stock low score, 0-10 range
- **TestComputePositionSizing** (4 tests): normal sizing, 30% cap, minimum 1 lot, 100-share alignment
- **TestGenerateRejectionReason** (5 tests): RSI overbought, high volatility, weak trend, low volume, fallback composite

## Commits

| Hash | Message |
|------|---------|
| ef6dcc6 | test(96-02): add simulator and pick pipeline unit tests |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None.

## Self-Check: PASSED

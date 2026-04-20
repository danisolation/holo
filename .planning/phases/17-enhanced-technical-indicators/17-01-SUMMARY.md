---
phase: 17-enhanced-technical-indicators
plan: "01"
subsystem: backend-indicators
tags: [technical-indicators, ATR, ADX, stochastic, ta-library, migration]
dependency_graph:
  requires: []
  provides:
    - "18-indicator computation pipeline (ATR/ADX/Stochastic added)"
    - "Migration 010 with 6 new Numeric(12,4) columns"
    - "API GET /api/analysis/{symbol}/indicators serves 18 fields"
  affects:
    - "backend/app/services/indicator_service.py"
    - "backend/app/models/technical_indicator.py"
    - "backend/app/schemas/analysis.py"
    - "backend/app/api/analysis.py"
tech_stack:
  added: []
  patterns:
    - "ATR/ADX warm-up 0.0→NaN replacement before storage"
    - "3-arg _compute_indicators(close, high, low) signature"
key_files:
  created:
    - backend/alembic/versions/010_enhanced_indicators.py
  modified:
    - backend/tests/test_indicator_service.py
    - backend/app/models/technical_indicator.py
    - backend/app/services/indicator_service.py
    - backend/app/schemas/analysis.py
    - backend/app/api/analysis.py
decisions:
  - "ATR/ADX/+DI/-DI 0.0 warm-up replaced with NaN via .replace(0.0, float('nan')) — prevents misleading flat lines at zero on charts"
  - "Stochastic already produces NaN during warm-up — no replacement needed"
  - "_compute_indicators extended to 3-arg (close, high, low) — backwards incompatible but all callers updated"
metrics:
  duration: "4.1m"
  completed: "2026-04-20T03:26:22Z"
  tasks_completed: 3
  tasks_total: 3
  test_count: 13
  full_suite: 400
---

# Phase 17 Plan 01: Backend (tests + migration + indicators + API) Summary

**One-liner:** ATR(14), ADX(14) with ±DI, and Stochastic(14,3) added to 18-indicator computation pipeline with warm-up NaN handling, migration 010, and full API exposure.

## Tasks Completed

| # | Task | Commit | Key Changes |
|---|------|--------|-------------|
| 1 | TDD RED: Tests for 18 indicators + warm-up | `ba001c9` | 8 test methods covering 18-key dict, ATR/ADX/Stochastic warm-up NaN, high/low params, schema fields |
| 2 | Migration 010 + Model + Service (GREEN) | `dd668b3` | Migration 010 (6 columns), model attrs, 3-arg `_compute_indicators`, AverageTrueRange/ADXIndicator/StochasticOscillator |
| 3 | Schema + API response mapping | `35e93a8` | 6 new fields on IndicatorResponse, 6 new Decimal→float mappings in API endpoint |

## Verification Results

- `pytest tests/test_indicator_service.py -x` → **13/13 passed**
- `pytest tests/ -x` → **400/400 passed** (0 regressions)
- Migration 010 exists with `revision: str = "010"` and `down_revision: "009"`
- `grep -c "atr_14|adx_14|stoch_k_14" backend/app/api/analysis.py` → 3 matches
- `replace(0.0, float` count in service → 4 (atr, adx, plus_di, minus_di)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all indicators fully wired from computation through API response.

## Key Implementation Details

### Warm-up NaN Handling (Critical)
The `ta` library's `AverageTrueRange` and `ADXIndicator` classes produce `0.0` during warm-up periods instead of `NaN`. This differs from RSI/MACD/SMA which correctly produce `NaN`. Without `.replace(0.0, float('nan'))`, these zeros would be stored as `Decimal('0')` and rendered as misleading flat lines at zero on charts. Four replace calls cover: `atr_14`, `adx_14`, `plus_di_14`, `minus_di_14`.

`StochasticOscillator` already produces proper `NaN` during warm-up — no replacement needed.

### Warm-up Periods
| Indicator | Warm-up Rows (NaN) |
|-----------|-------------------|
| ATR(14) | 13 |
| ADX(14) | 27 |
| +DI/-DI(14) | 15 |
| Stochastic %K(14) | 13 |
| Stochastic %D(14,3) | 15 |

## Self-Check: PASSED

- [x] `backend/alembic/versions/010_enhanced_indicators.py` exists
- [x] `backend/app/models/technical_indicator.py` has 6 new columns
- [x] `backend/app/services/indicator_service.py` has 18-indicator computation
- [x] `backend/app/schemas/analysis.py` has 18 fields
- [x] `backend/app/api/analysis.py` maps 18 fields
- [x] Commit `ba001c9` exists
- [x] Commit `dd668b3` exists
- [x] Commit `35e93a8` exists

---
phase: 17
slug: enhanced-technical-indicators
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-20
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 with pytest-asyncio |
| **Config file** | `backend/pytest.ini` (asyncio_mode = auto) |
| **Quick run command** | `cd backend && .venv/Scripts/python.exe -m pytest tests/test_indicator_service.py -x` |
| **Full suite command** | `cd backend && .venv/Scripts/python.exe -m pytest tests/ -x` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && .venv/Scripts/python.exe -m pytest tests/test_indicator_service.py -x`
- **After every plan wave:** Run `cd backend && .venv/Scripts/python.exe -m pytest tests/ -x`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 17-01-01 | 01 | 1 | SIG-01 | — | N/A | unit | `pytest tests/test_indicator_service.py::TestComputeIndicators::test_returns_18_indicators -x` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | SIG-01 | — | N/A | unit | `pytest tests/test_indicator_service.py::TestComputeIndicators::test_atr_warmup_is_nan -x` | ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 1 | SIG-02 | — | N/A | unit | `pytest tests/test_indicator_service.py::TestComputeIndicators::test_adx_series_valid -x` | ❌ W0 | ⬜ pending |
| 17-01-04 | 01 | 1 | SIG-02 | — | N/A | unit | `pytest tests/test_indicator_service.py::TestComputeIndicators::test_adx_warmup_is_nan -x` | ❌ W0 | ⬜ pending |
| 17-01-05 | 01 | 1 | SIG-03 | — | N/A | unit | `pytest tests/test_indicator_service.py::TestComputeIndicators::test_stochastic_series_valid -x` | ❌ W0 | ⬜ pending |
| 17-01-06 | 01 | 1 | ALL | — | N/A | unit | `pytest tests/test_indicator_service.py::TestIndicatorResponseSchema -x` | ❌ W0 | ⬜ pending |
| 17-01-07 | 01 | 1 | ALL | — | N/A | unit | `pytest tests/test_indicator_service.py::TestComputeIndicators::test_compute_indicators_requires_high_low -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Update `test_returns_12_indicators` → `test_returns_18_indicators` with 6 new keys
- [ ] Add `test_atr_warmup_is_nan` — verify ATR warm-up 0.0 replaced with NaN
- [ ] Add `test_adx_warmup_is_nan` — verify ADX/+DI/-DI warm-up 0.0 replaced with NaN
- [ ] Add `test_stochastic_warmup_produces_nan` — verify %K NaN for first 13 rows, %D for first 15
- [ ] Add `test_compute_indicators_requires_high_low` — verify new signature works with high/low Series
- [ ] Update `test_series_length_matches_input` to include high/low params

*Existing infrastructure covers framework — only test file updates needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Chart renders correctly with real data | SIG-01,02,03 | Visual chart rendering | Open /ticker/VNM, verify ATR/ADX/Stochastic charts display in accordion |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

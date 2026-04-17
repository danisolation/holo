---
phase: 12
slug: multi-market-foundation
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-17
---
# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with asyncio_mode=auto |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest tests/ -x --tb=short -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x --tb=short -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | MKT-01 | — | N/A | unit | `pytest tests/test_ticker_service_multi.py -x` | ❌ W0 | ⬜ pending |
| 12-01-02 | 01 | 1 | MKT-02 | — | Validate exchange enum | unit | `pytest tests/test_api.py -x -k exchange` | ❌ W0 | ⬜ pending |
| 12-01-03 | 01 | 1 | MKT-03 | — | N/A | unit | `pytest tests/test_scheduler.py -x -k exchange` | ❌ W0 | ⬜ pending |
| 12-01-04 | 01 | 1 | MKT-04 | — | N/A | unit | `pytest tests/test_ai_analysis_tiered.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_ticker_service_multi.py` — stubs for MKT-01, MKT-03 (exchange-parameterized sync, deactivation scoping)
- [ ] `tests/test_ai_analysis_tiered.py` — stubs for MKT-04 (tiered analysis, on-demand, budget cap)
- [ ] Add exchange filter tests to existing `tests/test_api.py` — covers MKT-02
- [ ] Add exchange-parameterized job tests to existing `tests/test_scheduler.py` — covers MKT-03

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| HNX/UPCOM tickers visible in dashboard | MKT-01, MKT-02 | Requires browser + visual check of exchange tabs/badges | Open dashboard → verify exchange filter tabs → switch between HOSE/HNX/UPCOM/All → check badge colors |
| Heatmap exchange borders render correctly | MKT-02 | Canvas rendering — visual check | Open heatmap → verify colored borders per exchange |
| On-demand "Analyze now" button works | MKT-04 | Requires Gemini API call + UI interaction | Navigate to non-watchlisted HNX ticker → click Analyze now → verify loading/success states |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

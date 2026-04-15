---
phase: 1
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | backend/pytest.ini or "none — Wave 0 installs" |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | DATA-01 | — | N/A | unit | `python -m pytest tests/test_models.py` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | DATA-01 | — | N/A | unit | `python -m pytest tests/test_config.py` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 1 | DATA-01 | — | N/A | integration | `python -m pytest tests/test_crawl_service.py` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 1 | DATA-04 | — | N/A | integration | `python -m pytest tests/test_financial_crawl.py` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 2 | DATA-03 | — | N/A | integration | `python -m pytest tests/test_backfill.py` | ❌ W0 | ⬜ pending |
| 01-04-01 | 04 | 2 | DATA-02 | — | N/A | unit | `python -m pytest tests/test_scheduler.py` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/conftest.py` — shared fixtures, DB session factory
- [ ] `backend/tests/test_models.py` — stubs for DATA-01 model tests
- [ ] `backend/tests/test_config.py` — stubs for config validation
- [ ] `backend/tests/test_crawl_service.py` — stubs for crawl service
- [ ] `pytest` — install in requirements

*If none: "Existing infrastructure covers all phase requirements."*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Daily crawl fires at 15:30 UTC+7 | DATA-02 | Requires waiting for scheduled time | Set scheduler to 1-min interval, verify job fires and data appears in DB |
| vnstock API returns real data | DATA-01 | External service dependency | Run backfill for 1 ticker, verify OHLCV rows in PostgreSQL |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

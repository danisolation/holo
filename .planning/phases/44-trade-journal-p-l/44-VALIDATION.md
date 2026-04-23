---
phase: 44
slug: trade-journal-p-l
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-23
---

# Phase 44 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), Next.js build (frontend) |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && python -m pytest tests/test_trade_service.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_trade_service.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 44-01-01 | 01 | 1 | JRNL-01 | unit | `pytest tests/test_trade_service.py -k "test_create_buy"` | ❌ W0 | ⬜ pending |
| 44-01-02 | 01 | 1 | JRNL-02 | unit | `pytest tests/test_trade_service.py -k "test_fifo"` | ❌ W0 | ⬜ pending |
| 44-01-03 | 01 | 1 | JRNL-02 | unit | `pytest tests/test_trade_service.py -k "test_fee_calc"` | ❌ W0 | ⬜ pending |
| 44-01-04 | 01 | 1 | JRNL-03 | unit | `pytest tests/test_trade_service.py -k "test_pick_link"` | ❌ W0 | ⬜ pending |
| 44-02-01 | 02 | 2 | JRNL-01 | integration | `pytest tests/test_trade_service.py -k "test_create_sell"` | ❌ W0 | ⬜ pending |
| 44-02-02 | 02 | 2 | JRNL-02 | unit | `pytest tests/test_trade_service.py -k "test_delete_reversal"` | ❌ W0 | ⬜ pending |
| 44-03-01 | 03 | 3 | JRNL-01 | build | `cd frontend && npm run build` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_trade_service.py` — stubs for JRNL-01, JRNL-02, JRNL-03
- [ ] Existing `backend/tests/conftest.py` — shared fixtures already exist

*Existing test infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Trade form renders correctly | JRNL-01 | Visual layout verification | Open /journal, click "Ghi lệnh", verify form fields render |
| Pick auto-suggest appears | JRNL-03 | Requires recent daily pick data | Create a daily pick, open trade form, select same ticker |
| Color coding (green/red/neutral) | JRNL-02 | Visual verification | Create BUY+SELL trades, verify P&L colors in table |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

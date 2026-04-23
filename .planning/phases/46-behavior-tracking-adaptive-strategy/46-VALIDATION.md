---
phase: 46
slug: behavior-tracking-adaptive-strategy
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-23
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), Next.js build (frontend) |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && python -m pytest tests/test_behavior_service.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 20 seconds

---

## Wave 0 Requirements

- [ ] `backend/tests/test_behavior_service.py` — stubs for viewing stats, habit detection, consecutive loss check, sector preferences
- [ ] Existing test infrastructure covers framework requirements

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Viewing stats display | BEHV-01 | Visual layout | View tickers, check "Mã bạn hay xem" shows counts |
| Habit badges render | BEHV-02 | Visual verification | Create trades matching patterns, check habit card |
| Risk banner UX | ADPT-01 | Interactive flow | Trigger 3 losses, verify banner appears with accept/reject buttons |
| Sector preferences display | ADPT-02 | Requires trade data | Create trades in multiple sectors, verify ranked list |
| Sector bias in picks | ADPT-02 | End-to-end flow | Verify picks favor profitable sectors after preference refresh |

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Sampling continuity maintained
- [ ] Wave 0 covers all MISSING references
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

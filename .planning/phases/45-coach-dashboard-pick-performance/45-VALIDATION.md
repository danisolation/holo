---
phase: 45
slug: coach-dashboard-pick-performance
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-23
---

# Phase 45 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), Next.js build (frontend) |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && python -m pytest tests/test_pick_outcome.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Wave 0 Requirements

- [ ] `backend/tests/test_pick_outcome.py` — stubs for outcome computation, performance stats
- [ ] Existing test infrastructure covers framework requirements

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Unified coach page layout | CDSH-01 | Visual layout | Open /coach, verify 4 sections visible |
| Outcome badges color | CDSH-02 | Visual verification | Check Thắng/Thua/Hết hạn badges render correctly |
| Performance cards values | CDSH-03 | Requires real data | Create picks + trades, verify card calculations |

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Sampling continuity maintained
- [ ] Wave 0 covers all MISSING references
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

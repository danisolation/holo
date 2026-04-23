---
phase: 47
slug: goals-weekly-reviews
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-23
---

# Phase 47 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend), Next.js build (frontend) |
| **Config file** | backend/pytest.ini |
| **Quick run command** | `cd backend && python -m pytest tests/test_goals_service.py -x -q` |
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

- [ ] `backend/tests/test_goals_service.py` — stubs for goal CRUD, weekly prompt, review generation
- [ ] Existing test infrastructure covers framework requirements

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Progress bar colors | GOAL-01 | Visual verification | Set goal, create trades, verify green/amber/red thresholds |
| Weekly prompt card render | GOAL-02 | Visual + interaction | Wait for Monday prompt, test all 3 response buttons |
| AI review Vietnamese quality | GOAL-03 | Content quality | Generate review, verify Vietnamese narrative is coherent |
| Coach page layout order | All | Visual layout | Verify sections appear in correct order on /coach |

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] Sampling continuity maintained
- [ ] Wave 0 covers all MISSING references
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

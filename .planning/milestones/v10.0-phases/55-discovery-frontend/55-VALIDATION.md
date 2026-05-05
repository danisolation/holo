---
phase: 55
slug: discovery-frontend
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-04
---

# Phase 55 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Playwright 1.59.1 |
| **Config file** | `frontend/playwright.config.ts` |
| **Quick run command** | `cd frontend && npx playwright test e2e/page-smoke.spec.ts --project=chromium` |
| **Full suite command** | `cd frontend && npx playwright test --project=chromium` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd frontend && npx playwright test e2e/page-smoke.spec.ts --project=chromium`
- **After every plan wave:** Run `cd frontend && npx playwright test --project=chromium`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 55-01-01 | 01 | 1 | DPAGE-01 | — | N/A | e2e smoke | `npx playwright test e2e/page-smoke.spec.ts` | ❌ W0 | ⬜ pending |
| 55-01-02 | 01 | 1 | DPAGE-02 | — | N/A | e2e interaction | `npx playwright test e2e/interact-discovery.spec.ts` | ❌ W0 | ⬜ pending |
| 55-01-03 | 01 | 1 | DPAGE-03 | — | N/A | e2e interaction | `npx playwright test e2e/interact-discovery.spec.ts` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Add `/discovery` to `APP_ROUTES` in `e2e/fixtures/test-helpers.ts` — covers DPAGE-01 smoke
- [ ] `e2e/interact-discovery.spec.ts` — covers DPAGE-02, DPAGE-03
- [ ] Backend smoke: ensure GET `/api/discovery` returns 200 (add to `api-smoke.spec.ts`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Score bars render with correct colors | DPAGE-01 | Visual rendering | Open /discovery, verify teal/amber/red bars match score thresholds |
| Daily update freshness | DPAGE-01 | Requires pipeline run | Run pipeline, verify scores update on page |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

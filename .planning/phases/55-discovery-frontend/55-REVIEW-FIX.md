---
phase: 55-discovery-frontend
fixed_at: 2025-01-28T12:30:00Z
review_path: .planning/phases/55-discovery-frontend/55-REVIEW.md
iteration: 1
findings_in_scope: 2
fixed: 2
skipped: 0
status: all_fixed
---

# Phase 55: Code Review Fix Report

**Fixed at:** 2025-01-28T12:30:00Z
**Source review:** .planning/phases/55-discovery-frontend/55-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 2
- Fixed: 2
- Skipped: 0

## Fixed Issues

### WR-01: Page header badge shows unfiltered count while table is filtered

**Files modified:** `frontend/src/app/discovery/page.tsx`, `frontend/src/components/discovery-table.tsx`
**Commit:** 13c9bd2
**Applied fix:** Removed the duplicate `useDiscovery()` call from `page.tsx` (along with the `"use client"` directive and unused imports since the component no longer needs client-side hooks). Simplified `page.tsx` to only render the heading and `<DiscoveryTable />`. Moved the result count badge (`{n} mã`) and score date display into `discovery-table.tsx` where they now use the already-fetched filtered data, ensuring the count and date always match the currently displayed filtered results.

### WR-02: Flaky e2e test uses hardcoded timeout instead of condition-based wait

**Files modified:** `frontend/e2e/interact-discovery.spec.ts`
**Commit:** f583515
**Applied fix:** Replaced `page.waitForTimeout(3000)` with a condition-based wait that checks for the skeleton loading indicator (`.space-y-2 .animate-pulse`) to become hidden, with a 10-second timeout. This makes the test wait for the actual loading state transition rather than an arbitrary delay, eliminating flakiness from variable network/server speed.

---

_Fixed: 2025-01-28T12:30:00Z_
_Fixer: the agent (gsd-code-fixer)_
_Iteration: 1_

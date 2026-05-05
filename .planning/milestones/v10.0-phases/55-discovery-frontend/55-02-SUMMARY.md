---
phase: 55-discovery-frontend
plan: 02
subsystem: discovery-page-ui
tags: [discovery, react-table, shadcn, e2e]
dependency_graph:
  requires: [useDiscovery hook, DiscoveryItem type, fetchDiscovery, SectorCombobox]
  provides: [/discovery page route, DiscoveryTable component, navbar Khám phá link, discovery E2E tests]
  affects: [frontend navigation, page-smoke tests]
tech_stack:
  added: []
  patterns: [ScoreCell bar with threshold colors, column meta className for responsive hiding, isStaleData business-day check]
key_files:
  created:
    - frontend/src/components/discovery-table.tsx
    - frontend/src/app/discovery/page.tsx
    - frontend/e2e/interact-discovery.spec.ts
  modified:
    - frontend/src/components/navbar.tsx
    - frontend/e2e/fixtures/test-helpers.ts
decisions:
  - "Used native HTML <select> for signal filter instead of shadcn Select — project uses base-ui not radix, simpler and reliable"
  - "Score bar thresholds: ≥7 green (#26a69a), ≥4 amber, <4 red (#ef5350) — matches existing color scheme"
  - "Button size xs for compact table actions — fits 80px column width constraint"
metrics:
  duration: ~3 min
  completed: 2026-05-04
---

# Phase 55 Plan 02: Discovery Page UI Summary

**One-liner:** Discovery page at /discovery with scored ticker table (ScoreCell bars, sector/signal filters, add-to-watchlist buttons), responsive column hiding, empty/error/stale states, and 4 E2E interaction tests

## What Was Built

### Task 1: DiscoveryTable component, Discovery page, and navbar link
- Created `frontend/src/components/discovery-table.tsx` (310+ lines):
  - ScoreCell with green/amber/red progress bars based on score thresholds
  - 11 columns: Mã, Tên, Ngành, Điểm, RSI, MACD, ADX, Volume, P/E, ROE, Action
  - Responsive column hiding via meta.className (md/lg/xl breakpoints)
  - SectorCombobox reuse for sector filter, native `<select>` for signal type filter
  - Watchlist integration: "Thêm"/"Đã thêm" buttons with stopPropagation
  - Default sort by total_score descending
  - Row click navigation to /ticker/{symbol}
  - Empty states: no data (SearchX), filtered empty (FilterX), error
  - Stale data warning badge when score_date > 1.5 days old
- Created `frontend/src/app/discovery/page.tsx`:
  - Page heading "Khám phá cổ phiếu" with count badge and formatted score_date subtitle
  - Renders DiscoveryTable component
- Modified `frontend/src/components/navbar.tsx`:
  - Added `{ href: "/discovery", label: "Khám phá" }` after Tổng quan in NAV_LINKS

### Task 2: E2E test updates for Discovery page
- Modified `frontend/e2e/fixtures/test-helpers.ts`:
  - Added `{ path: '/discovery', name: 'Discovery' }` to APP_ROUTES for smoke test coverage
- Created `frontend/e2e/interact-discovery.spec.ts` with 4 tests:
  - Page renders with heading and data-testid
  - Table renders or shows empty state
  - Signal filter dropdown exists
  - Navbar contains Khám phá link pointing to /discovery

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | f2f692b | feat(55-02): add DiscoveryTable component, Discovery page, and navbar link |
| 2 | a41c06a | test(55-02): add Discovery page E2E tests and route to smoke tests |

## Deviations from Plan

None — plan executed exactly as written.

## Threat Mitigations Applied

| Threat ID | Disposition | Notes |
|-----------|-------------|-------|
| T-55-04 | accept | Symbol from backend response used in router.push — same pattern as watchlist-table |
| T-55-05 | accept | Single-user app, no auth — same exposure as existing watchlist page |

## Self-Check: PASSED

- [x] `frontend/src/components/discovery-table.tsx` exists with DiscoveryTable export
- [x] `frontend/src/app/discovery/page.tsx` exists with data-testid="discovery-page"
- [x] `frontend/src/components/navbar.tsx` contains "/discovery" link
- [x] `frontend/e2e/fixtures/test-helpers.ts` contains /discovery route
- [x] `frontend/e2e/interact-discovery.spec.ts` exists with 4 tests
- [x] Commit f2f692b exists
- [x] Commit a41c06a exists
- [x] TypeScript compiles with zero errors

---
phase: 43-daily-picks-engine
plan: "03"
title: "Daily Picks Frontend Page"
subsystem: frontend
tags: [react, next-js, coach-page, daily-picks, components, websocket]
dependency_graph:
  requires: [PickService, picks-api-endpoints, DailyPick-model, picks-schemas]
  provides: [coach-page, PickCard-component, AlmostSelectedList-component, ProfileSettingsCard-component, coach-navbar-link]
  affects: [frontend/src/lib/api.ts, frontend/src/lib/hooks.ts, frontend/src/components/navbar.tsx]
tech_stack:
  added: [react-hook-form, zod, "@hookform/resolvers"]
  patterns: [react-query-hooks, zod-form-validation, base-ui-dialog, base-ui-accordion, websocket-live-price]
key_files:
  created:
    - frontend/src/components/pick-card.tsx
    - frontend/src/components/almost-selected-list.tsx
    - frontend/src/components/profile-settings-card.tsx
    - frontend/src/app/coach/page.tsx
  modified:
    - frontend/package.json
    - frontend/src/lib/api.ts
    - frontend/src/lib/hooks.ts
    - frontend/src/components/navbar.tsx
key_decisions:
  - "Used base-ui Dialog render prop pattern (not radix asChild) matching existing project conventions"
  - "Capital input uses formatted display with vi-VN Intl.NumberFormat, parsed to int on submit"
  - "Risk level as 5-button toggle group (1-5) with Vietnamese labels instead of slider for precision"
metrics:
  duration: "4m 44s"
  completed: "2026-04-23T08:57:11Z"
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  files_modified: 4
---

# Phase 43 Plan 03: Daily Picks Frontend Page Summary

Complete /coach page with PickCard (entry/SL/TP + position sizing + WebSocket live price + P&L badge), AlmostSelectedList accordion, ProfileSettingsCard with react-hook-form + zod validation, navbar "Huấn luyện" link — 3 new npm packages, 4 new files, build clean.

## Tasks Completed

### Task 1: Install deps, add API types/hooks, update navbar
- **Commit:** fb016c4
- **Files:** `package.json`, `api.ts`, `hooks.ts`, `navbar.tsx`
- Installed react-hook-form, zod, @hookform/resolvers
- Added 4 TypeScript interfaces: DailyPickResponse, DailyPicksResponse, ProfileResponse, ProfileUpdate
- Added 4 fetch functions: fetchDailyPicks, fetchPickHistory, fetchProfile, updateProfile
- Added 3 React Query hooks: useDailyPicks (5min stale), useProfile (10min stale), useUpdateProfile (invalidates profile + picks)
- Added "Huấn luyện" nav link to /coach in navbar NAV_LINKS array

### Task 2: Create PickCard, AlmostSelectedList, ProfileSettings components
- **Commit:** 188c97a
- **Files:** `pick-card.tsx`, `almost-selected-list.tsx`, `profile-settings-card.tsx`
- PickCard: rank badge, symbol/name, ScoreBar, MUA/Swing badges, Vietnamese explanation, 2-col price grid (Giá vào/Cắt lỗ/Chốt lời 1+2/R:R), position sizing block, live WebSocket price with color-coded P&L badge (▲/▼), aria-label + aria-live accessibility
- AlmostSelectedList: base-ui Accordion, collapsed by default, "Mã suýt được chọn (N mã)" trigger, ticker + rejection reason rows
- ProfileSettingsCard: base-ui Dialog with render prop pattern, react-hook-form + zodResolver, formatted capital input (vi-VN), 5-button risk level toggle with Vietnamese labels, Loader2 spinner on save, error message on failure

### Task 3: Create /coach page and verify build
- **Commit:** e330816
- **Files:** `frontend/src/app/coach/page.tsx`
- CoachPage assembles all components with 4 states:
  - Loading: 3 PickCardSkeleton in responsive grid
  - Error: AlertTriangle + "Không thể tải gợi ý" + retry button
  - Empty: Calendar icon + "Chưa có gợi ý hôm nay" + time note
  - Success: responsive 3-col grid of PickCards + AlmostSelectedList accordion
- Header: "Gợi ý hôm nay" + pick count + capital display + ProfileSettingsCard trigger
- Frontend build passes: /coach route registered as static page

## Verification Results

- ✅ TypeScript compiles: `npx tsc --noEmit` exits 0
- ✅ Frontend builds: `npm run build` — /coach route visible in output
- ✅ All 4 new component files export correctly
- ✅ Navbar contains "Huấn luyện" link to /coach
- ✅ 3 npm packages installed (react-hook-form, zod, @hookform/resolvers)
- ✅ All acceptance criteria from plan met

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all components have complete implementations, all hooks wire to real API endpoints, all states (loading/error/empty/success) implemented.

## Self-Check: PASSED

- All 4 created files verified present on disk
- All 4 modified files verified in git
- Commits fb016c4, 188c97a, and e330816 verified in git log

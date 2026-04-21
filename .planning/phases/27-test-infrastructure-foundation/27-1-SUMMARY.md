---
phase: 27
plan: 1
subsystem: test-infrastructure
tags: [playwright, e2e, testing, infrastructure]
dependency_graph:
  requires: []
  provides: [playwright-config, e2e-smoke-test]
  affects: [frontend/package.json, frontend/.gitignore]
tech_stack:
  added: ["@playwright/test ^1.59.1", "Chromium browser binary"]
  patterns: [dual-webserver-e2e, auto-start-servers]
key_files:
  created:
    - frontend/playwright.config.ts
    - frontend/e2e/smoke.spec.ts
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/.gitignore
decisions:
  - "Playwright 1.59.1 with Chromium-only project (no WebKit on Windows)"
  - "Dual webServer: FastAPI :8001 + Next.js :3000 with auto-start"
  - "HOLO_TEST_MODE env var passed to FastAPI via webServer config"
  - "reuseExistingServer: !process.env.CI for fast local iteration"
  - "HTML reporter with open: never to avoid browser popup"
metrics:
  duration: "2m 10s"
  completed: "2026-04-21"
  tasks: 4
  files_changed: 5
---

# Phase 27 Plan 1: Playwright Installation & Configuration Summary

**One-liner:** Playwright E2E infrastructure with dual webServer (FastAPI :8001 + Next.js :3000) auto-start and Chromium smoke test.

## What Was Done

### Task 1: Install Playwright as devDependency
- Added `@playwright/test ^1.59.1` to `frontend/package.json` devDependencies
- Installed Chromium browser binary (Chrome for Testing 147.0.7727.15)
- Verified: `npx playwright --version` → Version 1.59.1
- **Commit:** `e1e7300`

### Task 2: Create playwright.config.ts with dual webServer
- Created `frontend/playwright.config.ts` with complete configuration
- Dual webServer array: FastAPI on port 8001 (with `cwd: '../backend'`), Next.js on port 3000
- `HOLO_TEST_MODE: 'true'` env var for FastAPI to prevent scheduler/Telegram side effects
- Chromium-only project, HTML reporter with `open: 'never'`
- `reuseExistingServer: !process.env.CI` for fast local dev
- **Commit:** `afc2af5`

### Task 3: Create initial smoke test
- Created `frontend/e2e/smoke.spec.ts` with minimal infrastructure validation test
- Test navigates to `/`, checks title matches `/Holo/`, verifies body visible
- Validates entire stack: both servers start, Next.js serves page, page loads
- **Commit:** `1cdb919`

### Task 4: Update .gitignore for test artifacts
- Appended Playwright-specific ignore patterns to `frontend/.gitignore`
- Patterns: `/test-results/`, `/playwright-report/`, `/blob-report/`, `/playwright/.cache/`, `/e2e/**/*.png`
- **Commit:** `c58723b`

## Deviations from Plan

None — plan executed exactly as written.

## Decisions Made

1. **Playwright 1.59.1** — Latest stable version at time of install
2. **Chromium-only** — No WebKit on Windows, as stated in plan
3. **Port 8001 for FastAPI** — Avoids conflict with default dev server on 8000
4. **Windows paths** — Used `../backend/.venv/Scripts/python` for venv activation

## Known Stubs

None — all files are fully functional configuration/test code.

## Verification

- [x] `frontend/package.json` devDependencies contains `@playwright/test`
- [x] `npx playwright --version` outputs 1.59.1
- [x] `frontend/playwright.config.ts` contains dual webServer array
- [x] `frontend/playwright.config.ts` contains port 8001, HOLO_TEST_MODE, reuseExistingServer
- [x] `frontend/e2e/smoke.spec.ts` exists with proper Playwright test
- [x] `frontend/.gitignore` contains test-results, playwright-report, playwright/.cache

## Self-Check: PASSED

All 5 files verified present. All 4 commit hashes verified in git log.

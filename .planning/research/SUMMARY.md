# Research Summary: Holo v5.0 — E2E Testing & Quality Assurance

**Domain:** E2E Testing Infrastructure for Vietnamese Stock Intelligence Platform
**Researched:** 2025-07-21
**Overall confidence:** HIGH

## Executive Summary

Playwright v1.59.1 is the clear and only choice for E2E testing of Holo's Next.js 16 + FastAPI stack. The framework has matured to the point where it eliminates the need for multiple supporting libraries — built-in `toHaveScreenshot()` replaces SaaS visual regression tools (Argos, Percy, Chromatic), built-in `APIRequestContext` replaces HTTP testing libraries (supertest, axios), and built-in `webServer` config replaces server management utilities (start-server-and-test, wait-on, concurrently). The entire E2E testing stack is essentially one devDependency: `@playwright/test`.

The main technical challenge is the dual-server architecture (FastAPI on Python + Next.js on Node.js). Playwright's `webServer` array config handles this natively, but getting both servers starting reliably — especially with Python venv activation on Windows vs Linux — requires careful initial setup. This should be the very first phase task with validation before any test writing begins.

Visual regression is the highest-value testing capability for Holo because the most complex UI components (candlestick charts via lightweight-charts, technical indicator overlays, heatmap) render to canvas and are invisible to DOM assertions. `toHaveScreenshot()` is the only reliable way to verify chart rendering. However, live financial data means every screenshot test MUST mask dynamic data areas to avoid daily false positives.

The existing 560 backend pytest tests provide excellent API coverage. Playwright API tests should be integration-level smoke tests only — verify endpoints respond with correct shapes, not duplicate edge case testing. The real value of Playwright is testing what pytest cannot: browser rendering, user flows across pages, visual layout, and the integration between frontend and backend.

## Key Findings

**Stack:** Single devDependency `@playwright/test@^1.59.1` covers E2E, visual regression, and API testing. Optional additions: `@axe-core/playwright` for accessibility, `@faker-js/faker` for test data.

**Architecture:** Three-layer test structure — API smoke tests (no browser), page-level tests (per-route), and multi-page flow tests. All using Playwright's `webServer` to manage both FastAPI and Next.js lifecycle.

**Critical pitfall:** Live financial data causes flaky tests if asserting on specific values. Every assertion must be structure/presence-based, and every visual regression screenshot must mask price/volume areas.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Foundation & Setup** — Get Playwright installed, both servers starting via `webServer`, one smoke test passing
   - Addresses: Playwright config, `data-testid` attributes on key components, `.gitignore` updates
   - Avoids: Pitfall 5 (server startup), Pitfall 10 (browser install), Pitfall 11 (.env.test)

2. **Page Smoke Tests + API Health Checks** — Every route loads, every API endpoint responds
   - Addresses: Table stakes coverage, bug discovery through basic page loads
   - Avoids: Pitfall 6 (over-testing API), Pitfall 2 (don't try DOM assertions on charts)

3. **Visual Regression** — Screenshot-based testing for key pages and chart components
   - Addresses: Chart rendering validation, layout regression detection
   - Avoids: Pitfall 4 (stability measures), Pitfall 9 (screenshot overload), Pitfall 1 (mask dynamic data)

4. **Critical User Flows + Bug Discovery** — Multi-page journeys, edge cases, error states
   - Addresses: Signal-to-trade flow verification, empty state testing, error handling
   - Avoids: Pitfall 1 (live data flakiness), Pitfall 8 (test data cleanup)

5. **Polish & CI Readiness** — Optimize for CI, finalize reporters, document test patterns
   - Addresses: CI configuration, test parallelism, documentation
   - Avoids: Pitfall 12 (artifact bloat in git)

**Phase ordering rationale:**
- Phase 1 MUST be first — nothing works without reliable server startup. This is the #1 failure point.
- Phase 2 before Phase 3 — smoke tests validate that pages load before we try to screenshot them.
- Phase 3 before Phase 4 — visual regression setup (stability helpers, masking patterns) informs how flow tests handle assertions.
- Phase 5 last — optimization only makes sense once the test suite exists and works.

**Research flags for phases:**
- Phase 1: May need deeper research on Windows vs Linux venv paths for `webServer` command — test early
- Phase 3: Visual regression threshold tuning is empirical — expect iteration on `maxDiffPixelRatio` values
- Phase 4: Standard patterns, unlikely to need research

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified via npm registry 2025-07-21. Playwright 1.59.1 is current stable. |
| Features | HIGH | Feature landscape based on project analysis (routes, components, API endpoints). Clear scope from PROJECT.md. |
| Architecture | HIGH | Playwright `webServer`, test organization, fixture patterns are well-documented and standard. |
| Pitfalls | HIGH | Pitfalls derived from project-specific characteristics (live data, canvas charts, dual-server, WebSocket) — highly relevant, not generic. |

## Gaps to Address

- **Windows-specific `webServer` command**: FastAPI venv activation differs on Windows (`.venv/Scripts/python`) vs Linux (`.venv/bin/python`). May need platform-conditional config or a wrapper script. Test empirically in Phase 1.
- **Test database strategy**: Research assumes tests run against real Aiven DB (read-heavy). If write tests cause issues, may need a test database strategy later — but defer unless problems arise.
- **Next.js 16 specific Playwright patterns**: PROJECT.md says Next.js 16 (package.json shows 16.2.3). No known breaking changes for Playwright integration vs Next.js 15, but monitor for edge cases with App Router + React 19 server components.
- **`data-testid` inventory**: Exact list of components needing `data-testid` attributes will emerge during Phase 1-2 implementation, not during research.

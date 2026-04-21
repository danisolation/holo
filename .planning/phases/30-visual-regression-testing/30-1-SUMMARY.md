---
phase: 30
plan: 1
subsystem: frontend/e2e
tags: [visual-regression, screenshot, playwright, responsive, charts]
dependency_graph:
  requires: [27-1, 28-1]
  provides: [visual-baselines, chart-verification, mobile-layout-tests]
  affects: [frontend/e2e]
tech_stack:
  added: []
  patterns: [toHaveScreenshot, dynamic-data-masking, viewport-override, canvas-verification]
key_files:
  created:
    - frontend/e2e/visual-pages.spec.ts
    - frontend/e2e/visual-charts.spec.ts
    - frontend/e2e/visual-responsive.spec.ts
  modified: []
decisions:
  - Mask canvas elements in page screenshots (lightweight-charts pixel output is non-deterministic)
  - Mask .font-mono class broadly to cover all numeric price/PnL values across components
  - Use VN stock market color palette selectors ([#26a69a], [#ef5350]) for gain/loss masking
  - Graceful SVG chart assertion — pass when no paper trading data exists (empty state is valid)
  - 5 pages for mobile responsive (exceeds 3-page minimum) to cover all critical routes
metrics:
  duration: 2m 22s
  completed: 2026-04-21
  tasks_completed: 3
  tasks_total: 3
  test_count: 14
  files_created: 3
---

# Phase 30 Plan 1: Visual Regression Tests Summary

**One-liner:** Playwright visual regression suite with screenshot baselines for 5 pages, canvas/SVG chart verification, and mobile 375px responsive layout tests with comprehensive dynamic data masking.

## What Was Built

### Task 1: Screenshot Baselines (visual-pages.spec.ts)
5 full-page screenshot tests with `toHaveScreenshot()`:
- **Homepage** — Market overview heatmap with exchange filter
- **Ticker detail** (`/ticker/VNM`) — Candlestick chart, indicators, analysis cards
- **Paper Trading** — Overview tab with stat cards
- **Portfolio** — Holdings, performance chart, allocation
- **Watchlist** — Watchlist table with exchange filter

All use shared `screenshotOpts()` with:
- `animations: 'disabled'` — prevents CSS animation flakiness
- `maxDiffPixelRatio: 0.05` — 5% tolerance for rendering diffs
- `fullPage: true` — captures below-fold content
- Dynamic masks: price colors (`#26a69a`, `#ef5350`), `.font-mono` values, `canvas`, `time` elements, skeleton loaders, price flash cells

### Task 2: Chart Rendering Verification (visual-charts.spec.ts)
4 tests covering two chart libraries:
- **Candlestick canvas** — Verifies `<canvas>` inside `[data-testid="ticker-chart"]` has non-zero `width` and `height` attributes
- **Chart container screenshot** — Element-level baseline with canvas masked
- **Recharts SVG check** — Navigates to analytics tab, verifies `.recharts-responsive-container svg` elements with non-zero dimensions (graceful empty state fallback)
- **Analytics screenshot** — Element-level baseline of `[data-testid="pt-analytics-content"]`

### Task 3: Mobile Responsive Layout (visual-responsive.spec.ts)
5 tests at iPhone SE viewport (`375×812`):
- **Homepage, Paper Trading, Watchlist, Ticker Detail, Portfolio** — all tested
- **No horizontal overflow** — `scrollWidth <= clientWidth` assertion on every page
- **Mobile nav verification** — Desktop nav (`[data-testid="nav-desktop"]`) hidden, hamburger menu accessible
- **Mobile screenshot baselines** — captured for visual tracking

## Verification Results

| Check | Result |
|-------|--------|
| `npx playwright test --list` shows 14 visual tests | ✅ |
| Screenshot tests use dynamic data masking | ✅ |
| Chart tests verify canvas/SVG existence + dimensions | ✅ |
| Mobile tests use 375px viewport | ✅ |
| `animations: 'disabled'` in all screenshot calls | ✅ |
| `maxDiffPixelRatio: 0.05` in all screenshot calls | ✅ |

## Requirements Coverage

| Requirement | Description | Status |
|-------------|-------------|--------|
| VIS-01 | Screenshot baselines for 5 key pages | ✅ 5 pages covered |
| VIS-02 | Chart canvas verification | ✅ Canvas existence + non-zero dimensions |
| VIS-03 | Dynamic data masking | ✅ Prices, timestamps, percentages masked |
| VIS-04 | Mobile responsive at 375px | ✅ 5 pages, no overflow, nav check |

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 782429b | Screenshot baseline tests for 5 key pages with dynamic data masking |
| 2 | 3c8f1e9 | Chart canvas existence and dimension verification tests |
| 3 | 1d8cdc0 | Mobile viewport responsive layout tests at 375px |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all tests are fully wired with real page navigation, DOM assertions, and screenshot comparisons.

## Self-Check: PASSED

All 3 created files exist on disk. All 3 task commits (782429b, 3c8f1e9, 1d8cdc0) found in git log.

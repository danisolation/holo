---
phase: 30
plan: 1
type: test
wave: 1
depends_on: []
files_modified:
  - frontend/e2e/visual-pages.spec.ts
  - frontend/e2e/visual-charts.spec.ts
  - frontend/e2e/visual-responsive.spec.ts
autonomous: true
requirements: [VIS-01, VIS-02, VIS-03, VIS-04]
---

# Plan 30.1: Visual Regression Tests

<objective>
Create screenshot baseline tests for key pages, verify chart canvas rendering, mask dynamic data areas, and test responsive layout at mobile viewport.
</objective>

<tasks>

<task id="1" type="file">
<title>Create screenshot baseline tests for 5 key pages</title>
<read_first>
- frontend/playwright.config.ts (screenshot config, use settings)
- frontend/e2e/fixtures/test-helpers.ts (APP_ROUTES, TEST_TICKER, navigateAndWait)
- frontend/src/app/dashboard/paper-trading/page.tsx (dynamic data areas to mask)
</read_first>
<action>
Create `frontend/e2e/visual-pages.spec.ts`:

Test VIS-01 + VIS-03: Screenshot baselines for 5 key pages with dynamic data masking.

For each of the 5 pages (Dashboard /, Ticker detail /ticker/VNM, Paper Trading, Portfolio, Watchlist):
1. Navigate to the page
2. Wait for network idle + content load
3. Mask dynamic data areas (prices, timestamps, percentages) using `mask` option in `toHaveScreenshot()`
4. Take screenshot with `await expect(page).toHaveScreenshot('page-name.png', { ... })`

Use these options for all screenshots:
```typescript
{
  animations: 'disabled',
  mask: [
    page.locator('.text-emerald-500, .text-red-500'), // price colors
    page.locator('time, [data-timestamp]'), // timestamps
  ],
  maxDiffPixelRatio: 0.05, // 5% tolerance for rendering differences
  fullPage: true,
}
```

Adapt masks based on actual page structure found when reading source files.
</action>
<verify>
`frontend/e2e/visual-pages.spec.ts` exists with 5 screenshot tests
</verify>
<acceptance_criteria>
- File contains `toHaveScreenshot` calls for 5 pages
- File contains `animations: 'disabled'` option
- File contains `mask:` option with dynamic data locators
- File contains `maxDiffPixelRatio` setting
</acceptance_criteria>
</task>

<task id="2" type="file">
<title>Create chart rendering verification tests</title>
<read_first>
- frontend/src/app/ticker/[symbol]/page.tsx (chart container structure)
- frontend/src/components/paper-trading/pt-analytics-tab.tsx (Recharts chart components)
</read_first>
<action>
Create `frontend/e2e/visual-charts.spec.ts`:

Test VIS-02: Candlestick chart canvas exists with non-zero dimensions.

Tests:
1. Navigate to `/ticker/VNM`
2. Wait for chart to render (network idle + short delay for canvas paint)
3. Verify `<canvas>` element exists inside chart container
4. Verify canvas has non-zero width and height: `await expect(canvas).toHaveAttribute('width')` + check value > 0
5. Optional: Take a screenshot of just the chart container for visual baseline

For Recharts (SVG-based in analytics):
1. Navigate to `/dashboard/paper-trading`, click Analytics tab
2. Verify `<svg>` elements exist within analytics content
3. SVG charts should have non-zero dimensions
</action>
<verify>
`frontend/e2e/visual-charts.spec.ts` exists with canvas verification tests
</verify>
<acceptance_criteria>
- File contains test verifying `<canvas>` element existence inside ticker chart
- File contains width/height non-zero check for canvas
- File uses `[data-testid="ticker-chart"]` to locate chart container
</acceptance_criteria>
</task>

<task id="3" type="file">
<title>Create responsive layout tests at mobile viewport</title>
<read_first>
- frontend/src/components/navbar.tsx (mobile menu - Sheet component, md:hidden/md:flex breakpoints)
</read_first>
<action>
Create `frontend/e2e/visual-responsive.spec.ts`:

Test VIS-04: Key pages render correctly at mobile viewport (375px) without layout breakage.

Use Playwright's viewport override:
```typescript
test.use({ viewport: { width: 375, height: 812 } }); // iPhone SE
```

Tests for mobile viewport:
1. Homepage (/) — renders without horizontal overflow
2. Paper Trading dashboard — renders, tabs may stack vertically
3. Watchlist — renders without content overflow
4. Verify no horizontal scrollbar: `await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)`
5. Verify mobile hamburger menu is visible (md:hidden class on desktop nav means mobile menu shows)
6. Optional: Take mobile screenshots for baseline

Key checks:
- No content extends beyond viewport width
- Mobile navigation (hamburger menu) is accessible
- Tables/charts adapt or scroll within container (not page-level overflow)
</action>
<verify>
`frontend/e2e/visual-responsive.spec.ts` exists with mobile viewport tests
</verify>
<acceptance_criteria>
- File contains `viewport: { width: 375` configuration
- File contains tests for at least 3 pages at mobile width
- File contains horizontal overflow check
</acceptance_criteria>
</task>

</tasks>

<verification>
1. `npx playwright test --list` shows all visual regression tests
2. Screenshot tests use dynamic data masking
3. Chart tests verify canvas/SVG existence with dimensions
4. Mobile tests use 375px viewport
</verification>

<success_criteria>
Addresses VIS-01 (5 page baselines), VIS-02 (chart canvas verification), VIS-03 (dynamic data masking), VIS-04 (mobile responsive).
</success_criteria>

<must_haves>
- Screenshot baselines for 5 key pages
- Dynamic data masking (prices, timestamps)
- Canvas element existence + non-zero dimensions check
- Mobile viewport (375px) layout tests
- animations: 'disabled' to prevent flaky diffs
</must_haves>

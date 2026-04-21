---
phase: 28
plan: 1
type: test
wave: 1
depends_on: []
files_modified:
  - frontend/e2e/page-smoke.spec.ts
  - frontend/e2e/navigation.spec.ts
  - frontend/e2e/theme.spec.ts
autonomous: true
requirements: [SMOKE-01, SMOKE-02, SMOKE-03, SMOKE-04]
---

# Plan 28.1: Page Smoke Tests

<objective>
Write Playwright tests verifying all 8 application routes load successfully, navigation works between pages, key components render on each page, and dark/light theme toggle doesn't break layout.
</objective>

<tasks>

<task id="1" type="file">
<title>Create page smoke tests for all 8 routes</title>
<read_first>
- frontend/e2e/fixtures/test-helpers.ts (APP_ROUTES constant, navigateAndWait, expectNavbarVisible, TEST_TICKER)
- frontend/e2e/infra.spec.ts (existing test pattern)
- frontend/src/components/navbar.tsx (NAV_LINKS for route list)
</read_first>
<action>
Create `frontend/e2e/page-smoke.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';
import { APP_ROUTES, TEST_TICKER, expectNavbarVisible } from './fixtures/test-helpers';

test.describe('Page Smoke Tests', () => {
  for (const route of APP_ROUTES) {
    test(`${route.name} (${route.path}) loads without errors`, async ({ page }) => {
      await page.goto(route.path);
      await expect(page.locator('body')).toBeVisible();
      await expectNavbarVisible(page);
    });
  }

  test(`Ticker detail page (/ticker/${TEST_TICKER}) loads without errors`, async ({ page }) => {
    await page.goto(`/ticker/${TEST_TICKER}`);
    await expect(page.locator('body')).toBeVisible();
    await expect(page.locator('[data-testid="ticker-page"]')).toBeVisible();
  });
});

test.describe('Key Components Render', () => {
  test('Dashboard renders stat cards or content sections', async ({ page }) => {
    await page.goto('/dashboard');
    await expectNavbarVisible(page);
    // Dashboard should have some content (cards, charts, etc.)
    await expect(page.locator('main, [role="main"], .container').first()).toBeVisible();
  });

  test('Paper Trading renders tabs', async ({ page }) => {
    await page.goto('/dashboard/paper-trading');
    await expect(page.locator('[data-testid="pt-tabs"]')).toBeVisible();
    await expect(page.locator('[data-testid="pt-tab-overview"]')).toBeVisible();
  });

  test('Watchlist page renders table', async ({ page }) => {
    await page.goto('/watchlist');
    await expect(page.locator('[data-testid="watchlist-page"]')).toBeVisible();
  });

  test('Ticker detail renders chart container', async ({ page }) => {
    await page.goto(`/ticker/${TEST_TICKER}`);
    await expect(page.locator('[data-testid="ticker-chart"]')).toBeVisible({ timeout: 15000 });
  });

  test('System Health page renders content', async ({ page }) => {
    await page.goto('/dashboard/health');
    await expectNavbarVisible(page);
    await expect(page.locator('main, [role="main"], .container').first()).toBeVisible();
  });

  test('Corporate Events page renders content', async ({ page }) => {
    await page.goto('/dashboard/corporate-events');
    await expectNavbarVisible(page);
    await expect(page.locator('main, [role="main"], .container').first()).toBeVisible();
  });

  test('Portfolio page renders content', async ({ page }) => {
    await page.goto('/dashboard/portfolio');
    await expectNavbarVisible(page);
    await expect(page.locator('main, [role="main"], .container').first()).toBeVisible();
  });
});
```

Key principles:
- Test ALL 8 routes from SMOKE-01
- Use data-testid where available for component rendering (SMOKE-03)
- No specific value assertions (live data)
- Generous timeout for chart container (canvas rendering)
</action>
<verify>
`frontend/e2e/page-smoke.spec.ts` exists and contains tests for all routes
</verify>
<acceptance_criteria>
- File contains `for (const route of APP_ROUTES)` loop testing all 7 basic routes
- File contains test for `/ticker/${TEST_TICKER}` (8th route)
- File contains `[data-testid="pt-tabs"]` assertion for Paper Trading
- File contains `[data-testid="watchlist-page"]` assertion for Watchlist
- File contains `[data-testid="ticker-chart"]` assertion for Ticker detail
</acceptance_criteria>
</task>

<task id="2" type="file">
<title>Create navigation tests</title>
<read_first>
- frontend/src/components/navbar.tsx (NAV_LINKS array, link structure)
- frontend/e2e/fixtures/test-helpers.ts (expectNavbarVisible)
</read_first>
<action>
Create `frontend/e2e/navigation.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';
import { expectNavbarVisible } from './fixtures/test-helpers';

test.describe('Navigation', () => {
  test('Navbar links navigate to correct pages', async ({ page }) => {
    await page.goto('/');
    await expectNavbarVisible(page);

    // Click "Danh mục" (Watchlist) nav link
    await page.locator('[data-testid="nav-desktop"]').getByText('Danh mục').click();
    await expect(page).toHaveURL(/\/watchlist/);

    // Click "Bảng điều khiển" (Dashboard) nav link
    await page.locator('[data-testid="nav-desktop"]').getByText('Bảng điều khiển').click();
    await expect(page).toHaveURL(/\/dashboard/);

    // Click "Paper Trading" nav link
    await page.locator('[data-testid="nav-desktop"]').getByText('Paper Trading').click();
    await expect(page).toHaveURL(/\/dashboard\/paper-trading/);

    // Click back to home "Tổng quan"
    await page.locator('[data-testid="nav-desktop"]').getByText('Tổng quan').click();
    await expect(page).toHaveURL(/^\/$|\/$/);
  });

  test('Navbar is visible on all pages', async ({ page }) => {
    const routes = ['/', '/watchlist', '/dashboard', '/dashboard/paper-trading', '/dashboard/health'];
    for (const route of routes) {
      await page.goto(route);
      await expectNavbarVisible(page);
    }
  });
});
```

Tests SMOKE-02: Navigation between pages works correctly via navbar links.
</action>
<verify>
`frontend/e2e/navigation.spec.ts` exists and contains navigation tests
</verify>
<acceptance_criteria>
- File contains `Navbar links navigate to correct pages` test
- File contains clicks on nav links using `[data-testid="nav-desktop"]`
- File contains URL assertions (`toHaveURL`)
- File contains `Navbar is visible on all pages` test
</acceptance_criteria>
</task>

<task id="3" type="file">
<title>Create theme toggle test</title>
<read_first>
- frontend/src/components/navbar.tsx (theme toggle button with data-testid="theme-toggle")
</read_first>
<action>
Create `frontend/e2e/theme.spec.ts`:

```typescript
import { test, expect } from '@playwright/test';
import { expectNavbarVisible } from './fixtures/test-helpers';

test.describe('Theme Toggle', () => {
  test('Dark/light theme toggle works without breaking layout', async ({ page }) => {
    await page.goto('/');
    await expectNavbarVisible(page);

    // Get initial theme state
    const htmlElement = page.locator('html');

    // Click theme toggle
    await page.locator('[data-testid="theme-toggle"]').click();
    await page.waitForTimeout(500); // Allow transition

    // Verify page still renders correctly
    await expectNavbarVisible(page);
    await expect(page.locator('body')).toBeVisible();

    // Click again to toggle back
    await page.locator('[data-testid="theme-toggle"]').click();
    await page.waitForTimeout(500);

    // Verify still no layout break
    await expectNavbarVisible(page);
    await expect(page.locator('body')).toBeVisible();
  });

  test('Theme persists across page navigation', async ({ page }) => {
    await page.goto('/');

    // Toggle theme
    await page.locator('[data-testid="theme-toggle"]').click();
    await page.waitForTimeout(500);

    // Get current theme class
    const themeAfterToggle = await page.locator('html').getAttribute('class');

    // Navigate to another page
    await page.goto('/watchlist');
    await page.waitForTimeout(500);

    // Theme should persist
    const themeAfterNav = await page.locator('html').getAttribute('class');
    expect(themeAfterNav).toBe(themeAfterToggle);
  });
});
```

Tests SMOKE-04: Dark/light theme toggle doesn't break layout.
</action>
<verify>
`frontend/e2e/theme.spec.ts` exists and contains theme toggle tests
</verify>
<acceptance_criteria>
- File contains `Dark/light theme toggle works without breaking layout` test
- File contains `[data-testid="theme-toggle"]` selector
- File contains `Theme persists across page navigation` test
- File verifies navbar still visible after toggle
</acceptance_criteria>
</task>

</tasks>

<verification>
1. `npx playwright test --list` shows all page smoke, navigation, and theme tests
2. Tests use data-testid selectors (not fragile CSS selectors)
3. No assertions on specific data values (structure only)
</verification>

<success_criteria>
Addresses SMOKE-01 (all 8 routes load), SMOKE-02 (navigation works), SMOKE-03 (key components render), SMOKE-04 (theme toggle).
</success_criteria>

<must_haves>
- All 8 routes tested for successful loading
- Navigation tests using navbar links
- Key component rendering verified per page (tabs, tables, chart containers)
- Theme toggle test verifying no layout breakage
</must_haves>

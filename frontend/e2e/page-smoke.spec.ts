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
});

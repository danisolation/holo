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

import { test, expect } from '@playwright/test';
import { expectNavbarVisible } from './fixtures/test-helpers';

test.describe('Navigation', () => {
  test('Navbar links navigate to correct pages', async ({ page }) => {
    await page.goto('/');
    await expectNavbarVisible(page);

    // Click "Danh mục" (Watchlist) nav link
    await page.locator('[data-testid="nav-desktop"]').getByText('Danh mục').click();
    await expect(page).toHaveURL(/\/watchlist/);

    // Click "Huấn luyện" (Coach) nav link
    await page.locator('[data-testid="nav-desktop"]').getByText('Huấn luyện').click();
    await expect(page).toHaveURL(/\/coach/);

    // Click back to home "Tổng quan"
    await page.locator('[data-testid="nav-desktop"]').getByText('Tổng quan').click();
    await expect(page).toHaveURL(/^\/$|\/$/);
  });

  test('Navbar is visible on all pages', async ({ page }) => {
    const routes = ['/', '/watchlist', '/dashboard/health'];
    for (const route of routes) {
      await page.goto(route);
      await expectNavbarVisible(page);
    }
  });
});

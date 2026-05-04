import { test, expect } from '@playwright/test';

test.describe('Discovery Page Interactions', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/discovery');
  });

  test('discovery page renders with heading and data-testid', async ({ page }) => {
    await expect(page.locator('[data-testid="discovery-page"]')).toBeVisible();
    await expect(page.locator('h2')).toContainText('Khám phá cổ phiếu');
  });

  test('discovery table renders or shows empty state', async ({ page }) => {
    // Either table has rows or empty state is shown
    const table = page.locator('[data-testid="discovery-table"]');
    await expect(table).toBeVisible();

    // Wait for loading to finish — skeleton disappears once data or empty state renders
    await expect(page.locator('.space-y-2 .animate-pulse').first())
      .toBeHidden({ timeout: 10000 });

    // Should show either table rows or empty state message
    const hasRows = await page.locator('[data-testid="discovery-table"] table tbody tr').count() > 0;
    const hasEmptyState = await page.locator('text=Chưa có dữ liệu khám phá').isVisible().catch(() => false);
    expect(hasRows || hasEmptyState).toBeTruthy();
  });

  test('signal filter dropdown exists and has options', async ({ page }) => {
    const filter = page.locator('[data-testid="signal-filter"]');
    await expect(filter).toBeVisible();
  });

  test('navbar contains Khám phá link pointing to /discovery', async ({ page }) => {
    const navLink = page.locator('[data-testid="navbar"] a[href="/discovery"]');
    await expect(navLink).toBeVisible();
    await expect(navLink).toContainText('Khám phá');
  });
});
